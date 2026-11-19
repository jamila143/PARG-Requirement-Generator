# PARG — Process-Aware Requirement Generation

A web application that converts a single agile user story into structured, IEEE-830 style software requirements.

The pipeline combines a trained BERT process classifier, a trained BERT NER model, an ontology-based mapping system, and a hybrid scoring algorithm (Algorithm A1) to generate and validate requirements. No results are hard-coded or simulated.

---

## 1. Pipeline

```
User Story → Preprocessing → Process Classification → Ontology Mapping →
NER Extraction → Algorithm A1 Hybrid Scoring → Requirement Generation → Validation
```

**Output:** detected process concept, ontology mapping, extracted actor/action/condition/outcome, model confidence, ontology similarity, hybrid score, generated requirements, and validation results (duplicate, ambiguous-term, and coverage checks).

---

## 2. Architecture

| Layer | Stack |
| --- | --- |
| Backend | Python, FastAPI, PyTorch, Transformers. Loads the trained BERT-based models at startup and exposes `/generate` and `/health` endpoints. |
| Frontend | React + Vite. Sends the user story to the backend and renders the pipeline results. |

The frontend and backend run as separate local processes communicating over HTTP, with CORS enabled on the backend for the frontend's origin.

---

## 3. Project Structure

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
│       ├── db.py
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

---

## 4. Prerequisites

- Python 3.10+
- Node.js 18+ (with npm)

---

## 5. Data

PARG is trained and validated on two separate spreadsheets. Both must be referenced correctly — they are **not interchangeable**.

| Dataset | Purpose | Link |
| --- | --- | --- |
| **Main training dataset** (`PARG_Dataset_v8.xlsx`) | The source corpus the NER model and process classifier are trained, validated, and tested on. This is the file that must be placed in `backend/data/`. | [Open in Google Sheets](https://docs.google.com/spreadsheets/d/1ga7fO2jz31HtORJQlQRWrDNjG2eTqVHfBRlEIFyqG1Y/edit?usp=sharing) |
| **Expert validation dataset** | The separate review cohort used for independent human expert validation of the *generated* requirements (precision/recall/F1 reported in the paper). Not used for training. | [Open in Google Sheets](https://docs.google.com/spreadsheets/d/1Fha33LR5f4oN4HQPSpGtlTRybMZD0rEfiu8mKxvdRbU/edit?usp=sharing) |

> Download the main training dataset as `.xlsx` and place it at `backend/data/PARG_Dataset_Final.xlsx` before starting the backend (see Section 6/7). The expert validation dataset is only needed if you are reproducing the human-validation evaluation, not for running the app itself.

---

## 6. Model and Dataset Files

Download the trained checkpoints and place them in `backend/models/` using the exact filenames:

- NER model → `ner_model_state_dict.pt`
- Process classifier → `classifier_model_state_dict.pt`

Ensure `backend/data/PARG_Dataset_v8.xlsx` (see Section 5 for the link) is present and matches the exact dataset version used during training — **a mismatched dataset will cause a classifier checkpoint error.**

---

## 7. Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # Windows: copy .env.example .env
```

Confirm `.env` contains:

```
VITE_API_URL=http://localhost:8000
```

---

## 8. Running

**Terminal 1 — backend** (`parg-ui/backend`, venv active):

```bash
uvicorn app.main:app --reload --port 8000
```

On first run this downloads `bert-base-uncased` and `all-MiniLM-L6-v2`, then loads the local `.pt` checkpoints. Ready when the log shows `Application startup complete`.

**Terminal 2 — frontend** (`parg-ui/frontend`):

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). A "Backend Ready" indicator confirms a successful connection to `http://localhost:8000/health`.

---

## 9. Example

**Input**

```
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

**Example output**

- Process concept: `FundsTransferProcess`
- Ontology mapping: `Banking → PaymentSubDomain → FundsTransferProcess`
- Extracted actor/action/condition/outcome
- Model confidence, ontology similarity, and hybrid score (Algorithm A1)
- Generated requirements, e.g.:
  1. The system shall initiate the workflow associated with money online.
  2. The system shall validate money online against the required business rules and return a pass or fail result.
  3. The system shall check the bank customer's permissions before authorizing the operation on money online.
  4. The system shall process money online on behalf of the bank customer and confirm the outcome.
  5. The system shall send a notification about money online to the relevant stakeholders.
- Validation results: duplicate check, ambiguous-term check, coverage check

---

## 10. Troubleshooting

| Issue | Cause / Fix |
| --- | --- |
| "Backend not ready" | Check `backend/models/` (both `.pt` files) and `backend/data/` (`.xlsx`) are present |
| Classifier checkpoint mismatch error | `backend/data/` dataset differs from the one used for training; use the exact training file (Section 5) |
| CORS error | Confirm backend runs on port 8000 and frontend `.env` has `VITE_API_URL=http://localhost:8000` |
| Port already in use | Free the port or run with `--port 8001` and update frontend `.env` accordingly |
| `pip install` fails on torch | Install a CPU-only build from [pytorch.org/get-started](https://pytorch.org/get-started/locally/), then re-run `pip install -r requirements.txt` |

---

## 11. Technologies Used

- **Backend:** Python, FastAPI, PyTorch, Hugging Face Transformers, BERT
- **Frontend:** React, Vite, JavaScript, CSS
- **NLP/AI:** BERT-based process classification and NER, sentence embeddings, ontology mapping, hybrid scoring, automated requirement generation and validation
