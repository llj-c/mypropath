# pytest子进程状态响应机制

## 核心原理

pytest子进程**不直接控制**任务状态，而是通过`run_id`从**共享的StateStore**中读取状态标志，并做出相应响应。

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 主进程                            │
│                                                              │
│  1. 创建任务，生成 run_id                                    │
│  2. 启动pytest子进程，传递 run_id                           │
│  3. 通过 StateStore 设置状态标志                             │
│     - state_store.set_flag(run_id, "paused", True)          │
│     - state_store.set_flag(run_id, "cancelled", True)       │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ 共享StateStore (Redis/内存/文件)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              pytest 子进程                                    │
│                                                              │
│  1. 获取 run_id (从命令行参数或环境变量)                     │
│  2. 连接共享的 StateStore                                    │
│  3. 在关键钩子点检查状态标志                                 │
│     - pytest_collection_modifyitems: 检查cancelled          │
│     - pytest_runtest_setup: 检查cancelled/paused            │
│     - pytest_runtest_teardown: 检查cancelled                │
│  4. 根据标志执行相应行为                                     │
│     - cancelled → pytest.skip()                             │
│     - paused → wait_for_flag() 等待恢复                      │
└─────────────────────────────────────────────────────────────┘
```

## 详细实现步骤

### 1. pytest子进程获取run_id

```python
# 在 pytest_configure 钩子中
def pytest_configure(self, config):
    # 从命令行参数获取
    self.run_id = self.config.getoption("--run-id", default=None)
    
    # 或从环境变量获取
    if not self.run_id:
        self.run_id = os.environ.get("PYTEST_RUN_ID")
```

### 2. 连接共享的StateStore

```python
def _get_state_store(self) -> Optional[StateStore]:
    """获取状态存储实例"""
    # 注意：主进程和子进程必须使用同一个StateStore实例
    # 方案A: Redis (推荐，支持多进程/多机器)
    # 方案B: 内存字典 + 文件锁 (单机多进程)
    # 方案C: SQLite + 文件锁 (单机，支持持久化)
    
    # 当前实现使用全局单例（仅用于演示）
    # 实际应该从依赖注入容器或共享存储获取
    if not hasattr(TaskPlugin, "_global_state_store"):
        TaskPlugin._global_state_store = MemoryStateStore()
    return TaskPlugin._global_state_store
```

### 3. 在关键钩子点检查状态

#### 3.1 测试用例收集阶段

```python
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(self, config, items):
    """收集阶段检查中止标志"""
    if not self.run_id or not self.state_store:
        return
    
    # 通过run_id检查是否已中止
    if self.state_store.check_flag(self.run_id, "cancelled"):
        logger.warning("检测到任务已中止，跳过所有测试用例")
        # 跳过所有测试用例
        for item in items:
            item.add_marker(pytest.mark.skip(reason="任务已中止"))
```

#### 3.2 每个测试用例执行前

```python
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(self, item):
    """每个测试用例开始前检查状态"""
    if not self.run_id or not self.state_store:
        return
    
    # 检查是否已中止
    if self.state_store.check_flag(self.run_id, "cancelled"):
        logger.warning(f"测试用例 {item.nodeid} 被跳过：任务已中止")
        pytest.skip("任务已中止")
    
    # 检查是否暂停，如果暂停则等待恢复
    if self.state_store.check_flag(self.run_id, "paused"):
        logger.info(f"测试用例 {item.nodeid} 等待恢复：任务已暂停")
        # 等待恢复（轮询直到暂停标志被清除）
        self.state_store.wait_for_flag(self.run_id, "paused", timeout=None)
        logger.info(f"测试用例 {item.nodeid} 继续执行：任务已恢复")
```

#### 3.3 每个测试用例执行后

```python
@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(self, item):
    """每个测试用例结束后检查状态"""
    if not self.run_id or not self.state_store:
        return
    
    # 再次检查是否已中止（在用例执行过程中可能被中止）
    if self.state_store.check_flag(self.run_id, "cancelled"):
        logger.warning(f"测试用例 {item.nodeid} 执行后检测到任务已中止")
