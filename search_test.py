"""Search the local SVG FAISS index with story-beat queries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent
DEFAULT_INDEX_DIR = ROOT / "index"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_QUERIES = (
    "a detective looking for clues in the dark",
    "a rocket launching into space",
    "a person walking beside a house and a tree",
)


def load_index(index_dir: Path) -> tuple[faiss.Index, dict]:
    index_path = index_dir / "svgs.index"
    metadata_path = index_dir / "metadata.json"
    if not index_path.is_file() or not metadata_path.is_file():
        raise FileNotFoundError(
            f"Missing index files under '{index_dir}'. Run build_index.py first."
        )
    index = faiss.read_index(str(index_path))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = metadata.get("records")
    if not isinstance(records, list) or index.ntotal != len(records):
        raise ValueError("Index vector count does not match metadata record count.")
    return index, metadata


def search(query: str, model: SentenceTransformer, index: faiss.Index, metadata: dict, top_k: int) -> None:
    vector = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32", copy=False)
    scores, positions = index.search(vector, top_k)
    print(f"\nQUERY: {query}")
    for rank, (score, position) in enumerate(zip(scores[0], positions[0]), start=1):
        record = metadata["records"][int(position)]
        print(
            f"{rank:>2}. {float(score):.4f}  "
            f"{record['path']}  [{record['description']}]"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", nargs="*", help="Story-beat queries to search.")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top_k < 1:
        print("--top-k must be at least 1.", file=sys.stderr)
        return 2
    try:
        index, metadata = load_index(args.index_dir.resolve())
        model_name = metadata.get("model", args.model)
        model = SentenceTransformer(model_name, device="cpu")
        queries = args.queries or list(DEFAULT_QUERIES)
        for query in queries:
            search(query, model, index, metadata, args.top_k)
    except (FileNotFoundError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Search failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
