"""
Configuration for the PARG backend.

Every path here is where YOU (the beginner following the README) put your own
files. Nothing in this file is a placeholder to "figure out" — it is exact
paths relative to the `backend/` folder, matching the folder structure in the
README.
"""
import os
import torch

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Put your PARG_Dataset_v8.xlsx (or v7/v6) here. The dataset is REQUIRED even
# though the models are trained, because it is where the ontology (process
# concepts, sub-domains, step templates) and the process-concept label list
# come from — the classifier's output indices only mean something in
# combination with this file.
DATASET_PATH = os.path.join(DATA_DIR, "PARG_Dataset_v8.xlsx")

# Put the two files exported by Cell 20 of PARG_Kaggle_Pipeline_v6.ipynb here:
#   ner_model_state_dict.pt
#   classifier_model_state_dict.pt
NER_MODEL_PATH = os.path.join(MODELS_DIR, "ner_model_state_dict.pt")
CLASSIFIER_MODEL_PATH = os.path.join(MODELS_DIR, "classifier_model_state_dict.pt")

# Optional: Cell 20 also exports run_config_and_headline_metrics.json, which
# records the ALPHA/BETA the notebook's own grid search found. If you place a
# copy of it here, the backend will report (but NOT silently switch to) that
# value alongside the formula you specified. If it is absent, this is simply
# skipped.
RUN_CONFIG_PATH = os.path.join(DATA_DIR, "run_config_and_headline_metrics.json")

# ── Model architecture (must match training exactly) ────────────────────
BERT_MODEL = "bert-base-uncased"
NER_LABELS = ["O", "B-ACTOR", "I-ACTOR", "B-ACTION", "B-COND", "I-COND", "B-OUT", "I-OUT"]
NER_LABEL2ID = {l: i for i, l in enumerate(NER_LABELS)}
NER_ID2LABEL = {i: l for l, i in NER_LABEL2ID.items()}
MAX_LEN = 64
NER_MAX_LEN = 96
MIN_SAMPLES_PER_CLASS = 8  # must match the notebook's Cell 7 MIN_SAMPLES, or
                           # the label list rebuilt here will not line up
                           # with the class indices the classifier was
                           # trained on.

# ── Algorithm A1 hyperparameters ────────────────────────────────────────
# Per your explicit instruction: Hybrid Score = 0.55 * C_model + 0.45 * S_ontology.
# This is a REPORTED confidence indicator alongside the top-1 prediction. It
# is deliberately NOT used to override which process concept gets selected —
# an earlier version of the underlying notebook tried hard-switching the
# prediction based on a similar hybrid score and it reduced accuracy by ~40
# points (documented in the notebook's "Lessons Learned" cell), because a
# single held-out story's ontology similarity is a much noisier signal than
# the classifier's own top-1 confidence. Reporting both scores, transparently,
# without letting the noisier one silently override the model, is the safer
# design confirmed by that experiment.
ALPHA = float(os.environ.get("PARG_ALPHA", 0.55))
BETA = float(os.environ.get("PARG_BETA", 0.45))
# NOTE ON THIS THRESHOLD (found by reviewing a real training run): with label
# smoothing applied during classifier training, softmax confidence is
# systematically compressed even for correct predictions -- on one real run,
# the classifier was 100% accurate on its test set, yet a naive fixed 0.45
# threshold flagged 96.5% of predictions as "low confidence" purely because
# of that compression, not genuine uncertainty. The notebook's Cell 12
# recalibrates this threshold empirically per-checkpoint (from the
# validation-set confidence distribution of correct predictions) before
# generating requirements. If you retrain the classifier, check that
# notebook cell's printed "new calibrated threshold" value and set
# PARG_THETA to match here, rather than trusting this default blindly.
CONFIDENCE_THRESHOLD = float(os.environ.get("PARG_THETA", 0.45))

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

DUP_SIMILARITY_THRESHOLD = 0.92
AMBIGUOUS_TERMS = [
    "appropriate", "sufficient", "as needed", "user-friendly",
    "easy to use", "quickly", "efficiently", "etc", "and so on",
]
