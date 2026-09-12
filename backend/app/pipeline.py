"""
The actual PARG pipeline: loads your trained NER model and process classifier
(the .pt files exported by Cell 20 of PARG_Kaggle_Pipeline_v6.ipynb) plus the
dataset (for the ontology and process-concept label list), and runs one user
story through the same stages as the notebook:

  preprocess -> classify process concept -> ontology mapping ->
  NER extraction (actor/action/condition/outcome) -> hybrid scoring ->
  requirement generation -> validation

Everything here is REAL model inference — nothing is hard-coded or simulated.
If a model file is missing, the relevant functions raise a clear error rather
than silently returning fake numbers (see `startup_status()`).
"""
import os
import re
import threading

import torch
import torch.nn.functional as F
from transformers import BertTokenizer, BertForTokenClassification, BertForSequenceClassification

from . import config
from . import ontology as onto
from .nlp_utils import preprocess, word_tokenize

_lock = threading.Lock()
_state = {
    "loaded": False,
    "error": None,
    "df_raw": None,
    "ONTOLOGY": {},
    "ONTOLOGY_DOMAIN_OF": {},
    "ALL_PROCESSES": [],
    "STEP_TEMPLATE": {},
    "LABELS": [],
    "story_entity_fallback": {},
    "tokenizer": None,
    "ner_model": None,
    "cls_model": None,
    "sbert": None,
    "prototype_emb": None,  # tensor [num_classes, dim]
    "run_config": None,
    "session_covered_processes": set(),
}


def _load_everything():
    # BUG FIXED HERE: this used to permanently cache a failed load attempt
    # (via "or _state['error']") and silently no-op on every call after
    # that -- so if loading failed once (e.g. a model file wasn't in place
    # yet), fixing the actual problem and trying again never re-attempted
    # loading. /generate would then proceed with cls_model/ner_model still
    # None and crash with a confusing "'NoneType' object is not callable"
    # instead of a clear "still not loaded" message. Loading is safe to
    # retry (a still-missing file just fails again quickly), so this now
    # retries every time it hasn't succeeded yet, and clears any stale error
    # before trying.
    if _state["loaded"]:
        return

    with _lock:
        if _state["loaded"]:
            return
        _state["error"] = None
        try:
            if not os.path.isfile(config.DATASET_PATH):
                raise FileNotFoundError(
                    f"Dataset not found at {config.DATASET_PATH}. Put "
                    f"PARG_Dataset_v8.xlsx in backend/data/."
                )
            df_raw = onto.load_dataset(config.DATASET_PATH)
            ONTOLOGY, ONTOLOGY_DOMAIN_OF, ALL_PROCESSES, STEP_TEMPLATE = onto.build_ontology(df_raw)
            LABELS = onto.build_label_list(df_raw, config.MIN_SAMPLES_PER_CLASS)
            story_entity_fallback = (
                df_raw.drop_duplicates("User Story ID").set_index("User Story ID")["Domain Entity"].to_dict()
            )

            tokenizer = BertTokenizer.from_pretrained(config.BERT_MODEL)

            if not os.path.isfile(config.NER_MODEL_PATH):
                raise FileNotFoundError(
                    f"NER model weights not found at {config.NER_MODEL_PATH}. "
                    f"Export ner_model_state_dict.pt from Cell 20 of the notebook "
                    f"and place it in backend/models/."
                )
            ner_model = BertForTokenClassification.from_pretrained(
                config.BERT_MODEL, num_labels=len(config.NER_LABELS)
            )
            ner_model.load_state_dict(torch.load(config.NER_MODEL_PATH, map_location=config.DEVICE))
            ner_model.to(config.DEVICE).eval()

            if not os.path.isfile(config.CLASSIFIER_MODEL_PATH):
                raise FileNotFoundError(
                    f"Classifier weights not found at {config.CLASSIFIER_MODEL_PATH}. "
                    f"Export classifier_model_state_dict.pt from Cell 20 of the "
                    f"notebook and place it in backend/models/."
                )
            cls_model = BertForSequenceClassification.from_pretrained(
                config.BERT_MODEL, num_labels=len(LABELS)
            )
            state_dict = torch.load(config.CLASSIFIER_MODEL_PATH, map_location=config.DEVICE)
            head_shape = state_dict.get("classifier.weight")
            if head_shape is not None and head_shape.shape[0] != len(LABELS):
                raise ValueError(
                    f"The classifier checkpoint was trained on {head_shape.shape[0]} process "
                    f"concepts, but rebuilding the label list from your dataset with "
                    f"MIN_SAMPLES_PER_CLASS={config.MIN_SAMPLES_PER_CLASS} gives "
                    f"{len(LABELS)} concepts. This means the dataset in backend/data/ is not "
                    f"the exact one the model was trained on (or MIN_SAMPLES_PER_CLASS in "
                    f"backend/app/config.py does not match the notebook's Cell 7 MIN_SAMPLES). "
                    f"Use the same PARG_Dataset_v8.xlsx you trained on in the notebook."
                )
            cls_model.load_state_dict(state_dict)
            cls_model.to(config.DEVICE).eval()

            from sentence_transformers import SentenceTransformer, util as st_util
            sbert = SentenceTransformer("all-MiniLM-L6-v2", device=str(config.DEVICE))

            # Class-prototype embeddings for S_ontology. NOTE: rebuilt here from
            # ALL stories per concept in the dataset (the original train/val/test
            # split is not persisted by the notebook), so this is a close but not
            # byte-identical reproduction of Cell 11's prototypes. The notebook's
            # own reported test-set numbers remain the authoritative evaluation.
            df_stories = df_raw.drop_duplicates("User Story ID").copy()
            df_stories["cleaned_story"] = df_stories["Agile User Story"].apply(preprocess)
            prototype_emb = torch.zeros(len(LABELS), sbert.get_sentence_embedding_dimension())
            for i, concept in enumerate(LABELS):
                texts = df_stories.loc[df_stories["Process Concept"] == concept, "cleaned_story"].tolist()
                if texts:
                    emb = sbert.encode(texts, convert_to_tensor=True, show_progress_bar=False)
                    prototype_emb[i] = emb.mean(dim=0)

            run_config = None
            if os.path.isfile(config.RUN_CONFIG_PATH):
                import json
                with open(config.RUN_CONFIG_PATH) as f:
                    run_config = json.load(f)

            _state.update({
                "df_raw": df_raw, "ONTOLOGY": ONTOLOGY, "ONTOLOGY_DOMAIN_OF": ONTOLOGY_DOMAIN_OF,
                "ALL_PROCESSES": ALL_PROCESSES, "STEP_TEMPLATE": STEP_TEMPLATE, "LABELS": LABELS,
                "story_entity_fallback": story_entity_fallback, "tokenizer": tokenizer,
                "ner_model": ner_model, "cls_model": cls_model, "sbert": sbert,
                "prototype_emb": prototype_emb, "run_config": run_config, "loaded": True,
            })
        except Exception as e:
            _state["error"] = str(e)
            raise


