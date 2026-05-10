from playwright.sync_api import sync_playwright
import anthropic
import json
import re


def _company_from_url(url):
    """Extract company name from known ATS URL patterns.

    Workday:  swift.wd3.myworkdayjobs.com  → 'Swift'
    Greenhouse: boards.greenhouse.io/company → 'Company'
    Lever:    jobs.lever.co/company         → 'Company'
    """
    m = re.match(r'https?://([^.]+)\.wd\d+\.myworkdayjobs\.com', url)
    if m:
        return m.group(1).title()
    m = re.search(r'boards\.greenhouse\.io/([^/?]+)', url)
    if m:
        return m.group(1).replace("-", " ").title()
    m = re.search(r'jobs\.lever\.co/([^/?]+)', url)
    if m:
        return m.group(1).replace("-", " ").title()
    return None


def _title_from_url(url):
    """Extract a rough job title from the URL path slug (fallback only).

    e.g. .../Senior-FP-A-Analyst_2026-15510  →  'Senior FP A Analyst'
    """
    path = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"_\d{4}-\d+$", "", path)   # strip trailing job-id like _2026-15510
    return slug.replace("-", " ").strip() or None


def scrape_job(url):
    with sync_playwright() as p:
        # headless=True required for page.pdf() to produce a real PDF
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for h1 first, then for the actual job description body
        try:
            page.wait_for_selector("h1", timeout=10000)
        except Exception:
            pass

        # Workday SPAs load content asynchronously — wait for the description panel
        if "myworkdayjobs.com" in url:
            for sel in [
                '[data-automation-id="jobPostingDescription"]',
                '[data-automation-id="job-description"]',
                ".job-description",
            ]:
                try:
                    page.wait_for_selector(sel, timeout=12000)
                    break
                except Exception:
                    continue

        _dismiss_cookie_popup(page)

        raw_text = page.inner_text("body")

        try:
            pdf_bytes = page.pdf(format="A4", print_background=True)
        except Exception:
            pdf_bytes = None

        browser.close()

    structured = _extract_with_claude(raw_text, url=url)

    company = structured.get("company", "UNKNOWN")
    if company == "UNKNOWN":
        company = _company_from_url(url) or "UNKNOWN"

    title = structured.get("title", "") or _title_from_url(url) or ""

    return {
        "title": title,
        "company": company,
        "country": structured.get("country"),
        "description": raw_text,
        "intro": structured.get("intro", ""),
        "responsibilities": structured.get("responsibilities", ""),
        "qualifications": structured.get("qualifications", ""),
        "url": url,
        "pdf_bytes": pdf_bytes,
    }


def _dismiss_cookie_popup(page):
    """Try to reject/dismiss cookie consent popups before scraping."""
    # Selectors for reject/decline buttons (tried first)
    reject_selectors = [
        "button[id*='reject']", "button[id*='decline']", "button[id*='deny']",
        "button[class*='reject']", "button[class*='decline']", "button[class*='deny']",
        "a[id*='reject']", "a[class*='reject']",
        "[data-testid*='reject']", "[data-testid*='decline']",
        # Text-based matches
        "button:has-text('Reject all')", "button:has-text('Reject All')",
        "button:has-text('Decline all')", "button:has-text('Decline All')",
        "button:has-text('Decline')", "button:has-text('Reject')",
        "button:has-text('No thanks')", "button:has-text('No, thanks')",
    ]
    # Fallback: accept to at least dismiss the popup
    accept_selectors = [
        "button[id*='accept']", "button[class*='accept']",
        "[data-testid*='accept']",
        "button:has-text('Accept all')", "button:has-text('Accept All')",
        "button:has-text('Accept')", "button:has-text('I agree')",
        "button:has-text('Got it')", "button:has-text('OK')",
        "button:has-text('Agree')",
    ]

    for selector in reject_selectors + accept_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=150):
                btn.click(timeout=2000)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
                return
        except Exception:
            continue


def _extract_with_claude(raw_text, url=""):
    client = anthropic.Anthropic()
    url_hint = f"\nJob URL (use subdomain/path as hints for company and title if not clear from text): {url}" if url else ""
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": f"""Extract structured job posting data from the text below.

Return ONLY valid JSON with these keys:
- "title": a clean, professional job title suitable for use in a cover letter. Start from the posted title but use the full description to resolve ambiguity — expand abbreviations (e.g. "Snr" → "Senior"), pick the most fitting option when multiple levels or slash-separated titles are listed, and infer the actual role when the posted title is generic (e.g. "Team Member – Corporate Finance" → "Corporate Finance Associate"). Do not invent seniority not supported by the description.
- "company": the commonly used short name for the hiring company, as a professional would write it in a cover letter. Strip legal suffixes (Berhad, Sdn Bhd, Pty Ltd, Ltd, Inc, Corp, Group, Holdings, etc.) unless they are part of the brand (e.g. "S&P Global" keeps "Global"). Use the well-known abbreviation or brand name when one exists (e.g. "RHB" not "RHB Banking Group", "Maybank" not "Malayan Banking Berhad"). Return "UNKNOWN" if you cannot determine the company with confidence (e.g. staffing agency or aggregator page).
- "country": the country where the job is based (e.g. "Australia", "Malaysia", "United Kingdom") — return null if not determinable
- "intro": the introductory paragraph(s) before responsibilities/qualifications
- "responsibilities": the responsibilities section text
- "qualifications": the qualifications/requirements section text
{url_hint}
Job posting text:
{raw_text[:12000]}

Return only the JSON object, no explanation."""}]
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"title": "", "company": "UNKNOWN", "country": None, "intro": "", "responsibilities": "", "qualifications": ""}
