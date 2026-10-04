#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_utf8_lf(path: Path, value: str) -> None:
    """Write deterministic UTF-8/LF bytes on every operating system."""
    path.write_bytes(value.encode("utf-8"))


summary = {
    "release": "ObligationBench-v1.1.1",
    "release_date": "2026-10-04",
    "splits": {},
    "total_trajectories": 0,
    "total_obligations": 0,
}
source_occurrences: dict[str, list[str]] = defaultdict(list)
sample_index: list[dict[str, object]] = []

for split in ("positive", "negative"):
    samples = sorted(path for path in (ROOT / "data" / split).iterdir() if path.is_dir())
    benchmarks: Counter[str] = Counter()
    models: Counter[str] = Counter()
    source_images: set[str] = set()
    obligations = 0
    source_task_ids: set[str] = set()
    for sample in samples:
        truth = load(sample / "ground_truth.json")
        provenance = load(sample / "provenance.json")
        trajectory = load(sample / "trajectory.json")
        obligations += truth["obligation_count"]
        benchmarks[provenance.get("source_benchmark", "unknown")] += 1
        source_image = provenance.get("source_image", "unknown")
        source_images.add(source_image)
        source_id = provenance.get("source_task_id", "unknown")
        source_task_ids.add(source_id)
        source_occurrences[source_id].append(f"{split}/{sample.name}")
        config = trajectory.get("info", {}).get("config", {}).get("model", {})
        model = config.get("model_name") or config.get("name") or "unknown"
        models[model] += 1
        sample_index.append(
            {
                "split": split,
                "sample": sample.name,
                "task_id": truth.get("task_id"),
                "source_benchmark": provenance.get("source_benchmark"),
                "source_task_id": source_id,
                "source_image": source_image,
                "obligation_count": truth.get("obligation_count"),
                "model_format_condition": model,
            }
        )
    summary["splits"][split] = {
        "trajectory_count": len(samples),
        "obligation_count": obligations,
        "unique_source_task_ids": len(source_task_ids),
        "unique_source_images": len(source_images),
        "benchmarks": dict(sorted(benchmarks.items())),
        "model_format_conditions": dict(sorted(models.items())),
    }
    summary["total_trajectories"] += len(samples)
    summary["total_obligations"] += obligations

summary["cross_split_source_task_overlap"] = {
    source_id: paths
    for source_id, paths in sorted(source_occurrences.items())
    if len(paths) > 1
}

write_utf8_lf(
    ROOT / "manifests" / "release_summary.json",
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
)
write_utf8_lf(
    ROOT / "manifests" / "samples.jsonl",
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sample_index),
)

excluded = {Path("manifests/files.sha256")}
paths = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and path.relative_to(ROOT) not in excluded
    and ".git" not in path.parts
)
lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in paths]
write_utf8_lf(ROOT / "manifests" / "files.sha256", "\n".join(lines) + "\n")
print(json.dumps(summary, ensure_ascii=False, indent=2))
