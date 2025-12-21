// src/common/utils/sseUtil.ts
import type { Page, Route, Request, APIResponse } from '@playwright/test';

// 定义 SSE 事件的类型
export type SseEvent = {
    data: any;
    event?: string;
    id?: string;
    raw: string;
};

/**
 * 在页面加载前设置 SSE 监听（必须在 page.goto() 之前调用）
 * @param page Playwright 页面实例
 * @param sseUrlPattern SSE 接口 URL 匹配模式（字符串或正则表达式）
 */
export const setupSseListener = async (page: Page, sseUrlPattern: string | RegExp) => {
    const urlPatternStr = typeof sseUrlPattern === 'string'
        ? sseUrlPattern
        : sseUrlPattern.toString();

    // 在页面加载前注入代码，重写 EventSource
    await page.addInitScript((urlPattern) => {
        // 存储事件的全局变量
        (window as any).__playwrightSseEvents = [];

        // 如果已经重写过 EventSource，就不再重复
        if ((window as any).__playwrightSseEventSourcePatched) {
            return;
        }

        // 保存原始的 EventSource
        const OriginalEventSource = window.EventSource;

        // 重写 EventSource 构造函数
        window.EventSource = class extends OriginalEventSource {
            constructor(url: string | URL, eventSourceInitDict?: EventSourceInit) {
                super(url, eventSourceInitDict);

                // 转义特殊字符用于正则表达式
                const escapedPattern = urlPattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const pattern = new RegExp(escapedPattern);
                const urlStr = url.toString();

                if (pattern.test(urlStr)) {
                    const es = this;

                    // 通用的事件捕获函数，根据事件类型动态设置 event 字段
                    const captureEvent = (eventType: string) => {
                        return (event: MessageEvent) => {
                            // 根据事件类型构建 raw 数据
                            const raw = eventType === 'message' 
                                ? `data: ${event.data}\n\n`
                                : `event: ${eventType}\ndata: ${event.data || ''}\n\n`;
                            
                            (window as any).__playwrightSseEvents.push({
                                data: event.data,
                                event: eventType,
                                raw: raw
                            });
                        };
                    };

                    // 保存原始的 onmessage（如果存在），并包装它以确保页面原有逻辑能执行
                    const originalOnMessage = this.onmessage;
                    if (originalOnMessage) {
                        this.onmessage = (event) => {
                            originalOnMessage.call(this, event);
                            // 捕获 message 事件
                            // captureEvent('message')(event);
                        };
                    }

                    // 使用 setTimeout 确保 EventSource 完全初始化后再添加监听器
                    setTimeout(() => {
                        // 监听默认的 message 事件
                        es.addEventListener('message', captureEvent('message'));

                        // 拦截 addEventListener 来动态监听所有事件类型
                        // 这样当页面代码注册事件监听器时，我们也能自动监听相同的事件类型
                        const originalAddEventListener = es.addEventListener.bind(es);
                        const capturedEventTypes = new Set(['message']); // 已捕获的事件类型
                        
                        // 需要忽略的标准事件类型
                        const ignoredEventTypes = new Set(['error', 'open']);
                        
                        es.addEventListener = function(type: string, listener: any, options?: boolean | AddEventListenerOptions) {
                            // 先调用原始的 addEventListener（让页面逻辑正常执行）
                            originalAddEventListener(type, listener, options);
                            
                            // 如果是自定义事件类型，且我们还没监听，且不在忽略列表中，添加我们的监听器
                            if (!capturedEventTypes.has(type) && !ignoredEventTypes.has(type)) {
                                capturedEventTypes.add(type);
                                // 添加我们的监听器来捕获事件
                                originalAddEventListener(type, captureEvent(type));
                            }
                        };
                        
                        // 主动监听一些常见的自定义事件类型（如果 SSE 流中有这些事件）
                        // 注意：这不会影响页面逻辑，只是确保我们能捕获到这些事件
                        const commonEventTypes = ['done', 'toolsCalling', 'toolsFinished', 'progress', 'update'];
                        commonEventTypes.forEach(eventType => {
                            if (!capturedEventTypes.has(eventType)) {
                                capturedEventTypes.add(eventType);
                                originalAddEventListener(eventType, captureEvent(eventType));
                            }
                        });
                    }, 0);
                }
            }
        } as any;

        (window as any).__playwrightSseEventSourcePatched = true;
    }, urlPatternStr);
};

