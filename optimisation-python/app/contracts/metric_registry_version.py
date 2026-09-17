"""Version of the canonical scoring-metric registry (S8).

Owned by L3. Bump it whenever a metric is added, removed or redefined, or the
cached evaluation payload changes shape because of a metric change. The
evaluation cache context reads this constant by name, so a bump invalidates
older cache entries without any change to cache code.
"""

METRIC_REGISTRY_VERSION = "1"
