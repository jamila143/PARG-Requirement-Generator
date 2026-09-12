<<<<<<< HEAD
# PARG Requirement Generation — Web UI

This is a web interface around your existing PARG pipeline (the models and dataset from
`PARG_Kaggle_Pipeline_v6.ipynb`). You type in one user story, and it runs the real PARG
pipeline — preprocessing → process classification → ontology mapping → NER extraction →
Algorithm A1 hybrid scoring → requirement generation → validation — and shows you the result.

**Nothing in this app is hard-coded.** The process concept, ontology mapping, scores, and
generated requirements all come from your actual trained models and dataset. If a model file
is missing, the app tells you exactly that — it does not fall back to fake data.

## What changed in this revision (reliability pass)

You reported inconsistent extraction quality across different story types. Two of those were
real bugs, now fixed, and the rest are now handled by being explicit instead of silent:

- **Fixed a real span-extraction bug**: the NER span decoder used to collect *every* word
  anywhere in the sentence tagged with a given label and join them together. If the model
  mistagged one stray, non-adjacent word with the same label, it got glued onto the real span —
  that was your "mixing parts of the sentence" symptom. It now decodes proper contiguous BIO
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
  turns your PARG pipeline into an API the browser can call. It loads your trained BERT models
  (via the `transformers` library, the same one the notebook uses) once when it starts, then
  answers requests using them.
- **Frontend**: React + [Vite](https://vitejs.dev/) — Vite is a tool that runs a local
  development web server for a React app and rebuilds it instantly as you edit files. Plain CSS
  for styling (no extra UI framework to learn).
- The frontend and backend are two **separate processes** that talk over HTTP on your own
  computer (`localhost`). You will run two terminal windows.

## 2. Complete folder structure

You already have all of this — it was generated for you. Here is what everything is:

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

## 3. Where your existing PARG code goes

Your PARG pipeline lives in `PARG_Kaggle_Pipeline_v6.ipynb`, which you run on Kaggle (it needs
a GPU to train). This app does **not** retrain anything — it loads the two files Kaggle's
**Cell 20** already exports for you and runs them for inference (predicting on new text), which
is fast enough to run on a normal laptop CPU.

**Step-by-step, after your Kaggle notebook run finishes:**

1. On Kaggle, go to your notebook's **Output** tab (or the `parg_outputs/` folder Cell 20
   creates).
2. Download these two files:
   - `ner_model_state_dict.pt`
   - `classifier_model_state_dict.pt`
3. Put them in `parg-ui/backend/models/` (replacing the placeholder `.txt` file there).
4. `PARG_Dataset_v8.xlsx` is already included in `parg-ui/backend/data/` for you. **Only
   replace it if you trained on a different copy of the dataset** — the classifier's output
   numbers only line up with the correct process-concept names if this is the exact dataset
   the model was trained on.
5. *(Optional)* Also copy `run_config_and_headline_metrics.json` from Cell 20's output into
   `parg-ui/backend/data/` — if present, the backend will tell you the alpha/beta the
   notebook's own grid search found, so you can compare it with what this app uses.

That's it — `backend/app/pipeline.py` does the loading and inference. You do not need to write
or change any model code yourself.

### If a component is missing

I inspected the notebook you built. Everything the UI needs already exists in it:

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

Nothing was missing, so nothing here is a stand-in implementation — it's your pipeline's own
logic, reused.

**One design choice worth knowing about:** Algorithm A1's hybrid score is *reported* next to the
model's prediction, but it does **not** override which process concept gets selected — the
classifier's own top-1 prediction is always used. This is because an earlier version of your
notebook tried using the hybrid score to switch predictions and it reduced accuracy by about 40
points (a single story's ontology-similarity score turned out to be a much noisier signal than
the classifier's own confidence). Showing both scores honestly, without letting the noisier one
silently override the trained model, is the safer design your own experiment pointed to.

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

## 6. Exact commands to start everything

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

## 7. What URL to open

Open your browser to:

```
http://localhost:5173
```

You should see the PARG interface with a "Backend ready" badge at the top if both servers
started correctly (it checks `http://localhost:8000/health` automatically). If it says "Backend
not ready," re-check step 3 (model/dataset files) and look at Terminal 1 for the exact error.

## 8. Testing it with one sample story

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

## 9. Troubleshooting

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

## 10. Applying this update if you already have it running

Nothing about your trained models or dataset changed — only the backend's inference code
(`backend/app/pipeline.py`, `schemas.py`, `main.py`) and the frontend display components. If
you already had the app running:

1. Replace your local `backend/app/` folder and `frontend/src/` folder with the ones in this
   zip (your `backend/models/` and `backend/data/` folders — the actual model weights and
   dataset — don't need to change).
2. If `uvicorn --reload` is already running, it should pick up the backend changes
   automatically; if not, stop it (Ctrl+C) and restart with the same command as before.
3. Refresh the frontend page in your browser (Vite's dev server hot-reloads automatically while
   `npm run dev` is running).

No retraining, no new model files, no dataset changes required.

## 11. History (every submission is saved automatically)

Every time you click **Generate Requirements**, the full result — the story, the extracted
actor/action/condition/outcome, the scores, every generated requirement, and the validation
result — is saved automatically to a local database file: `backend/parg_history.db`. No setup
needed; it's created the first time the server starts.

**Where to find it:** click the **History** tab at the top of the page. It lists every story
you've ever submitted, newest first, with its process concept, hybrid score, and validation
status. Click any entry to view its full saved result again — actor/action/condition/outcome,
scores, generated requirements, everything, exactly as it looked the first time. Click
**Delete** on an entry to remove it permanently.

**Downloading your history:** two buttons at the top of the History tab —
- **Download as Excel** — a single-sheet `.xlsx`, one row per generated requirement, with the
  story-level fields (Actor, Domain Entity, Condition, Outcome, scores) repeated on every row —
  same layout style as `PARG_Dataset_v8.xlsx`, not split across multiple linked sheets.
- **Download database file** — the raw `parg_history.db` file itself, useful for backing up
  everything or moving it to another computer.

**Technical notes, if you're curious:**
- It's SQLite (Python's built-in database), not a separate server you need to run.
- Two tables: `submissions` (one row per story) and `requirements` (one row per generated
  requirement, linked to its story).
- If saving to history ever fails for some reason (e.g. disk full), it will not break your
  actual result — you'll still see your generated requirements, just with a warning printed in
  the backend terminal instead of the entry being saved.
- Want to inspect the database directly? With the backend stopped, run:
  ```bash
  cd backend
  python -c "import sqlite3; c = sqlite3.connect('parg_history.db'); print(c.execute('SELECT COUNT(*) FROM submissions').fetchone())"
  ```
- To start over with an empty history, just delete `backend/parg_history.db` while the server
  is stopped — a fresh one will be created next time you start it.
=======
# PARG-Requirement-Generator
An NLP-based Process-Aware Requirement Generation system
>>>>>>> f97ae06f10b2fefacd035ccd0331b4e2898e03db
