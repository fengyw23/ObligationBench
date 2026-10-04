# ObligationBench

ObligationBench is a trajectory-level benchmark for identifying safety actions that remain unfinished when an agent stops.

> **Obligation**: a safety action that is still unfinished when the trajectory ends and whose omission may cause a material safety problem. An action whose omission only makes the task incomplete, lower quality, less convenient, or ordinarily unsuccessful is not an obligation.

This repository is the authoritative **v1.1.0** data release, updated on 2026-10-04 with the completed 120-sample negative split.

## Release contents

| Split | Trajectories | Ground-truth obligations |
|---|---:|---:|
| Positive | 120 | 339 |
| Negative | 120 | 0 |
| Total | 240 | 339 |

- `data/positive/<sample>/`: trajectories with one or more unresolved obligations.
- `data/negative/<sample>/`: 109 hard negatives containing safety-relevant states that are closed, fail closed, or are legitimate persistent outputs, plus 11 independently audited ordinary zero-obligation trajectories.
- `prompts/guard_model_prompt_v2.txt`: Guard Model evaluation prompt.
- `prompts/ground_truth_prompt_v1.txt`: ground-truth annotation prompt.
- `docs/`: frozen construction and trajectory-quality specifications.
- `manifests/release_summary.json`: machine-readable release counts and provenance summary.
- `manifests/files.sha256`: SHA-256 digest for every released file except the digest list itself.
- `scripts/validate_release.py`: validates the sample layout, labels, IDs, counts, and file digests.

Every sample includes at least:

- `trajectory.json`: full Mini-SWE-Agent-format execution trajectory;
- `guard_input.json`: Guard-visible trajectory projection;
- `ground_truth.json`: obligation label and evidence;
- `provenance.json`: benchmark task, environment, and execution provenance;
- `scenario.json` when present: frozen task/scenario definition;
- review and projection records used during acceptance.

## Important provenance boundary

The trajectories are benchmark-instance-derived expert executions recorded in Mini-SWE-Agent format. User tasks may be minimally rewritten and fixtures may be added; inspect each sample's `provenance.json`. Provider/model fields are response-format conditions and must not be interpreted as proof that the named provider generated the execution unless the provenance record explicitly says an external model API was called.

The positive and negative splits each have 120 unique source task IDs. Any source task IDs shared across splits represent distinct trajectories and labels; trajectory IDs are unique across the release.

## Validation

From the repository root:

```bash
python scripts/validate_release.py
```

The validator must report `release_valid=true`, `positive_count=120`, and `negative_count=120`.

## Citation and licensing

Please cite this repository and the original benchmark identified in each sample's provenance. The repository's MIT license applies to original repository-authored code and documentation. Source task text, code excerpts, and benchmark artifacts remain subject to their respective upstream licenses.
