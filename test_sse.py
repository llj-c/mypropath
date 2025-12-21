from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import json


app = FastAPI()

# 配置 CORS, 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源, 生产环境应该指定具体域名
    allow_credentials=False,  # 使用通配符时不能为 True
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_sse_data():
    """生成 SSE 数据流."""
    cnt = 0
    
    # 发送一些 message 事件
    for i in range(3):
        event_data = {
            "count": cnt,
            "message": f"普通消息 {i}"
        }
        sse_message = (
            f"event: message\n"
            f"id: {cnt}\n"
            f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        )
        yield sse_message
        cnt += 1
        time.sleep(0.5)
    
    # 发送 toolsCalling 事件
    tools_calling_data = {
        "tool_name": "search_tool",
        "parameters": {
            "query": "Python FastAPI SSE",
            "limit": 10
        },
        "status": "calling"
    }
    tools_calling_message = (
        f"event: toolsCalling\n"
        f"id: {cnt}\n"
        f"data: {json.dumps(tools_calling_data, ensure_ascii=False)}\n\n"
    )
    yield tools_calling_message
    cnt += 1
    time.sleep(0.5)
    
    # 模拟工具调用过程中的一些消息
    for i in range(2):
        event_data = {
            "count": cnt,
            "message": f"工具调用中... {i+1}"
        }
        sse_message = (
            f"event: message\n"
            f"id: {cnt}\n"
            f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        )
        yield sse_message
        cnt += 1
        time.sleep(0.5)
    
    # 发送 toolsFinished 事件
    tools_finished_data = {
        "tool_name": "search_tool",
        "result": {
            "results": [
                {"title": "FastAPI SSE 教程", "url": "https://example.com/1"},
                {"title": "Python 流式响应", "url": "https://example.com/2"}
            ],
            "total": 2
        },
        "status": "finished",
        "duration_ms": 1250
    }
    tools_finished_message = (
        f"event: toolsFinished\n"
        f"id: {cnt}\n"
        f"data: {json.dumps(tools_finished_data, ensure_ascii=False)}\n\n"
    )
    yield tools_finished_message
    cnt += 1
    time.sleep(0.5)
    
    # 继续发送一些 message 事件
    for i in range(3):
        event_data = {
            "count": cnt,
            "message": f"后续消息 {i}"
        }
        sse_message = (
            f"event: message\n"
            f"id: {cnt}\n"
            f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
        )
        yield sse_message
        cnt += 1
        time.sleep(0.5)
    
    # 发送结束事件, 通知客户端数据流已完成
    end_event = {
        "info": "数据流已全部发送完成"
    }
    end_message = (
        f"event: done\n"
        f"id: {cnt}\n"
        f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
    )
    yield end_message


@app.options("/test-sse")
async def test_sse_options():
    """处理 SSE 的 OPTIONS 预检请求."""
    from fastapi.responses import Response
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/test-sse")
async def test_sse():
    """测试 SSE 流式响应."""
    return StreamingResponse(
        generate_sse_data(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Access-Control-Allow-Origin": "*",  # CORS 头
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=48050)