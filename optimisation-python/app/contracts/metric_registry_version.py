"""Version of the canonical scoring-metric registry (S8).

Owned by L3. Bump it whenever a metric is added, removed or redefined, or the
cached evaluation payload changes shape because of a metric change. The
evaluation cache context reads this constant by name, so a bump invalidates
older cache entries without any change to cache code.
"""

# Bumped to "2" by WP2-5 and WP2-6: AFFECTED_PARCEL_ROW_AREA and
# ENVIRONMENTAL_OVERLAP joined the registry. Both carry weight 0.0, so scores are
# unchanged, but the cached evaluation payload now carries an extra metric and
# older entries must not be reused.
METRIC_REGISTRY_VERSION = "2"
