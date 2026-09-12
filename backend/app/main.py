"""
FastAPI application. Run with:  uvicorn app.main:app --reload --port 8000
(exact command is in the top-level README).
"""
import io
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .schemas import GenerateRequest, GenerateResponse, HealthResponse
from . import pipeline
from . import db

app = FastAPI(
    title="PARG API",
    description="Process-Aware Requirement Generation — backend for the PARG demo UI.",
    version="1.0.0",
)

# Allows the Vite dev server (http://localhost:5173) to call this API from
# the browser. If you deploy the frontend somewhere else later, add that
# origin to this list.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _init_history_db():
    # Creates parg_history.db (and its tables) the first time the server
    # runs. Safe to call on every startup -- never touches existing rows.
    db.init_db()


@app.get("/health", response_model=HealthResponse)
def health():
    status = pipeline.startup_status()
    return HealthResponse(
        status=status["status"],
        ner_model_loaded=status["ner_model_loaded"],
        classifier_model_loaded=status["classifier_model_loaded"],
        num_process_concepts=status["num_process_concepts"],
        device=status["device"],
        error=status.get("error"),
    )


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    story = req.user_story.strip()
    if not story:
        raise HTTPException(status_code=400, detail="user_story must not be empty.")
    try:
        result = pipeline.run_pipeline(story)
    except (FileNotFoundError, RuntimeError) as e:
        # Missing/failed-to-load model or dataset files -- tell the user
        # exactly what to fix instead of a generic 500.
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PARG pipeline failed: {e}")

    # Save every successful result automatically. A storage failure should
    # never break the response the person is waiting on, so it's logged
    # rather than raised -- you still get your requirements even if, say,
    # the disk is full.
    try:
        submission_id = db.save_submission(result)
        result = dict(result)
        result["history_id"] = submission_id
    except Exception as e:
        print(f"[WARN] Failed to save submission to history database: {e}")

    return result


# ── History API ──────────────────────────────────────────────────────────
class HistoryListItem(BaseModel):
    id: int
    created_at: str
    user_story: str
    process_concept: str
    hybrid_score: float
    selection_status: str
    validation_status: str


class HistoryListResponse(BaseModel):
    total: int
    items: List[HistoryListItem]


@app.get("/history", response_model=HistoryListResponse)
def history_list(limit: int = 50, offset: int = 0):
    """Newest-first list of every story ever submitted, for the History page."""
    limit = max(1, min(limit, 200))
    return {"total": db.count_submissions(), "items": db.list_submissions(limit=limit, offset=offset)}


@app.get("/history/{submission_id}", response_model=GenerateResponse)
def history_detail(submission_id: int):
    """Full stored result for one past submission -- same shape as /generate,
    so the frontend's existing result view can display it unchanged."""
    result = db.get_submission(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No history entry with id {submission_id}.")
    return result


@app.delete("/history/{submission_id}")
def history_delete(submission_id: int):
    deleted = db.delete_submission(submission_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No history entry with id {submission_id}.")
    return {"deleted": True, "id": submission_id}


@app.get("/history/export/db")
def history_export_db():
    """Downloads the raw SQLite database file itself -- everything ever
    saved, in one file you can back up, move to another computer, or open
    with any SQLite browser."""
    if not db.os.path.isfile(db.DB_PATH):
        raise HTTPException(status_code=404, detail="No history database exists yet -- generate at least one story first.")
    return FileResponse(
        db.DB_PATH, media_type="application/x-sqlite3", filename="parg_history.db"
    )


@app.get("/history/export/xlsx")
def history_export_xlsx():
    """Downloads everything in history as a single-sheet Excel workbook --
    one row per generated requirement, with the story-level fields (Actor,
    Domain Entity, Condition, Outcome, scores, etc.) repeated on every row
    for that story, matching PARG_Dataset_v8.xlsx's own layout rather than
    splitting submissions and requirements into two linked sheets."""
    import pandas as pd
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    all_items = db.list_submissions(limit=db.count_submissions() or 1, offset=0)
    if not all_items:
        raise HTTPException(status_code=404, detail="No history to export yet -- generate at least one story first.")

    rows = []
    row_no = 1
    for item in reversed(all_items):  # oldest first in the export
        detail = db.get_submission(item["id"])
        for r in detail["requirements"]:
            rows.append({
                "Row No.": row_no,
                "Submission ID": detail["id"],
                "Created At": detail["created_at"],
                "User Story": detail["user_story"],
                "Process Concept": detail["process_concept"],
                "Ontology Hierarchy": detail["ontology_mapping"],
                "Actor": detail["ner"]["actor"]["text"],
                "Domain Entity": detail.get("domain_entity", ""),
                "Condition": detail["ner"]["condition"]["text"],
                "Outcome": detail["ner"]["outcome"]["text"],
                "Sequence Step": r["step"],
                "Step Purpose": r["step_purpose"],
                "Action Verb": r["action_verb"],
                "Generated Requirement (IEEE 830)": r["text"],
                "Model Confidence": detail["scoring"]["model_confidence"],
                "Ontology Similarity": detail["scoring"]["ontology_similarity"],
                "Hybrid Score": detail["scoring"]["hybrid_score"],
                "Selection Status": detail["scoring"]["selection_status"],
                "Auto-Repaired": r["repaired"],
                "Requires Review": r["requires_review"],
                "Validation Status": detail["validation"]["status"],
            })
            row_no += 1

    df = pd.DataFrame(rows)

    wb = Workbook()
    ws = wb.active
    ws.title = "PARG History"
    headers = list(df.columns)
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="2F5597")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for row in df.itertuples(index=False):
        ws.append(list(row))
    for r in range(2, len(df) + 2):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).font = Font(size=9)
            ws.cell(row=r, column=c).alignment = Alignment(vertical="top", wrap_text=True)
    widths = {
        "Row No.": 8, "Submission ID": 12, "Created At": 20, "User Story": 45,
        "Process Concept": 26, "Ontology Hierarchy": 38, "Actor": 18, "Domain Entity": 24,
        "Condition": 32, "Outcome": 32, "Sequence Step": 18, "Step Purpose": 26,
        "Action Verb": 12, "Generated Requirement (IEEE 830)": 55,
        "Model Confidence": 14, "Ontology Similarity": 14, "Hybrid Score": 12,
        "Selection Status": 22, "Auto-Repaired": 12, "Requires Review": 12, "Validation Status": 14,
    }
    for i, h in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(h, 16)
    ws.row_dimensions[1].height = 30

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=parg_history_export.xlsx"},
    )


# ── Serve the built frontend from this same server (single deployed URL) ──
# Only active when frontend/dist actually exists (i.e. `npm run build` was
# run and the result was copied next to this file -- see the Dockerfile and
# README Section 12). In local development (npm run dev on :5173), this
# folder won't exist, so this block does nothing and the two servers run
# separately as normal -- nothing about local dev changes.
import os
from fastapi.staticfiles import StaticFiles

_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend_dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
