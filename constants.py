# Internal tuning constants. Not user-facing — change only if you know what
# you're doing. User config lives in config.py.

# ---------------------------------------------------------------------------
# Job classifier
# ---------------------------------------------------------------------------
TITLE_MULTIPLIER     = 3     # title keyword match scores 3x a description match
SPECIALIST_THRESHOLD = 0.6   # specialist must score >= 60% of broad winner to override

# ---------------------------------------------------------------------------
# Scraper timeouts (milliseconds)
# ---------------------------------------------------------------------------
PAGE_GOTO_TIMEOUT        = 60000
H1_WAIT_TIMEOUT          = 10000
WORKDAY_SELECTOR_TIMEOUT = 12000
NETWORKIDLE_TIMEOUT      = 10000

# ---------------------------------------------------------------------------
# LLM retry (shared with llm.py)
# ---------------------------------------------------------------------------
RETRY_ATTEMPTS    = 4    # total Anthropic API call attempts before giving up
RETRY_BASE_WAIT_S = 10   # backoff base; actual wait = base * (attempt + 1)
