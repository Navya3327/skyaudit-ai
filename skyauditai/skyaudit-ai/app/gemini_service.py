"""
SkyAudit AI - Gemini multimodal analysis service.

Takes thermal/RGB footage (as image bytes), an optional pilot voice note
(as audio bytes), and optional free-text context, and returns a
structured inspection finding as JSON.

Uses the google-genai SDK (client.models.generate_content), which supports
mixing text, image, and audio Parts in a single call.
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_MODEL = "gemini-3-flash-preview"  # good balance of speed/cost for report generation

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Lazy-init the Gemini client so importing this module doesn't require
    an API key to be set (useful for tests / no-key local dev)."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
                "from https://aistudio.google.com/apikey"
            )
        _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are SkyAudit AI, an expert solar/roofing thermal inspection
analyst. You are given thermal imagery and/or RGB imagery of a solar array or
roof, and may also receive a pilot's spoken field note and/or technical
documentation context.

Analyze the imagery and any notes, then return ONLY a single JSON object
(no markdown fences, no commentary) with this exact shape:

{
  "defects": [
    {
      "id": "string, short identifier e.g. 'Panel 14' or 'Section C'",
      "defect_type": "string, e.g. 'hotspot', 'cell degradation', 'delamination'",
      "root_cause": "string, your best-evidence explanation of WHY this occurred",
      "severity": "one of: Critical, High, Medium, Low",
      "confidence": "number 0-1, your confidence in this finding",
      "estimated_annual_energy_loss_kwh": "number, estimate, or null if not estimable",
      "estimated_annual_revenue_loss_usd": "number, estimate, or null if not estimable",
      "estimated_repair_cost_usd": "number, estimate, or null if not estimable",
      "recommended_action": "string, concrete next step",
      "recommended_timeframe": "string, e.g. 'within 30 days'"
    }
  ],
  "overall_summary_technical": "2-4 sentences, technical audience",
  "overall_summary_plain_language": "2-4 sentences, non-technical customer audience",
  "notes_used_pilot_audio": "boolean - did you incorporate the audio note, if provided"
}

If you cannot make a confident numeric estimate, use null rather than guessing
wildly. Be conservative and evidence-based - this output may be shown directly
to a paying customer."""


def analyze_inspection(
    image_bytes_list: list[bytes],
    image_mime_types: list[str],
    audio_bytes: Optional[bytes] = None,
    audio_mime_type: Optional[str] = None,
    text_context: Optional[str] = None,
) -> dict:
    """
    Run one multimodal Gemini call over the uploaded footage + optional voice
    note + optional text context (e.g. equipment manual excerpt, weather note).

    Returns the parsed JSON dict described in SYSTEM_PROMPT.
    """
    client = get_client()

    parts: list = [types.Part.from_text(text=SYSTEM_PROMPT)]

    for img_bytes, mime in zip(image_bytes_list, image_mime_types):
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    if audio_bytes and audio_mime_type:
        parts.append(types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type))
        parts.append(types.Part.from_text(
            text="Above is the pilot's spoken field note. Incorporate it into your analysis."
        ))

    if text_context:
        parts.append(types.Part.from_text(text=f"Additional context/documentation:\n{text_context}"))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            temperature=0.2,  # low temperature - this is a factual analysis task, not creative
            response_mime_type="application/json",
        ),
    )

    raw_text = response.text.strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: Gemini occasionally wraps JSON in fences despite instructions
        cleaned = raw_text.strip("`").replace("json\n", "", 1).strip()
        return json.loads(cleaned)


def ask_copilot(report_json: dict, question: str) -> str:
    """
    Tier 2 feature: chat over an already-generated report.
    Takes the structured report + a follow-up question, returns a plain-text answer.
    """
    client = get_client()
    prompt = f"""You are the SkyAudit AI inspection copilot. Here is the full
inspection report you previously generated (as JSON):

{json.dumps(report_json, indent=2)}

The customer now asks: "{question}"

Answer helpfully and specifically, referencing the relevant defect(s) by id.
Keep the answer conversational and under 150 words."""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(temperature=0.3),
    )
    return response.text.strip()
