"""UI 测试自定义异常"""


class UIError(Exception):
    """UI 基础异常"""
    pass


class ElementNotFoundError(UIError):
    """元素未找到异常"""
    pass


class ElementNotVisibleError(UIError):
    """元素不可见异常"""
    pass


class TimeoutError(UIError):
    """超时异常"""
    pass


class NavigationError(UIError):
    """页面导航错误"""
    pass




