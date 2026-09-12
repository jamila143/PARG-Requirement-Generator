# PARG — Process-Aware Requirement Generation

A web app that turns a single agile user story into structured, IEEE-830 software requirements,
using a trained BERT classifier (process detection), a trained BERT NER model (actor/action/
condition/outcome extraction), and an ontology-based generator.

## Input → Output

**Input:** one user story, e.g.

```
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

**Output:**

- Detected process concept (e.g. `FundsTransferProcess`) and its ontology mapping
  (`Banking → PaymentSubDomain → FundsTransferProcess`)
- Extracted actor, action, condition, outcome
- Model confidence / ontology similarity / hybrid score
- A numbered list of generated requirements, e.g.:
  1. *The system shall validate the account holder's transfer request.*
  2. *The system shall notify the account holder, so that they can pay their bills conveniently.*

## Folder structure

```
parg-ui/
├── backend/
│   ├── requirements.txt
│   ├── data/PARG_Dataset_v8.xlsx
│   ├── models/                  <- place the two .pt files here (see below)
│   └── app/
│       ├── config.py
│       ├── nlp_utils.py
│       ├── ontology.py
│       ├── pipeline.py          <- loads the models, runs the PARG pipeline
│       ├── db.py                <- saves every submission locally
│       ├── schemas.py
│       └── main.py              <- FastAPI app
└── frontend/
    ├── package.json
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
```

## Download the trained models

- **NER model:** https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing
- **Process classifier:** https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing

Place both in `backend/models/`.

## Setup

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows; Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (second terminal):
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open **http://localhost:5173**.
