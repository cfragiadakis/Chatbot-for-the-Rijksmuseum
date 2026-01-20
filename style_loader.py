from __future__ import annotations
from pathlib import Path
import random

def load_letter_texts(cfg: dict) -> list[str]:
    se = cfg.get("style_examples", {})
    folder = Path(se["folder"])
    glob_pat = se.get("file_glob", "*.txt")
    max_files = int(se.get("max_files", 50))
    sampling = se.get("sampling", "random")

    files = sorted(folder.glob(glob_pat))
    if not files:
        raise FileNotFoundError(f"No txt files found in {folder} with glob {glob_pat}")

    if sampling == "random":
        files = random.sample(files, k=min(max_files, len(files)))
    else:  # "first" / default
        files = files[:max_files]

    texts = [f.read_text(encoding="utf-8", errors="ignore") for f in files]
    return texts


def build_style_examples(cfg: dict, texts: list[str]) -> list[str]:
    se = cfg["style_examples"]
    max_examples = int(se.get("max_examples", 6))
    snippet_chars = int(se.get("snippet_chars", 800))

    # Simple: sample snippets from random letters
    examples = []
    for _ in range(max_examples):
        t = random.choice(texts).strip()
        if len(t) <= snippet_chars:
            examples.append(t)
        else:
            start = random.randint(0, max(0, len(t) - snippet_chars))
            examples.append(t[start:start + snippet_chars].strip())
    return examples
