# Operations and recovery

## Startup and health

Use `python atom_doctor.py` after installation and after updates. The report distinguishes Pi hardware, cooling/power, boot storage, Hailo, audio, wake model, local model, backend, internet, knowledge drive, and disk capacity. Offline internet status is degraded, not fatal.

The unauthenticated backend and Kiwix service must remain on loopback. Do not set `ATOM_BIND_HOST=0.0.0.0` without authentication, firewall rules, and an explicit review.

## Data, backup, and recovery

Source knowledge stays on the removable drive. `library_index/` contains rebuildable schema-versioned snippets and metadata only. Run `python atom_knowledge.py --index` after reconnecting or changing content. The index updates modified files and removes deleted paths; if a schema changes, it is rebuilt automatically.

`python atom_doctor.py --backup` creates an archive that may contain credentials and conversation history. Encrypt it, restrict it to the owner, store it off-device, and test restoration. Delete obsolete backups according to the owner's retention choice.

For rollback, restore the previously recorded upstream commit pins and ATOM version, rerun `bash install.sh --sync`, then run diagnostics. Do not report the system ready until the physical validation in `VALIDATION.md` passes.

## Hardware-only checks

Run on the intended Raspberry Pi: `hailortcli fw-control identify`, `python atom_doctor.py --sound`, `python atom_doctor.py --mic`, `python validate_model.py`, `python vision_describe.py`, and the complete interaction contract in `VALIDATION.md`. These checks are intentionally excluded from standard CI.
