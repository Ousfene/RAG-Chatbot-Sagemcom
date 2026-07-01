# backend/fastapi_app.py
import sys
import traceback
import os
from pathlib import Path
from typing import List, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# --- Resolve paths so chatbot.py can be imported -----------------------
THIS_FILE = Path(__file__).resolve()
UI_ROOT = THIS_FILE.parent.parent  # .../UI
PROJECT_ROOT = UI_ROOT.parent

# make sure the project root / UI root are on sys.path
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# set working directory to project root so relative paths inside chatbot.py work
# (this ensures checks like os.path.exists("./pdfs/...") behave as expected)
os.chdir(str(PROJECT_ROOT))
print("FastAPI running with cwd =", os.getcwd())

try:
    from chatbot import get_chatbot_backend, get_bot_answer
except Exception as e:
    print("❌ ERROR importing chatbot.py")
    traceback.print_exc()
    raise RuntimeError("Make sure chatbot.py is inside UI/ or project root.") from e

# --- FastAPI app --------------------------------------------------------
app = FastAPI(title="Sagemcom Chatbot API")

# CORS: allow frontend dev server (React runs on 5173)
origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    # if you are testing from different host add it here or use ["*"] temporarily
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot backend once (expensive objects)
backend_objects = get_chatbot_backend()

# --- Request/response model --------------------------------------------
class ChatRequest(BaseModel):
    question: str
    # use a default_factory to avoid shared mutable default
    history: List[Any] = Field(default_factory=list)

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Main endpoint to talk with chatbot."""
    try:
        answer, sources_html = get_bot_answer(
            backend_objects, req.question, req.history or []
        )

        # defensive: ensure it's a str
        if sources_html is None:
            sources_html = ""

        # debug log — useful while troubleshooting missing sources
        print("CHAT REQUEST:", {"question": req.question, "history_len": len(req.history)})
        print("SOURCES_HTML (len=%d): %s" % (len(sources_html), sources_html[:1000]))

        return {"answer": f"✨ {answer}", "sources_html": sources_html}
    except Exception as e:
        tb = traceback.format_exc()
        print("Error in get_bot_answer():\n", tb)
        return JSONResponse(status_code=500, content={"answer": f"[ERROR] {e}", "sources_html": ""})
