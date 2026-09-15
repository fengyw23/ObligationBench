#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"positive": 120, "negative": 104}
REQUIRED = {
    "trajectory.json",
    "guard_input.json",
    "ground_truth.json",
    "provenance.json",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    task_ids: dict[str, str] = {}
    source_ids: dict[str, dict[str, str]] = defaultdict(dict)
    counts: Counter[str] = Counter()
    obligation_counts: Counter[str] = Counter()

    for split, expected in EXPECTED.items():
        split_root = ROOT / "data" / split
        samples = sorted(path for path in split_root.iterdir() if path.is_dir())
        counts[split] = len(samples)
        if len(samples) != expected:
            errors.append(f"{split}: expected {expected} samples, found {len(samples)}")
        for sample in samples:
            missing = REQUIRED - {path.name for path in sample.iterdir() if path.is_file()}
            if missing:
                errors.append(f"{split}/{sample.name}: missing {sorted(missing)}")
                continue
            try:
                trajectory = load_json(sample / "trajectory.json")
                guard_input = load_json(sample / "guard_input.json")
                truth = load_json(sample / "ground_truth.json")
                provenance = load_json(sample / "provenance.json")
            except Exception as exc:
                errors.append(f"{split}/{sample.name}: JSON load failed: {exc}")
                continue

            if trajectory.get("trajectory_format") != "mini-swe-agent-1.1":
                errors.append(f"{split}/{sample.name}: unexpected trajectory format")
            if guard_input.get("trajectory_format") != "mini-swe-agent-1.1":
                errors.append(f"{split}/{sample.name}: unexpected guard format")

            task_id = truth.get("task_id")
            if not task_id:
                errors.append(f"{split}/{sample.name}: missing ground-truth task_id")
            elif task_id in task_ids:
                errors.append(
                    f"duplicate task_id {task_id}: {task_ids[task_id]} and {split}/{sample.name}"
                )
            else:
                task_ids[task_id] = f"{split}/{sample.name}"

            source_id = provenance.get("source_task_id")
            if not source_id:
                errors.append(f"{split}/{sample.name}: missing source_task_id")
            elif source_id in source_ids[split]:
                errors.append(
                    f"duplicate {split} source_task_id {source_id}: "
                    f"{source_ids[split][source_id]} and {sample.name}"
                )
            else:
                source_ids[split][source_id] = sample.name

            count = truth.get("obligation_count")
            obligations = truth.get("obligations")
            if not isinstance(count, int) or not isinstance(obligations, list):
                errors.append(f"{split}/{sample.name}: malformed ground truth")
            elif count != len(obligations):
                errors.append(f"{split}/{sample.name}: count/list mismatch")
            else:
                obligation_counts[split] += count
                if split == "positive" and count < 1:
                    errors.append(f"{split}/{sample.name}: positive sample has no obligation")
                if split == "negative" and count != 0:
                    errors.append(f"{split}/{sample.name}: negative sample is nonzero")

    digest_path = ROOT / "manifests" / "files.sha256"
    if digest_path.exists():
        for line_number, line in enumerate(digest_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                expected_hash, relative = line.split("  ", 1)
            except ValueError:
                errors.append(f"files.sha256:{line_number}: malformed line")
                continue
            path = ROOT / Path(relative)
            if not path.is_file():
                errors.append(f"files.sha256:{line_number}: missing {relative}")
            elif sha256(path) != expected_hash:
                errors.append(f"files.sha256:{line_number}: digest mismatch for {relative}")
    else:
        errors.append("missing manifests/files.sha256")

    report = {
        "release_valid": not errors,
        "positive_count": counts["positive"],
        "negative_count": counts["negative"],
        "positive_obligations": obligation_counts["positive"],
        "negative_obligations": obligation_counts["negative"],
        "unique_task_ids": len(task_ids),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
