import { test, expect } from '@playwright/test';
import { setupSseListener, listenSse } from '@/common/utils/sseUtil';


test('should listen to SSE events', async ({ page }) => {
    // 1. 在页面加载前设置 SSE 监听（必须在 page.goto() 之前调用）
    const sseUrl = 'http://localhost:48050/test-sse';
    await setupSseListener(page, sseUrl);

    // 2. 加载页面
    await page.goto('file:///D:/code/temp/pyt/test_sse.html');

    // 3. 开始监听 SSE 事件
    const { getSseEvents, stopListening, waitSseFinish } = await listenSse(page, new RegExp(sseUrl));

    // 4. 点击按钮启动 SSE 连接
    await page.click('#startBtn');


    await waitSseFinish(1000 * 11, 100);

    // 6. 验证 SSE 事件数据
    const allSseEvents = getSseEvents();
    console.log('捕获到的所有 SSE 事件：', JSON.stringify(allSseEvents, null, 2));
    expect(allSseEvents.length).toBeGreaterThan(0); // 至少有一条事件
    // 校验是否有任务完成事件
    const finishEvent = allSseEvents.find((event) => event.event === 'done');
    expect(finishEvent).toBeTruthy();


    // 清理资源：停止监听 SSE
    await stopListening();
})