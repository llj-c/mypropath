// SSE 事件捕获脚本
// 占位符 __SSE_URL_PATTERN__ 会被 Python 替换为实际 URL 模式
(function () {
    // ========== 全局状态管理 ==========
    // 初始化全局变量，存储 SSE 事件、状态和 URL 匹配规则
    function initGlobalState(urlPattern) {
        window.__sseEvents = [];       // 存储解析后的 SSE 事件
        window.__sseFinished = false;  // 标记 SSE 流是否结束
        window.__sseUrlPattern = urlPattern; // SSE 请求匹配规则
    }

    // ========== SSE 数据解析 ==========
    // 解析单条 SSE 事件（如 "event:message\ndata:hello"）
    function parseSSEEvent(rawEvent) {
        let eventName = 'message'; // 默认事件名
        let data = '';

        // 按行拆分解析 SSE 字段
        rawEvent.split('\n').forEach(line => {
            line = line.trim();
            if (line.startsWith('event:')) {
                eventName = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
                data = line.substring(5).trim();
            }
        });

        // 尝试解析 JSON 格式的数据，失败则保留原始字符串
        let parsedData = data;
        try {
            parsedData = JSON.parse(data);
        } catch (e) { /* 静默失败，不影响流程 */ }

        return {
            event: eventName,
            data: parsedData,
            rawData: data
        };
    }

    // ========== SSE 流读取 ==========
    // 流式读取 SSE 响应并解析事件
    async function readSSEStream(reader) {
        const decoder = new TextDecoder();
        let buffer = ''; // 缓存未完整解析的流数据

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    window.__sseFinished = true; // 标记流结束
                    break;
                }

                // 解码二进制流并拼接缓存
                buffer += decoder.decode(value, { stream: true });
                // 按 SSE 分隔符（双换行）拆分事件
                const eventParts = buffer.split('\n\n');
                // 最后一段可能不完整，放回缓存
                buffer = eventParts.pop() || '';

                // 解析并存储所有完整的 SSE 事件
                eventParts.forEach(part => {
                    if (part.trim()) {
                        const sseEvent = parseSSEEvent(part);
                        window.__sseEvents.push(sseEvent);
                    }
                });
            }
        } catch (err) {
            console.error('SSE 流读取失败:', err);
            window.__sseFinished = true; // 异常时也标记流结束
        }
    }

    // ========== fetch 方法劫持 ==========
    // 重写 fetch 以拦截 SSE 请求
    function hijackFetch() {
        const originalFetch = window.fetch; // 保存原生 fetch

        window.fetch = async function (...args) {
            // 执行原生 fetch 获取响应
            const response = await originalFetch(...args);
            const requestUrl = args[0]; // 获取请求 URL

            // 仅处理匹配 URL 模式的 SSE 请求
            if (requestUrl && requestUrl.includes(window.__sseUrlPattern)) {
                const contentType = response.headers.get('content-type') || '';
                // 验证响应类型为 SSE 且有可读流
                if (contentType.includes('text/event-stream') && response.body) {
                    // 克隆响应（避免原流被消费），启动流读取
                    const clonedResponse = response.clone();
                    const reader = clonedResponse.body.getReader();
                    readSSEStream(reader); // 异步读取，不阻塞原请求
                }
            }

            return response; // 返还原生响应，不影响页面逻辑
        };
    }

    // ========== 初始化执行 ==========
    // 替换占位符并初始化
    const urlPattern = '__SSE_URL_PATTERN__';
    initGlobalState(urlPattern);
    hijackFetch();
})();