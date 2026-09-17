"""Final-design fingerprint canonicaliser. Owned by L3 (WP0B-6).

Geometry fingerprint plus final installed conductor assignments and other
explicitly versioned installed fields. This is the identity the strong claim
uses. Output format: ``final_design:<version>:<sha256>``.
"""

from typing import Literal

FINAL_DESIGN_FINGERPRINT_VERSION = "1"


class FinalDesignFingerprinter:
    kind: Literal["final_design"] = "final_design"
    version = FINAL_DESIGN_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        raise NotImplementedError("Implemented by WP0B-6 (L3)")
