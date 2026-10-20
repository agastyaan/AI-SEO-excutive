
# Agastyaan AI SEO Executive

A local Streamlit application for basic website SEO audits.

## Features
- Page title and meta description checks
- H1 heading and image alt checks
- Internal and external link counts
- Content-based keyword ideas
- Sitemap XML validation
- SEO fix preview and JSON export
- Backlink opportunity tracking
- SQLite audit history

## Installation

Install Python 3.10 or newer.

Open Command Prompt inside this project folder:

```bash
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python -m streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Important
This version does not directly edit or deploy a live website,
verify Google search volumes, create backlinks, or run scheduled
audits automatically. Audit findings require human review.
