# pytest任务管理插件

## 功能说明

该插件实现了测试任务管理功能，包括：
- 任务状态检查（运行中、暂停、中止、完成等）
- 测试用例级别的traceid管理
- 日志收集和文件输出
- 暂停/恢复机制
- 中止机制

## 钩子函数实现

### 1. `pytest_configure(config)`
- **功能**：初始化插件，获取run_id
- **执行时机**：pytest配置阶段
- **主要操作**：
  - 从命令行参数或环境变量获取`run_id`
  - 初始化状态存储实例
  - 设置日志文件handler
  - 注册自定义marker

### 2. `pytest_sessionstart(session)`
- **功能**：会话开始，设置traceid
- **执行时机**：测试会话开始时
- **主要操作**：
  - 生成会话级别的traceid
  - 更新任务状态为`RUNNING`

### 3. `pytest_sessionfinish(session, exitstatus)`
- **功能**：会话结束，清理资源
- **执行时机**：测试会话结束时
- **主要操作**：
  - 根据退出状态更新任务状态（`COMPLETED`或`FAILED`）
  - 清除traceid

### 4. `pytest_collection_modifyitems(config, items)`
- **功能**：收集阶段检查中止标志
- **执行时机**：测试用例收集完成后
- **主要操作**：
  - 检查任务是否已中止
  - 如果已中止，跳过所有测试用例

### 5. `pytest_runtest_setup(item)`
- **功能**：每个测试用例开始前检查状态
- **执行时机**：每个测试用例执行前
- **主要操作**：
  - 为每个测试用例生成独立的traceid
  - 检查任务是否已中止，如果已中止则跳过
  - 检查任务是否已暂停，如果已暂停则等待恢复

### 6. `pytest_runtest_teardown(item)`
- **功能**：每个测试用例结束后检查状态
- **执行时机**：每个测试用例执行后
- **主要操作**：
  - 记录测试用例执行完成
  - 检查任务是否在用例执行过程中被中止

## 使用方法

### 1. 通过命令行参数传递run_id

```bash
pytest --run-id test_20240101_120000_abc12345 tests/
```

### 2. 通过环境变量传递run_id

```bash
export PYTEST_RUN_ID=test_20240101_120000_abc12345
pytest tests/
```

### 3. 在代码中使用traceid

```python
from framework.task.traceid import get_traceid

def test_example():
    traceid = get_traceid()
    print(f"当前测试用例的traceid: {traceid}")
    # 在API请求中携带traceid
    headers = {"X-Trace-Id": traceid}
```

## 状态管理

插件通过`StateStore`与主进程通信，支持以下操作：

- **检查中止标志**：`state_store.check_flag(run_id, "cancelled")`
- **检查暂停标志**：`state_store.check_flag(run_id, "paused")`
- **等待恢复**：`state_store.wait_for_flag(run_id, "paused", timeout=None)`

## 日志输出

日志文件保存在 `logs/{run_id}/pytest.log`，日志格式包含traceid：

```
2024-01-01 12:00:00 - framework.pytest_plugin.task_plugin - INFO - [abc12345-def67890] - pytest_runtest_setup: tests/test_example.py::test_example
```

## 注意事项

1. 如果没有提供`run_id`，插件会记录警告但不会影响测试执行
2. 暂停机制会阻塞测试用例执行，直到任务恢复
3. 中止机制会跳过后续测试用例，但正在执行的用例会继续完成
4. traceid使用`contextvars`实现，支持异步环境

