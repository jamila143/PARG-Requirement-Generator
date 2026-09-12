"""
Loads PARG_Dataset_v8.xlsx and rebuilds everything the notebook computes from
it: the ontology (process concept -> hierarchy -> step template) and the
grammatically-correct verb-response vocabulary used to instantiate IEEE-830
requirement text (Cells 3, 4, and 12 of PARG_Kaggle_Pipeline_v6.ipynb).
"""
import re
import pandas as pd

EXPECTED_COLS = [
    "Requirement ID", "User Story ID", "Original User Story", "Agile User Story",
    "Requirement Type", "Domain", "Actor", "Sequence Step", "Action Verb",
    "Condition", "Condition Quality", "Outcome", "Outcome Quality",
    "Domain Entity", "Action Constraint", "System Response",
    "Process Concept", "Ontology Hierarchy", "Process Coverage Status",
    "Generated Requirement (IEEE 830)",
]


def load_dataset(path: str) -> pd.DataFrame:
    """Multi-sheet-aware loader, identical in spirit to notebook Cell 3: a
    v7/v8 workbook has README as sheet 0, so we search every sheet/header
    combination for one whose columns match, rather than assuming sheet 0."""
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        for header_row in (0, 1):
            try:
                candidate = xl.parse(sheet, header=header_row)
            except Exception:
                continue
            if all(c in candidate.columns for c in EXPECTED_COLS):
                df = candidate
                if "Row No." in df.columns:
                    df = df.drop(columns=["Row No."])
                df = df.dropna(subset=["Requirement ID", "User Story ID"]).reset_index(drop=True)
                return df
    raise ValueError(
        f"None of the sheets {xl.sheet_names} in {path} contain the expected "
        f"PARG columns. Make sure you placed PARG_Dataset_v8.xlsx (or v7/v6) "
        f"at backend/data/PARG_Dataset_v8.xlsx."
    )


def build_ontology(df_raw: pd.DataFrame):
    """Ports Cell 4: process-concept -> ontology-hierarchy map and the
    per-concept ordered step-verb template, both read directly from the
    dataset (not invented)."""
    ontology_df = (
        df_raw[["Process Concept", "Ontology Hierarchy", "Domain"]]
        .dropna().drop_duplicates("Process Concept").reset_index(drop=True)
    )
    ontology = dict(zip(ontology_df["Process Concept"], ontology_df["Ontology Hierarchy"]))
    ontology_domain_of = dict(zip(ontology_df["Process Concept"], ontology_df["Domain"]))
    all_processes = sorted(ontology.keys())

    step_template = {}
    for concept, grp in df_raw.groupby("Process Concept"):
        steps = (
            grp[["Sequence Step", "Action Verb"]]
            .drop_duplicates()
            .assign(step_num=lambda d: d["Sequence Step"].str.extract(r"Step-(\d+)").astype(int))
            .sort_values("step_num")
        )
        step_template[concept] = list(steps["Action Verb"])

    return ontology, ontology_domain_of, all_processes, step_template


def build_label_list(df_raw: pd.DataFrame, min_samples: int):
    """Rebuilds the SAME sorted class list the notebook's LabelEncoder produced
    at training time (Cell 7): one row per User Story ID, filtered to concepts
    with >= min_samples stories, sorted alphabetically (sklearn's
    LabelEncoder.fit sorts its classes_ alphabetically by default, so as long
    as this filter matches Cell 7 exactly, the resulting index order matches
    the trained classifier's output indices)."""
    df_stories = df_raw.drop_duplicates(subset="User Story ID")
    counts = df_stories["Process Concept"].value_counts()
    valid = counts[counts >= min_samples].index
    return sorted(valid)


