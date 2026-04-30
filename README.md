# Auto Resume & Cover Letter Generator

Automatically generates a tailored cover letter and selects the right resume template for any job application — given just a URL.

**What it does:**
1. Scrapes the job posting (title, company, country, responsibilities, qualifications)
2. Auto-detects the job country and pre-selects the matching profile
3. Presents an arrow-key menu to confirm or change the country
4. Classifies the role against your template categories using a keyword scorer
5. Copies the matching resume template
6. Fills in the `_` blanks in your cover letter template using Claude AI, with company- and role-specific language
7. Converts everything to PDF and opens the output folder

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

Edit `.env` and paste your Anthropic API key.

### 3. Configure paths

```bash
cp config.example.py config.py
```

Edit `config.py` with your template and output folder paths. For multiple countries, define `PROFILES` (see below).

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

### Cover letter blanks

Use `_` as a placeholder in your `Cover Letter.docx` for content that should be tailored per company and role. Only the sentence(s) containing `_` are sent to Claude — everything else is left exactly as written.

**Template:**
> I am writing to express my keen interest in the Financial Analyst role at `_`.

> What draws me to `_` is its reputation for disciplined execution and a culture where data-driven analysis shapes business decisions.

**Generated:**
> I am writing to express my keen interest in the Financial Analyst role at RHB.

> What draws me to RHB is its position as one of Southeast Asia's leading financial services groups, where rigorous analysis directly informs strategic decisions.

---

## Usage

```bash
python apply.py
```

Paste the job URL when prompted. The tool will:
- Auto-detect the job country and pre-select it in the menu
- Show an arrow-key country selector to confirm or change (if `PROFILES` is configured)
- Ask you to confirm or correct the detected company name
- Generate and open your output folder

---

## Single vs multi-country setup

**Single country** — set `OUTPUT_BASE` and `TEMPLATE_BASE` directly in `config.py`. No profile menu appears.

**Multiple countries** — define `PROFILES` in `config.py` and populate `locations.json`. The menu appears on every run with the detected country pre-selected.

```python
# config.py
DEFAULT_PROFILE = "United States"

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

| File | What to edit |
|------|-------------|
| `config.py` | Template/output paths, multi-country profiles |
| `applicant.json` | Personal info, work history, education, skills |
| `keywords.json` | Job categories and their matching keywords |
| `locations.json` | Country/city strings mapped to each profile |
| `Cover Letter.docx` | Your template — use `_` where AI should fill in company/role details |

---

## Requirements

- Python 3.9+
- Windows (for `docx2pdf` via Microsoft Word)
- Microsoft Edge (used by Playwright for scraping)
- Anthropic API key ([get one here](https://console.anthropic.com))
