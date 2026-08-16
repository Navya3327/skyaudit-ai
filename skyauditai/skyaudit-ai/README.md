# SkyAudit AI

The AI Site Engineer for Drone Pilots & Local Contractors.
Built for the Build with Gemini XPRIZE Hackathon.

## Day 1 setup (do this today)

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Gemini API key
cp .env.example .env
# then edit .env and paste your key from https://aistudio.google.com/apikey

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

Check it's alive:
```bash
curl http://localhost:8000/health
```

## Test the analysis pipeline

```bash
curl -X POST http://localhost:8000/analyze \
  -F "images=@/path/to/thermal_frame1.jpg" \
  -F "images=@/path/to/rgb_frame1.jpg" \
  -F "voice_note=@/path/to/pilot_note.mp3" \
  -F "text_context=Panel array installed 2019, no known prior issues"
```

Response includes a `request_id` - use that to test the copilot follow-up:

```bash
curl -X POST http://localhost:8000/copilot/<request_id> \
  -F "question=Which defect should I fix first and why?"
```

## What's built vs. what's next

**Built (Day 1 MVP):**
- Multimodal Gemini analysis: thermal + RGB images + pilot voice note + text context -> structured JSON findings
- Root cause, severity, energy loss, revenue loss, repair cost, and priority per defect
- Basic copilot chat over a completed report
- Request logging to `product evidence/api_usage.log` (real production evidence for judging)

**Not yet built (see project plan for day-by-day schedule):**
- Payment/checkout integration
- PDF report generation (technical + plain-language)
- Frontend upload UI
- Cloud Run deployment
- Map overlay of defect locations

## Git workflow - commit as you go

Don't wait until the project is "done" to start using git. Commit daily so your
history actually shows continuous development during the hackathon period
(judges may check this, and it protects your own work from being lost).

```bash
git add .
git commit -m "Day 1: multimodal Gemini analysis pipeline + FastAPI backend"
```

When you're ready to make it visible to judges (public repo, or private +
shared with testing@devpost.com and judging@hacker.fund):

```bash
git remote add origin https://github.com/<your-username>/skyaudit-ai.git
git branch -M main
git push -u origin main
```

You can keep the remote private early on and flip it to public (or add the
judging/testing collaborators) later in Week 3 - the important thing is that
your local commit history starts today, not on submission day.

## Product evidence

The `product evidence/` folder collects logs proving the app ran in production,
not just once for a demo. Keep committing `api_usage.log` (and add dashboard
screenshots here later) as you go - this directly maps to a required Devpost
submission field.
