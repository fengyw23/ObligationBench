# ObligationBench v1.0 data card

## Task

Given a user task and an execution trajectory, identify each concrete safety action that remains unfinished at trajectory end and whose omission may cause a material safety problem. The benchmark deliberately excludes ordinary incompleteness, quality defects, performance problems, and unrelated unsafe behavior from the obligation label.

## Splits

- **Positive (120):** 339 independently recorded unresolved obligations.
- **Hard negative (104):** zero unresolved obligations. These samples include closed lifecycles, legitimate persistent security resources, fail-closed behavior, successful rotation, and ordinary failures whose safety-relevant state is closed.

The released corpus contains 224 trajectories. The negative construction pipeline originally targeted 120; this authoritative v1.0 snapshot intentionally freezes the 104 accepted samples selected by the user.

## Benchmark sources

Positive split:

- Terminal-Bench 2.0: 64
- SWE-Bench Pro: 40
- FeatureBench: 16

Negative split:

- SWE-Bench Pro: 36
- FeatureBench: 32
- TerminalWorld: 28
- Terminal-Bench: 6
- Terminal-Bench 2.0: 2

## Sample identity

- Ground-truth `task_id` values are unique across all 224 samples.
- `source_task_id` values are unique within each split.
- Seven benchmark source task IDs occur in both splits, each with a distinct task trajectory and label.
- The negative split contains 91 distinct source images; limited image reuse is documented in provenance and the release summary.

## Trajectory and model metadata

All trajectories use `mini-swe-agent-1.1` structure. The corpus contains four balanced response-format conditions. These conditions control envelope shape and are not, by themselves, evidence of provider authorship. The authoritative execution status is the per-sample `provenance.json`.

## Guard-visible data

`guard_input.json` is the evaluation view. It omits hidden reasoning and construction-only material while preserving the user task, assistant tool calls, tool returns, and exit state needed to infer obligations. Ground-truth and semantic-review files must not be supplied to the Guard.

## Known evaluation consideration

The negative trajectories are generally shorter than the positive trajectories. This is recorded as a distribution advisory, not a semantic rejection criterion. Researchers should avoid using trajectory length as a label feature and should report shortcut-controlled results where possible.

## Intended use

- Evaluation and analysis of obligation identification in agent trajectories.
- Error analysis of false negatives on unresolved safety state and false positives on safely closed or legitimate persistent state.
- Research on trajectory-level safety monitoring.

## Limitations

- Tasks are benchmark-instance-derived; some user tasks were minimally rewritten or use local fixtures.
- Expert execution and provider-format conditioning mean the corpus must not be used to infer behavioral differences among the named model providers.
- The release does not claim that every possible safety action in the underlying software is represented.
- Upstream benchmark licenses continue to apply to third-party task text and code excerpts.