def startup_status() -> dict:
    """Called by /health. Tries to load everything; reports what succeeded."""
    try:
        _load_everything()
    except Exception:
        pass
    return {
        "status": "ready" if _state["loaded"] else "not_ready",
        "ner_model_loaded": _state["ner_model"] is not None,
        "classifier_model_loaded": _state["cls_model"] is not None,
        "num_process_concepts": len(_state["LABELS"]),
        "device": str(config.DEVICE),
        "error": _state["error"],
    }


def _require_loaded():
    """Called at the start of every /generate request. Unlike the old
    version, this NEVER silently proceeds if loading didn't actually
    succeed -- it raises the real underlying reason (missing file, shape
    mismatch, etc.) so the caller gets a clear 503 with an actionable
    message instead of a cryptic crash deep inside model inference."""
    if _state["loaded"]:
        return
    try:
        _load_everything()
    except Exception:
        pass  # the specific exception is already stored in _state["error"]
    if not _state["loaded"]:
        raise RuntimeError(
            _state["error"] or "Models/dataset failed to load for an unknown reason. "
            "Check the backend terminal output."
        )


# ── NER inference for one story: hybrid Condition/Outcome extraction ────
# BUG FIXED: the previous version collected EVERY word anywhere in the
# sentence tagged with a given label and joined them together. If the model
# mistagged one stray, non-adjacent word with the same label, it got glued
# onto the real span -- producing exactly the "mixing parts of the sentence"
# symptom. Fixed by decoding proper contiguous BIO runs.
#
# ARCHITECTURE for Condition/Outcome (per the recommended design): the BIO
# model remains the primary extractor (it is responsible for understanding
# the sentence); a linguistic layer only CORRECTS boundary errors around
# known connector words, and a scoring layer decides whether the resulting
# candidate is trustworthy enough to feed into Algorithm A1 / requirement
# generation, or should be flagged/rejected instead:
#
#   BIO NER -> span reconstruction -> boundary detection (connector-anchored)
#   -> candidate scoring (BIO confidence + connector presence + grammatical
#   completeness + verbatim-in-story check) -> accept / flag / reject
#
# Actor/Action do not go through the boundary-detection step (they are not
# clause-shaped the way conditions/outcomes are), but do go through the same
# contiguous-span decoding and confidence gating.

