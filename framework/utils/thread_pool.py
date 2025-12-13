import asyncio
import logging
import queue
import threading
import time
from concurrent.futures import Future as ConcurrentFuture, TimeoutError as FutureTimeoutError
from enum import Enum
from typing import Any, Callable, Coroutine, Iterator, Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class RejectPolicy(str, Enum):
    """拒绝策略枚举"""
    ABORT = "abort"  # 直接抛出异常
    DISCARD = "discard"  # 静默丢弃任务
    DISCARD_OLDEST = "discard_oldest"  # 丢弃最旧的任务
    CALLER_RUNS = "caller_runs"  # 在调用线程中执行


class ThreadPoolConfig(BaseModel):
    min_workers: int = Field(default=1, ge=1, description="最小工作线程数（核心线程数）")
    max_workers: int = Field(default=10, ge=1, description="最大工作线程数")
    thread_name_prefix: str = Field(default="thread-pool", description="线程名称前缀")
    daemon: bool = Field(default=False, description="是否为守护线程")
    queue_size: int = Field(default=0, ge=0, description="任务队列大小，0表示无界队列")
    keep_alive_time: float = Field(
        default=60.0, ge=0, description="线程空闲保持时间（秒），超过此时间且线程数大于min_workers则回收线程")
    initializer: Callable[..., Any] | None = Field(default=None, description="每个工作线程启动时调用的初始化函数")
    initargs: tuple[Any, ...] = Field(default_factory=tuple, description="传递给初始化函数的参数元组")
    reject_policy: RejectPolicy = Field(default=RejectPolicy.ABORT, description="队列满时的拒绝策略")
    shutdown_wait: bool = Field(default=True, description="关闭时是否等待任务完成")
    shutdown_timeout: float | None = Field(default=None, ge=0, description="关闭超时时间（秒），None表示无限等待")
    task_timeout: float | None = Field(default=None, ge=0, description="任务执行超时时间（秒），None表示不超时")
    enable_metrics: bool = Field(default=False, description="是否启用性能指标统计")

    @model_validator(mode="after")
    def validate_workers(self) -> "ThreadPoolConfig":
        """验证最大工作线程数必须大于等于最小工作线程数"""
        if self.max_workers < self.min_workers:
            raise ValueError("max_workers 必须大于等于 min_workers")
        return self


class ThreadPoolError(Exception):
    """线程池基础异常类"""
    pass


class RejectedExecutionError(ThreadPoolError):
    """任务被拒绝执行异常"""
    pass


class ThreadPoolShutdownError(ThreadPoolError):
    """线程池已关闭异常"""
    pass


