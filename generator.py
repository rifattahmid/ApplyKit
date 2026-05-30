import os
import re
import json
import shutil
import time
import anthropic
from datetime import datetime
from docx import Document
from docx2pdf import convert
from pypdf import PdfWriter
from dotenv import load_dotenv

import config
try:
    from config import BUNDLE_APPENDIX
except ImportError:
    BUNDLE_APPENDIX = []

load_dotenv()

_KEYWORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.json")

def _load_keywords():
    if not os.path.exists(_KEYWORDS_PATH):
        print("  WARNING: keywords.json not found -- all categories will score 0. Copy keywords.example.json to keywords.json to fix this.")
        return {}, set()
    with open(_KEYWORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    broad = {c.lower() for c in data.get("_broad_categories", [])}
    keywords = {k.lower(): v for k, v in data.items() if not k.startswith("_")}
    return keywords, broad

_MONTHS = (
    r"January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
)
_ORD = r"(?:st|nd|rd|th)?"   # optional ordinal suffix
DATE_PATTERN = re.compile(
    rf"\d{{1,2}}{_ORD}\s+(?:{_MONTHS})\s+20\d{{2}}"   # DD[th] Month YYYY  (e.g. 13th February 2026)
    rf"|(?:{_MONTHS})\s+\d{{1,2}}{_ORD},?\s+20\d{{2}}" # Month DD[th], YYYY (e.g. April 15th, 2026)
    rf"|\d{{1,2}}/\d{{1,2}}/20\d{{2}}"                 # DD/MM/YYYY         (e.g. 15/04/2026)
    rf"|20\d{{2}}-\d{{2}}-\d{{2}}",                    # YYYY-MM-DD         (e.g. 2026-04-15)
    re.IGNORECASE,
)


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

# Australian states/territories and common location suffixes to strip from job titles
_LOCATION_TOKENS = re.compile(
    r"[\s,|\-]+\b("
    r"NSW|VIC|QLD|SA|WA|TAS|NT|ACT"          # AU states/territories
    r"|Australia|Remote|Hybrid|On[- ]?site"   # other common tags
    r")\b[\s,|\-]*$",
    re.IGNORECASE,
)


def _iter_all_paragraphs(doc):
    """Yield every paragraph in the document, including those inside table cells."""
    for para in doc.paragraphs:
        yield para
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    yield para


def clean_job_title(title: str) -> str:
    """Strip trailing location/unnecessary tokens from a job title.

    Example: 'Investment Analyst - Investments & Treasury NSW' -> 'Investment Analyst - Investments & Treasury'
    """
    return _LOCATION_TOKENS.sub("", title).strip()


def _set_para_text(para, text):
    """Replace paragraph text preserving the first run's formatting (used for dates)."""
    if para.runs:
        para.runs[0].text = text
        for run in para.runs[1:]:
            run.text = ""
    else:
        para.add_run(text)


def classify_job(title, description):
    """Match job to a template subfolder. Reads available folders dynamically.

    Scoring:
    - Title keyword match  -> +3  (title signals intent; weighted 3x over body text)
    - Description keyword  -> +1
    Tie-break order: investment > m&a > finance > accounting > esg > economics > fund accounting.
    """
    title_text = title.lower()
    desc_text  = description.lower()
    available  = [
        f for f in os.listdir(config.TEMPLATE_BASE)
        if os.path.isdir(os.path.join(config.TEMPLATE_BASE, f))
    ]

    keywords, broad_categories = _load_keywords()

    TITLE_MULTIPLIER = 3

    scores       = {folder: 0 for folder in available}
    title_scores = {folder: 0 for folder in available}

    for folder in available:
        for kw in keywords.get(folder.lower(), []):
            if kw in title_text:
                scores[folder]       += TITLE_MULTIPLIER
                title_scores[folder] += TITLE_MULTIPLIER
            if kw in desc_text:
                scores[folder] += 1

    best = max(scores, key=lambda f: scores[f]) if scores else available[0]

    # If the winner has no title evidence, defer to the best title-matched category.
    # Prevents description noise from overriding a clear title signal
    # (e.g. "Project Accountant" desc mentioning equity/infrastructure shouldn't pick investment).
    title_override = False
    if title_scores.get(best, 0) == 0:
        title_candidates = [f for f in available if title_scores.get(f, 0) > 0]
        if title_candidates:
            best = max(title_candidates, key=lambda f: (title_scores[f], scores[f]))
            title_override = True

    # Tie-break: if two or more categories share the top score, prefer whichever has
    # title evidence first; among those still tied, prefer investment > finance > accounting.
    # Skip if title override already resolved the winner -- tie-break must not undo it.
    if not title_override:
        top_score = scores[best]
        if sum(1 for v in scores.values() if v == top_score) > 1:
            # Prefer tied candidates with title evidence over those without
            title_tied = [f for f in available if scores.get(f, 0) == top_score and title_scores.get(f, 0) > 0]
            if title_tied:
                best = max(title_tied, key=lambda f: (title_scores[f], scores[f]))
            else:
                available_lower = {f.lower(): f for f in available}
                for preferred in ("investment", "m&a", "finance", "accounting", "esg", "economics", "fund accounting"):
                    if preferred in available_lower and scores.get(available_lower[preferred], -1) == top_score:
                        best = available_lower[preferred]
                        break

    # Specialist override: if a broad category wins, prefer a specialist that is
    # competitive (scores >= 60% of the broad winner). Override fires when:
    #   (a) the specialist has title evidence — handles cases where the broad category's
    #       title match is a false positive caused by the specialist keyword containing
    #       the broad keyword (e.g. "Fund Accounting" also matches "Accounting"), OR
    #   (b) the broad category has no title evidence at all.
    # Additionally, if the specialist's category name appears literally in the title
    # (e.g. "Fund Accounting Senior Analyst"), that is treated as a hard override signal
    # even when the score threshold isn't met — other keywords in the title (e.g.
    # "Valuations") can inflate unrelated categories enough to suppress the threshold.
    if best.lower() in broad_categories:
        specialists = [
            f for f in available
            if f.lower() not in broad_categories and scores.get(f, 0) > 0
        ]
        if specialists:
            top_specialist = max(specialists, key=lambda f: (
                title_scores.get(f, 0),
                1 if f.lower() in title_text else 0,
                scores[f],
            ))
            specialist_has_title    = title_scores.get(top_specialist, 0) > 0
            specialist_name_in_title = top_specialist.lower() in title_text
            broad_has_title          = title_scores.get(best, 0) > 0
            if scores[top_specialist] >= scores[best] * 0.6 and (specialist_has_title or not broad_has_title):
                best = top_specialist
            elif specialist_has_title and specialist_name_in_title:
                best = top_specialist

    print(f"  Job classified as: {best}\n")
    print("  Scores:")
    for folder in sorted(scores):
        marker = " <--" if folder == best else ""
        print(f"    {folder:<20} {scores[folder]:>2}  (title: {title_scores.get(folder, 0)}){marker}")
    print()
    return best


def get_paths(category):
    base = os.path.join(config.TEMPLATE_BASE, category)
    if not os.path.isdir(base):
        raise FileNotFoundError(f"Template folder not found: {base}")

    resume_pdf = cover_docx = None
    for f in os.listdir(base):
        if f.startswith("~$"):          # skip Word temporary lock files
            continue
        f_lower = f.lower()
        if f_lower.endswith(".pdf") and "resume" in f_lower:
            resume_pdf = os.path.join(base, f)
        elif f_lower.endswith(".docx") and "cover" in f_lower:
            cover_docx = os.path.join(base, f)

    missing = [
        name for name, val in [
            ("Resume.pdf", resume_pdf),
            ("Cover Letter.docx", cover_docx),
        ]
        if val is None
    ]
    if missing:
        raise FileNotFoundError(f"Missing in {base}: {', '.join(missing)}")
    return resume_pdf, cover_docx



def _rebold_title(para, title):
    """After _set_para_text, rebuild paragraph runs cleanly so the title is bold.

    Strips all existing runs from the XML (instead of leaving empty leftovers) and
    rebuilds with at most 3 runs: before (regular), title (bold), after (regular).
    The leftover-empty-run approach was fragile across Word/python-docx versions.
    """
    if not para.runs:
        return
    text = para.runs[0].text
    if title not in text:
        return
    idx = text.index(title)
    before = text[:idx]
    after = text[idx + len(title):]

    # Capture font properties from first run before nuking everything
    run0 = para.runs[0]
    font_name = run0.font.name
    font_size = run0.font.size

    # Remove all existing runs from the paragraph XML
    for r in list(para.runs):
        r._element.getparent().remove(r._element)

    def _add(text, bold):
        if not text:
            return
        r = para.add_run(text)
        r.bold = bold
        if font_name:
            r.font.name = font_name
        if font_size:
            r.font.size = font_size

    _add(before, False)
    _add(title, True)
    _add(after, False)


def fill_cover_letter(path, company, title, intro, responsibilities, qualifications):
    doc = Document(path)
    now = datetime.now()
    today = f"{now.day}{_ordinal(now.day)} {now.strftime('%B %Y')}"

    # Replace dates
    date_replaced = False
    for para in _iter_all_paragraphs(doc):
        if DATE_PATTERN.search(para.text):
            _set_para_text(para, DATE_PATTERN.sub(today, para.text))
            print(f"  Date:          {today}")
            date_replaced = True
    if not date_replaced:
        print(f"  WARNING: no date found in template (today={today})")

    # Collect paragraphs with _ blanks
    blank_paras = [
        (i, para, any(r.bold and "_" in r.text for r in para.runs))
        for i, para in enumerate(_iter_all_paragraphs(doc)) if "_" in para.text
    ]

    if not blank_paras:
        doc.save(path)
        print("  Cover letter saved (no blanks found)")
        return

    # Extract only the sentence(s) containing _ from each paragraph
    blank_items = []
    for _, para, had_bold_blank in blank_paras:
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', para.text)
        for si, s in enumerate(sentences):
            if '_' in s:
                blank_items.append((para, sentences, si, had_bold_blank))

    print(f"\n  Blanks ({len(blank_items)}):")
    for j, (_, sentences, si, _) in enumerate(blank_items):
        print(f"    {j+1}. {sentences[si]}")

    numbered_lines = "\n".join(
        f"{j+1}. {sentences[si]}"
        for j, (_, sentences, si, _) in enumerate(blank_items)
    )

    client = anthropic.Anthropic()
    for attempt in range(4):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{"role": "user", "content": f"""Fill in the blank(s) (_) in each numbered sentence below.

Role: {title}
Company (USE EXACTLY THIS): {company}

Job description: {intro}
Responsibilities: {responsibilities}
Qualifications: {qualifications}

Sentences to fill:
{numbered_lines}

Rules:
- Return each sentence IN FULL with ONLY the _ replaced -- do NOT change, remove, or rephrase any other word
- Use EXACTLY "{company}" for the company name -- never modify it
- Use EXACTLY "{title}" for the role -- never modify it
- Fill _ with company/role-specific content: what the company does, why the applicant is drawn to this role or company
- NEVER use em dashes (--) or en dashes (-)
- Return ONLY the numbered sentences, nothing else"""}]
            )
            break
        except anthropic.APIStatusError as e:
            if e.status_code in (500, 502, 503, 529) and attempt < 3:
                wait = 10 * (attempt + 1)
                print(f"  API error {e.status_code} — retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    response = message.content[0].text.strip()

    rewrites = {}
    for line in response.splitlines():
        m = re.match(r'^(\d+)\.\s*(.+)$', line.strip())
        if m:
            rewrites[int(m.group(1)) - 1] = m.group(2).strip()

    print(f"\n  Filled:")
    for j, (para, sentences, si, had_bold_blank) in enumerate(blank_items):
        new_sentence = rewrites.get(j, "")
        if not new_sentence:
            print(f"    {j+1}. WARNING: no rewrite returned")
            continue
        print(f"    {j+1}. {new_sentence}")
        sentences[si] = new_sentence
        new_text = ' '.join(sentences)
        _set_para_text(para, new_text)
        if title in new_text and para.runs:
            _rebold_title(para, title)

    print()
    doc.save(path)
    print("  Cover letter saved")


def _merge_cover_letter_bundle(cover_pdf: str, output_folder: str):
    """Merge cover letter + BUNDLE_APPENDIX into one PDF in output_folder."""
    bundle_path = os.path.join(output_folder, "Cover Letter, Recommendations, Transcripts.pdf")
    writer = PdfWriter()
    for path in [cover_pdf] + BUNDLE_APPENDIX:
        if not os.path.exists(path):
            print(f"  WARNING: bundle file not found, skipping: {path}")
            continue
        writer.append(path)
    with open(bundle_path, "wb") as f:
        writer.write(f)
    print(f"  Bundle PDF: {bundle_path}")


def generate_application(data, category=None):
    title = clean_job_title(data["title"])
    company = data["company"]

    if category is None:
        category = classify_job(title, data["description"])
    resume_pdf, cover_docx = get_paths(category)

    folder_name = re.sub(r'[<>:"/\\|?*]', '-', f"{company} - {title}")
    output_folder = os.path.join(config.OUTPUT_BASE, folder_name)
    os.makedirs(output_folder, exist_ok=True)

    shutil.copy(resume_pdf, os.path.join(output_folder, os.path.basename(resume_pdf)))
    cover_dest = os.path.join(output_folder, os.path.basename(cover_docx))
    shutil.copy(cover_docx, cover_dest)

    # Write position description PDF (captured during scraping while session was live)
    position_pdf = os.path.join(output_folder, "Position Description.pdf")
    if data.get("pdf_bytes"):
        with open(position_pdf, "wb") as f:
            f.write(data["pdf_bytes"])
        print(f"  Position description PDF: {position_pdf}")

    fill_cover_letter(
        cover_dest, company, title,
        data.get("intro", ""),
        data.get("responsibilities", ""),
        data.get("qualifications", ""),
    )

    pdf_dest = cover_dest.replace(".docx", ".pdf")
    try:
        convert(cover_dest, pdf_dest)
        print(f"  Cover letter PDF: {pdf_dest}")
        if BUNDLE_APPENDIX:
            _merge_cover_letter_bundle(pdf_dest, output_folder)
    except Exception as e:
        print(f"  WARNING: PDF conversion failed ({e})")
        print("  Make sure Microsoft Word is installed and the .docx is not open.")

    print(f"\nDone! Saved to: {output_folder}")
    os.startfile(output_folder)
    return output_folder
