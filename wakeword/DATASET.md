# Dataset layout

data/
├── positive/    pos_01.wav ... pos_30.wav   — you saying "Hey ATOM"
└── negative/    neg_01.wav ... neg_40.wav   — everything else

Format: WAV, 16 kHz, mono, 16-bit (record_dataset.py enforces this).

POSITIVE (aim 30+, more speakers = better): vary pitch, speed, volume
(quiet to normal), distance (0.5m / 2m / across the room), angle, and
room noise (some clips with TV/music quietly on).

NEGATIVE (aim 40+): ordinary conversation, reading a paragraph aloud,
TV/radio snippets, household noise, silence, and — most important —
SIMILAR PHRASES: "hey adam", "hey autumn", "hey tom", "atom bomb",
"a tomb", "hey mom", "hey" alone, "atom" alone.

Split: validate_model.py uses everything as a held-out test set (the
notebook trains on synthetic data), which is exactly what you want —
your recordings prove generalization to your real room and mic.