class _Task:
    """任务封装类"""

    def __init__(
        self,
        func: Callable[..., Any],
        args: tuple,
        kwargs: dict,
        future: ConcurrentFuture,
        is_coroutine: bool = False,
        timeout: Optional[float] = None,
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.future = future
        self.is_coroutine = is_coroutine
        self.timeout = timeout
        self.create_time = time.time()


class ThreadPool:
    """自定义线程池，支持同步和异步任务提交"""

    def __init__(self, thread_pool_config: ThreadPoolConfig):
        """
        初始化线程池

        Args:
            thread_pool_config: 线程池配置对象
        """
        self._config = thread_pool_config
        self._shutdown = False
        self._shutdown_lock = threading.Lock()

        # 任务队列
        if self._config.queue_size > 0:
            self._task_queue = queue.Queue(maxsize=self._config.queue_size)
        else:
            self._task_queue = queue.Queue()

        # 工作线程管理
        self._workers: list[threading.Thread] = []
        self._workers_lock = threading.Lock()
        self._active_workers = 0  # 当前活跃工作线程数
        self._worker_id_counter = 0

        # 线程同步
        self._shutdown_event = threading.Event()
        self._worker_condition = threading.Condition(self._workers_lock)

        # 异步支持
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._event_loop_thread: Optional[threading.Thread] = None
        self._event_loop_lock = threading.Lock()

        # 性能指标
        self._metrics = {
            "completed_tasks": 0,
            "failed_tasks": 0,
            "rejected_tasks": 0,
        } if self._config.enable_metrics else None

        # 初始化核心线程
        self._start_workers(self._config.min_workers)

        # 启动事件循环线程（用于异步任务）
        self._start_event_loop()

    def _start_workers(self, count: int) -> None:
        """启动指定数量的工作线程"""
        with self._workers_lock:
            for _ in range(count):
                if len(self._workers) >= self._config.max_workers:
                    break
                self._worker_id_counter += 1
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"{self._config.thread_name_prefix}-{self._worker_id_counter}",
                    daemon=self._config.daemon,
                )
                worker.start()
                self._workers.append(worker)
                self._active_workers += 1

    def _start_event_loop(self) -> None:
        """启动事件循环线程（用于异步任务支持）"""
        loop_ready = threading.Event()
        def _run_event_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            with self._event_loop_lock:
                self._event_loop = loop
            loop_ready.set()
            try:
                loop.run_forever()
            finally:
                loop.close()
                with self._event_loop_lock:
                    self._event_loop = None  # 清空引用

        self._event_loop_thread = threading.Thread(
            target=_run_event_loop,
            name=f"{self._config.thread_name_prefix}-event-loop",
            daemon=True,
        )
        self._event_loop_thread.start()

        # # 等待事件循环启动
        if not loop_ready.wait(timeout=5.0):
            raise RuntimeError("Event loop thread failed to start")

    def _worker_loop(self) -> None:
        """工作线程主循环"""
        # 执行初始化函数
        if self._config.initializer is not None:
            try:
                self._config.initializer(*self._config.initargs)
            except Exception as e:
                logger.error(f"Worker initializer failed: {e}", exc_info=True)

        last_task_time = time.time()

        while not self._shutdown_event.is_set():
            task: _Task | None = None
            try:
                try:
                    with self._worker_condition:
                        self._worker_condition.wait()

                        # 检查 shutdown 信号，若已触发则退出
                        if self._shutdown_event.is_set():
                            break
                        # 防止虚假唤醒
                        if self._task_queue.empty():
                            continue

                    # wait() 后已确认有任务，使用 get_nowait() 避免再次阻塞
                    task = self._task_queue.get_nowait()
                except queue.Empty:
                    # 检查是否需要回收线程
                    if self._should_recycle_worker():
                        current_time = time.time()
                        if current_time - last_task_time > self._config.keep_alive_time:
                            # 回收当前线程
                            with self._workers_lock:
                                if len(self._workers) > self._config.min_workers:
                                    if threading.current_thread() in self._workers:
                                        self._workers.remove(threading.current_thread())
                                        self._active_workers -= 1
                                    return

                # 如果 shutdown 了，即使获取到任务也不执行，直接取消并退出
                if self._shutdown_event.is_set():
                    # 取消任务，设置异常通知调用者
                    if task is not None and not task.future.cancelled():
                        task.future.set_exception(
                            ThreadPoolShutdownError("Thread pool is shutdown, task cancelled")
                        )
                    if task is not None:
                        self._task_queue.task_done()

                    break
                if not task:
                    continue
                # 正常执行任务
                last_task_time = time.time()
                self._execute_task(task)
                self._task_queue.task_done()

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)

    def _should_recycle_worker(self) -> bool:
        """
        判断是否可以回收工作线程（前提条件检查）

        注意: 这个方法只检查线程数是否大于最小工作线程数，是回收的前提条件。
        真正的回收还需要结合空闲时间（keep_alive_time）来判断，具体逻辑在 _worker_loop 中。

        Returns:
            True: 当前线程数大于 min_workers，可以回收多余的线程
            False: 当前线程数等于 min_workers，不能回收（需要保持核心线程数）
        """
        with self._workers_lock:
            return len(self._workers) > self._config.min_workers

    def _execute_task(self, task: _Task) -> None:
        """执行任务"""
        if task.is_coroutine:
            # 异步任务：在线程池的事件循环中执行
            self._execute_async_task(task)
        else:
            # 同步任务：直接执行
            self._execute_sync_task(task)

    def _execute_sync_task(self, task: _Task) -> None:
        """执行同步任务"""
        if task.future.cancelled():
            return

        try:
            if task.timeout is not None:
                # 使用 threading.Timer 实现超时
                result_container = {"value": None, "exception": None, "done": False}

                def _run_with_timeout():
                    try:
                        result_container["value"] = task.func(*task.args, **task.kwargs)
                    except Exception as e:
                        result_container["exception"] = e
                    finally:
                        result_container["done"] = True

                worker_thread = threading.Thread(target=_run_with_timeout)
                worker_thread.daemon = True
                worker_thread.start()
                worker_thread.join(timeout=task.timeout)

                if not result_container["done"]:
                    task.future.set_exception(TimeoutError(
                        f"Task timeout after {task.timeout} seconds"))
                    return

                if result_container["exception"]:
                    task.future.set_exception(result_container["exception"])
                else:
                    task.future.set_result(result_container["value"])
            else:
                result = task.func(*task.args, **task.kwargs)
                task.future.set_result(result)

            if self._metrics:
                self._metrics["completed_tasks"] += 1

        except Exception as e:
            task.future.set_exception(e)
            if self._metrics:
                self._metrics["failed_tasks"] += 1

    def _execute_async_task(self, task: _Task) -> None:
        """执行异步任务（协程）"""
        if task.future.cancelled():
            return

        try:
            # 将协程提交到事件循环
            with self._event_loop_lock:
                if self._event_loop is None or self._event_loop.is_closed():
                    task.future.set_exception(RuntimeError("Event loop is not available"))
                    return

                async_future = asyncio.run_coroutine_threadsafe(
                    task.func(*task.args, **task.kwargs),
                    self._event_loop,
                )

            # 等待异步结果
            if task.timeout is not None:
                try:
                    result = async_future.result(timeout=task.timeout)
                    task.future.set_result(result)
                except asyncio.TimeoutError:
                    async_future.cancel()
                    task.future.set_exception(TimeoutError(
                        f"Task timeout after {task.timeout} seconds"))
                except Exception as e:
                    task.future.set_exception(e)
            else:
                try:
                    result = async_future.result()
                    task.future.set_result(result)
                except Exception as e:
                    task.future.set_exception(e)

            if self._metrics:
                self._metrics["completed_tasks"] += 1

        except Exception as e:
            task.future.set_exception(e)
            if self._metrics:
                self._metrics["failed_tasks"] += 1

    def _handle_reject(self, task: _Task) -> None:
        """处理任务拒绝策略"""
        if self._metrics:
            self._metrics["rejected_tasks"] += 1

        if self._config.reject_policy == RejectPolicy.ABORT:
            task.future.set_exception(RejectedExecutionError("Task queue is full"))
        elif self._config.reject_policy == RejectPolicy.DISCARD:
            task.future.cancel()
        elif self._config.reject_policy == RejectPolicy.DISCARD_OLDEST:
            try:
                old_task: _Task = self._task_queue.get_nowait()
                old_task.future.cancel()
                self._task_queue.put_nowait(task)
            except queue.Empty:
                task.future.set_exception(RejectedExecutionError("Failed to discard oldest task"))
        elif self._config.reject_policy == RejectPolicy.CALLER_RUNS:
            # 在调用线程中直接执行
            try:
                if task.is_coroutine:
                    # 对于协程，需要在新的事件循环中运行
                    result = asyncio.run(task.func(*task.args, **task.kwargs))
                    task.future.set_result(result)
                else:
                    result = task.func(*task.args, **task.kwargs)
                    task.future.set_result(result)
            except Exception as e:
                task.future.set_exception(e)

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> ConcurrentFuture:
        """
        提交同步任务

        Args:
            fn: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            concurrent.futures.Future 对象

        Raises:
            ThreadPoolShutdownError: 线程池已关闭
            RejectedExecutionError: 任务被拒绝（根据拒绝策略）
        """
        with self._shutdown_lock:
            if self._shutdown:
                raise ThreadPoolShutdownError(
                    "Thread pool is shutdown or ready to shutdown,don't submit task")

        future = ConcurrentFuture()
        task = _Task(
            func=fn,
            args=args,
            kwargs=kwargs,
            future=future,
            is_coroutine=False,
            timeout=self._config.task_timeout,
        )

        try:
            self._task_queue.put_nowait(task)
            with self._worker_condition:
                self._worker_condition.notify()
        except queue.Full:
            self._handle_reject(task)
            return future

        # 动态扩展工作线程
        with self._workers_lock:
            if len(self._workers) < self._config.max_workers and self._active_workers < len(self._workers):
                self._start_workers(1)

        return future

    async def submit_async(self, coro: Coroutine[Any, Any, Any], *args: Any, **kwargs: Any) -> Any:
        """
        提交异步任务（协程）

        Args:
            coro: 要执行的协程对象
            *args: 协程位置参数（如果 coro 需要参数，应通过 functools.partial 传递）
            **kwargs: 协程关键字参数（如果 coro 需要参数，应通过 functools.partial 传递）

        Returns:
            协程的执行结果

        Raises:
            ThreadPoolShutdownError: 线程池已关闭
            RejectedExecutionError: 任务被拒绝（根据拒绝策略）
        """
        with self._shutdown_lock:
            if self._shutdown:
                raise ThreadPoolShutdownError("Thread pool is shutdown")

        # 创建包装协程函数，直接执行传入的协程
        async def _coro_wrapper():
            return await coro

        future = ConcurrentFuture()
        task = _Task(
            func=_coro_wrapper,
            args=(),
            kwargs={},
            future=future,
            is_coroutine=True,
            timeout=self._config.task_timeout,
        )

        try:
            self._task_queue.put_nowait(task)
            with self._worker_condition:
                self._worker_condition.notify()
        except queue.Full:
            self._handle_reject(task)
            exc = task.future.exception()
            if exc is not None:
                raise exc
            return await asyncio.wrap_future(task.future)

        # 动态扩展工作线程
        with self._workers_lock:
            if len(self._workers) < self._config.max_workers and self._active_workers < len(self._workers):
                self._start_workers(1)

        # 等待结果
        return await asyncio.wrap_future(future)

    async def run_async(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        在线程池中异步执行同步函数

        Args:
            fn: 要执行的同步函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数的执行结果

        Raises:
            ThreadPoolShutdownError: 线程池已关闭
            RejectedExecutionError: 任务被拒绝（根据拒绝策略）
        """
        future = self.submit(fn, *args, **kwargs)
        return await asyncio.wrap_future(future)

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """
        关闭线程池

        Args:
            wait: 是否等待任务完成
            timeout: 等待超时时间（秒），None 表示使用配置的超时时间
        """
        with self._shutdown_lock:
            if self._shutdown:
                return
            self._shutdown = True

        # 设置关闭事件
        self._shutdown_event.set()

        # 唤醒所有正在等待的线程,让其线程退出
        with self._worker_condition:
            self._worker_condition.notify_all()
        print("worker condition notified all")
        # 处理正在执行的任务的工作线程
        if wait:
            wait_timeout = timeout if timeout is not None else self._config.shutdown_timeout
            if wait_timeout is not None:
                # 等待任务队列清空（带超时）
                end_time = time.time() + wait_timeout
                while not self._task_queue.empty() and time.time() < end_time:
                    time.sleep(0.1)
                # 等待工作线程结束
                # 即使超时，也要尝试 join 所有线程（使用最小超时时间），避免资源泄漏
                workers_to_join = list(self._workers)
                for worker in workers_to_join:
                    remaining_time = end_time - time.time()
                    if remaining_time <= 0:
                        # 超时后仍尝试 join，但使用最小超时时间（0.1秒），确保至少尝试一次
                        worker.join(timeout=0.1)
                    else:
                        worker.join(timeout=remaining_time)
            else:
                # 无限等待
                self._task_queue.join()
                for worker in self._workers:
                    worker.join()
        print("pool thread worker shutdown completed,ready to close event loop")
        # 关闭事件循环（在所有工作线程结束后再关闭，避免异步任务被中断）
        with self._event_loop_lock:
            if self._event_loop is not None and not self._event_loop.is_closed():
                self._event_loop.call_soon_threadsafe(self._event_loop.stop)
                if self._event_loop_thread is not None:
                    self._event_loop_thread.join(timeout=5.0)
        print("event loop closed")
    def get_metrics(self) -> Optional[dict]:
        """
        获取性能指标

        Returns:
            性能指标字典，如果未启用则返回 None
        """
        if not self._config.enable_metrics:
            return None

        with self._workers_lock:
            metrics_dict = {
                "active_workers": self._active_workers,
                "total_workers": len(self._workers),
                "queue_size": self._task_queue.qsize(),
            }
            if self._metrics is not None:
                metrics_dict.update(self._metrics)
            return metrics_dict

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown(wait=True)
