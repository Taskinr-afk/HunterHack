"""
Embedding pipeline for PotholeIQ.

Produces two CSV files in kevin/data/:
  potholes_raw.csv        — full 311 enriched dataset, human-readable
  potholes_embeddings.csv — unique_key + 384-dim sentence embedding per pothole

Embedding model: all-MiniLM-L6-v2 (22 MB, runs locally, no API key needed)
Text encoded:    "{descriptor} on {street_name} in {borough} — {location_type}, status: {status}"

Usage:
  python -m kevin.cortex.embed
  python -m kevin.cortex.embed --source live   # bypass cache, fetch fresh from NYC Open Data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from .data import fetch_all

DATA_DIR      = Path(__file__).parent.parent / "data"
RAW_CSV       = DATA_DIR / "potholes_raw.csv"
EMBED_CSV     = DATA_DIR / "potholes_embeddings.csv"

EMBED_MODEL   = "all-MiniLM-L6-v2"   # 384-dim, ~22 MB, fast CPU inference
EMBED_DIM     = 384
BATCH_SIZE    = 256


def _build_text(row: pd.Series) -> str:
    """Single text string representing one pothole — what gets embedded."""
    desc     = row.get("descriptor", "Pothole") or "Pothole"
    street   = row.get("street_name", "") or ""
    borough  = row.get("borough", "") or ""
    loc_type = row.get("location_type", "") or ""
    status   = row.get("status", "Open") or "Open"
    age      = row.get("age_days", 0) or 0

    parts = [f"{desc}"]
    if street:
        parts.append(f"on {street}")
    if borough:
        parts.append(f"in {borough}")
    if loc_type:
        parts.append(f"({loc_type})")
    parts.append(f"— status: {status}, open {int(age)} days")
    return " ".join(parts)


def export_raw_csv(df: pd.DataFrame) -> None:
    """Write the enriched 311 dataset to CSV — sorted by risk_score if present."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = df.copy()

    # convert timestamps to readable strings
    for col in ("created_date", "closed_date"):
        if col in out.columns:
            out[col] = out[col].astype(str).replace("NaT", "")

    if "risk_score" in out.columns:
        out = out.sort_values("risk_score", ascending=False)

    out.to_csv(RAW_CSV, index=False)
    print(f"  [embed] Raw CSV  → {RAW_CSV}  ({len(out):,} rows, {out.shape[1]} cols)")


def build_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate sentence embeddings for every pothole.
    Returns DataFrame: unique_key + emb_0 … emb_383
    """
    print(f"  [embed] Loading model '{EMBED_MODEL}' …")
    model = SentenceTransformer(EMBED_MODEL)

    texts = df.apply(_build_text, axis=1).tolist()

    print(f"  [embed] Encoding {len(texts):,} potholes (batch_size={BATCH_SIZE}) …")
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # L2-norm → cosine similarity = dot product
    )

    col_names = [f"emb_{i}" for i in range(EMBED_DIM)]
    emb_df = pd.DataFrame(vectors, columns=col_names, dtype=np.float32)
    emb_df.insert(0, "unique_key", df["unique_key"].values)

    # attach key metadata so the embeddings CSV is self-contained
    for meta_col in ("descriptor", "borough", "street_name", "status", "risk_score", "urgency_label"):
        if meta_col in df.columns:
            emb_df.insert(emb_df.columns.get_loc("unique_key") + 1, meta_col, df[meta_col].values)

    return emb_df


def export_embeddings_csv(emb_df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    emb_df.to_csv(EMBED_CSV, index=False)
    print(f"  [embed] Embeddings CSV → {EMBED_CSV}  ({len(emb_df):,} rows, {EMBED_DIM} dims)")


def run(use_cache: bool = True) -> None:
    print("=" * 55)
    print("  PotholeIQ — Data Export + Embedding Pipeline")
    print("=" * 55)

    print("\n[1/3] Loading enriched pothole data …")
    df = fetch_all(use_cache=use_cache)

    # attach scores if model is trained
    try:
        from .model import score_potholes
        df = score_potholes(df)
        print(f"       ML scores attached (risk_score, urgency_label)")
    except Exception:
        print("       No trained model found — exporting without ML scores")

    print("\n[2/3] Exporting raw CSV …")
    export_raw_csv(df)

    print("\n[3/3] Generating embeddings …")
    emb_df = build_embeddings(df)
    export_embeddings_csv(emb_df)

    print(f"\n✓ Done — files in kevin/data/")
    print(f"  {RAW_CSV.name:<30} {RAW_CSV.stat().st_size / 1024:.0f} KB")
    print(f"  {EMBED_CSV.name:<30} {EMBED_CSV.stat().st_size / 1024:.0f} KB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export pothole data and generate embeddings")
    parser.add_argument("--source", choices=["cache", "live"], default="cache",
                        help="cache = use parquet cache (fast), live = re-fetch from NYC Open Data")
    args = parser.parse_args()
    run(use_cache=(args.source == "cache"))


if __name__ == "__main__":
    main()
