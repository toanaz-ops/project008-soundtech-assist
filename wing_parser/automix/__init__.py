"""Genre-driven channel-strip proposals (GUI wave 12).

Importing this package loads nothing heavy; the UI imports it only when
the Automix mode is not Disabled (AM-20).
"""

from wing_parser.automix.engine import propose, to_patches
from wing_parser.automix.options import (
    GENRES,
    STAGES,
    AutomixOptions,
    Change,
    Proposal,
    Skipped,
    Suggestion,
)

__all__ = ["GENRES", "STAGES", "AutomixOptions", "Change", "Proposal", "Skipped",
           "Suggestion", "propose", "to_patches"]
