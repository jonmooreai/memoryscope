#!/usr/bin/env python3
"""
Simple web server for the test app UI.
"""
import os
import sys
import json
import threading
import queue
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import deque

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_app.api_client import MemoryAPIClient
from test_app.openai_client import OpenAIDataGenerator
from test_app.rigorous_test_runner import RigorousTestRunner
# Lazy import for setup_test_api_key to avoid requiring database on startup
# from test_app.setup_test_api_key import load_test_api_key
from test_app.config import config as test_config
from datetime import datetime


app = FastAPI(title="Memory Scope API Test App")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TestConfig(BaseModel):
    api_url: str
    api_key: str
    openai_key: str
    num_users: int = 3
    memories_per_user: int = 10
    model: str = "gpt-4o-mini"


class TestStatus:
    """Global test status tracker with progress queue."""
    def __init__(self):
        self.running = False
        self.results = None
        self.error = None
        self.progress_queue = deque(maxlen=1000)  # Keep last 1000 progress updates
        self.lock = threading.Lock()
    
    def reset(self):
        with self.lock:
            self.running = False
            self.results = None
            self.error = None
            self.progress_queue.clear()
    
    def add_progress(self, progress: Dict[str, Any]):
        """Add a progress update."""
        with self.lock:
            self.progress_queue.append(progress)
    
    def get_recent_progress(self, since_index: int = 0) -> List[Dict[str, Any]]:
        """Get progress updates since a given index."""
        with self.lock:
            return list(self.progress_queue)[since_index:]


