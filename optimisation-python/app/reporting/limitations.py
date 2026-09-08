from app.reporting.schema_version import CURRENT_REPORT_SCHEMA_VERSION

REPORT_SCHEMA_LIMITATIONS = {
    CURRENT_REPORT_SCHEMA_VERSION: {
        "spatial.hard_exclusion_violation_count": "not_materialized_upstream",
    }
}