MIN_SPAN_CONFIDENCE = 0.55        # actor/action: below this, flagged low_confidence
_REPEATED_WORD_RE = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
_DOUBLE_SPACE_RE = re.compile(r"\s{2,}")
MIN_SPAN_TOKENS_FOR_CLAUSE = 2    # condition/outcome shorter than this = noise

CONDITION_CONNECTORS = [
    "provided that", "only if", "in case", "as long as", "given that",
    "if", "when", "before", "after", "while", "unless", "once", "until",
]
OUTCOME_CONNECTORS = [
    "in order that", "to ensure that", "resulting in", "so as to",
    "so that", "such that", "thereby", "to ensure",
]
CLAUSE_BOUNDARY_TOKENS = {".", ",", ";"}
MAX_BOUNDARY_EXTENSION = 10        # don't let boundary correction run away

# BUG FOUND (reviewing a real notebook run's hard-pattern test suite): a
# multi-clause outcome ("...so that the team stays informed and so that
# compliance requirements are met.") extracted "team stays informed and" --
# the forward boundary-extension loop correctly stops just before the second
# "so that" connector (to avoid merging two distinct clauses), but leaves the
# connecting word immediately before it ("and") dangling on the end. Trimmed
# in a dedicated post-processing pass, applied after boundary correction.
_DANGLING_TRAILING_WORDS = {
    "and", "or", "but", "so", "that", "the", "a", "an", "to", "of", "for",
    "with", "on", "in", "if", "when", "unless", "while", "because",
}


def _trim_dangling(words_slice):
    """Trims trailing connective/filler words from a list of words (operates
    on the word list, not text, so it can report how many were trimmed)."""
    words_slice = list(words_slice)
    while words_slice and words_slice[-1].lower() in _DANGLING_TRAILING_WORDS:
        words_slice.pop()
    return words_slice

# Candidate-scoring weights and decision thresholds.
W_BIO_CONF, W_CONNECTOR, W_GRAMMAR, W_VERBATIM = 0.40, 0.25, 0.20, 0.15
ACCEPT_THRESHOLD = 0.60
FLAG_THRESHOLD = 0.35


def _decode_bio_span(word_labels, tag):
    """Returns the (start, end) index of the LONGEST contiguous BIO run for
    `tag`, or None. Contiguity is the fix for the old "mixing parts of the
    sentence" bug -- a stray, non-adjacent mislabeled token no longer gets
    glued onto the real span."""
    spans = []
    i, n = 0, len(word_labels)
    while i < n:
        if word_labels[i] == f"B-{tag}":
            start = i
            j = i + 1
            while j < n and word_labels[j] == f"I-{tag}":
                j += 1
            spans.append((start, j - 1))
            i = j
        else:
            i += 1
    if not spans:
        return None
    return max(spans, key=lambda se: se[1] - se[0])


def _match_connector(words_lower, idx, connectors, direction=1):
    """Checks if a (possibly multi-word) connector phrase starts at `idx`
    when reading in `direction` (1 = forward, -1 = backward search anchor).
    Returns the connector's (start, end) index span if matched, else None."""
    for connector in sorted(connectors, key=len, reverse=True):
        c_words = connector.split()
        span = c_words if direction == 1 else list(reversed(c_words))
        end = idx + len(span) - 1
        if direction == 1:
            if end < len(words_lower) and words_lower[idx:idx + len(span)] == c_words:
                return (idx, idx + len(span) - 1)
        else:
            start = idx - len(span) + 1
            if start >= 0 and words_lower[start:idx + 1] == c_words:
                return (start, idx)
    return None


def _boundary_correct(words, words_lower, start, end, connectors, other_connectors):
    """Linguistic boundary-detection layer: looks a short distance BEFORE the
    model's predicted start for a connector word the model may have clipped
    (e.g. model predicts "processing the medical claim" but the sentence
    reads "before processing the medical claim" -- the connector "before" is
    restored), and extends AFTER the model's predicted end up to the next
    clause boundary (comma/period/semicolon) or the start of a different
    connector's clause, so a truncated span like "before processing the" is
    completed to "before processing the medical claim" instead of being left
    mid-phrase. This never invents words -- everything added comes from the
    original story text between the existing indices."""
    corrected_start, corrected_end = start, end
    boundary_corrected = False

    # Look backward up to 4 tokens for a connector the model may have clipped.
    lookback = max(0, start - 4)
    for i in range(start - 1, lookback - 1, -1):
        match = _match_connector(words_lower, i, connectors, direction=-1)
        if match:
            corrected_start = match[0]
            boundary_corrected = True
            break

    # Extend forward to the next clause boundary, but stop if we run into a
    # different connector's clause (avoid merging two distinct clauses).
    extra = 0
    i = end + 1
    while i < len(words) and extra < MAX_BOUNDARY_EXTENSION:
        if words[i] in CLAUSE_BOUNDARY_TOKENS:
            break
        if _match_connector(words_lower, i, connectors, direction=1) or \
           _match_connector(words_lower, i, other_connectors, direction=1):
            break
        corrected_end = i
        extra += 1
        i += 1
        boundary_corrected = True if extra > 0 else boundary_corrected

    return corrected_start, corrected_end, boundary_corrected


