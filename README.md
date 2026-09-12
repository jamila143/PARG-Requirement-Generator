# PARG Requirement Generation — Web UI

A web application for the **PARG (Process-Aware Requirement Generation)** pipeline. Given a user story, the system performs:

**Preprocessing → Process Classification → Ontology Mapping → NER Extraction → Algorithm A1 Scoring → Requirement Generation → Validation**

The application uses the trained PARG models and dataset; no results are hard-coded or simulated.

## 1. Architecture

- **Backend**: Python + FastAPI. Loads the trained BERT-based models (via `transformers`) once at startup and exposes a `/generate` endpoint.
- **Frontend**: React + Vite. Sends the user story to the backend and renders the returned pipeline results.
- The two run as separate local processes communicating over HTTP (`localhost`), with CORS enabled on the backend for the frontend's origin.

## 2. Folder Structure

```
parg-ui/
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── data/
│   │   └── PARG_Dataset_v8.xlsx
│   ├── models/
│   │   ├── ner_model_state_dict.pt
│   │   └── classifier_model_state_dict.pt
│   └── app/
│       ├── config.py
│       ├── nlp_utils.py
│       ├── ontology.py
│       ├── pipeline.py
│       ├── schemas.py
│       └── main.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── api.js
        ├── styles.css
        └── components/
            ├── InputPanel.jsx
            ├── PipelineStepper.jsx
            ├── ProcessAnalysis.jsx
            ├── ScoringPanel.jsx
            ├── RequirementsList.jsx
            └── ValidationPanel.jsx
```

## 3. Prerequisites

- Python 3.10+
- Node.js 18+

## 4. Model Files

Download the trained model checkpoints and place them in `backend/models/` using the exact filenames below:

- [NER model](https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing) → `ner_model_state_dict.pt`
- [Process classifier](https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing) → `classifier_model_state_dict.pt`

## 5. Setup

**Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env          # Windows: copy .env.example .env
```

## 6. Running

**Terminal 1 — backend** (`parg-ui/backend`, venv active):
```bash
uvicorn app.main:app --reload --port 8000
```
On first run this downloads `bert-base-uncased` and `all-MiniLM-L6-v2`, then loads the local `.pt` checkpoints. Ready when the log shows `Application startup complete.`

**Terminal 2 — frontend** (`parg-ui/frontend`):
```bash
npm run dev
```

Open `http://localhost:5173`. A "Backend ready" badge confirms the backend health check (`http://localhost:8000/health`) succeeded.

## 7. Example

Input:
```
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

Output includes: detected process concept (e.g. `FundsTransferProcess`), ontology mapping (`Banking → PaymentSubDomain → FundsTransferProcess`), extracted actor/action/condition/outcome, model confidence / ontology similarity / hybrid score, generated requirements, and validation results (duplicate check, ambiguous-term check, coverage check).

## 8. Troubleshooting

| Issue | Cause / Fix |
|---|---|
| "Backend not ready" | Check `backend/models/` (both `.pt` files) and `backend/data/` (`.xlsx`) are present |
| Classifier checkpoint mismatch error | `backend/data/` dataset differs from the one used for training; use the exact training file |
| CORS error | Confirm backend runs on port 8000 and `frontend/.env` has `VITE_API_URL=http://localhost:8000` |
| Port already in use | Free the port or run with `--port 8001` and update `frontend/.env` accordingly |
| `pip install` fails on `torch` | Install a CPU-only build from [pytorch.org/get-started](https://pytorch.org/get-started/locally/), then re-run `pip install -r requirements.txt` |
