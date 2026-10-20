
import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from seo_core import (
    clean_url,
    audit_page,
    keyword_ideas,
    validate_sitemap,
    build_fix_preview,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
EXPORT_DIR = os.path.join(APP_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "seo_executive.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

st.set_page_config(
    page_title="Agastyaan AI SEO Executive",
    page_icon="🔎",
    layout="wide",
)

def connect_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audited_at TEXT,
                url TEXT,
                title TEXT,
                issues_count INTEGER,
                word_count INTEGER,
                status TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backlinks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_url TEXT NOT NULL,
                target_url TEXT,
                method TEXT,
                status TEXT,
                notes TEXT,
                created_at TEXT
            )
        """)

def save_audit(result):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO audits
            (audited_at, url, title, issues_count, word_count, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            result["url"],
            result["title"],
            len(result["issues"]),
            result["word_count"],
            str(result["status"]),
        ))

def load_audits():
    with connect_db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM audits ORDER BY id DESC LIMIT 100", conn
        )

def load_backlinks():
    with connect_db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM backlinks ORDER BY id DESC", conn
        )

def save_backlink(prospect, target, method, status, notes):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO backlinks
            (prospect_url, target_url, method, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prospect, target, method, status, notes,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ))

init_db()

st.title("🔎 Agastyaan AI SEO Executive")
st.caption("Website audits • Keyword ideas • Sitemap validation • SEO fixes • Backlink tracking")

with st.sidebar:
    st.header("Website Settings")
    website_url = st.text_input(
        "Website URL",
        value="https://agastyaan.com",
        help="Enter a public website URL you are authorized to audit."
    )
    sitemap_url = st.text_input(
        "Sitemap URL",
        value="https://agastyaan.com/sitemap.xml"
    )
    st.info("SEO changes are preview-only. No live website changes are made.")
    run_audit = st.button("Run SEO Audit", type="primary", use_container_width=True)

if "audit_result" not in st.session_state:
    st.session_state.audit_result = None

if run_audit:
    try:
        with st.spinner("Website ka audit ho raha hai..."):
            result = audit_page(website_url)
            st.session_state.audit_result = result
            save_audit(result)
        st.success("Audit complete. Results neeche hain.")
    except Exception as exc:
        st.error(f"Audit failed: {exc}")
        st.caption(
            "Check the URL, internet connection, website availability and "
            "whether the website allows automated requests."
        )

tabs = st.tabs([
    "SEO Overview",
    "Keyword Ideas",
    "Fix Preview",
    "Sitemap",
    "Backlink Tracker",
    "Audit History",
])

result = st.session_state.audit_result

with tabs[0]:
    st.subheader("Website SEO Overview")

    if result:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HTTP Status", result["status"])
        c2.metric("SEO Issues", len(result["issues"]))
        c3.metric("Word Count", result["word_count"])
        c4.metric("Missing Image Alt", result["missing_alt"])

        st.write("**Audited URL:**", result["url"])
        st.write("**Page title:**", result["title"] or "Missing")
        st.write("**Meta description:**", result["description"] or "Missing")
        st.write("**H1 headings:**")
        st.write(result["h1"] or ["No H1 found"])
        st.write("**Canonical URL:**", result["canonical"] or "Missing")
        st.write("**Internal links:**", result["internal_links"])
        st.write("**External links:**", result["external_links"])

        st.subheader("Issues to review")
        if result["issues"]:
            for issue in result["issues"]:
                st.warning(issue)
        else:
            st.success("No issues detected by these basic checks.")

        st.download_button(
            "Download audit JSON",
            data=pd.Series({
                "url": result["url"],
                "title": result["title"],
                "description": result["description"],
                "issues": result["issues"],
                "word_count": result["word_count"],
                "canonical": result["canonical"],
            }).to_json(indent=2),
            file_name="seo_audit.json",
            mime="application/json",
        )
    else:
        st.info("Start by clicking Run SEO Audit in the sidebar.")

with tabs[1]:
    st.subheader("Keyword Research Ideas")
    st.caption(
        "Ideas are generated from page content and headings. "
        "They are not verified search-volume, ranking or difficulty data."
    )

    if result:
        ideas = keyword_ideas(result)
        if ideas:
            keyword_df = pd.DataFrame({
                "Keyword / Topic Idea": ideas,
                "Research Status": ["Needs validation"] * len(ideas),
            })
            st.dataframe(keyword_df, use_container_width=True)
            st.download_button(
                "Download keyword ideas CSV",
                data=keyword_df.to_csv(index=False).encode("utf-8"),
                file_name="keyword_ideas.csv",
                mime="text/csv",
            )
        else:
            st.info("No keyword ideas found. Try a page with more content.")
    else:
        st.info("Run an audit first to generate keyword ideas.")

with tabs[2]:
    st.subheader("SEO Fix Preview")
    st.caption(
        "Review proposed changes before applying them in your React project."
    )

    if result:
        proposed_title = st.text_input(
            "Proposed page title",
            value=result["title"],
            max_chars=200,
        )
        proposed_description = st.text_area(
            "Proposed meta description",
            value=result["description"],
            max_chars=320,
        )

        if st.button("Generate Fix Preview"):
            fixes = build_fix_preview(
                result, proposed_title, proposed_description
            )
            st.session_state.fix_preview = fixes

        fixes = st.session_state.get("fix_preview", [])
        if fixes:
            st.dataframe(pd.DataFrame(fixes), use_container_width=True)
            st.download_button(
                "Download fixes as JSON",
                data=pd.Series(fixes).to_json(indent=2),
                file_name="seo_fix_preview.json",
                mime="application/json",
            )
            st.info(
                "Preview ready. This MVP does not modify React source files "
                "or publish changes to the live site."
            )
        else:
            st.write("Enter proposed metadata and click Generate Fix Preview.")
    else:
        st.info("Run an audit before creating a fix preview.")

with tabs[3]:
    st.subheader("Sitemap Validator")
    st.write("Default sitemap:", sitemap_url)

    if st.button("Validate Sitemap"):
        try:
            with st.spinner("Checking sitemap XML..."):
                sitemap = validate_sitemap(sitemap_url)
            if sitemap["valid"]:
                st.success(sitemap["message"])
            else:
                st.error(sitemap["message"])

            if sitemap["urls"]:
                sitemap_df = pd.DataFrame({"URL": sitemap["urls"]})
                st.dataframe(sitemap_df, use_container_width=True)
                st.download_button(
                    "Download sitemap URLs",
                    data=sitemap_df.to_csv(index=False).encode("utf-8"),
                    file_name="sitemap_urls.csv",
                    mime="text/csv",
                )
        except Exception as exc:
            st.error(f"Sitemap validation failed: {exc}")

with tabs[4]:
    st.subheader("Backlink Opportunity Tracker")
    st.caption(
        "Record legitimate outreach prospects such as relevant directories, "
        "industry blogs, partners and guest-post opportunities. "
        "This tool does not create backlinks automatically."
    )

    with st.form("backlink_form", clear_on_submit=True):
        prospect_url = st.text_input("Prospect website URL")
        target_url = st.text_input(
            "Agastyaan page to promote",
            value=clean_url(website_url),
        )
        method = st.selectbox(
            "Opportunity type",
            [
                "Relevant business directory",
                "Guest article",
                "Partner / association",
                "Resource page",
                "Unlinked brand mention",
                "Other",
            ],
        )
        status = st.selectbox(
            "Outreach status",
            ["To Research", "Ready to Contact", "Contacted", "Published", "Rejected"],
        )
        notes = st.text_area("Relevance, contact notes or next step")
        submitted = st.form_submit_button("Save Opportunity")

        if submitted:
            if not prospect_url.strip():
                st.error("Prospect website URL is required.")
            else:
                save_backlink(
                    prospect_url.strip(),
                    target_url.strip(),
                    method,
                    status,
                    notes.strip(),
                )
                st.success("Opportunity saved.")

    backlink_df = load_backlinks()
    if not backlink_df.empty:
        st.dataframe(backlink_df, use_container_width=True)
        st.download_button(
            "Export backlink tracker CSV",
            data=backlink_df.to_csv(index=False).encode("utf-8"),
            file_name="backlink_tracker.csv",
            mime="text/csv",
        )
    else:
        st.info("No backlink opportunities saved yet.")

with tabs[5]:
    st.subheader("Audit History")
    history_df = load_audits()
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
        st.download_button(
            "Export audit history CSV",
            data=history_df.to_csv(index=False).encode("utf-8"),
            file_name="seo_audit_history.csv",
            mime="text/csv",
        )
    else:
        st.info("Your completed audits will appear here.")

st.divider()
st.caption(
    "Agastyaan Technology • Local SEO utility • "
    "Audit results are preliminary and should be reviewed before implementation."
)
