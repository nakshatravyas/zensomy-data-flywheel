"""Budget-constrained data selection for an autonomous-systems data flywheel.

Implements the selection stage described in `1-TECHNICAL-DESIGN.md` section 4:
turn a corpus of recorded clips into the subset most worth paying a human to
annotate, under a fixed annotation budget.
"""

__version__ = "1.0.0"

from .config import SelectionConfig
from .pipeline import run_selection

__all__ = ["SelectionConfig", "run_selection", "__version__"]