def _grammar_completeness_score(text: str) -> float:
    tokens = text.split()
    if len(tokens) < 3:
        return 0.3
    trivial = {"the", "a", "an", "and", "or", "of", "to", "is", "was"}
    content_tokens = [t for t in tokens if t.lower() not in trivial]
    return 1.0 if len(content_tokens) >= 2 else 0.5


def _build_clause_candidate(words, words_lower, word_conf, word_labels, tag, raw_story_lower):
    """Full pipeline for one clause-shaped field (condition/outcome):
    reconstruct span -> boundary-correct -> score -> accept/flag/reject."""
    connectors = CONDITION_CONNECTORS if tag == "COND" else OUTCOME_CONNECTORS
    other_connectors = OUTCOME_CONNECTORS if tag == "COND" else CONDITION_CONNECTORS

    span = _decode_bio_span(word_labels, tag)
    if span is None:
        return {"text": "", "confidence": 0.0, "low_confidence": False,
                "connector_detected": False, "boundary_corrected": False, "decision": "not_found"}

    start, end = span
    bio_conf = sum(word_conf[start:end + 1]) / (end - start + 1)

    c_start, c_end, boundary_corrected = _boundary_correct(
        words, words_lower, start, end, connectors, other_connectors
    )
    trimmed_words = _trim_dangling(words[c_start:c_end + 1])
    text = " ".join(trimmed_words)
    n_tokens = len(trimmed_words)

    if n_tokens < MIN_SPAN_TOKENS_FOR_CLAUSE:
        return {"text": "", "confidence": 0.0, "low_confidence": False,
                "connector_detected": False, "boundary_corrected": False, "decision": "rejected"}

    connector_detected = any(text.lower().startswith(c) or f" {c} " in f" {text.lower()} "
                              for c in connectors)
    connector_score = 1.0 if connector_detected else 0.5
    grammar_score = _grammar_completeness_score(text)
    # Verbatim check: the span is built by slicing the original tokenized
    # story, so this should always hold -- kept as an explicit, auditable
    # safety check rather than an assumption.
    verbatim_score = 1.0 if text.lower() in raw_story_lower else 0.0

    final_score = (W_BIO_CONF * bio_conf + W_CONNECTOR * connector_score
                   + W_GRAMMAR * grammar_score + W_VERBATIM * verbatim_score)

    if final_score >= ACCEPT_THRESHOLD:
        decision = "accepted"
    elif final_score >= FLAG_THRESHOLD:
        decision = "flagged"
    else:
        decision = "rejected"

    return {
        "text": text if decision != "rejected" else "",
        "confidence": round(final_score, 4),
        "low_confidence": decision == "flagged",
        "connector_detected": connector_detected,
        "boundary_corrected": boundary_corrected,
        "decision": decision,
    }


def _predict_ner(story: str) -> dict:
    tokenizer = _state["tokenizer"]
    model = _state["ner_model"]
    words = word_tokenize(story)
    words_lower = [w.lower() for w in words]
    raw_story_lower = story.lower()

    bert_tokens, word_idx = ["[CLS]"], [-1]
    for wi, w in enumerate(words):
        sub = tokenizer.tokenize(w) or ["[UNK]"]
        bert_tokens.extend(sub)
        word_idx.extend([wi] * len(sub))
    bert_tokens = bert_tokens[: config.NER_MAX_LEN - 1] + ["[SEP]"]
    word_idx = word_idx[: config.NER_MAX_LEN - 1] + [-1]
    input_ids = tokenizer.convert_tokens_to_ids(bert_tokens)
    attn = [1] * len(input_ids)
    pad = config.NER_MAX_LEN - len(input_ids)
    input_ids += [tokenizer.pad_token_id] * pad
    attn += [0] * pad
    with torch.no_grad():
        out = model(
            input_ids=torch.tensor([input_ids]).to(config.DEVICE),
            attention_mask=torch.tensor([attn]).to(config.DEVICE),
        )
    probs = F.softmax(out.logits, dim=-1).squeeze(0)
    preds = probs.argmax(-1).cpu().tolist()

    word_labels = ["O"] * len(words)
    word_conf = [0.0] * len(words)
    assigned = [False] * len(words)
    for tok_i, wi in enumerate(word_idx):
        if wi >= 0 and not assigned[wi]:
            lbl = config.NER_ID2LABEL[preds[tok_i]]
            word_conf[wi] = float(probs[tok_i, preds[tok_i]].item())
            if lbl != "O":
                word_labels[wi] = lbl
            assigned[wi] = True

    result = {}
    for field, tag in [("actor", "ACTOR"), ("action", "ACTION")]:
        span = _decode_bio_span(word_labels, tag)
        if span is None:
            result[field] = {"text": "", "confidence": 0.0, "low_confidence": False}
            continue
        start, end = span
        text = " ".join(words[start:end + 1])
        conf = sum(word_conf[start:end + 1]) / (end - start + 1)
        result[field] = {"text": text, "confidence": round(conf, 4),
                          "low_confidence": conf < MIN_SPAN_CONFIDENCE}

    for field, tag in [("condition", "COND"), ("outcome", "OUT")]:
        result[field] = _build_clause_candidate(
            words, words_lower, word_conf, word_labels, tag, raw_story_lower
        )

    return result


