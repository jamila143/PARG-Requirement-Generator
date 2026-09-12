# PARG-Requirement-Generator

An NLP-based Process-Aware Requirement Generation system — a web interface around a trained
PARG pipeline (the models and dataset from `PARG_Kaggle_Pipeline_v6.ipynb`). You type in one
user story, and it runs the real PARG pipeline — preprocessing → process classification →
ontology mapping → NER extraction → Algorithm A1 hybrid scoring → requirement generation →
validation — and shows you the result.

**Nothing in this app is hard-coded.** The process concept, ontology mapping, scores, and
generated requirements all come from the actual trained models and dataset. If a model file is
missing, the app tells you exactly that — it does not fall back to fake data.

## What changed in this revision (reliability pass)

Inconsistent extraction quality was reported across different story types. Two of those were
real bugs, now fixed, and the rest are now handled by being explicit instead of silent:

- **Fixed a real span-extraction bug**: the NER span decoder used to collect *every* word
  anywhere in the sentence tagged with a given label and join them together. If the model
  mistagged one stray, non-adjacent word with the same label, it got glued onto the real span —
  that was the "mixing parts of the sentence" symptom. It now decodes proper contiguous BIO
  runs and keeps the longest one, ignoring stray fragments elsewhere in the sentence.
- **Per-span confidence + quality gates**: each extracted actor/action/condition/outcome now
  carries the model's own confidence. Condition/outcome spans below a confidence threshold, or
  shorter than 2 tokens, are treated as unreliable and excluded from the generated requirement
  text rather than stitched in as a garbled fragment.
- **Low-confidence process predictions are now flagged, not hidden**: if the classifier's
  confidence is below the threshold, the process concept is marked "tentative" in the UI and a
  top-level warning is shown, instead of presenting an uncertain guess as a settled fact.
