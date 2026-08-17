# Corpus Generation Fixtures

| Fixture | Layout | Turbines | Provenance | Verification | Not verified |
| --- | --- | ---: | --- | --- | --- |
| `SYN-1-CLUSTERED-8.json` | Clustered, constrained feeder | 8 | `SYNTHETIC` | `PYTHON_CONTRACT_VERIFIED` | `REAL_SOURCE`, `ROUND_TRIP_VERIFIED` |
| `SYN-2-SPREAD-12.json` | Spread, west substation | 12 | `SYNTHETIC` | `PYTHON_CONTRACT_VERIFIED` | `REAL_SOURCE`, `ROUND_TRIP_VERIFIED` |
| `SYN-3-CLUSTERED-20.json` | Clustered, north-east substation | 20 | `SYNTHETIC` | `PYTHON_CONTRACT_VERIFIED` | `REAL_SOURCE`, `ROUND_TRIP_VERIFIED` |
| `SYN-4-SPREAD-30.json` | Spread, south substation | 30 | `SYNTHETIC` | `PYTHON_CONTRACT_VERIFIED` | `REAL_SOURCE`, `ROUND_TRIP_VERIFIED` |
| `SYN-5-MIXED-40.json` | Mixed, east substation | 40 | `SYNTHETIC` | `PYTHON_CONTRACT_VERIFIED` | `REAL_SOURCE`, `ROUND_TRIP_VERIFIED` |

The fixtures are deterministically generated with seed `42` by
`app/optimisation/corpus/synthetic_projects.py`. Feeder capacity varies through
the cable current limit in each request. They are synthetic Python contract
fixtures and must not be described as real-source or round-trip verified data.