# ── Process classification + Algorithm A1 scoring for one story ────────
def _predict_process(cleaned_story: str, raw_story: str):
    tokenizer, cls_model, sbert = _state["tokenizer"], _state["cls_model"], _state["sbert"]
    from sentence_transformers import util as st_util

    enc = tokenizer(
        cleaned_story, max_length=config.MAX_LEN, padding="max_length",
        truncation=True, return_tensors="pt",
    ).to(config.DEVICE)
    with torch.no_grad():
        probs = F.softmax(cls_model(**enc).logits, dim=-1).squeeze(0)
    top1_idx = int(torch.argmax(probs).item())
    c_model = float(probs[top1_idx].item())
    concept = _state["LABELS"][top1_idx]

    story_emb = sbert.encode(cleaned_story, convert_to_tensor=True)
    proto = _state["prototype_emb"][top1_idx].to(story_emb.device)
    s_ontology = float(st_util.cos_sim(story_emb, proto).item())

    hybrid_score = config.ALPHA * c_model + config.BETA * s_ontology
    selection_status = (
        "High confidence (model)" if c_model >= config.CONFIDENCE_THRESHOLD
        else "Low confidence — flagged for review"
    )
    return concept, c_model, s_ontology, hybrid_score, selection_status


# ── Structured Requirement Representation + Controlled Generation ──────
# BUGS FIXED HERE, all found from a live example:
#   1. Condition/outcome were attached to EVERY step (Submit, Verify,
#      Approve, Settle all got the same "before processing the claim" /
#      "so that invalid claims are rejected" clause pasted on). Fixed:
#      condition now belongs only to the step that gates the process (the
#      first step), outcome only to the step that completes it (the last
#      step) -- matching the notebook's Cell 13 redesign.
#   2. REQ_FRAMES rotated through filler wrapper phrases ("always" / "be
#      required to" / "without exception") for no semantic reason. Fixed:
#      one canonical atomic frame (onto.REQ_FRAME).
#   3. "so that so that invalid claims are rejected" -- the boundary-
#      detection layer above can restore a clipped "so that" onto the
#      outcome span (that is its job), but generation ALSO unconditionally
#      prepended "so that". Fixed: generation now checks whether the
#      outcome text already carries a connector before adding its own.

_OUTCOME_CONNECTOR_PREFIXES = (
    "so that", "in order that", "to ensure that", "such that",
    "thereby", "resulting in", "so as to",
)


def _build_structured_steps(us_id, concept, steps, actor, entity, condition, outcome, story_text):
    structured = []
    n = len(steps)
    for step_i, verb in enumerate(steps, start=1):
        if n == 1:
            purpose = "Single-step process"
        elif step_i == 1:
            purpose = "Initiation (gates process entry)"
        elif step_i == n:
            purpose = "Completion (produces the process outcome)"
        else:
            purpose = "Processing"
        structured.append({
            "user_story_id": us_id, "process_concept": concept, "step_number": step_i,
            "step_purpose": purpose, "action_verb": verb, "actor": actor, "entity": entity,
            "condition": condition if step_i == 1 else "",
            "outcome": outcome if step_i == n else "",
            "source_story_span": story_text,
        })
    return structured


def _render_requirement(slots):
    resp = onto.grounded_response(slots["action_verb"], slots["entity"], slots["actor"])
    text = onto.REQ_FRAME.format(resp=resp)
    if slots["condition"]:
        text = text[:-1] + f", {slots['condition']}."
    if slots["outcome"]:
        outcome_lower = slots["outcome"].lower().strip()
        if any(outcome_lower.startswith(p) for p in _OUTCOME_CONNECTOR_PREFIXES):
            text = text[:-1] + f", {slots['outcome']}."
        else:
            text = text[:-1] + f", so that {slots['outcome']}."
    return text