# ---------------------------------------------------------------------------
# Requirement-generation vocabulary (identical to notebook Cell 12 /
# verb_response_v8.py). See that module's docstring for the grammar-bug
# history: every entry below is bare base/infinitive form with no subject,
# which is correct after the modal "shall" in every frame in REQ_FRAMES.
# ---------------------------------------------------------------------------
VERB_RESPONSE = {
    "validate": "validate {ent} against the required business rules and return a pass or fail result",
    "verify": "verify {ent} and return either a confirmation or a detailed error explanation",
    "authenticate": "authenticate the {actor_l} before allowing any further operation on {ent}",
    "authorize": "check the {actor_l}'s permissions before authorizing the operation on {ent}",
    "notify": "send a notification about {ent} to the relevant stakeholders",
    "log": "record the event related to {ent} in the audit trail with a timestamp",
    "record": "persist the details of {ent} and confirm successful storage",
    "store": "store {ent} securely and return a confirmation reference",
    "report": "compile and deliver a report covering {ent}",
    "escalate": "escalate the issue related to {ent} to the appropriate authority",
    "alert": "raise an alert regarding {ent} to the responsible {actor_l}",
    "approve": "route {ent} for approval and record the decision",
    "confirm": "confirm the outcome of the operation on {ent} to the {actor_l}",
    "activate": "activate {ent} and update its status accordingly",
    "issue": "issue {ent} and update the relevant records",
    "dispense": "dispense {ent} and log the transaction",
    "publish": "publish {ent} and make it available to authorized users",
    "generate": "generate {ent} based on the collected data",
    "calculate": "calculate the required values for {ent} and store the result",
    "monitor": "continuously monitor {ent} against predefined thresholds",
    "detect": "detect anomalies in {ent} and flag them for review",
    "review": "route {ent} for review by an authorized {actor_l}",
    "assign": "assign {ent} to the appropriate {actor_l}",
    "update": "update {ent} and timestamp the change",
    "track": "track the status of {ent} in real time",
    "collect": "collect the required data for {ent}",
    "route": "route {ent} to the correct handler",
    "schedule": "schedule {ent} and send a confirmation",
    "receive": "receive and acknowledge {ent} from the {actor_l}",
    "process": "process {ent} and confirm the outcome to the {actor_l}",
    "dispatch": "dispatch the resource associated with {ent}",
    "register": "register {ent} and persist the associated record",
    "isolate": "isolate the affected subsystem related to {ent}",
    "trigger": "trigger the downstream action associated with {ent}",
    "submit": "accept the submission of {ent} from the {actor_l} and queue it for processing",
    "request": "capture the {actor_l}'s request for {ent} and initiate the corresponding workflow",
    "apply": "apply the requested change described by {ent}",
    "add": "add {ent} to the relevant record set",
    "check": "check {ent} for completeness before proceeding",
    "upload": "accept the upload of {ent} and validate its format",
    "inspect": "inspect {ent} and record the findings",
    "classify": "classify {ent} according to the configured categories",
    "initiate": "initiate the workflow associated with {ent}",
    "assess": "assess {ent} against the applicable criteria",
    "investigate": "investigate the case associated with {ent}",
    "resolve": "resolve the issue associated with {ent} and close the case",
    "deduct": "deduct the amount associated with {ent} from the relevant balance",
    "reserve": "reserve {ent} on behalf of the {actor_l}",
    "propose": "propose a change to {ent} for approval",
    "analyze": "analyze {ent} and summarize the findings",
    "settle": "settle the transaction associated with {ent}",
    "capture": "capture the details of {ent} from the {actor_l}",
    "compile": "compile the information required for {ent}",
    "deliver": "deliver {ent} to the intended recipient",
    "disburse": "disburse the funds associated with {ent}",
    "flag": "flag {ent} for follow-up review",
    "select": "select {ent} based on the {actor_l}'s input",
    "search": "search for {ent} matching the {actor_l}'s criteria",
    "book": "book {ent} on behalf of the {actor_l}",
    "welcome": "confirm the arrival associated with {ent} and record it",
    "conduct": "conduct the activity associated with {ent}",
    "audit": "audit {ent} against the applicable compliance requirements",
    "grant": "grant the access or privilege associated with {ent}",
    "index": "index {ent} for efficient future retrieval",
    "cross-check": "cross-check {ent} against an independent data source",
    "measure": "measure the value associated with {ent}",
    "adjust": "adjust the parameters associated with {ent}",
    "diagnose": "diagnose the fault associated with {ent}",
    "repair": "repair the issue associated with {ent} and update its status",
    "locate": "locate the resource associated with {ent}",
    "poll": "poll for updates related to {ent}",
    "synchronize": "synchronize {ent} across all connected systems",
    "sense": "capture a fresh reading for {ent}",
    "transmit": "transmit {ent} to the receiving system",
    "configure": "apply the requested configuration for {ent}",
    "install": "install the update associated with {ent}",
    "download": "download the package associated with {ent}",
    "build": "build the artifact associated with {ent}",
    "deploy": "deploy the release associated with {ent}",
    "test": "test the change associated with {ent} before release",
    "ingest": "ingest {ent} into the processing pipeline",
    "calibrate": "calibrate the values associated with {ent}",
    "merge": "merge {ent} into the master dataset",
    "render": "render {ent} for display to the {actor_l}",
    "optimize": "optimize the plan associated with {ent}",
    "input": "accept {ent} as input and prepare it for processing",
    "survey": "record the survey data associated with {ent}",
    "plan": "prepare a plan covering {ent}",
    "coordinate": "coordinate the response effort associated with {ent}",
    "evaluate": "evaluate the severity associated with {ent}",
    "archive": "archive {ent} for long-term retention",
    "order": "place the order associated with {ent}",
    "prescribe": "record the prescription details for {ent}",
    "renew": "renew the subscription associated with {ent}",
    "charge": "charge the {actor_l} for {ent}",
    "rank": "rank {ent} according to relevance to the {actor_l}",
    "screen": "screen {ent} against the moderation policy",
    "decide": "record the moderation decision for {ent}",
    "transcode": "transcode {ent} into the required delivery format",
    "stream": "stream {ent} to the {actor_l} once authorized",
    "connect": "establish the connection required for {ent}",
    "consult": "conduct the consultation session associated with {ent}",
    "remind": "send a reminder to the {actor_l} about {ent}",
    "grade": "grade the submission associated with {ent}",
    "aggregate": "aggregate the records associated with {ent}",
    "invoice": "generate the invoice associated with {ent}",
    "pay": "process the payment associated with {ent}",
    "return": "process the return associated with {ent}",
    "refund": "process the refund associated with {ent}",
    "replenish": "replenish the stock associated with {ent}",
    "incentivize": "apply the applicable incentive to {ent}",
    "cache": "cache {ent} for faster subsequent access",
    "actuate": "actuate the control associated with {ent}",
    "release": "release {ent} to the {actor_l}",
    "respond": "respond to the request associated with {ent}",
    "retrieve": "retrieve the record associated with {ent}",
}
DEFAULT_RESPONSE = "process {ent} on behalf of the {actor_l} and confirm the outcome"

