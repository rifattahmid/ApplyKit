# =============================================================================
# USER CONFIGURATION — copy this file to config.py and fill in your values
# =============================================================================

# ---------------------------------------------------------------------------
# Output & template paths
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Option A — single country (simple, no profile prompt at runtime)
# ---------------------------------------------------------------------------

OUTPUT_BASE   = r"C:\Users\YourName\Documents\Job Applications"
TEMPLATE_BASE = r"C:\Users\YourName\Documents\Templates"

# ---------------------------------------------------------------------------
# Option B — multiple countries (shows an arrow-key country selector at runtime)
# ---------------------------------------------------------------------------
# Uncomment PROFILES below. Each key becomes a selectable option in the menu.
# Country-to-profile matching is handled by locations.json (copy locations.example.json).
# DEFAULT_PROFILE is pre-selected in the menu; falls back to first profile if unset.
#
# DEFAULT_PROFILE = "United States"
#
# PROFILES = {
#     "United States": {
#         "OUTPUT_BASE":   r"C:\Users\YourName\Documents\Applications\US",
#         "TEMPLATE_BASE": r"C:\Users\YourName\Documents\Templates\US",
#     },
#     "United Kingdom": {
#         "OUTPUT_BASE":   r"C:\Users\YourName\Documents\Applications\UK",
#         "TEMPLATE_BASE": r"C:\Users\YourName\Documents\Templates\UK",
#     },
#     "Singapore": {
#         "OUTPUT_BASE":   r"C:\Users\YourName\Documents\Applications\SG",
#         "TEMPLATE_BASE": r"C:\Users\YourName\Documents\Templates\SG",
#     },
# }

# ---------------------------------------------------------------------------
# Supplementary file uploads (optional)
# ---------------------------------------------------------------------------
# Extra PDFs uploaded alongside your resume (e.g. transcripts, references)
# Leave empty [] if you have none.

SUPPLEMENTARY_FILES = [
    # r"C:\Users\YourName\Documents\References.pdf",
    # r"C:\Users\YourName\Documents\Transcript.pdf",
]

# ---------------------------------------------------------------------------
# Cover letter bundle (optional)
# ---------------------------------------------------------------------------
# PDFs appended after the cover letter to create a combined bundle PDF.
# Leave empty [] if you do not want a bundle.

BUNDLE_APPENDIX = [
    # r"C:\Users\YourName\Documents\Recommendations.pdf",
    # r"C:\Users\YourName\Documents\Transcript.pdf",
]