def _generate_requirements(concept: str, raw_story: str, action_verb_hint: str,
                            ner: dict, actor_fallback: str, entity_fallback: str, us_id: str = ""):
    steps = _state["STEP_TEMPLATE"].get(concept, ["process", "validate", "notify", "log"])
    actor_field = ner["actor"]
    actor = actor_field["text"] or actor_fallback or "user"
    entity = onto.extract_entity_from_text(raw_story, action_verb_hint or steps[0], entity_fallback)
    if len(entity.strip()) < 2:  # quality gate: degenerate extraction -> fall back
        entity = entity_fallback

    # Quality gate: don't attach a condition/outcome clause the model itself
    # is not confident about -- an unreliable fragment stitched onto an
    # otherwise-correct sentence is worse than no clause at all.
    condition = ner["condition"]["text"] if ner["condition"]["decision"] == "accepted" else ""
    outcome = ner["outcome"]["text"] if ner["outcome"]["decision"] == "accepted" else ""

    structured_steps = _build_structured_steps(us_id, concept, steps, actor, entity, condition, outcome, raw_story)

    items = []
    generic_fallback_count = 0
    for slots in structured_steps:
        if slots["action_verb"].lower() not in onto.VERB_RESPONSE:
            generic_fallback_count += 1
        text = _render_requirement(slots)
        issues = _check_requirement(text, slots, steps)
        repaired = False
        repair_log = []
        if any(k in _REPAIRABLE_TYPES for k, _ in issues):
            text, repair_log, issues = _repair_requirement(text, slots, issues, steps)
            repaired = len(repair_log) > 0
        items.append({
            "step": f"Step-{slots['step_number']}: {slots['action_verb'].capitalize()}",
            "step_purpose": slots["step_purpose"],
            "action_verb": slots["action_verb"],
            "text": text,
            "repaired": repaired,
            "repair_actions": repair_log,
            "requires_review": len(issues) > 0,
            "unrepaired_issues": [f"{k}: {d}" for k, d in issues],
        })
    return items, entity, generic_fallback_count


# ── Quality Checker + Repair Loop (mirrors notebook Cell 13) ────────────
_VAGUE_TERMS_MAP = {
    "appropriate": "as defined by the applicable business rule",
    "sufficient": "meeting the configured minimum threshold",
    "as needed": "according to the configured schedule",
    "user-friendly": "consistent with the organization's interface standards",
    "easy to use": "consistent with the organization's interface standards",
    "quickly": "within the configured time limit",
    "efficiently": "within the configured resource limits",
    "etc": "",
    "and so on": "",
}
_REPAIRABLE_TYPES = {"grammar", "vague_term"}
_MAX_REPAIR_ATTEMPTS = 2


def _check_requirement(text, slots, ontology_step_template):
    issues = []
    if not text.strip().startswith("The system shall"):
        issues.append(("grammar", "missing subject/modal"))
    if not text.strip().endswith("."):
        issues.append(("grammar", "missing terminal period"))
    if _DOUBLE_SPACE_RE.search(text):
        issues.append(("grammar", "double space"))
    m = _REPEATED_WORD_RE.search(text)
    if m:
        issues.append(("grammar", f"repeated word ('{m.group(1)}')"))
    if re.search(r"\b(if|when|unless|so)\s+\1\b", text, re.IGNORECASE):
        issues.append(("grammar", "duplicated connector word"))
    wc = len(text.split())
    if wc < 6:
        issues.append(("completeness", "too short"))
    if wc > 60:
        issues.append(("completeness", "too long"))
    if not slots["entity"] or slots["entity"].lower() not in text.lower():
        issues.append(("completeness", "object/entity missing from rendered text"))
    entity_tokens = set(slots["entity"].lower().split())
    text_tokens = set(text.lower().replace(".", "").replace(",", "").split())
    if entity_tokens and len(entity_tokens & text_tokens) / len(entity_tokens) < 0.5:
        issues.append(("semantic_relevance", "entity not clearly referenced"))
    valid_verbs = set(v.lower() for v in ontology_step_template)
    if valid_verbs and slots["action_verb"].lower() not in valid_verbs:
        issues.append(("traceability", f"verb '{slots['action_verb']}' not in ontology step template"))
    for term in _VAGUE_TERMS_MAP:
        if term in text.lower():
            issues.append(("vague_term", term))
    if slots["condition"] and slots["condition"].lower().count(" not ") >= 2:
        issues.append(("contradiction", "condition clause contains double negation"))
    return issues


