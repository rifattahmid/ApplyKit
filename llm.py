import time
import anthropic

from constants import RETRY_ATTEMPTS, RETRY_BASE_WAIT_S

MODEL = "claude-haiku-4-5-20251001"


def call_claude(prompt: str, max_tokens: int = 1000) -> str:
    """Call Claude with retry on transient errors (500/502/503/529).

    Returns the response text (stripped). Raises on non-retryable errors or
    after RETRY_ATTEMPTS attempts.
    """
    client = anthropic.Anthropic()
    for attempt in range(RETRY_ATTEMPTS):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code in (500, 502, 503, 529) and attempt < RETRY_ATTEMPTS - 1:
                wait = RETRY_BASE_WAIT_S * (attempt + 1)
                print(f"  API error {e.status_code} — retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