- **Expanded post-generation validation**: beyond duplicate and ambiguous-term checks, it now
  runs a grammar check (sentence structure, repeated words, double spaces, length sanity), a
  semantic-relevance check (does the requirement actually reference the extracted entity?), and
  a traceability check (does every generated step's verb genuinely belong to that process
  concept's own ontology template?). Every issue found is listed specifically, not just a
  pass/fail flag.
- **Session coverage vs. Algorithm A2 coverage are now explicitly distinguished** in both the
  API response and the UI text — the running "concepts touched this session" counter was never
  the notebook's full-dataset coverage metric, and the wording now says so directly instead of
  letting the two be confused.

## 1. What technology this uses

- **Backend**: Python + [FastAPI](https://fastapi.tiangolo.com/) — a Python web framework that
  turns the PARG pipeline into an API the browser can call. It loads the trained BERT models
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
│   │   └── PARG_Dataset_v8.xlsx       <- already included
│   ├── models/
│   │   ├── ner_model_state_dict.pt    <- download separately, see Section 3
│   │   └── classifier_model_state_dict.pt   <- download separately, see Section 3
│   └── app/
│       ├── __init__.py
│       ├── config.py                  <- paths and hyperparameters
│       ├── nlp_utils.py               <- tokenization/preprocessing (ported from the notebook)
│       ├── ontology.py                <- ontology + requirement-generation vocabulary (ported)
│       ├── pipeline.py                <- loads the models and runs the full PARG flow
│       ├── db.py                      <- local SQLite history storage
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
            ├── ValidationPanel.jsx
            └── HistoryPanel.jsx
```

## 3. Download the trained models

The two trained model files are **not** in this repository — each is ~430MB, and GitHub blocks
any file over 100MB. Download them here:

- **NER model**: [ner_model_state_dict.pt](https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing)
- **Process classifier**: [classifier_model_state_dict.pt](https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing)

After downloading, place both files directly in `backend/models/` (replacing the placeholder
`.txt` file there).

`backend/data/PARG_Dataset_v8.xlsx` is already included in this repo — **only replace it if
you trained on a different copy of the dataset**, since the classifier's output numbers only
line up with the correct process-concept names if this is the exact dataset the model was
trained on.

*(Optional)* If you have `run_config_and_headline_metrics.json` from the notebook's Cell 20
output, you can also copy that into `backend/data/` — if present, the backend will report the
notebook's own grid-searched alpha/beta alongside the values it's actually using.

**Retraining instead?** The pipeline lives in `PARG_Kaggle_Pipeline_v6.ipynb`, run on Kaggle
(needs a GPU). This app does not retrain anything itself — it only loads the two files Kaggle's
Cell 20 exports and runs them for inference, which is fast enough on a normal laptop CPU.

### What each part of the pipeline comes from

| UI needs | Comes from |
|---|---|
| Preprocessing | Notebook Cell 5's `preprocess()` — ported into `backend/app/nlp_utils.py` |
| Process classifier | Notebook Cell 10's trained `BertForSequenceClassification` — loaded from the `.pt` file |
| Process labels | Notebook Cell 7's label list — rebuilt in `backend/app/ontology.py` from the dataset |
| Ontology mapping | Notebook Cell 4's ontology dict — rebuilt from the dataset |
| NER (actor/action/condition/outcome) | Notebook Cell 8's trained `BertForTokenClassification` — loaded from the `.pt` file |
| Algorithm A1 (α, β, θ) | Notebook Cell 11 — reimplemented in `backend/app/pipeline.py` using `Hybrid = 0.55 × confidence + 0.45 × similarity` |
| Requirement generation | Notebook Cell 12's template logic — ported into `backend/app/ontology.py` |
| Validation / coverage | Notebook Cell 13's duplicate + coverage checks — reimplemented per-request in `backend/app/pipeline.py` |

**One design choice worth knowing about:** Algorithm A1's hybrid score is *reported* next to the
model's prediction, but it does **not** override which process concept gets selected — the
classifier's own top-1 prediction is always used. An earlier design tried using the hybrid score
to switch predictions and it reduced accuracy by about 40 points (a single story's
ontology-similarity score turned out to be a much noisier signal than the classifier's own
confidence). Showing both scores honestly, without letting the noisier one silently override the
trained model, is the safer design that experiment pointed to.

## 4. How the frontend talks to the backend

The React app runs at `http://localhost:5173` (Vite's default). The Python API runs at
`http://localhost:8000` (FastAPI's default with the command below). When you click **Generate
Requirements**, the browser sends a `POST` request to `http://localhost:8000/generate` with your
story as JSON, and the backend sends back JSON with the results. `frontend/src/api.js` is the
only file that does this — everything else just displays what it returns.

This only works because the backend explicitly allows the frontend's address to talk to it (look
for `CORSMiddleware` in `backend/app/main.py` — CORS is a browser security rule that blocks
requests between different addresses unless the server says it's OK).

## 5. Installing everything

You need **Python 3.10+** and **Node.js 18+** installed first. If you don't have them: Python
from [python.org](https://www.python.org/downloads/), Node.js from
[nodejs.org](https://nodejs.org/) (choose the LTS version).

Open a terminal and navigate to the `parg-ui` folder:

```bash
cd path/to/parg-ui
```

### Backend setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

- **Windows**: `venv\Scripts\activate` (if PowerShell blocks this, run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first)
- **Mac/Linux**: `source venv/bin/activate`

You should see `(venv)` at the start of your terminal prompt. Then:

```bash
pip install -r requirements.txt
```

This downloads FastAPI, PyTorch, Transformers, and the other libraries the pipeline needs — can
take several minutes and a few GB of disk space the first time.

### Frontend setup

Open a **second terminal window**:

```bash
cd path/to/parg-ui/frontend
npm install
cp .env.example .env
```

(`cp` is Mac/Linux; on Windows PowerShell use `copy .env.example .env`.)

## 6. Exact commands to start everything

**Terminal 1 — backend** (from inside `parg-ui/backend`, with the virtual environment active):

```bash
uvicorn app.main:app --reload --port 8000
```

The first run downloads `bert-base-uncased` and `all-MiniLM-L6-v2` automatically (needs
internet once), then loads the two `.pt` files. Wait for `Application startup complete.`

**Terminal 2 — frontend** (from inside `parg-ui/frontend`):

```bash
npm run dev
```

You'll see a line like `Local: http://localhost:5173/`.

## 7. What URL to open

```
http://localhost:5173
```

You should see a green **"Backend ready"** badge at the top if both servers started correctly
(it checks `http://localhost:8000/health` automatically). If it says "Backend not ready,"
re-check Section 3 (model/dataset files) and look at Terminal 1 for the exact error — it will
now report the real reason (e.g. "NER model weights not found at ...") rather than a generic
failure.

## 8. Testing it with one sample story

```
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

Click **Generate Requirements**. Within a few seconds you should see the detected process
concept, ontology mapping, extracted actor/action/condition/outcome, confidence/similarity/
hybrid score bars, a numbered list of generated requirements, and a validation section.

Try **Copy requirements** and **Download .txt**, and try clicking **Generate** with an empty box
to see the warning message.

## 9. Troubleshooting

- **"Backend not ready" / red badge**: check `http://localhost:8000/health` directly in your
  browser — it reports the specific reason. Almost always a missing file: re-check
  `backend/models/` has both `.pt` files and `backend/data/` has the `.xlsx`.
- **"The classifier checkpoint was trained on N process concepts, but..."**: the
  `backend/data/` dataset isn't the exact one the model was trained on.
- **CORS error in the browser console**: make sure the backend is running on port 8000 and
  `frontend/.env` has `VITE_API_URL=http://localhost:8000`.
- **Port already in use**: change the port in the `uvicorn` command (`--port 8001`) and update
  `frontend/.env` to match.
- **`pip install` fails on `torch`**: loosen the version pin in `requirements.txt` to
  `torch>=2.2` and re-run — a hard-pinned version can be unavailable for newer Python releases.
- **Every new terminal window needs re-activation**: `venv\Scripts\activate` only applies to
  the terminal window it was run in — opening a new window means running it again.

## 10. History (every submission is saved automatically)

Every time you click **Generate Requirements**, the full result — the story, the extracted
actor/action/condition/outcome, the scores, every generated requirement, and the validation
result — is saved automatically to a local database file: `backend/parg_history.db`. No setup
needed; it's created the first time the server starts, and stays there permanently across
restarts unless you delete an entry yourself.

**Where to find it:** click the **History** tab at the top of the page. It lists every story
submitted, newest first, with its process concept, hybrid score, and validation status. Click
any entry to view its full saved result again. Click **Delete** on an entry to remove it
permanently.

**Downloading your history:** two buttons at the top of the History tab —
- **Download as Excel** — a single-sheet `.xlsx`, one row per generated requirement, with the
  story-level fields (Actor, Domain Entity, Condition, Outcome, scores) repeated on every row —
  same layout style as `PARG_Dataset_v8.xlsx`, not split across multiple linked sheets.
- **Download database file** — the raw `parg_history.db` file itself, useful for backing up
  everything or moving it to another computer.

**Technical notes:**
- SQLite (Python's built-in database) — no separate server to run.
- Two tables: `submissions` (one row per story) and `requirements` (one row per generated
  requirement, linked to its story).
- If saving to history ever fails (e.g. disk full), it will not break your actual result — a
  warning is printed in the backend terminal instead.
- To start over with an empty history, delete `backend/parg_history.db` while the server is
  stopped — a fresh one is created next time it starts.