def _repair_requirement(text, slots, issues, ontology_step_template):
    repair_log = []
    for _ in range(_MAX_REPAIR_ATTEMPTS):
        repairable = [i for i in issues if i[0] in _REPAIRABLE_TYPES]
        if not repairable:
            break
        for kind, detail in repairable:
            if kind == "grammar":
                if "double space" in detail:
                    text = _DOUBLE_SPACE_RE.sub(" ", text)
                    repair_log.append("collapsed double space")
                elif "repeated word" in detail:
                    text = _REPEATED_WORD_RE.sub(r"\1", text)
                    repair_log.append("removed repeated word")
                elif "terminal period" in detail:
                    text = text.rstrip() + "."
                    repair_log.append("added terminal period")
                elif "duplicated connector" in detail:
                    text = re.sub(r"\b(if|when|unless|so)\s+\1\b", r"\1", text, flags=re.IGNORECASE)
                    repair_log.append("removed duplicated connector")
            elif kind == "vague_term":
                replacement = _VAGUE_TERMS_MAP.get(detail, "")
                if replacement:
                    text = re.sub(re.escape(detail), replacement, text, flags=re.IGNORECASE)
                    repair_log.append(f'replaced vague term "{detail}"')
                else:
                    text = re.sub(rf"\s*{re.escape(detail)}\s*", " ", text, flags=re.IGNORECASE)
                    text = _DOUBLE_SPACE_RE.sub(" ", text).strip()
                    repair_log.append(f'removed vague filler "{detail}"')
        issues = _check_requirement(text, slots, ontology_step_template)
    return text, repair_log, issues


def _grammar_check(text: str) -> list:
    problems = []
    if not text.strip().startswith("The system shall"):
        problems.append("does not start with 'The system shall'")
    if not text.strip().endswith("."):
        problems.append("does not end with a period")
    if _DOUBLE_SPACE_RE.search(text):
        problems.append("contains a double space")
    if _REPEATED_WORD_RE.search(text):
        problems.append(f"contains a repeated word ('{_REPEATED_WORD_RE.search(text).group(1)}')")
    word_count = len(text.split())
    if word_count < 6:
        problems.append("unusually short for an IEEE-830 requirement")
    if word_count > 60:
        problems.append("unusually long for a single requirement")
    return problems


def _semantic_relevance_check(text: str, entity: str, raw_story: str) -> bool:
    """Defensive traceability check: the entity substituted into the sentence
    should actually appear in it (verifies the template substitution did what
    it was supposed to -- this should always pass; a failure here would mean
    a real bug in generation, not just an ambiguous story)."""
    entity_tokens = set(entity.lower().split())
    text_tokens = set(text.lower().replace(".", "").replace(",", "").split())
    if not entity_tokens:
        return True
    overlap = entity_tokens & text_tokens
    return len(overlap) / len(entity_tokens) >= 0.5


