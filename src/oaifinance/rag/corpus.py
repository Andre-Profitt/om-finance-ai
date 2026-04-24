"""Corpus loader: reads markdown policy / contract files and chunks by section."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from oaifinance.config import BRONZE_DIR, SAMPLES_DIR

POLICIES_DIR = SAMPLES_DIR / "payer_policies"
CONTRACTS_DIR = SAMPLES_DIR / "gpo_contracts"

SECTION_PATTERN = re.compile(r"^##\s+§?\d+[.\s]*([^\n]+)", re.MULTILINE)


def _chunk_markdown(text: str) -> list[tuple[str, str]]:
    """Split markdown into (section_title, body) pairs by `##` headers."""
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return [("document", text.strip())]

    chunks = []
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            chunks.append((title, body))
    return chunks


def _doc_title(md_text: str, fallback: str) -> str:
    first = md_text.strip().splitlines()[0] if md_text.strip() else fallback
    return first.lstrip("# ").strip() or fallback


def load() -> pl.DataFrame:
    rows = []
    for label, dir_ in (("payer_policy", POLICIES_DIR), ("gpo_contract", CONTRACTS_DIR)):
        for path in sorted(Path(dir_).glob("*.md")):
            text = path.read_text()
            title = _doc_title(text, path.stem)
            chunks = _chunk_markdown(text)
            for section_idx, (section_title, body) in enumerate(chunks):
                rows.append(
                    {
                        "doc_id": path.stem,
                        "doc_type": label,
                        "doc_title": title,
                        "section_idx": section_idx,
                        "section_title": section_title,
                        "text": body,
                        "path": str(path.relative_to(SAMPLES_DIR.parent.parent)),
                    }
                )

    df = pl.DataFrame(rows).with_columns(
        pl.concat_str(
            [
                pl.col("doc_id"),
                pl.lit("#"),
                pl.col("section_idx").cast(pl.Utf8),
            ]
        ).alias("chunk_id"),
    )

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(BRONZE_DIR / "corpus.parquet")
    return df


if __name__ == "__main__":
    df = load()
    print(df.group_by("doc_type").len())
    print(f"total chunks: {len(df)}")
    for row in df.head(3).iter_rows(named=True):
        print(f"  {row['chunk_id']} — {row['section_title']}")
