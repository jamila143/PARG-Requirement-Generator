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

## 4. Where your existing PARG code goes

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

Nothing was missing, so nothing here is a stand-in implementation — it's your pipeline's own
logic, reused.

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

## 11. Applying this update if you already have it running

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

## 12. History (every submission is saved automatically)

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

## 13. Deploying a real public link (Hugging Face Spaces)

This turns your local-only app into a single public URL anyone can open directly — no terminal,
no localhost, works from any device.

**Why Hugging Face Spaces specifically, not a generic free host:** your two model files need
roughly 1-2GB of RAM to run together, and most free hosting tiers (Render, Railway, etc.) only
give 512MB-1GB, which usually isn't enough. Hugging Face's free CPU tier gives considerably more
headroom and is built for exactly this kind of model-serving app. It's also entirely free for a
CPU Space like this one.

This repo already includes a `Dockerfile` that builds the frontend and backend into **one**
container serving both from a single URL — you don't need to host them separately.

### Steps

1. Go to **https://huggingface.co** and create a free account (or sign in).
2. Click your profile picture → **New Space**.
3. Fill in:
   - **Space name**: anything, e.g. `parg-requirement-generator`
   - **License**: your choice
   - **Space SDK**: choose **Docker** → **Blank**
   - **Visibility**: Public
4. Click **Create Space**. You'll land on an empty repo page with git clone instructions.
5. On your computer, clone that new (empty) Space repo, then copy this project's files into it:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/parg-requirement-generator
   cd parg-requirement-generator
   ```
   Copy `backend/`, `frontend/`, and `Dockerfile` from this project into that folder.
6. **Set up Git LFS for the model files** (required — they're too big for a normal git commit):
   ```bash
   git lfs install
   git lfs track "*.pt"
   git add .gitattributes
   ```
7. Make sure your two `.pt` files are actually in `backend/models/` in this folder (unlike the
   GitHub repo, this one should include them directly).
8. Commit and push:
   ```bash
   git add .
   git commit -m "Deploy PARG"
   git push
   ```
9. Go back to your Space's page on huggingface.co — it will automatically start building the
   Docker image (you can watch the build log there). This takes several minutes the first time.
10. Once it says **Running**, your app is live at:
    ```
    https://huggingface.co/spaces/YOUR_USERNAME/parg-requirement-generator
    ```
    That's the link you can send to anyone — they open it in a browser, no setup on their end.

### Notes

- The free CPU tier can be slower than your own laptop for the first request after the Space has
  been idle (it "sleeps" and needs to reload the models) — subsequent requests are fast.
- If the build fails, the Space's **Logs** tab shows exactly why (usually a missing dependency
  or a file that didn't get committed) — paste that error if you get stuck.
- This is separate from your GitHub repo (Section 3) — the GitHub repo is your public *source
  code* (without the large model files, per its `.gitignore`); the Hugging Face Space is the
  *running app* (with the model files, since Spaces support them via Git LFS).
=======

>>>>>>> a4727731ade4a0fd092022c020cee367c6608bb3
