# Agency Client Postings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect recruiter or agency postings, preserve correct output folder naming, and use safe client-facing cover-letter language.

**Architecture:** Extend scraper extraction with posting-context metadata, normalize that metadata at the scrape boundary, display it in the CLI review, and pass a separate cover-letter company reference into generation. Existing direct-employer postings default to current behavior.

**Tech Stack:** Python, pytest, python-docx, existing ATSmith scraper/apply/generator modules.

---

### Task 1: Normalize Posting Context At Scrape Boundary

**Files:**
- Modify: `scraper.py`
- Test: `tests/test_scraper.py`

- [ ] **Step 1: Write failing scraper tests**

Add tests that patch `_extract_with_llm()` and assert:

```python
def test_scrape_job_named_agency_client_uses_client_as_company(monkeypatch):
    import scraper

    raw_text = "Recruiter text. Our client Acme Energy is hiring a Finance Analyst."
    monkeypatch.setattr(scraper, "sync_playwright", fake_playwright_factory(raw_text))
    monkeypatch.setattr(
        scraper,
        "_extract_with_llm",
        lambda _raw, url="": {
            "title": "Finance Analyst",
            "company": "Acme Energy",
            "posting_company": "Robert Walters",
            "posting_context": "agency_for_named_client",
            "client_company": "Acme Energy",
            "cover_letter_company_reference": "Acme Energy",
            "country": "Malaysia",
            "intro": "Intro",
            "responsibilities": "Responsibilities",
            "qualifications": "Qualifications",
        },
    )

    result = scraper.scrape_job("https://jobs.example.com/finance-analyst")

    assert result["company"] == "Acme Energy"
    assert result["posting_company"] == "Robert Walters"
    assert result["posting_context"] == "agency_for_named_client"
    assert result["client_company"] == "Acme Energy"
    assert result["cover_letter_company_reference"] == "Acme Energy"
```

Add a second test for unnamed agency client:

```python
def test_scrape_job_unknown_agency_client_uses_recruiter_for_folder_and_client_for_letter(monkeypatch):
    import scraper

    raw_text = "Recruiter text. Our client is a leading financial services firm."
    monkeypatch.setattr(scraper, "sync_playwright", fake_playwright_factory(raw_text))
    monkeypatch.setattr(
        scraper,
        "_extract_with_llm",
        lambda _raw, url="": {
            "title": "Finance Analyst",
            "company": "Robert Walters",
            "posting_company": "Robert Walters",
            "posting_context": "agency_for_unknown_client",
            "client_company": None,
            "cover_letter_company_reference": "your client",
            "country": "Malaysia",
            "intro": "Intro",
            "responsibilities": "Responsibilities",
            "qualifications": "Qualifications",
        },
    )

    result = scraper.scrape_job("https://jobs.example.com/finance-analyst")

    assert result["company"] == "Robert Walters"
    assert result["posting_context"] == "agency_for_unknown_client"
    assert result["client_company"] is None
    assert result["cover_letter_company_reference"] == "your client"
```

- [ ] **Step 2: Run scraper tests to verify failure**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_scraper.py -q -p no:cacheprovider
```

Expected: new tests fail because `scrape_job()` drops the new fields.

- [ ] **Step 3: Implement metadata normalization**

In `scraper.py`, add helpers:

```python
POSTING_CONTEXTS = {
    "direct_employer",
    "agency_for_named_client",
    "agency_for_unknown_client",
}

def _normalized_posting_context(structured, company):
    context = str(structured.get("posting_context") or "direct_employer").strip().lower()
    if context not in POSTING_CONTEXTS:
        context = "direct_employer"
    posting_company = _clean_optional_text(structured.get("posting_company"))
    client_company = _clean_optional_text(structured.get("client_company"))

    if context == "agency_for_named_client" and not client_company:
        context = "agency_for_unknown_client"
    if context == "agency_for_named_client":
        company = client_company
        reference = client_company
    elif context == "agency_for_unknown_client":
        reference = "your client"
        posting_company = posting_company or company
    else:
        reference = company
        posting_company = None
        client_company = None
    return company, posting_company, context, client_company, reference
