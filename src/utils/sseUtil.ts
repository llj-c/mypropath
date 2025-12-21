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

                    // 使用 addEventListener 添加监听器，不覆盖 onmessage，确保不影响页面原有逻辑
                    // 这样页面可以正常使用 onmessage 或 addEventListener，我们的代码只是额外监听
                    const captureMessage = (event: MessageEvent) => {
                        (window as any).__playwrightSseEvents.push({
                            data: event.data,
                            event: 'message',
                            raw: `data: ${event.data}\n\n`
                        });
                    };

                    // 保存原始的 onmessage（如果存在），并包装它以确保页面原有逻辑能执行
                    const originalOnMessage = this.onmessage;
                    if (originalOnMessage) {
                        this.onmessage = (event) => {
                            originalOnMessage.call(this, event);
                        };
                    }

                    // 使用 setTimeout 确保 EventSource 完全初始化后再添加监听器
                    setTimeout(() => {
                        // 使用 addEventListener 添加监听器，可以捕获所有消息事件
                        // 包括通过 onmessage 和 addEventListener 触发的
                        // 这样无论页面使用哪种方式，我们都能捕获到
                        es.addEventListener('message', captureMessage);

                        // 监听自定义事件（如 'done'）
                        // 自定义事件只能通过 addEventListener 监听
                        es.addEventListener('done', (event: any) => {
                            (window as any).__playwrightSseEvents.push({
                                data: event.data || '',
                                event: 'done',
                                raw: `event: done\ndata: ${event.data || ''}\n\n`
                            });
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