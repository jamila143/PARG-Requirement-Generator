"""
Small text utilities, ported directly from PARG_Kaggle_Pipeline_v6.ipynb
(Cells 5 and 6) so behavior matches what the models were trained on.
"""
import re

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
    "been", "being", "this", "that", "these", "those", "it", "its", "i",
    "you", "he", "she", "they", "we", "my", "your", "his", "her", "their",
    "our",
}
KEEP_WORDS = {"not", "no", "without", "must", "shall", "should",
              "can", "want", "need", "when", "if", "so", "that", "only", "unless"}


def word_tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9']+|[.,;!?]", str(text))


def preprocess(text: str) -> str:
    """Cleans a raw user story into the space-separated token string the
    process classifier expects as input (matches Cell 5's `preprocess`)."""
    if not isinstance(text, str) or text.strip() == "":
        return ""
    text = re.sub(r"\(see R\d+\)", "", text)
    text = re.sub(r"\(Ref\. US-\d+\)", "", text)
    text = text.lower()
    tokens = re.findall(r"[a-z0-9']+", text)
    tokens = [t for t in tokens if (t not in STOP_WORDS) or (t in KEEP_WORDS)]
    return " ".join(tokens)
