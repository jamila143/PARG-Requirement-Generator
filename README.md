# PARG Requirement Generation — Web UI

A web application for the **PARG (Process-Aware Requirement Generation)** pipeline.

Enter a user story and the app performs:

**Preprocessing → Process Classification → Ontology Mapping → NER Extraction → Algorithm A1 Scoring → Requirement Generation → Validation**

The application uses the trained PARG models and dataset. It does not use fake or hard-coded prediction results.



## 1. What technology this uses

- **Backend**: Python + [FastAPI](https://fastapi.tiangolo.com/) — a Python web framework that
  turns your PARG pipeline into an API the browser can call. It loads your trained BERT models
  (via the `transformers` library, the same one the notebook uses) once when it starts, then
  answers requests using them.
- **Frontend**: React + [Vite](https://vitejs.dev/) — Vite is a tool that runs a local
  development web server for a React app and rebuilds it instantly as you edit files. Plain CSS
  for styling (no extra UI framework to learn).
- The frontend and backend are two **separate processes** that talk over HTTP on your own
  computer (`localhost`). You will run two terminal windows.

## 2. Complete folder structure


```
parg-ui/
├── README.md                          <- this file
├── backend/
│   ├── requirements.txt               <- Python packages to install
│   ├── data/
│   │   └── PARG_Dataset_v8.xlsx       <- already included for you
│   ├── models/
│   │   ├── ner_model_state_dict.pt    <- YOU place this here (from Kaggle)
│   │   └── classifier_model_state_dict.pt   <- YOU place this here (from Kaggle)
│   └── app/
│       ├── __init__.py
│       ├── config.py                  <- paths and hyperparameters
│       ├── nlp_utils.py               <- tokenization/preprocessing (ported from the notebook)
│       ├── ontology.py                <- ontology + requirement-generation vocabulary (ported)
│       ├── pipeline.py                <- loads your models and runs the full PARG flow
│       ├── schemas.py                 <- defines the shape of the API's JSON
│       └── main.py                    <- the FastAPI app itself (the "/generate" endpoint)
└── frontend/
    ├── package.json                   <- JavaScript dependencies
    ├── vite.config.js
    ├── index.html
    ├── .env.example                   <- copy this to .env
    └── src/
        ├── main.jsx                   <- React entry point
        ├── App.jsx                    <- main page component
        ├── api.js                     <- talks to the backend
        ├── styles.css                 <- all styling
        └── components/
            ├── InputPanel.jsx
            ├── PipelineStepper.jsx
            ├── ProcessAnalysis.jsx
            ├── ScoringPanel.jsx
            ├── RequirementsList.jsx
            └── ValidationPanel.jsx
```

## 4. Download the trained models

The app needs two trained model files. You can download them from Google Drive:

- **NER model:** [Download NER model](https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing)
- **Process classifier:** [Download Process Classifier](https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing)

After downloading, place the files in:

```text
backend/models/
├── ner_model_state_dict.pt
└── classifier_model_state_dict.pt
```

> Rename the downloaded files to the exact names above if they have different names.



### What the application uses

Everything needed by the UI comes from your existing PARG notebook and trained models:

| UI needs | Comes from |
|---|---|
| Preprocessing | Cell 5's `preprocess()` — ported into `backend/app/nlp_utils.py` |
| Process classifier | Cell 10's trained `BertForSequenceClassification` — loaded from your `.pt` file |
| Process labels | Cell 7's label list — rebuilt in `backend/app/ontology.py` from your dataset |
| Ontology mapping | Cell 4's ontology dict — rebuilt from your dataset |
| NER (actor/action/condition/outcome) | Cell 8's trained `BertForTokenClassification` — loaded from your `.pt` file |
| Algorithm A1 (α, β, θ) | Cell 11 — reimplemented in `backend/app/pipeline.py` using **your specified formula**, `Hybrid = 0.55 × confidence + 0.45 × similarity` |
| Requirement generation | Cell 12's template logic — ported into `backend/app/ontology.py` |
| Validation / coverage | Cell 13's duplicate + coverage checks — reimplemented per-request in `backend/app/pipeline.py` |


**One design choice worth knowing about:** Algorithm A1's hybrid score is *reported* next to the
model's prediction, but it does **not** override which process concept gets selected — the
classifier's own top-1 prediction is always used. This is because an earlier version of your
notebook tried using the hybrid score to switch predictions and it reduced accuracy by about 40
points (a single story's ontology-similarity score turned out to be a much noisier signal than
the classifier's own confidence). Showing both scores honestly, without letting the noisier one
silently override the trained model, is the safer design your own experiment pointed to.

## 5. How the frontend talks to the backend

The React app runs at `http://localhost:5173` (Vite's default). The Python API runs at
`http://localhost:8000` (FastAPI's default with the command below). When you click **Generate
Requirements**, the browser sends a `POST` request to `http://localhost:8000/generate` with your
story as JSON, and the backend sends back JSON with the results. `frontend/src/api.js` is the
only file that does this — everything else just displays what it returns.

This only works because the backend explicitly allows the frontend's address to talk to it (look
for `CORSMiddleware` in `backend/app/main.py` — CORS is a browser security rule that blocks
requests between different addresses unless the server says it's OK).

## 6. Installing everything

You need **Python 3.10+** and **Node.js 18+** installed on your computer first. If you don't have
them: Python from [python.org](https://www.python.org/downloads/), Node.js from
[nodejs.org](https://nodejs.org/) (choose the LTS version). Installers for both are
double-click-and-follow-the-prompts.

Open a terminal (Command Prompt / PowerShell on Windows, Terminal on Mac/Linux), and navigate to
the `parg-ui` folder:

```bash
cd path/to/parg-ui
```

### Backend setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment (a private, isolated copy of Python for this project only):

- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

You should now see `(venv)` at the start of your terminal prompt. Then install the Python
packages:

```bash
pip install -r requirements.txt
```

This downloads FastAPI, PyTorch, Transformers, and the other libraries the pipeline needs. It
can take several minutes and a few GB of disk space the first time — that's normal.

### Frontend setup

Open a **second terminal window** (leave the first one's virtual environment as is), and:

```bash
cd path/to/parg-ui/frontend
npm install
cp .env.example .env
```

(`cp` is Mac/Linux; on Windows PowerShell use `copy .env.example .env`.)

## 7. Exact commands to start everything

**Terminal 1 — backend** (from inside `parg-ui/backend`, with the virtual environment active):

```bash
uvicorn app.main:app --reload --port 8000
```

Wait for the server to finish loading — the first time it downloads `bert-base-uncased` and
`all-MiniLM-L6-v2` automatically (needs internet access once), then loads your two `.pt` files.
When it's ready you'll see log lines ending in something like `Application startup complete.`

**Terminal 2 — frontend** (from inside `parg-ui/frontend`):

```bash
npm run dev
```

You'll see a line like `Local: http://localhost:5173/`.

## 8. What URL to open

Open your browser to:

```
http://localhost:5173
```

You should see the PARG interface with a "Backend ready" badge at the top if both servers
started correctly (it checks `http://localhost:8000/health` automatically). If it says "Backend
not ready," re-check step 3 (model/dataset files) and look at Terminal 1 for the exact error.

## 9. Testing it with one sample story

Paste this into the text area:

```
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

Click **Generate Requirements**. Within a few seconds you should see:

- The detected process concept (e.g. `FundsTransferProcess`)
- The ontology mapping (e.g. `Banking → PaymentSubDomain → FundsTransferProcess`)
- Extracted actor/action/condition/outcome
- Model confidence, ontology similarity, and hybrid score bars
- A numbered list of generated requirements
- A validation section (duplicate check, ambiguous-term check, session coverage)

Try the **Copy requirements** and **Download .txt** buttons, and try clicking **Generate** with
an empty box to see the warning message.

## 10. Troubleshooting

- **"Backend not ready" / red badge**: Terminal 1 will show why. Almost always it's a missing
  file — re-check `backend/models/` has both `.pt` files and `backend/data/` has your `.xlsx`.
- **"The classifier checkpoint was trained on N process concepts, but..."**: your
  `backend/data/` dataset isn't the exact one the model was trained on. Use the same file you
  trained with in the Kaggle notebook.
- **CORS error in the browser console**: make sure the backend is running on port 8000 and the
  frontend's `.env` file has `VITE_API_URL=http://localhost:8000` (see `frontend/.env.example`).
- **Port already in use**: another program is using 8000 or 5173. Stop it, or change the port
  in the `uvicorn` command (`--port 8001`) and update `frontend/.env` to match.
- **`pip install` fails on `torch`**: on some machines you may need a CPU-only PyTorch build —
  see [pytorch.org/get-started](https://pytorch.org/get-started/locally/) for the exact command
  for your OS, then re-run `pip install -r requirements.txt` for the rest.



