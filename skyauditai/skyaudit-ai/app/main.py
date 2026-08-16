"""
SkyAudit AI - minimal FastAPI backend.

Day 1 goal: a working /analyze endpoint you can hit with curl or a simple
form to prove the Gemini multimodal pipeline works end-to-end. UI, payment,
and Cloud deployment get layered on in later days per the plan.
"""

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.gemini_service import analyze_inspection, ask_copilot

# --- basic logging setup so you have "production evidence" from day one ---
os.makedirs("product evidence", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("product evidence/api_usage.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("skyaudit")

app = FastAPI(title="SkyAudit AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before public launch
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory store for demo purposes; swap for a real DB before scaling up
_reports: dict[str, dict] = {}


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/analyze")
async def analyze(
    images: list[UploadFile] = File(..., description="Thermal and/or RGB footage frames"),
    voice_note: Optional[UploadFile] = File(None, description="Optional pilot voice note"),
    text_context: Optional[str] = Form(None, description="Optional manual/context text"),
):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    logger.info(f"[{request_id}] analyze request received: {len(images)} image(s), "
                f"voice_note={'yes' if voice_note else 'no'}")

    image_bytes_list = []
    image_mime_types = []
    for img in images:
        image_bytes_list.append(await img.read())
        image_mime_types.append(img.content_type or "image/jpeg")

    audio_bytes = None
    audio_mime_type = None
    if voice_note is not None:
        audio_bytes = await voice_note.read()
        audio_mime_type = voice_note.content_type or "audio/mpeg"

    report = analyze_inspection(
        image_bytes_list=image_bytes_list,
        image_mime_types=image_mime_types,
        audio_bytes=audio_bytes,
        audio_mime_type=audio_mime_type,
        text_context=text_context,
    )

    _reports[request_id] = report
    elapsed = round(time.time() - start, 2)
    logger.info(f"[{request_id}] analysis complete in {elapsed}s, "
                f"{len(report.get('defects', []))} defect(s) found")

    return {"request_id": request_id, "elapsed_seconds": elapsed, "report": report}


@app.post("/copilot/{request_id}")
async def copilot(request_id: str, question: str = Form(...)):
    """Tier 2: chat over a previously generated report."""
    report = _reports.get(request_id)
    if report is None:
        return {"error": f"No report found for request_id={request_id}"}

    logger.info(f"[{request_id}] copilot question: {question!r}")
    answer = ask_copilot(report, question)
    return {"request_id": request_id, "question": question, "answer": answer}


@app.get("/reports/{request_id}")
def get_report(request_id: str):
    report = _reports.get(request_id)
    if report is None:
        return {"error": f"No report found for request_id={request_id}"}
    return {"request_id": request_id, "report": report}
