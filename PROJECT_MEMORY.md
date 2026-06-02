# Project Memory — ApplyKit

Use this file to onboard a new AI assistant instance for debugging or feature work.
Paste it at the start of your chat, then describe the issue or task.

---

## What this project does

Given a job posting URL, automatically:
1. Scrapes the job title, company, country, and description using Playwright + Claude Haiku
2. Auto-detects the job country, matches against `locations.json`
3. If detected: uses that profile silently. If not: shows an arrow-key country selector
4. Classifies the role against template subfolders using a keyword scorer (`keywords.json`)
5. Copies the matching resume template to an output folder
6. Fills blanks in the cover letter template using Claude Haiku — supports `_` (short fill) and `[DESCRIPTION]` (guided fill); only sentences containing a blank are sent, everything else untouched
7. Converts `.docx` to PDF via Microsoft Word and opens the output folder
8. Optionally merges cover letter with supplementary PDFs into a bundle (skipped if `BUNDLE_APPENDIX` is empty)

---

## File structure

```
auto-resume-cover-letter-tailor/
├── apply.py                # Entry point — scrape, country detect, generate
├── scraper.py              # Playwright scraper — extracts job data including country
├── generator.py            # Classifier + cover letter filler + PDF conversion
├── llm.py                  # Shared Claude call helper with retry
├── constants.py            # Internal tuning constants (classifier weights, timeouts)
├── config.py               # USER-SPECIFIC settings (gitignored)
├── config.example.py       # Template for config.py
├── keywords.json           # USER-SPECIFIC keyword map (gitignored)
├── keywords.example.json   # Extensive example covering 18+ job categories
├── locations.json          # USER-SPECIFIC country/city location map (gitignored)
├── locations.example.json  # Example covering 11 countries
├── requirements.txt        # anthropic, python-docx, docx2pdf, pypdf, python-dotenv, playwright, pywin32, questionary
├── .env                    # LLM API key (gitignored)
├── .env.example            # API key template — includes Anthropic, OpenAI, Groq, DeepSeek, etc.
└── .gitignore
```

---

## config.py — structure

```python
# Single country (simple)
OUTPUT_BASE               # path where generated folders are saved
TEMPLATE_BASE             # path to template subfolders
BUNDLE_NAME               # filename for the bundle PDF (defaults to "Cover Letter Bundle")
BUNDLE_APPENDIX           # PDFs merged into cover letter bundle PDF — skip merge if []

# Multi-country (optional — enables country detection + selector)
PROFILES = {
    "Malaysia":  { "OUTPUT_BASE": ..., "TEMPLATE_BASE": ... },
    "Australia": { "OUTPUT_BASE": ..., "TEMPLATE_BASE": ... },
    "Singapore": { "OUTPUT_BASE": ..., "TEMPLATE_BASE": ... },
    "Canada":    { "OUTPUT_BASE": ..., "TEMPLATE_BASE": ... },
    "Brunei":    { "OUTPUT_BASE": ..., "TEMPLATE_BASE": ... },
}
# Fallback — auto-set to first profile in dict
OUTPUT_BASE   = next(iter(PROFILES.values()))["OUTPUT_BASE"]
TEMPLATE_BASE = next(iter(PROFILES.values()))["TEMPLATE_BASE"]
```

No `DEFAULT_PROFILE` key — first entry in `PROFILES` is always the default.

---

## apply.py — runtime flow

Runs in a `while _run_once(): pass` loop — after each application is saved, it loops back and prompts for the next URL. Type `q` or press Enter on a blank line to exit. Any exception in `_process(url)` is caught and printed; the loop continues to the next URL. Ctrl+C exits cleanly.

Each iteration (`_run_once()`):
1. Prompt for job URL (returns `False` if blank or `q`)
2. `scrape_job(url)` → returns `data` dict including `country`
3. Blank line printed for visual separation
4. If `PROFILES` defined in config:
   - `_load_locations()` reads `locations.json` from project root
   - `_detect_profile(country, locations)` matches country string against location lists
   - If detected: print `Country: X` and use that profile silently — no menu shown
   - If not detected: print `Location not detected` and show `questionary.select` menu
   - `config.OUTPUT_BASE` and `config.TEMPLATE_BASE` overridden with chosen profile
5. `classify_job` runs and category is shown to user
6. User confirms/corrects title, company, and category via a 6-choice prompt: Yes / edit title / edit company / edit title and company / edit category / edit all (category uses arrow-key selector)
7. `generate_application(data, category=category)` called

---

## generator.py — key functions

**`_load_keywords()`**
Reads `keywords.json` from project root. Returns dict keyed by lowercase folder name. Warns if file missing.

**`classify_job(title, description)`**
Scores available template subfolders against keywords. Title matches x3 weight. Tie-break: prefer folders with title evidence first, then by priority order. Prints score table to terminal.

