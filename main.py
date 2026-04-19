from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import requests
import json
import os
from typing import List, Dict

app = FastAPI(title="ZaiwenAI Web2API - 完美伪装版")

ZAIWENAI_TOKEN = os.getenv("ZAIWENAI_TOKEN")
ZAIWENAI_BASE_URL = "https://back.zaiwenai.com/api/v1/ai/message/stream"

@app.get("/")
async def root():
    return {"status": "ok", "message": "🚀 ZaiwenAI Web2API 完美伪装版已启动"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效 JSON")

    messages: List[Dict] = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "你好")

    payload = {
        "data": {
            "content": last_user_msg,
            "model": body.get("model", "Gemini-3.0-Flash"),
            "round": "10",
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
        "referer": "https://chat.zaiwenai.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "accept": "*/*",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site"
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
                        content = data.get("content", "")
                        if content:
                            yield f'data: {json.dumps({"choices": [{"delta": {"content": content}}]})}\n\n'
                except:
                    pass
            elif line_str == "data: [DONE]":
                yield "data: [DONE]\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")
