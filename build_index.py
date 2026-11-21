"""Build a semantic FAISS index for the local SVG library."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent
DEFAULT_ASSET_DIR = ROOT / "assets" / "svgs"
DEFAULT_INDEX_DIR = ROOT / "index"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
WHITESPACE = re.compile(r"\s+")
SEPARATORS = re.compile(r"[_\-./\\]+")
XML_NAMESPACE = re.compile(r"\{[^}]+\}")


@dataclass(frozen=True)
class AssetRecord:
    path: str
    pack: str
    category: str
    filename: str
    description: str
    title: str
    desc: str
    group_ids: list[str]
    bytes: int


def clean_text(value: str) -> str:
    return WHITESPACE.sub(" ", value).strip()


def humanize(value: str) -> str:
    value = XML_NAMESPACE.sub("", value)
    value = SEPARATORS.sub(" ", value)
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return clean_text(value).lower()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse_svg(path: Path, relative_path: Path) -> AssetRecord:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise ValueError(f"{relative_path}: invalid SVG/XML: {error}") from error

    title_parts: list[str] = []
    desc_parts: list[str] = []
    group_ids: list[str] = []
    for element in root.iter():
        name = local_name(element.tag)
        text = clean_text(" ".join(element.itertext()))
        if name == "title" and text:
            title_parts.append(text)
        elif name == "desc" and text:
            desc_parts.append(text)
        element_id = clean_text(element.attrib.get("id", ""))
        if name == "g" and element_id:
            group_ids.append(element_id)

    parts = relative_path.with_suffix("").parts
    pack = parts[0] if parts else "unknown"
    category = " / ".join(parts[1:-1]) if len(parts) > 2 else pack
    filename = humanize(relative_path.stem)
    title = clean_text(" ".join(title_parts))
    description = clean_text(" ".join(desc_parts))
    ids = " ".join(humanize(item) for item in group_ids)
    search_text = clean_text(
        f"{filename}. Pack: {humanize(pack)}. Category: {humanize(category)}. "
        f"Title: {title}. Description: {description}. Groups: {ids}."
    )
    return AssetRecord(
        path=relative_path.as_posix(),
        pack=pack,
        category=category,
        filename=relative_path.name,
        description=search_text,
        title=title,
        desc=description,
        group_ids=group_ids,
        bytes=path.stat().st_size,
    )


def discover_records(asset_dir: Path) -> list[AssetRecord]:
    files = sorted(asset_dir.rglob("*.svg"), key=lambda item: item.as_posix().lower())
    if not files:
        raise FileNotFoundError(f"No SVG files found under '{asset_dir}'.")
    records: list[AssetRecord] = []
    invalid: list[str] = []
    for path in files:
        relative = path.relative_to(asset_dir)
        try:
            records.append(parse_svg(path, relative))
        except ValueError as error:
            invalid.append(str(error))
    if invalid:
        details = "\n".join(f"  - {item}" for item in invalid[:20])
        more = f"\n  ... and {len(invalid) - 20} more." if len(invalid) > 20 else ""
        raise ValueError(
            f"{len(invalid)} SVG files failed validation; no index was written.\n"
            f"{details}{more}"
        )
    return records


def build_index(
    records: list[AssetRecord],
    model_name: str,
    index_dir: Path,
    asset_dir: Path,
    batch_size: int,
) -> None:
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name, device="cpu")
    texts = [record.description for record in records]
    print(f"Encoding {len(texts):,} SVG descriptions on CPU...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32", copy=False)
    if embeddings.ndim != 2 or embeddings.shape[0] != len(records):
        raise RuntimeError(f"Unexpected embedding shape: {embeddings.shape}")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "svgs.index"
    metadata_path = index_dir / "metadata.json"
    temporary_index = index_dir / "svgs.index.tmp"
    temporary_metadata = index_dir / "metadata.json.tmp"
    faiss.write_index(index, str(temporary_index))
    metadata = {
        "format_version": 1,
        "model": model_name,
        "metric": "inner_product_on_normalized_embeddings",
        "asset_root": (
            str(asset_dir.relative_to(ROOT))
            if asset_dir.is_relative_to(ROOT)
            else str(asset_dir)
        ),
        "count": len(records),
        "dimension": embeddings.shape[1],
        "records": [asdict(record) for record in records],
    }
    temporary_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_index.replace(index_path)
    temporary_metadata.replace(metadata_path)
    print(f"Wrote {index_path} ({index.ntotal:,} vectors)")
    print(f"Wrote {metadata_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    asset_dir = args.asset_dir.resolve()
    if not asset_dir.is_dir():
        print(f"Asset directory does not exist: {asset_dir}", file=sys.stderr)
        return 2
    if args.batch_size < 1:
        print("--batch-size must be at least 1.", file=sys.stderr)
        return 2
    try:
        records = discover_records(asset_dir)
        print(f"Validated {len(records):,} SVG files.")
        build_index(
            records,
            args.model,
            args.index_dir.resolve(),
            asset_dir,
            args.batch_size,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(f"Index build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
