# PARG — Process-Aware Requirement Generation

A web application that converts a single agile user story into structured, IEEE-830 style software requirements.

The pipeline combines a trained BERT process classifier, a trained BERT NER model, an ontology-based mapping system, and a hybrid scoring algorithm (Algorithm A1) to generate and validate requirements. No results are hard-coded or simulated.

## 1. Pipeline

```
User Story → Preprocessing → Process Classification → Ontology Mapping →
NER Extraction → Algorithm A1 Hybrid Scoring → Requirement Generation → Validation
```

**Output:** detected process concept, ontology mapping, extracted actor/action/condition/outcome, model confidence, ontology similarity, hybrid score, generated requirements, and validation results (duplicate, ambiguous-term, and coverage checks).

## 2. Architecture

- **Backend** — Python, FastAPI, PyTorch, Transformers. Loads the trained BERT-based models at startup and exposes `/generate` and `/health` endpoints.
- **Frontend** — React + Vite. Sends the user story to the backend and renders the pipeline results.
- The frontend and backend run as separate local processes communicating over HTTP, with CORS enabled on the backend for the frontend's origin.

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

## 4. Prerequisites

- Python 3.10+
- Node.js 18+ (with npm)

## 5. Model and Dataset Files

Download the trained checkpoints and place them in `backend/models/` using the exact filenames:

- [NER model](https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing) → `ner_model_state_dict.pt`
- [Process classifier](https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing) → `classifier_model_state_dict.pt`

Ensure `backend/data/PARG_Dataset_v8.xlsx` is present and matches the exact dataset version used during training — a mismatched dataset will cause a classifier checkpoint error.

## 6. Setup

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

Confirm `.env` contains:
```
VITE_API_URL=http://localhost:8000
```

## 7. Running

**Terminal 1 — backend** (`parg-ui/backend`, venv active):
```bash
uvicorn app.main:app --reload --port 8000
```
On first run this downloads `bert-base-uncased` and `all-MiniLM-L6-v2`, then loads the local `.pt` checkpoints. Ready when the log shows `Application startup complete.`

**Terminal 2 — frontend** (`parg-ui/frontend`):
```bash
npm run dev
```

Open `http://localhost:5173`. A "Backend Ready" indicator confirms a successful connection to `http://localhost:8000/health`.

## 8. Example

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
  ```
  1. The system shall initiate the workflow associated with money online.
  2. The system shall validate money online against the required business rules and return a pass or fail result.
  3. The system shall check the bank customer's permissions before authorizing the operation on money online.
  4. The system shall process money online on behalf of the bank customer and confirm the outcome.
  5. The system shall send a notification about money online to the relevant stakeholders.
  ```
- Validation results: duplicate check, ambiguous-term check, coverage check

## 9. Technologies Used

- **Backend:** Python, FastAPI, PyTorch, Hugging Face Transformers, BERT
- **Frontend:** React, Vite, JavaScript, CSS
- **NLP/AI:** BERT-based process classification and NER, sentence embeddings, ontology mapping, hybrid scoring, automated requirement generation and validation
