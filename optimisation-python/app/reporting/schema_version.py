"""Single source of truth for the report schema version string.

The PY-037 suppression mechanism (REPORT_SCHEMA_LIMITATIONS in limitations.py)
keys on this exact string to decide which report fields are placeholders.
Keeping the version in one place prevents a silent regression where bumping
the literal in builder.py alone causes the limitation lookup to miss, exposing
unmaterialized upstream data as real metrics in production reports.
"""

CURRENT_REPORT_SCHEMA_VERSION: str = "1.0.0"