# BUG FIXED HERE (found from a live example: "The system shall always accept
# the submission..." / "The system shall, without exception, route..."): this
# used to rotate through four wrapper phrases per step purely for lexical
# variety. The variety served no purpose and added meaningless filler words
# to every requirement. One canonical, atomic frame now -- matching the
# notebook's Cell 13 redesign.
REQ_FRAME = "The system shall {resp}."


def grounded_response(verb: str, entity: str, actor: str) -> str:
    tpl = VERB_RESPONSE.get(verb.lower(), DEFAULT_RESPONSE)
    return tpl.format(ent=entity, actor_l=(actor.lower() if actor else "user"))


def extract_entity_from_text(story_text: str, verb: str, fallback: str) -> str:
    """Pulls the noun phrase right after the story's own action verb, so the
    generated requirement talks about what THIS story is actually about
    rather than a canned per-domain value.

    BUG FIXED HERE (found from a live example: entity came back as "a
    patient's insurance coverage before processing" -- the condition
    clause's own connector word got swallowed INTO the entity phrase because
    it wasn't in the stop-word list). The stop-word set now covers every
    single-word CONDITION_CONNECTORS / OUTCOME_CONNECTORS first-word (see
    pipeline.py), so entity extraction reliably stops at the boundary of any
    condition/outcome clause instead of running into it.
    """
    from .nlp_utils import word_tokenize
    words = word_tokenize(story_text)
    words_lower = [w.lower() for w in words]
    if verb.lower() in words_lower:
        vi = words_lower.index(verb.lower())
        stop_words = {
            "so", "when", "if", "provided", "unless", "only", "before", "after",
            "while", "once", "until", "given", "in", "case", "as", "long",
            "that", "order", "to", "ensure", "resulting", "thereby", "such",
        }
        phrase = []
        for w in words[vi + 1:]:
            if w.lower() in stop_words or w in (".", ","):
                break
            phrase.append(w)
            if len(phrase) >= 6:
                break
        if phrase:
            return " ".join(phrase)
    return fallback
