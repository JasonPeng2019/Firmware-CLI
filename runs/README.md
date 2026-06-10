# Runtime Output

`runs/` is the canonical home for local runtime output.

Tracked code and docs define the shape; actual session output stays untracked.

Canonical layout:

```text
runs/<session_id>/
├── logs/
├── captured-serial/
├── applied-patches/
└── run-metadata/
```

Use the same `<session_id>` everywhere later runtime state is keyed so logs,
serial captures, and metadata stay correlated.
