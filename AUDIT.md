# ATOM-Pi audit — 2026-08-22

## Evidence summary

- Canonical name: ATOM-Pi. Repository evidence consistently defines ATOM; MILES is not the current product.
- Stage: release-candidate hardware integration prototype (`1.0.0-rc2`), not yet a general personal-assistant platform.
- Stack: Python device/tool modules, React/Electron UI components, shell installer, FastAPI/WebSocket behavior supplied by pinned upstream `pocket-ai`, SQLite FTS5 knowledge index, Ollama/Moondream, openWakeWord, Hailo, Kiwix.
- Deployment: Raspberry Pi 5 on NVMe with active cooling; Hailo-8L vision acceleration; touchscreen, camera, USB audio, and optional removable knowledge drive.
- Architecture: a deliberately small overlay around a pinned modular monolith. Preserve it; do not split it into services without evidence.

## Initial condition and risks

The repository had strong hardware and interaction documentation but no automated tests, CI, package metadata, safe environment example, threat model, action-authorization boundary, deterministic brief schema, scheduled-job idempotency primitive, or agent guide. The document index added files but did not refresh modified documents or remove deleted ones. Diagnostics invoked fixed commands through a shell, log selection could escape the application directory, and camera/model exceptions exposed internal details to users. The browser demo calls an external model API and must never embed a secret; production should prefer the local pipeline.

Hardware documentation is realistic that Hailo supports selected vision workloads, not arbitrary LLM inference. Physical performance, thermals, audio, camera, Hailo, NVMe, wake-word accuracy, and end-to-end barge-in remain unverified outside the Pi.

## Implemented priorities

Critical: code-level action classification, prohibited financial actions, explicit confirmation for external writes, untrusted-content delimiters, secret redaction, loopback guidance, safer diagnostics, sanitized user errors, secret scanning, and a threat/privacy model.

Important: versioned change/delete-aware knowledge indexing, deterministic sourced/freshness-labeled briefs, DST-aware rendering, SQLite job idempotency, tests/evaluations, dependency auditing, reproducible package metadata, and CI.

Optional/future: real read-only email/calendar/tasks/news/weather/market adapters; authenticated LAN access; encrypted backup automation; structured provider adapters and circuit breakers in upstream `pocket-ai`; measured Pi performance budgets.

## Product decisions still required

1. Which integrations and providers to support first, and their acceptable data-sharing/privacy boundaries.
2. Default home time zone and morning-brief delivery time/channel.
3. Backup location, encryption method, retention, and deletion policy.
4. Whether LAN access is needed; loopback-only remains the safe default.
5. Whether any external write capability should exist. Trading and financial execution remain prohibited.

## Validation record

Passed locally: editable development install; Python compilation; Ruff format check; Ruff lint; 15 unit/evaluation tests; dependency audit with no known vulnerabilities after upgrading pip; mock-only offline brief smoke test; high-confidence secret-pattern and large-file scan.

Not runnable here: Raspberry Pi installer, apt/systemd, Electron build inherited from `pocket-ai`, Hailo, NVMe, thermal, camera, microphone/speaker, wake model, Ollama/Moondream, Kiwix, and physical interaction tests. Exact commands are in `AGENTS.md`, `OPERATIONS.md`, and `VALIDATION.md`.

Quality score: 4/10 before (well-documented prototype, weak automated assurance) and 7/10 after (clearer boundaries, repeatable checks, failure-mode evaluations, and safer indexing). It cannot credibly reach 9–10 until the changes are integrated with the upstream runtime and the complete Pi validation contract passes.