/**
 * 监听 SSE 接口，收集所有事件流数据（必须在 setupSseListener 之后调用）
 * @param page Playwright 页面实例
 * @param sseUrlPattern SSE 接口 URL 匹配模式
 * @returns 操作对象
 */
export const listenSse = async (page: Page, sseUrlPattern: string | RegExp) => {
    const sseEvents: SseEvent[] = [];
    let routeHandler: (route: Route) => Promise<void>;
    let isListening = false;
    let pollInterval: NodeJS.Timeout | null = null;

    // 解析 SSE 流数据
    const parseSseStream = (streamData: string) => {
        const events = streamData.split(/\r?\n\r?\n/).filter(Boolean);
        for (const eventStr of events) {
            const sseEvent: Partial<SseEvent> = { raw: eventStr, data: null };
            const lines = eventStr.split(/\r?\n/).filter(Boolean);

            let dataStr = '';
            for (const line of lines) {
                if (line.startsWith('data:')) {
                    dataStr += line.slice(5).trim();
                } else if (line.startsWith('event:')) {
                    sseEvent.event = line.slice(6).trim();
                } else if (line.startsWith('id:')) {
                    sseEvent.id = line.slice(3).trim();
                }
            }

            try {
                sseEvent.data = JSON.parse(dataStr);
            } catch (e) {
                sseEvent.data = dataStr;
            }

            sseEvents.push(sseEvent as SseEvent);
        }
    };

    // 启动监听
    const startListening = async () => {
        isListening = true;

        // 使用 route.continue() 让请求继续，不拦截
        routeHandler = async (route: Route) => {
            await route.continue();
        };

        await page.route(sseUrlPattern, routeHandler);

        // 确保浏览器端有事件存储数组
        await page.evaluate(() => {
            if (!(window as any).__playwrightSseEvents) {
                (window as any).__playwrightSseEvents = [];
            }
        });

        // 定期从浏览器上下文获取事件
        pollInterval = setInterval(async () => {
            if (!isListening) return;

            try {
                const browserEvents = await page.evaluate(() => {
                    return (window as any).__playwrightSseEvents || [];
                });

                // 只处理新事件
                if (browserEvents.length > sseEvents.length) {
                    const newEvents = browserEvents.slice(sseEvents.length);
                    for (const event of newEvents) {
                        parseSseStream(event.raw);
                    }
                }
            } catch (e) {
                // 忽略错误
            }
        }, 100);
    };

    // 停止监听
    const stopListening = async () => {
        isListening = false;

        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }

        if (routeHandler) {
            await page.unroute(sseUrlPattern, routeHandler);
        }

        // 清理浏览器端的全局变量
        await page.evaluate(() => {
            delete (window as any).__playwrightSseEvents;
        });
    };

    const waitSseFinish = async (timeout: number = 1000 * 10, duration: number = 100) => {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const events = getSseEvents();
            if (events.some((event) => event.event === 'done')) {
                return;
            }
            await page.waitForTimeout(duration); // 每durationms轮询一次
        }
        throw new Error(`超时 ${timeout}ms 未收到 SSE 完成事件`);
    }

    // 获取所有 SSE 事件
    const getSseEvents = () => [...sseEvents];

    // 启动监听
    await startListening();

    return {
        stopListening,
        getSseEvents,
        waitSseFinish,
    };
};

/* 
这个代码对原来的版本进行了增强，主要是增加了对自定义事件的监听，以及对 SSE 流中事件的解析。
原来的版本只能监听 message 事件，这个版本可以监听所有事件。
原来的版本只能监听 SSE 流中事件，这个版本可以监听 SSE 流中事件，并且可以监听自定义事件。

*/