def _validate(requirement_items, concept, entity, raw_story, ner, c_model):
    sbert = _state["sbert"]
    from sentence_transformers import util as st_util

    requirement_texts = [r["text"] for r in requirement_items]
    issues = []
    checks_performed = ["grammar", "duplicate", "ambiguous_terms", "semantic_relevance", "traceability"]

    # 1. Grammar
    for i, text in enumerate(requirement_texts, start=1):
        problems = _grammar_check(text)
        for p in problems:
            issues.append(f"Requirement {i}: {p}")

    # 2. Duplicate detection (within this story's own generated set)
    duplicate = False
    if len(requirement_texts) > 1:
        emb = sbert.encode(requirement_texts, convert_to_tensor=True)
        sim = st_util.cos_sim(emb, emb).cpu().numpy()
        for i in range(len(requirement_texts)):
            sim[i, i] = 0
        dup_pairs = [(i, j) for i in range(len(sim)) for j in range(i + 1, len(sim))
                     if sim[i, j] >= config.DUP_SIMILARITY_THRESHOLD]
        duplicate = len(dup_pairs) > 0
        for i, j in dup_pairs:
            issues.append(f"Requirements {i+1} and {j+1} are near-duplicates (similarity >= {config.DUP_SIMILARITY_THRESHOLD})")

    # 3. Ambiguous terms
    ambiguous_hits = []
    for i, text in enumerate(requirement_texts, start=1):
        t = text.lower()
        for term in config.AMBIGUOUS_TERMS:
            if term in t:
                issues.append(f"Requirement {i}: contains ambiguous term '{term}'")
                if term not in ambiguous_hits:
                    ambiguous_hits.append(term)

    # 4. Semantic relevance (defensive traceability check)
    for i, (text, item) in enumerate(zip(requirement_texts, requirement_items), start=1):
        if not _semantic_relevance_check(text, entity, raw_story):
            issues.append(f"Requirement {i}: does not clearly reference the extracted entity ('{entity}')")

    # 5. Traceability: every step verb must belong to the predicted concept's
    # own ontology step template (should always hold by construction --
    # included as an explicit, auditable check rather than an assumption).
    valid_verbs = set(v.lower() for v in _state["STEP_TEMPLATE"].get(concept, []))
    for i, item in enumerate(requirement_items, start=1):
        if valid_verbs and item["action_verb"].lower() not in valid_verbs:
            issues.append(f"Requirement {i}: action verb '{item['action_verb']}' is not part of "
                           f"{concept}'s ontology step template")

    extraction_summary = {
        "actor_found": bool(ner["actor"]["text"]),
        "action_found": bool(ner["action"]["text"]),
        "condition_found": ner["condition"]["decision"] == "accepted",
        "outcome_found": ner["outcome"]["decision"] == "accepted",
    }
    if not extraction_summary["actor_found"] or not extraction_summary["action_found"]:
        issues.append("Core extraction incomplete: actor or action was not confidently identified")

    _state["session_covered_processes"].add(concept)
    total = len(_state["ALL_PROCESSES"]) or 1
    covered = len(_state["session_covered_processes"])

    if c_model < config.CONFIDENCE_THRESHOLD:
        status = "Issues found"
    elif issues:
        status = "Passed with warnings"
    else:
        status = "Passed"

    return {
        "status": status,
        "issues": issues,
        "checks_performed": checks_performed,
        "duplicate_within_story": duplicate,
        "ambiguous_terms_found": ambiguous_hits,
        "extraction_summary": extraction_summary,
        "session_processes_covered": covered,
        "session_total_processes": total,
        "session_coverage_pct": round(100 * covered / total, 2),
        "note": (
            "Session coverage above counts distinct process concepts predicted across all "
            "stories submitted to THIS running backend session (resets on server restart). "
            "It is a live, per-session analogue for demonstration purposes -- it is NOT the "
            "notebook's Algorithm A2 coverage metric (Cell 13), which is computed once over an "
            "entire held-out test-set batch using the full evaluation pipeline. For the "
            "authoritative coverage figure, use the notebook's own reported result."
        ),
    }


def run_pipeline(user_story: str) -> dict:
    _require_loaded()

    cleaned = preprocess(user_story)
    if not cleaned:
        raise ValueError("The user story is empty after preprocessing.")

    concept, c_model, s_ontology, hybrid_score, selection_status = _predict_process(cleaned, user_story)
    ontology_hierarchy = _state["ONTOLOGY"].get(concept, "Unknown -> Unknown -> " + concept)

    ner = _predict_ner(user_story)

    steps = _state["STEP_TEMPLATE"].get(concept, ["process"])
    action_hint = ner["action"]["text"] or steps[0]
    entity_fallback = "the requested item"
    requirements, entity_used, generic_fallback_count = _generate_requirements(
        concept, user_story, action_hint, ner, actor_fallback="user", entity_fallback=entity_fallback,
        us_id="live-request",
    )

    validation = _validate(requirements, concept, entity_used, user_story, ner, c_model)
    validation["generic_fallback_count"] = generic_fallback_count

    warnings = []
    low_confidence = c_model < config.CONFIDENCE_THRESHOLD
    if low_confidence:
        warnings.append(
            f"Process concept prediction confidence ({c_model:.2f}) is below the "
            f"{config.CONFIDENCE_THRESHOLD} threshold — treat '{concept}' as tentative, "
            f"not certain."
        )
    if not ner["actor"]["text"] or not ner["action"]["text"]:
        warnings.append("Actor or action could not be confidently extracted from this story.")
    for field in ("condition", "outcome"):
        if ner[field]["decision"] == "flagged":
            warnings.append(
                f"A {field} clause was detected ('{ner[field]['text']}') but scored below the "
                f"acceptance threshold ({ner[field]['confidence']:.2f}) — excluded from the "
                f"generated requirements rather than used unreliably."
            )
    if generic_fallback_count > 0:
        warnings.append(
            f"{generic_fallback_count} of {len(requirements)} requirements used generic "
            f"phrasing because their action verb has no specific vocabulary entry."
        )

    return {
        "user_story": user_story,
        "process_concept": concept,
        "ontology_mapping": ontology_hierarchy,
        "domain_entity": entity_used,
        "ner": ner,
        "scoring": {
            "model_confidence": round(c_model, 4),
            "ontology_similarity": round(s_ontology, 4),
            "hybrid_score": round(hybrid_score, 4),
            "alpha": config.ALPHA,
            "beta": config.BETA,
            "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "selection_status": selection_status,
            "low_confidence": low_confidence,
        },
        "requirements": requirements,
        "validation": validation,
        "warnings": warnings,
    }

