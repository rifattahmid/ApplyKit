# =============================================================================
# USER CONFIGURATION - copy this file to config.py and fill in your values
# =============================================================================


# =============================================================================
# 1. Profiles And Folders
# =============================================================================
# Pick Option A for a single country, or Option B for multiple countries.

# ---------------------------------------------------------------------------
# Option A - single country
# ---------------------------------------------------------------------------
# Use this when all generated applications and templates live under one market.

OUTPUT_BASE   = r"C:\Users\YourName\Documents\Job Applications"
TEMPLATE_BASE = r"C:\Users\YourName\Documents\Templates"

# ---------------------------------------------------------------------------
# Option B - multiple countries
# ---------------------------------------------------------------------------
# Uncomment PROFILES below to enable country detection and a country selector.
# Each key becomes a selectable profile. Keys should match locations.json.
# DEFAULT_PROFILE is optional; it is preselected when location detection fails.
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


# =============================================================================
# 2. LLM Provider
# =============================================================================
# Supported providers:
# - "anthropic": uses ANTHROPIC_API_KEY and the Anthropic Messages API
# - "openai": uses OPENAI_API_KEY and the OpenAI Responses API
# - "openai-compatible": uses LLM_API_KEY + LLM_BASE_URL for compatible APIs
#
# Leave LLM_MODEL as None to use the built-in default for Anthropic/OpenAI.
# For openai-compatible, set LLM_MODEL to the provider's exact model name.

LLM_PROVIDER = "anthropic"
LLM_MODEL = None
LLM_BASE_URL = None


# =============================================================================
# 3. Template File Discovery
# =============================================================================
# These globs are matched inside the selected category folder. Leave them as
# None to use legacy auto-detection. Set them when you keep both original and
# editable resume files in the same category folder.
#
# Example category folder:
#   Applicant_Resume.docx       # original, unmarked
#   Applicant_Resume.pdf        # original static PDF copied to output
#   Applicant_Resume_Edit.docx  # editable marker template used by ATSmith
#   Applicant_Cover Letter.docx

RESUME_ORIGINAL_PDF_GLOB = None       # e.g. "*_Resume.pdf"
RESUME_EDITABLE_DOCX_GLOB = None      # e.g. "*_Resume_Edit.docx"
COVER_LETTER_DOCX_GLOB = None         # e.g. "*Cover Letter.docx"


# =============================================================================
# 4. Resume Tailoring
# =============================================================================
# ATSmith searches resume source files in this order:
# 1. Selected category folder:
#    TEMPLATE_BASE\<Category>\resume.source.md
# 2. Selected country/template folder:
#    TEMPLATE_BASE\resume.source.md
# 3. ATSmith project fallback:
#    RESUME_SOURCE below, resolved from the project folder if relative
#
# Use category-level files when categories differ, country-level files for facts
# shared by all categories in one country, and project-level files as a final
# fallback/default for new users. Leave as-is if you do not use resume markers.

RESUME_SOURCE_FILENAME = "resume.source.md"
RESUME_SOURCE = "resume.source.md"

# Optional second source layer for user-approved transferable phrasing. Use this
# for defensible mappings while keeping strict facts in resume.source.md.

RESUME_EXTENDED_FILENAME = "resume.extended.md"
RESUME_EXTENDED_SOURCE = "resume.extended.md"

# Tailored resume PDF filename in the job output folder.
# Available placeholders:
#   {resume_stem}       -> editable DOCX filename without .docx
#   {resume_stem_clean} -> same stem with trailing _Edit/-Edit/ Edit removed
#
# Default creates "Applicant_Resume.pdf" from
# "Applicant_Resume_Edit.docx", replacing the copied static resume PDF only
# inside that job's output folder. Set to "{resume_stem}.pdf" to keep "_Edit".

RESUME_TAILORED_PDF_NAME = "{resume_stem_clean}.pdf"

# Maximum acceptable resume PDF page count after tailoring. Keep this at 1 for
# one-page resumes; users with two-page resumes can set it to 2.

RESUME_PAGE_LIMIT = 1

# Resume tailoring strength:
# - "conservative": edit only direct, obvious sentence-to-job keyword matches
# - "balanced": edit direct and coherent adjacent matches
# - "aggressive": allow stronger adjacent phrasing when supported by source files

RESUME_TAILORING_AGGRESSION = "balanced"

# Large resume.extended.md files are parsed into sections; only relevant
# sections are sent to the LLM to keep prompts focused and cheaper.

RESUME_EXTENDED_SELECTION_ENABLED = True
RESUME_EXTENDED_MAX_SECTIONS = 8
RESUME_EXTENDED_MAX_CHARS = 12000
RESUME_EXTENDED_MIN_SCORE = 2


# =============================================================================
# 5. Cover Letter
# =============================================================================

# Cover letter PDF filename in the job output folder.
# Available placeholders:
#   {cover_stem}       -> cover DOCX filename without .docx
#   {cover_stem_clean} -> same stem with trailing _Edit/-Edit/ Edit removed

COVER_LETTER_PDF_NAME = "{cover_stem_clean}.pdf"

# Maximum acceptable cover letter PDF page count after filling blanks.

COVER_LETTER_PAGE_LIMIT = 1

# Number of times ATSmith may ask the LLM to micro-shorten a cover
# letter DOCX and re-render if the PDF exceeds its configured page limit.
# Set to 0 to only warn. Resumes use edit rollback instead of line-shortening.

PAGE_FIT_MAX_ATTEMPTS = 2

# Cover-letter page-fit shortening guardrails. ATSmith only sends this
# many long lines per attempt and rejects rewrites that cut a line below the
# retain ratio.

PAGE_FIT_MAX_LINES_PER_ATTEMPT = 4
PAGE_FIT_MIN_LINE_RETAIN_RATIO = 0.88


# =============================================================================
# 6. Cover Letter Bundle
# =============================================================================
# PDFs appended after the cover letter to create a combined bundle PDF.
# Leave BUNDLE_APPENDIX empty [] if you do not want a bundle PDF generated.
# BUNDLE_NAME is the filename of the bundle. The .pdf extension is added.

BUNDLE_NAME = "Cover Letter Bundle"

BUNDLE_APPENDIX = [
    # r"C:\Users\YourName\Documents\Recommendations.pdf",
    # r"C:\Users\YourName\Documents\Transcript.pdf",
]


# =============================================================================
# 7. CLI Output
# =============================================================================
# - "quiet": compact counts only
# - "normal": counts and per-marker added keyword phrases
# - "debug": normal output plus full edited resume sentences and skipped reasons
#
# Cover letter filled sentences are always shown because they are useful to review.

CLI_VERBOSITY = "normal"
