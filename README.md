# PARG — Process-Aware Requirement Generation

A web application that converts a single agile user story into structured **IEEE-830 style software requirements**.

PARG uses:
- A trained **BERT Process Classifier** to detect the software process
- A trained **BERT NER model** to extract actors, actions, conditions, and outcomes
- An **ontology-based mapping system**
- **Algorithm A1** for hybrid scoring
- A requirement generation and validation pipeline

---

## 🔄 Input → Output

### Input

```text
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

### Processing Pipeline

```text
User Story
    ↓
Preprocessing
    ↓
Process Classification
    ↓
Ontology Mapping
    ↓
NER Extraction
    ↓
Algorithm A1 Hybrid Scoring
    ↓
Requirement Generation
    ↓
Requirement Validation
```

### Output

The application provides:
- Detected process concept
- Ontology mapping
- Extracted actor, action, condition, and outcome
- Model confidence
- Ontology similarity
- Hybrid score
- Generated software requirements
- Validation results

---

# 1. Architecture

## Backend

Built with:
- Python
- FastAPI
- PyTorch
- Transformers

The backend loads the trained BERT-based models at startup and provides API endpoints such as:

```text
/generate
/health
```

## Frontend

Built with:
- React
- Vite
- JavaScript
- CSS

The frontend accepts a user story, sends it to the FastAPI backend, and displays the PARG pipeline results.

## Communication

The frontend and backend run as separate local processes and communicate through HTTP.

```text
React + Vite
    │
    │ HTTP
    ↓
FastAPI Backend
    │
    ├── Process Classifier
    ├── NER Model
    ├── Ontology
    ├── Algorithm A1
    └── Requirement Generator
```

---

# 2. Project Structure

```text
parg-ui/
│
├── README.md
│
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
│
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

# 3. Prerequisites

Before running the application, make sure you have:

- **Python 3.10 or newer**
- **Node.js 18 or newer**
- **npm**

---

# 4. Download the Trained Models

The application requires two trained model checkpoints.

### 🧠 NER Model

[Download NER Model](https://drive.google.com/file/d/1jeuA_6PRuqWpEHu7hkudMuH8u_GreWEr/view?usp=sharing)

Save it as:

```text
ner_model_state_dict.pt
```

### 🧠 Process Classifier

[Download Process Classifier](https://drive.google.com/file/d/1Dqhwd-vBcWhCSs0D4gQVOsuYhHBZxbjx/view?usp=sharing)

Save it as:

```text
classifier_model_state_dict.pt
```

Place both files inside:

```text
backend/models/
```

Your folder should look like:

```text
backend/
└── models/
    ├── ner_model_state_dict.pt
    └── classifier_model_state_dict.pt
```

> **Important:** The filenames must match exactly.

---

# 5. Setup

## Backend

```bash
cd backend
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create the environment file.

### Windows

```bash
copy .env.example .env
```

### macOS / Linux

```bash
cp .env.example .env
```

Make sure `.env` contains:

```text
VITE_API_URL=http://localhost:8000
```

---

# 6. Run the Application

You need **two terminals** running at the same time.

## Terminal 1 — Backend

From `parg-ui/backend`:

```bash
uvicorn app.main:app --reload --port 8000
```

On the first run, the application may download:

```text
bert-base-uncased
all-MiniLM-L6-v2
```

The backend is ready when you see:

```text
Application startup complete.
```

## Terminal 2 — Frontend

From `parg-ui/frontend`:

```bash
npm run dev
```

Then open:

```text
http://localhost:5173
```

The **Backend Ready** indicator confirms that the frontend successfully connected to:

```text
http://localhost:8000/health
```

---

# 7. Example

## Input

```text
As a bank customer, I want to transfer money online so that I can pay my bills conveniently.
```

## Example Generated Requirements

```text
1. The system shall initiate the workflow associated with money online.

2. The system shall validate money online against the required business
   rules and return a pass or fail result.

3. The system shall check the bank customer's permissions before
   authorizing the operation on money online.

4. The system shall process money online on behalf of the bank customer
   and confirm the outcome.

5. The system shall send a notification about money online to the
   relevant stakeholders.
```

The actual output is generated by the PARG pipeline and is not hard-coded.

---

# 8. What the Application Shows

### Process Detection

Identifies the process concept from the user story.

Example:

```text
FundsTransferProcess
```

### Ontology Mapping

Maps the detected process into the ontology hierarchy.

Example:

```text
Banking
   ↓
PaymentSubDomain
   ↓
FundsTransferProcess
```

### NER Extraction

Extracts important elements such as:

```text
Actor
Action
Condition
Outcome
```

### Hybrid Scoring

The application calculates scores based on:

- Model confidence
- Ontology similarity
- Hybrid scoring using Algorithm A1

### Requirement Generation

The identified process information is converted into structured software requirements.

### Validation

The generated requirements are checked using:

- Duplicate requirement check
- Ambiguous-term check
- Coverage check

---

# 9. Dataset

The project uses:

```text
backend/data/PARG_Dataset_v8.xlsx
```

Make sure the dataset is present at:

```text
backend/data/PARG_Dataset_v8.xlsx
```

> **Important:** Use the same dataset version that was used during model training. A different dataset may cause classifier checkpoint mismatch errors.

---

# 10. Troubleshooting

| Problem | Possible Solution |
|---|---|
| **Backend not ready** | Make sure both `.pt` model files are inside `backend/models/` and the dataset is inside `backend/data/`. |
| **Classifier checkpoint mismatch** | Make sure you are using the correct `PARG_Dataset_v8.xlsx` file used during training. |
| **CORS error** | Make sure the backend is running on port `8000` and `VITE_API_URL=http://localhost:8000` is set in `.env`. |
| **Port already in use** | Stop the process using the port or run the backend on another port, such as `8001`. |
| **Frontend cannot connect to backend** | Check that the FastAPI backend is running and that `VITE_API_URL` points to the correct backend URL. |
| **`pip install` fails for PyTorch** | Install a compatible CPU-only PyTorch build from [PyTorch](https://pytorch.org/get-started/locally/), then run `pip install -r requirements.txt` again. |

---

# 11. Technologies Used

### Backend
- Python
- FastAPI
- PyTorch
- Hugging Face Transformers
- BERT

### Frontend
- React
- Vite
- JavaScript
- CSS

### NLP / AI
- BERT-based Process Classification
- BERT-based Named Entity Recognition
- Sentence Embeddings
- Ontology Mapping
- Hybrid Scoring
- Automated Requirement Generation
- Requirement Validation

---

# 12. Important Notes

- The trained model files are **not included directly in the repository**.
- Download the two model checkpoints using the links provided above.
- Place them in `backend/models/` with the exact filenames.
- The dataset file must be available in `backend/data/`.
- The frontend and backend must both be running for the web application to work.
- The generated requirements come from the PARG pipeline rather than predefined hard-coded results.

---

# 13. Quick Start

If the models and dataset are already available:

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

## 🚀 PARG

**PARG — Process-Aware Requirement Generation**

Converts agile user stories into structured software requirements using NLP, process classification, ontology mapping, NER, hybrid scoring, and automated requirement generation.