test_status = TestStatus()


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the test app UI."""
    ui_path = Path(__file__).parent / "ui.html"
    if ui_path.exists():
        return ui_path.read_text()
    else:
        return HTMLResponse("""
        <html>
            <head><title>Test App UI</title></head>
            <body>
                <h1>Test App UI</h1>
                <p>UI file not found. Please ensure ui.html exists in the test_app directory.</p>
            </body>
        </html>
        """)


@app.get("/chat", response_class=HTMLResponse)
async def get_chat_demo():
    """Serve the chat demo UI."""
    chat_path = Path(__file__).parent / "chat_demo.html"
    if chat_path.exists():
        return chat_path.read_text()
    else:
        return HTMLResponse("""
        <html>
            <head><title>Chat Demo</title></head>
            <body>
                <h1>Chat Demo</h1>
                <p>Chat demo file not found.</p>
            </body>
        </html>
        """)


@app.get("/chat/v2", response_class=HTMLResponse)
async def get_chat_demo_v2():
    """Serve the v2 chat demo UI."""
    chat_path = Path(__file__).parent / "chat_demo_v2.html"
    if chat_path.exists():
        return chat_path.read_text()
    else:
        return HTMLResponse("""
        <html>
            <head><title>Chat Demo v2</title></head>
            <body>
                <h1>Chat Demo v2</h1>
                <p>Chat demo v2 file not found.</p>
            </body>
        </html>
        """)


@app.get("/favicon.ico")
async def get_favicon():
    """Return empty favicon to prevent 404 errors."""
    from fastapi.responses import Response
    return Response(content=b"", media_type="image/x-icon")


def progress_callback(progress: Dict[str, Any]):
    """Callback for test progress updates."""
    test_status.add_progress(progress)


def run_test_in_background(config: TestConfig):
    """Run test in background thread."""
    try:
        # Initialize clients
        api_client = MemoryAPIClient(config.api_url, config.api_key)
        data_generator = OpenAIDataGenerator(config.openai_key)
        data_generator.model = config.model
        
        # Create rigorous test runner with progress callback
        runner = RigorousTestRunner(
            api_client, 
            data_generator,
            progress_callback=progress_callback
        )
        
        # Run tests
        runner.run_all_tests(
            num_users=config.num_users,
            memories_per_user=config.memories_per_user
        )
        
        # Store results
        test_status.results = {
            "store": runner.results["store"],
            "read": runner.results["read"],
            "merge": runner.results["merge"],
            "continue": runner.results.get("continue", {"success": 0, "failed": 0, "errors": [], "test_cases": []}),
            "revoke": runner.results["revoke"],
            "total_success": sum(r["success"] for r in runner.results.values()),
            "total_failed": sum(r["failed"] for r in runner.results.values()),
            "test_cases": {
                "store": runner.results["store"]["test_cases"],
                "read": runner.results["read"]["test_cases"],
                "merge": runner.results["merge"]["test_cases"],
                "revoke": runner.results["revoke"]["test_cases"],
            }
        }
        test_status.running = False
        
    except Exception as e:
        test_status.running = False
        test_status.error = str(e)
        import traceback
        test_status.add_progress({
            "phase": "error",
            "test_case": "Fatal Error",
            "status": "error",
            "details": {"error": str(e), "traceback": traceback.format_exc()},
            "timestamp": str(datetime.now())
        })


@app.post("/api/test/run")
async def run_test(config: TestConfig):
    """Run the test suite."""
    if test_status.running:
        raise HTTPException(status_code=400, detail="Test is already running")
    
    test_status.reset()
    test_status.running = True
    test_status.error = None
    
    # Run test in background thread
    thread = threading.Thread(target=run_test_in_background, args=(config,))
    thread.daemon = True
    thread.start()
    
    return JSONResponse({"status": "started", "message": "Test started in background"})


@app.get("/api/test/results")
async def get_test_results():
    """Get test results if available."""
    if test_status.running:
        raise HTTPException(status_code=202, detail="Test is still running")
    
    if test_status.error:
        raise HTTPException(status_code=500, detail=test_status.error)
    
    if test_status.results is None:
        raise HTTPException(status_code=404, detail="No test results available")
    
    return JSONResponse(test_status.results)


@app.get("/api/test/status")
async def get_test_status():
    """Get current test status."""
    return JSONResponse({
        "running": test_status.running,
        "results": test_status.results,
        "error": test_status.error,
    })


@app.get("/api/test/progress")
async def get_progress(since: int = 0):
    """Get progress updates since a given index."""
    progress = test_status.get_recent_progress(since)
    return JSONResponse({
        "progress": progress,
        "current_index": len(test_status.progress_queue),
        "running": test_status.running,
    })


@app.get("/api/config/defaults")
async def get_default_config():
    """Get default configuration values."""
    # Lazy import to avoid requiring database on startup
    try:
        from test_app.setup_test_api_key import load_test_api_key
        default_api_key = load_test_api_key()
    except Exception as e:
        # If database is not available, just use empty key
        default_api_key = ""
    return JSONResponse({
        "api_key": default_api_key or "",
        "api_url": "http://localhost:8000",
        "openai_api_key": test_config.openai_api_key or "",
    })


@app.get("/api/memories")
async def get_memories(user_id: Optional[str] = None, scope: Optional[str] = None, limit: int = 100):
    """Get stored memories (for display in UI)."""
    try:
        # Lazy import to avoid requiring database on startup
        from app.database import SessionLocal
        from app.models import Memory
        from sqlalchemy import desc
        from datetime import datetime
        
        db = SessionLocal()
        try:
            query = db.query(Memory)
            
            if user_id:
                query = query.filter(Memory.user_id == user_id)
            if scope:
                query = query.filter(Memory.scope == scope)
            
            # Get recent memories
            memories = query.order_by(desc(Memory.created_at)).limit(limit).all()
            
            result = []
            for mem in memories:
                result.append({
                    "id": str(mem.id),
                    "user_id": mem.user_id,
                    "scope": mem.scope,
                    "domain": mem.domain,
                    "value_json": mem.value_json,
                    "value_shape": mem.value_shape,
                    "source": mem.source,
                    "ttl_days": mem.ttl_days,
                    "created_at": mem.created_at.isoformat() if mem.created_at else None,
                    "expires_at": mem.expires_at.isoformat() if mem.expires_at else None,
                })
            
            return JSONResponse({"memories": result, "count": len(result)})
        finally:
            db.close()
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")


@app.post("/api/test/stop")
async def stop_test():
    """Stop the current test (if running)."""
    test_status.running = False
    return JSONResponse({"stopped": True})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