**`fill_cover_letter(path, company, title, intro, responsibilities, qualifications)`**
- Finds all paragraphs containing `_` or `[...]` patterns
- Splits each paragraph into sentences using `re.split(r'(?<=[.!?])\s+(?=[A-Z])', ...)`
- Sends ONLY the sentence(s) containing a blank to Claude Haiku
- Two blank types: `_` (replace with short company/role-specific content), `[DESCRIPTION]` (replace entire bracket including brackets with a sentence matching the description)
- Claude is instructed to keep fills concise (one clause for `_`, one sentence max for `[DESCRIPTION]`)
- Splices filled sentence back into full paragraph
- Preserves bold formatting on job title
- Date replaced via regex (format: `2 June 2026` — no ordinal suffix)
- No em dashes in output (enforced in prompt)

**`generate_application(data)`**
Orchestrates: classify -> copy templates -> fill cover letter -> convert to PDF -> page count check (warns if > 1 page) -> merge bundle (only if `BUNDLE_APPENDIX` is non-empty) -> open output folder.

---

## scraper.py — key logic

**`scrape_job(url)`**
Headless Edge, navigates to URL, captures raw text (before cookie popup dismissal to avoid bot-detection timing), generates PDF, then passes text to Claude Haiku to extract structured JSON:
- `title`, `company`, `country` (null if not determinable), `intro`, `responsibilities`, `qualifications`

All fields returned in the data dict. `country` drives profile detection in `apply.py`.

URL-based fallback for company/title extraction: Workday (`*.wd*.myworkdayjobs.com`), Greenhouse (`boards.greenhouse.io`), Lever (`jobs.lever.co`).

If the scraped text is detected as a bot-block page (406, 403, captcha, challenge, <200 chars), `_is_blocked()` triggers a clipboard fallback: user copies the job page text (`Ctrl+A`, `Ctrl+C`) and presses Enter — content is read via `pyperclip.paste()`.

---

## locations.json format

```json
{
  "Malaysia":  ["malaysia", "kuala lumpur", "kl", "penang", "selangor"],
  "Australia": ["australia", "melbourne", "sydney", "brisbane"],
  "Singapore": ["singapore", "sg"],
  "Canada":    ["canada", "toronto", "vancouver", "montreal"],
  "Brunei":    ["brunei", "brunei darussalam", "bandar seri begawan"]
}
```

Keys must exactly match `PROFILES` keys in `config.py`. Keys starting with `_` are ignored.

---

## keywords.json format

```json
{
  "_broad_categories": ["Finance", "Accounting", "Investment"],
  "Finance":   ["fp&a", "budget", "forecasting", "finance analyst"],
  "Fixed Income": ["fixed income", "bonds", "yield"]
}
```

Keys must match template subfolder names (case-insensitive). Keys starting with `_` are ignored by the scorer.

**`_broad_categories`** — list categories that are general fallbacks. If a broad category wins with no title evidence but any specialist category has description signal, the specialist wins instead. Any category not listed here is treated as a specialist. This applies across all domains — not finance-specific.

---

## Cover letter blank rules

Two blank types supported in templates:
- `_` — short fill: company name, role title, or a brief phrase
- `[DESCRIPTION]` — guided fill: write what you want inside the brackets; Claude replaces the entire `[...]` with a natural sentence drawn from the job description

General rules:
- Fixed sentences (experience, background, tools) are NEVER modified
- Only the sentence(s) containing a blank are sent to Claude — rest of paragraph untouched
- Fills are kept concise: one clause for `_`, one sentence max for `[DESCRIPTION]`
- Date format: `2 June 2026` (no ordinal suffix)
- No em dashes or en dashes in output
- After PDF conversion, page count is checked; a warning is printed if > 1 page

---

## Template folder structure

```
TEMPLATE_BASE/
├── Finance/
│   ├── Resume.pdf
│   └── Cover Letter.docx
└── Marketing/
    └── ...
```

Subfolder names must match keys in `keywords.json`.

---

## Tech stack

| Library | Purpose |
|---------|---------|
| `playwright` (sync) | Headless Edge scraping |
| `anthropic` | Claude Haiku -- job extraction + cover letter filling |
| `python-docx` | Read/write `.docx` templates |
| `docx2pdf` | `.docx` -> PDF via Microsoft Word (Windows only) |
| `pypdf` | Merge cover letter bundle PDFs |
| `python-dotenv` | Load API key from `.env` |
| `questionary` | Arrow-key country selector in terminal |
| `pywin32` | Windows COM interface for Word/PDF conversion |
| `pyperclip` | Clipboard read for bot-protected job pages |

---

## GitHub

```
https://github.com/rifattahmid/ApplyKit
```
