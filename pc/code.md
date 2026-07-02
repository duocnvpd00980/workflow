sudo lxc exec pc-1 -- bash -c 'cat > /app/client_app.py << "EOF"
#!/usr/bin/env python3
"""LXD Client - Nodriver + Google Chrome"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

import nodriver as uc

# ============ CONFIG ============
STORAGE_DIR = "/app/storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

CHROME_PATH = "/usr/bin/google-chrome-stable"

FINGERPRINT = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "vi-VN",
    "timezone": "Asia/Ho_Chi_Minh",
    "lang": "vi,en-US,en",
}

# ============ STATE ============
_browser = None
_tab = None

# ============ MODELS ============
class TaskRequest(BaseModel):
    task_type: str
    params: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = {}
    error: Optional[str] = None

# ============ APP ============
app = FastAPI(title="FB Client - Nodriver", version="1.0.0")

@app.get("/health")
async def health():
    chrome_exists = os.path.exists(CHROME_PATH)
    return {
        "status": "ok",
        "browser": "nodriver+chrome",
        "chrome_path": CHROME_PATH,
        "chrome_exists": chrome_exists,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/fingerprint")
async def get_fingerprint():
    return FINGERPRINT

@app.post("/task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    global _browser, _tab
    
    try:
        data = {}
        
        if not _browser:
            _browser = await uc.start(
                headless=True,
                browser_executable_path=CHROME_PATH,
                lang=FINGERPRINT["lang"],
                no_sandbox=True,
            )
        
        if request.task_type == "navigate":
            url = request.params.get("url")
            if not _tab:
                _tab = await _browser.get(url)
            else:
                await _tab.get(url)
            await asyncio.sleep(2)
            data = {"url": url, "title": await _tab.evaluate("document.title")}
            
        elif request.task_type == "click":
            selector = request.params.get("selector")
            elem = await _tab.select(selector)
            await elem.click()
            await asyncio.sleep(0.5)
            data = {"clicked": selector}
            
        elif request.task_type == "type":
            selector = request.params.get("selector")
            text = request.params.get("text")
            elem = await _tab.select(selector)
            await elem.send_keys(text)
            data = {"typed": text[:30] + "..." if len(text) > 30 else text}
            
        elif request.task_type == "screenshot":
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = request.params.get("filename", "ss_" + now_str + ".png")
            filepath = os.path.join(STORAGE_DIR, filename)
            await _tab.save_screenshot(filepath)
            data = {"screenshot": filepath}
            
        elif request.task_type == "get_html":
            html = await _tab.evaluate("document.documentElement.outerHTML")
            data = {"html_length": len(html), "preview": html[:500]}
            
        elif request.task_type == "evaluate":
            script = request.params.get("script")
            result = await _tab.evaluate(script)
            data = {"result": result}
            
        elif request.task_type == "scroll":
            direction = request.params.get("direction", "down")
            amount = request.params.get("amount", 500)
            sign = "-" if direction == "up" else ""
            js = "window.scrollBy(0, " + sign + str(amount) + ")"
            await _tab.evaluate(js)
            await asyncio.sleep(0.5)
            data = {"scrolled": direction}
            
        else:
            return TaskResponse(success=False, error="Unknown: " + request.task_type)
        
        return TaskResponse(success=True, data=data)
        
    except Exception as e:
        return TaskResponse(success=False, error=str(e))

@app.post("/shutdown")
async def shutdown():
    global _browser
    if _browser:
        _browser.stop()
    return {"status": "shutdown"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
EOF'