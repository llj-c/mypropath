"""SSE (Server-Sent Events) 测试用例"""

from typing import List, Dict, Any

import pytest
from playwright.sync_api import Page

from tests.fixtures.sse_fixtures import SSECollector, sse_collector


class TestSSEDemo:
    """SSE 功能测试类"""

    # def test_sse_events(self, page: Page, sse_collector: SSECollector):
    #     """
    #     简单的 SSE 事件测试

    #     1. 打开页面
    #     2. 点击按钮触发 SSE
    #     3. 等待 SSE 流完成或超时
    #     4. 获取所有捕获的事件
    #     """
    #     # 打开页面
    #     page.goto("http://localhost:48050/testsse")

    #     # 清空事件数组和完成标志
    #     sse_collector.clear()

    #     # 点击按钮触发 SSE
    #     page.click("#startBtn")

    #     # 等待 SSE 流完成或超时
    #     events = sse_collector.wait_for_completion(
    #         max_wait_time=60,
    #         check_interval=0.5
    #     )

    #     # 打印事件
    #     sse_collector.print_events(events)

    #     return events

    # def test_sse_events_with_custom_timeout(
    #     self,
    #     page: Page,
    #     sse_collector: SSECollector
    # ):
    #     """
    #     带自定义超时的 SSE 事件测试

    #     演示如何使用自定义参数
    #     """
    #     page.goto("http://localhost:48050/testsse")
    #     sse_collector.clear()

    #     page.click("#startBtn")

    #     # 使用自定义超时和进度回调
    #     def on_progress(count: int):
    #         if count > 0:
    #             print(f"  已收集 {count} 个事件...", end="\r")

    #     sse_collector.url_pattern = "sse_demo"
    #     events = sse_collector.wait_for_completion(
    #         max_wait_time=30,
    #         check_interval=0.3,
    #         on_progress=on_progress
    #     )

    #     sse_collector.print_events(events)
    #     return events

    def test_sse_events_custom_endpoint(
        self,
        page: Page,
        sse_collector_custom: SSECollector
    ):
        """
        自定义 SSE 端点的测试示例

        演示如何使用自定义 URL 模式
        """
        # 设置自定义 URL 模式
        sse_collector_custom.url_pattern = "sse_demo"
        sse_collector_custom.setup_capture()

        page.goto("http://localhost:48050/testsse")
        sse_collector_custom.clear()

        page.click("#startBtn")

        # 使用自定义超时和进度回调
        def on_progress(count: int):
            if count > 0:
                print(f"  已收集 {count} 个事件...", end="\r")

        events = sse_collector_custom.wait_for_completion(on_progress=on_progress)
        sse_collector_custom.print_events(events)

        return events
