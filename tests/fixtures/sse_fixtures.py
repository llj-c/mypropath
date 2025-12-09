"""SSE (Server-Sent Events) 测试 fixtures 和辅助工具"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Generator

import pytest
from playwright.sync_api import Page


class SSECollector:
    """SSE 事件收集器辅助类"""

    def __init__(self, page: Page):
        """
        初始化 SSE 收集器

        Args:
            page: Playwright Page 实例
        """
        self.page = page
        self.__url_pattern = ""

    @property
    def url_pattern(self) -> str:
        return self.__url_pattern

    @url_pattern.setter
    def url_pattern(self, value: str):
        self.__url_pattern = value

    def _load_js_script(self) -> str:
        """
        加载 JavaScript 脚本文件

        Returns:
            JavaScript 代码字符串
        """
        # 获取 JS 文件路径（相对于当前文件）
        js_file = Path(__file__).parent / "sse_capture.js"
        
        if not js_file.exists():
            raise FileNotFoundError(f"SSE 捕获脚本文件不存在: {js_file}")
        
        # 读取 JS 文件内容
        with open(js_file, "r", encoding="utf-8") as f:
            js_content = f.read()
        
        return js_content

    def setup_capture(self):
        """
        设置 SSE 捕获（注入 JavaScript）
        """
        # 加载 JS 脚本
        js_script = self._load_js_script()
        
        # 替换 URL 模式占位符
        js_script = js_script.replace("__SSE_URL_PATTERN__", self.url_pattern)
        
        # 注入到页面
        self.page.add_init_script(js_script)

    def clear(self):
        """清空收集的事件"""
        self.page.evaluate("window.__sseEvents = []; window.__sseFinished = false;")

    def get_events(self) -> List[Dict[str, Any]]:
        """
        获取所有收集到的事件

        Returns:
            事件列表
        """
        return self.page.evaluate("window.__sseEvents || []")

    def is_finished(self) -> bool:
        """
        检查 SSE 流是否已完成

        Returns:
            是否完成
        """
        return self.page.evaluate("window.__sseFinished || false")

    def wait_for_completion(
        self,
        max_wait_time: float = 60,
        check_interval: float = 0.5,
        on_progress: Optional[Callable[[int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        等待 SSE 流完成或超时

        Args:
            max_wait_time: 最大等待时间（秒）
            check_interval: 检查间隔（秒）
            on_progress: 进度回调函数，接收当前事件数量

        Returns:
            收集到的事件列表
        """
        waited_time = 0

        while waited_time < max_wait_time:
            # 检查是否完成
            finished = self.is_finished()
            events = self.get_events()
            event_count = len(events)

            # 调用进度回调
            if on_progress:
                on_progress(event_count)

            # 如果完成标志为 true，说明流已结束
            if finished:
                print(f"\nSSE 流已完成，共捕获 {event_count} 个事件")
                break

            time.sleep(check_interval)
            waited_time += check_interval

        # 返回最终的事件列表
        return self.get_events()

    def print_events(self, events: Optional[List[Dict[str, Any]]] = None):
        """
        打印事件列表

        Args:
            events: 事件列表，如果为 None 则从页面获取
        """
        if events is None:
            events = self.get_events()

        print(f"\n捕获到 {len(events)} 个 SSE 事件:")
        for i, event in enumerate(events, 1):
            event_type = event.get('event', 'unknown')
            data = event.get('data', event.get('rawData', ''))
            print(f"  事件 {i}: [{event_type}] {data}")


@pytest.fixture(scope="function")
def sse_collector(page: Page) -> Generator[SSECollector, None, None]:
    """
    SSE 收集器 fixture

    Args:
        page: Playwright Page fixture

    Yields:
        SSECollector 实例
    """
    collector = SSECollector(page)
    # 默认设置捕获（可以自定义 URL 模式）
    collector.setup_capture()
    yield collector
    # 清理
    collector.clear()


@pytest.fixture(scope="function")
def sse_collector_custom(page: Page) -> Generator[SSECollector, None, None]:
    """
    自定义 SSE 收集器 fixture（允许自定义 URL 模式）

    使用示例:
        def test_my_sse(sse_collector_custom):
            sse_collector_custom.setup_capture("/my_sse_endpoint")
            # ... 测试代码

    Args:
        page: Playwright Page fixture

    Yields:
        SSECollector 实例（未设置捕获，需要手动调用 setup_capture）
    """
    collector = SSECollector(page)
    yield collector
    collector.clear()
