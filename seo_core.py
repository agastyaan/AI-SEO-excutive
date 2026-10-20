
import re
from collections import Counter
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "AgastyaanSEOExecutive/1.0 (website audit)"
}
TIMEOUT = 20


def clean_url(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def fetch_page(url):
    url = clean_url(url)
    response = requests.get(
        url, headers=HEADERS, timeout=TIMEOUT,
        allow_redirects=True
    )
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        raise ValueError("URL HTML webpage nahi hai.")
    return response.url, response.text, response.status_code


def audit_page(url):
    final_url, html, status = fetch_page(url)
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    desc_tag = soup.find("meta", attrs={"name": re.compile(
        "^description$", re.I
    )})
    description = desc_tag.get("content", "").strip() if desc_tag else ""

    canonical_tag = soup.find("link", rel=lambda x: x and "canonical" in x)
    canonical = canonical_tag.get("href", "") if canonical_tag else ""

    robots_tag = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    robots = robots_tag.get("content", "") if robots_tag else "Not specified"

    h1_tags = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2_tags = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]

    images = soup.find_all("img")
    missing_alt = sum(
        1 for image in images
        if not image.has_attr("alt") or not image.get("alt", "").strip()
    )

    links = soup.find_all("a", href=True)
    domain = urlparse(final_url).netloc.lower()
    internal_links = []
    external_links = []

    for link in links:
        href = urljoin(final_url, link["href"])
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower() == domain:
            internal_links.append(href)
        else:
            external_links.append(href)

    text = soup.get_text(" ", strip=True)
    word_count = len(re.findall(r"\b[\w'-]+\b", text))

    issues = []
    if not title:
        issues.append("Missing page title")
    elif len(title) < 30 or len(title) > 60:
        issues.append(f"Title length is {len(title)} characters; review it")
    if not description:
        issues.append("Missing meta description")
    elif len(description) < 120 or len(description) > 160:
        issues.append(
            f"Meta description is {len(description)} characters; review it"
        )
    if not h1_tags:
        issues.append("Missing H1 heading")
    elif len(h1_tags) > 1:
        issues.append(f"Multiple H1 headings found: {len(h1_tags)}")
    if missing_alt:
        issues.append(f"{missing_alt} images have missing/empty alt text")
    if not canonical:
        issues.append("Canonical URL not found")
    if word_count < 300:
        issues.append(f"Page has only {word_count} words; review content depth")

    return {
        "url": final_url,
        "status": status,
        "title": title,
        "title_length": len(title),
        "description": description,
        "description_length": len(description),
        "canonical": canonical,
        "robots": robots,
        "h1": h1_tags,
        "h2": h2_tags,
        "images": len(images),
        "missing_alt": missing_alt,
        "internal_links": len(internal_links),
        "external_links": len(external_links),
        "word_count": word_count,
        "issues": issues,
        "html": html,
        "text": text,
    }


def keyword_ideas(audit, limit=30):
    """Generate content-based ideas, not search-volume estimates."""
    source = " ".join([
        audit.get("title", ""),
        " ".join(audit.get("h1", [])),
        " ".join(audit.get("h2", [])),
        audit.get("description", ""),
        audit.get("text", "")[:12000],
    ]).lower()

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", source)
    stop_words = {
        "the", "and", "for", "with", "this", "that", "from", "your",
        "you", "are", "our", "was", "will", "have", "has", "not",
        "but", "can", "all", "about", "more", "into", "their", "they",
        "website", "home", "page", "click", "read", "learn", "best"
    }
    counts = Counter(w for w in words if w not in stop_words)
    single_words = [w for w, _ in counts.most_common(12)]

    phrases = []
    for heading in audit.get("h1", []) + audit.get("h2", []):
        if heading.strip():
            phrases.append(heading.strip())

    for word in single_words[:8]:
        phrases.extend([
            f"{word} services",
            f"{word} company",
            f"{word} solutions",
        ])

    result = []
    seen = set()
    for phrase in phrases:
        phrase = re.sub(r"\s+", " ", phrase).strip()
        key = phrase.lower()
        if key and key not in seen:
            result.append(phrase)
            seen.add(key)
        if len(result) >= limit:
            break

    return result


def validate_sitemap(url):
    url = clean_url(url)
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "xml")
    root = soup.find(["urlset", "sitemapindex"])

    if root is None:
        return {
            "valid": False,
            "message": "XML sitemap root tag not found.",
            "urls": [],
        }

    locs = [tag.get_text(strip=True) for tag in root.find_all("loc")]
    return {
        "valid": True,
        "message": f"Sitemap XML parsed. Found {len(locs)} location entries.",
        "urls": locs,
    }


def build_fix_preview(audit, proposed_title="", proposed_description=""):
    """Prepare suggested edits. Does not change the live website."""
    fixes = []

    if proposed_title.strip():
        fixes.append({
            "element": "title",
            "current": audit.get("title", ""),
            "proposed": proposed_title.strip(),
        })

    if proposed_description.strip():
        fixes.append({
            "element": "meta description",
            "current": audit.get("description", ""),
            "proposed": proposed_description.strip(),
        })

    if not audit.get("canonical"):
        fixes.append({
            "element": "canonical",
            "current": "(missing)",
            "proposed": audit.get("url", ""),
        })

    return fixes
