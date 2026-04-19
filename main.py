from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import requests
import json
import os
import uuid
from typing import List, Dict

app = FastAPI(title="ZaiwenAI Web2API Proxy - Docker版")

# 从环境变量读取（Docker / Render / Railway 都会自动读取）
ZAIWENAI_TOKEN = os.getenv("ZAIWENAI_TOKEN")
ZAIWENAI_BASE_URL = "https://back.zaiwenai.com/api/v1/ai/message/stream"

if not ZAIWENAI_TOKEN:
    raise ValueError("环境变量 ZAIWENAI_TOKEN 未设置！请在平台设置你的 token")

@app.get("/")
async def root():
    return {
        "status": "ok", 
        "message": "🚀 ZaiwenAI Web2API Docker 版运行正常！请在 NewAPI / OpenWebUI 使用 /v1/chat/completions"
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效的 JSON")

    messages: List[Dict] = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    # 动态 conversation_id（彻底解决上下文污染）
    conv_id = request.headers.get("x-zaiwenai-conversation-id")
    if not conv_id:
        conv_id = str(uuid.uuid4())

    # 把完整历史拼接成一条 prompt
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            prompt_parts.append(f"System: {content}")
        elif role == "user":
            prompt_parts.append(f"User: {content}")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}")
    full_prompt = "\n\n".join(prompt_parts)

    payload = {
        "conversation_id": conv_id,
        "data": {
            "content": full_prompt,
            "model": body.get("model", "Gemini-3.0-Flash"),
            "round": 20,
            "type": "text",
            "online": False,
            "file": {},
            "knowledge": [],
            "draw": {},
            "suno_input": {},
            "video": {
                "ratio": "1:1",
                "resolution": "720p",
                "duration": 5,
                "mediaModel": "referenceImage",
                "generate_audio": True,
                "original_image": {"image": {}, "weight": 50},
                "reference_medias": []
            },
            "pptx_extra": {"color_scheme": "", "style": "", "scenario": ""}
        }
    }

    headers = {
        "token": ZAIWENAI_TOKEN,
        "channel": "web.zaiwenai.com",
        "content-type": "application/json",
        "origin": "https://chat.zaiwenai.com",
        "referer": "https://chat.zaiwenai.com/"
    }

    resp = requests.post(ZAIWENAI_BASE_URL, headers=headers, json=payload, stream=True)

    def generate():
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data = json.loads(line_str[6:])
                    if isinstance(data, dict) and "content" in data:
                        content_chunk = data.get("content", "")
                        if content_chunk:
                            chunk = {
                                "id": f"chatcmpl-{conv_id[:8]}",
                                "object": "chat.completion.chunk",
                                "choices": [{"delta": {"content": content_chunk}, "index": 0, "finish_reason": None}]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                except:
                    pass
            elif line_str == "data: [DONE]":
                yield "data: [DONE]\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")
