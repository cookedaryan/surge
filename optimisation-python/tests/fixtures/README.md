# Test fixture provenance

## `constraint_demo_project_v2.json`

`constraint_demo_project_v2.json` is a hand-authored, deterministic
**Python-contract fixture**. It represents one well-formed V2 optimisation
request containing one WTG, one substation, one hard restricted polygon, and
one soft road.

The fixture proves that the Python service can:

- ingest the documented request shape;
- map and project constraint features;
- rasterize hard exclusions and soft penalties;
- reject endpoints covered by hard buffered geometry;
- route without crossing the hard polygon;
- report deterministic spatial constraint summaries; and
- preserve V1 behavior through the legacy adapter.

There is no separate V1 constraint fixture. The PY-021 V1 API tests load this
file and add the legacy `scenario` field in memory.

## Provenance limitation

This file is **not a verified KMZ round-trip artifact**. It was not captured
from Java after a KMZ upload, preview, classification, confirmation, commit,
and optimisation-job cycle. It therefore does not prove that Java's KMZ-to-JSON
transformation produces this exact request shape, identifiers, properties, or
constraint policy.

The JSON payload deliberately contains no `_provenance` field because it is
also submitted directly to the strict V2 request schema. Keeping provenance in
this sibling document avoids changing the API fixture itself.

## Upgrading to verified KMZ provenance

Closing the cross-system provenance gap requires the Java/frontend owners to:

1. Select a fixed, non-sensitive test KMZ containing the intended WTG,
   substation, restricted-area, and road features.
2. Run it through the real upload, preview, classification/override, confirm,
   and commit workflow.
3. Start an optimisation job and capture the exact JSON request that Java's
   `OptimizationJobService` sends to Python.
4. Compare that captured request with this fixture, documenting any intentional
   normalization of volatile identifiers and updating the contract fixture if
   the production mapping differs.
5. Retain the source KMZ, captured payload, capture procedure, and a Java-side
   integration test together so the transformation can be reproduced.

Once that evidence exists, Python can rerun the existing V1/V2 constraint tests
against the captured payload. Until then, describe this file only as a
Python-contract fixture.
