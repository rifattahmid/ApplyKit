# Auto Resume & Cover Letter Tailor

Paste a job URL. Get a tailored resume and cover letter in seconds.

---

## Why this is different from AI-generated cover letters

Most AI cover letter tools generate the entire letter from scratch — resulting in generic, interchangeable output that reads like it was written by an AI.

This tool works differently. **You write the cover letter once, optimised to your voice, experience, and strengths.** The AI only fills in the small parts that need to change per application — the company name, what draws you to the role, why this specific organisation. Everything else stays exactly as you wrote it.

The result is a letter that sounds like you, not like ChatGPT, because it mostly is you.

---

## What it does

1. Scrapes the job posting (title, company, country, responsibilities, qualifications)
2. Auto-detects the job country and selects the right resume/cover letter template
3. Classifies the role by category (Finance, Marketing, etc.) and picks the matching template
4. Fills only the `_` blanks in your cover letter with company- and role-specific language
5. Converts to PDF and opens the output folder

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install msedge
```

> **Windows only:** `docx2pdf` requires Microsoft Word to be installed for PDF conversion.

### 2. Set your API key

```bash
cp .env.example .env
```

Edit `.env` and paste your LLM API key.

### 3. Configure paths

```bash
cp config.example.py config.py
```

Edit `config.py` and set all paths:

- `OUTPUT_BASE` — folder where generated applications are saved
- `TEMPLATE_BASE` — folder containing your resume/cover letter template subfolders
- `SUPPLEMENTARY_FILES` — any extra PDFs to upload alongside your resume (transcripts, references, etc.)
- `BUNDLE_APPENDIX` — PDFs to append after the cover letter into a combined bundle PDF (leave empty `[]` if not needed)
- `PROFILES` — if applying to multiple countries, define one profile per country with its own `OUTPUT_BASE` and `TEMPLATE_BASE`

### 4. Add your candidate profile

```bash
cp applicant.example.json applicant.json
```

Edit `applicant.json` with your personal info, work history, education, and skills.

### 5. Set up your keyword map

```bash
cp keywords.example.json keywords.json
```

Edit `keywords.json` so each key matches a subfolder name inside your `TEMPLATE_BASE`. Keywords are matched against the job title (3x weight) and description (1x weight) to pick the right template.

### 6. Set up your location map (multi-country only)

```bash
cp locations.example.json locations.json
```

Edit `locations.json` so each key matches a profile name in `PROFILES`. Values are city/country strings matched against the scraped job location.

---

## Template folder structure

Your `TEMPLATE_BASE` folder should contain one subfolder per job category:

```
Templates/
├── Finance/
│   ├── Resume.docx
│   ├── Resume.pdf
│   ├── Resume.txt          ← plain text version of your resume
│   └── Cover Letter.docx
├── Marketing/
│   └── ...
└── ...
```

Subfolder names must match the keys in `keywords.json`.

### Writing your cover letter template

Write your cover letter in full — your background, experience, skills, and voice. Use `_` as a placeholder only where company- or role-specific content belongs. Only those sentences are sent to the AI. Everything else is untouched.

**Template:**
> I am writing to express my keen interest in the Financial Analyst role at `_`.

> What draws me to `_` is its reputation for disciplined execution and a culture where data-driven analysis shapes business decisions.

**Generated:**
> I am writing to express my keen interest in the Financial Analyst role at RHB.

> What draws me to RHB is its position as one of Southeast Asia's leading financial services groups, where rigorous analysis directly informs strategic decisions.

The AI fills the blank and nothing else. Your sentences stay your sentences.

---

## Usage

Run from a terminal (Command Prompt, PowerShell, or bash — not by double-clicking the file):

```bash
python apply.py
```

Paste the job URL when prompted. The tool auto-detects the country, confirms the company name, and generates your application.

> The browser runs headless (no window appears) during scraping.

---

## Single vs multi-country setup

**Single country** — set `OUTPUT_BASE` and `TEMPLATE_BASE` directly in `config.py`. No country prompt appears.

**Multiple countries** — define `PROFILES` in `config.py` and populate `locations.json`. Country is auto-detected from the job posting; the prompt only appears if detection fails.

```python
# config.py
PROFILES = {
    "United States": {
        "OUTPUT_BASE":   r"C:\...\Applications\US",
        "TEMPLATE_BASE": r"C:\...\Templates\US",
    },
    "United Kingdom": {
        "OUTPUT_BASE":   r"C:\...\Applications\UK",
        "TEMPLATE_BASE": r"C:\...\Templates\UK",
    },
}
```

```json
// locations.json
{
  "United States": ["united states", "new york", "san francisco", "chicago"],
  "United Kingdom": ["united kingdom", "london", "manchester", "edinburgh"]
}
```

---

## Personalisation summary

| File | What to configure |
|------|------------------|
| `config.py` | All folder paths, country profiles, bundle files |
| `applicant.json` | Personal info, work history, education, skills |
| `keywords.json` | Job categories and their matching keywords |
| `locations.json` | Country/city strings mapped to each profile |
| `Cover Letter.docx` | Your template — write it fully, use `_` only for company/role-specific sentences |

---

## Requirements

- Python 3.9+
- Windows (for `docx2pdf` via Microsoft Word)
- Microsoft Edge (used by Playwright for scraping)
- LLM API key (default: Anthropic Claude — [get one here](https://console.anthropic.com))