```

- [ ] **Step 4: Extend extraction prompt**

Update `_extract_with_llm()` JSON schema instructions for:

```text
"posting_context", "posting_company", "client_company", "cover_letter_company_reference"
```

Make direct-employer the default when no third-party client wording appears.

- [ ] **Step 5: Return metadata from `scrape_job()`**

Include the new fields in the returned data dict.

- [ ] **Step 6: Run scraper tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_scraper.py -q -p no:cacheprovider
```

Expected: pass.

### Task 2: Display Posting Context In CLI Review

**Files:**
- Modify: `apply.py`
- Test: local smoke via existing tests

- [ ] **Step 1: Add review output**

After printing `Company`, print:

```python
posting_context = data.get("posting_context", "direct_employer")
posting_company = data.get("posting_company")
if posting_company:
    print(f"  Posted by: {posting_company}")
if posting_context != "direct_employer":
    print(f"  Posting:  {posting_context.replace('_', ' ')}")
```

- [ ] **Step 2: Run smoke tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_scraper.py -q -p no:cacheprovider
```

Expected: pass.

### Task 3: Use Client Reference In Cover Letter

**Files:**
- Modify: `generator.py`
- Test: `tests/test_cover_letter_output.py`, `tests/test_application_generation.py`

- [ ] **Step 1: Write failing cover-letter prompt test**

Add a cover-letter test where `fill_cover_letter()` is called with `company="Robert Walters"` and `cover_letter_company_reference="your client"`. Assert the prompt contains:

```text
Company/folder name: Robert Walters
Cover-letter employer reference: your client
```

and the final document replaces `_` with `your client`, not `Robert Walters`.

- [ ] **Step 2: Implement derived cover-letter reference**

Add:

```python
def _cover_letter_company_reference(data):
    context = data.get("posting_context", "direct_employer")
    reference = str(data.get("cover_letter_company_reference") or "").strip()
    if context == "agency_for_unknown_client":
        return reference or "your client"
    return reference or data.get("company", "")
```

Update `generate_application()` to pass the derived reference into `fill_cover_letter()` while keeping `company` for folder naming.

- [ ] **Step 3: Update cover-letter prompt**

In `fill_cover_letter()`, rename prompt wording from "Company (USE EXACTLY THIS)" to distinguish folder/posting company from cover-letter employer reference:

```text
Company/folder name: {company}
Cover-letter employer reference (USE EXACTLY THIS): {company_reference}
```

For unknown-client postings, add rules:

```text
- This is an agency posting for an unnamed client.
- Use the cover-letter employer reference, not the posting company, when filling company/employer blanks.
- Do not describe the posting company as the employer.
- Avoid company/sector-specific claims unless the client context is stated in the job posting.
```

- [ ] **Step 4: Run cover-letter tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_cover_letter_output.py tests\test_application_generation.py -q -p no:cacheprovider
```

Expected: pass.

### Task 4: Full Verification And Commit

**Files:**
- Modify: `scraper.py`, `apply.py`, `generator.py`
- Plan: `docs/superpowers/plans/2026-06-14-agency-client-postings.md`

- [ ] **Step 1: Run full tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

Expected: all tests pass.

- [ ] **Step 2: Compile modules**

Run:

```powershell
.\venv\Scripts\python.exe -m py_compile apply.py scraper.py generator.py llm.py constants.py config.example.py classifier.py resume_context.py
```

Expected: exit code 0.

- [ ] **Step 3: Check diff**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors. CRLF warnings are acceptable in this repo.

- [ ] **Step 4: Commit and push when requested**

Commit message:

```bash
git commit -m "feat: handle agency client postings"
```