```

## 状态响应机制

### 中止机制 (Cancelled)

**主进程操作：**
```python
# FastAPI路由: POST /api/v1/tasks/{run_id}/cancel
state_store.set_flag(run_id, "cancelled", True)
```

**pytest子进程响应：**
```python
# 在测试用例执行前检查
if self.state_store.check_flag(self.run_id, "cancelled"):
    pytest.skip("任务已中止")  # 跳过当前和后续测试用例
```

**特点：**
- 正在执行的测试用例会继续完成
- 后续测试用例会被跳过
- 不会中断正在运行的用例

### 暂停/恢复机制 (Paused)

**主进程操作：**
```python
# FastAPI路由: POST /api/v1/tasks/{run_id}/pause
state_store.set_flag(run_id, "paused", True)

# FastAPI路由: POST /api/v1/tasks/{run_id}/resume
state_store.set_flag(run_id, "paused", False)
```

**pytest子进程响应：**
```python
# 在测试用例执行前检查
if self.state_store.check_flag(self.run_id, "paused"):
    # 等待恢复（轮询直到暂停标志被清除）
    self.state_store.wait_for_flag(self.run_id, "paused", timeout=None)
```

**wait_for_flag实现：**
```python
def wait_for_flag(self, run_id: str, flag_name: str, timeout: Optional[float] = None) -> bool:
    """等待标志位变化"""
    import time
    
    start_time = time.time()
    check_interval = 0.5  # 轮询间隔（秒）
    
    while True:
        # 检查标志位是否已清除
        if not self.check_flag(run_id, flag_name):
            return True
        
        # 检查超时
        if timeout is not None:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return False
        
        time.sleep(check_interval)  # 每0.5秒检查一次
```

**特点：**
- 测试用例会在执行前等待
- 使用轮询机制（每0.5秒检查一次）
- 主进程清除暂停标志后，子进程继续执行

## 关键点说明

### 1. 共享StateStore的重要性

主进程和pytest子进程必须使用**同一个StateStore实例**，才能实现状态同步：

- **Redis方案**：主进程和子进程都连接同一个Redis实例
- **内存方案**：需要确保是同一个进程或使用共享内存
- **文件方案**：使用文件锁确保多进程安全

### 2. 状态检查时机

pytest插件在以下时机检查状态：

1. **pytest_collection_modifyitems** - 测试用例收集完成后
2. **pytest_runtest_setup** - 每个测试用例执行前
3. **pytest_runtest_teardown** - 每个测试用例执行后

### 3. 轮询机制

暂停/恢复使用轮询机制，每0.5秒检查一次状态标志。这不是最优方案，但在没有信号机制的情况下是可行的。

### 4. 状态更新

pytest子进程也会更新状态：

```python
# 会话开始时
self.state_store.set_status(self.run_id, TaskStatus.RUNNING)

# 会话结束时
if exitstatus == 0:
    status = TaskStatus.COMPLETED
else:
    status = TaskStatus.FAILED
self.state_store.set_status(self.run_id, status)
```

## 完整示例

### 主进程（FastAPI）

```python
# 创建任务
run_id = generate_run_id()
state_store.set_status(run_id, TaskStatus.PENDING)

# 启动pytest子进程
subprocess.Popen(["pytest", "--run-id", run_id, "tests/"])

# 暂停任务
state_store.set_flag(run_id, "paused", True)

# 恢复任务
state_store.set_flag(run_id, "paused", False)

# 中止任务
state_store.set_flag(run_id, "cancelled", True)
```

### pytest子进程（自动响应）

```python
# 插件自动在钩子函数中检查状态
# 无需额外代码，插件会自动响应主进程的状态变化
```

## 总结

pytest子进程通过以下方式响应任务状态：

1. **获取run_id** - 从命令行参数或环境变量
2. **连接StateStore** - 获取共享的状态存储实例
3. **定期检查** - 在关键钩子点检查状态标志
4. **执行响应** - 根据标志执行相应行为（跳过、等待等）

这种设计实现了主进程和子进程的解耦，主进程负责控制，子进程负责响应。

