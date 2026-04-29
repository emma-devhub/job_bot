"""Skill 2 — PlatformAdapter: detect platform and parse the job application form."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from ..context import ApplicationContext, FormField
from ..skill import Skill

_PLATFORM_PATTERNS: list[tuple[str, str]] = [
    ("greenhouse", r"greenhouse\.io|boards\.greenhouse"),
    ("ashby",      r"ashbyhq\.com|jobs\.ashby"),
    ("workday",    r"myworkdayjobs\.com|wd\d+\.myworkday"),
    ("gem",        r"gem\.com"),
]


def detect_platform(url: str) -> str:
    for name, pattern in _PLATFORM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "unknown"


class PlatformAdapterSkill(Skill):
    name = "platform_adapter"
    description = "Detect the ATS platform from the job URL and parse form fields."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        if not ctx.job_url:
            return self.skip(ctx, "no job_url set")

        ctx.platform = detect_platform(ctx.job_url)

        parser = _get_parser(ctx.platform)
        try:
            html = _fetch(ctx.job_url)
            ctx.form_fields, ctx.job_description, ctx.job_title, ctx.company_name = (
                parser(html, ctx)
            )
        except Exception as exc:  # noqa: BLE001
            ctx.errors.append(f"platform_adapter parse error: {exc}")

        return ctx


# ── Per-platform parsers ───────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/0.1)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _get_parser(platform: str):
    return {
        "greenhouse": _parse_greenhouse,
        "ashby":      _parse_ashby,
        "workday":    _parse_workday,
        "gem":        _parse_generic,
    }.get(platform, _parse_generic)


def _field(soup_el, label_text: str, field_type: str = "text") -> FormField:
    el_id = soup_el.get("id") or soup_el.get("name") or label_text.lower().replace(" ", "_")
    required = bool(soup_el.get("required"))
    options: list[str] = []
    if field_type in ("select", "radio", "checkbox"):
        options = [
            o.get("value", o.text.strip())
            for o in soup_el.find_all(["option", "input"])
            if o.get("value") not in ("", None)
        ]
    return FormField(
        id=str(el_id),
        label=label_text,
        field_type=field_type,
        required=required,
        options=options,
    )


def _parse_greenhouse(html: str, ctx: ApplicationContext):
    soup = BeautifulSoup(html, "html.parser")
    fields: list[FormField] = []

    job_title = (soup.select_one("h1.app-title") or soup.select_one("h1"))
    title_text = job_title.get_text(strip=True) if job_title else ctx.job_title

    company_el = soup.select_one(".company-name") or soup.select_one(".employer")
    company_text = company_el.get_text(strip=True) if company_el else ctx.company_name

    jd_el = soup.select_one("#content") or soup.select_one(".job-description")
    jd_text = jd_el.get_text(" ", strip=True) if jd_el else ""

    for field_group in soup.select(".field"):
        label_el = field_group.select_one("label")
        label = label_el.get_text(strip=True) if label_el else "unlabeled"

        textarea = field_group.select_one("textarea")
        inp = field_group.select_one("input")
        sel = field_group.select_one("select")

        if textarea:
            fields.append(_field(textarea, label, "textarea"))
        elif sel:
            fields.append(_field(sel, label, "select"))
        elif inp:
            inp_type = inp.get("type", "text")
            fields.append(_field(inp, label, inp_type))

    return fields, jd_text, title_text, company_text


def _parse_ashby(html: str, ctx: ApplicationContext):
    soup = BeautifulSoup(html, "html.parser")
    fields: list[FormField] = []

    title_el = soup.select_one("h1")
    title_text = title_el.get_text(strip=True) if title_el else ctx.job_title
    company_text = ctx.company_name

    jd_el = soup.select_one("[class*='jobDescription']") or soup.select_one("main")
    jd_text = jd_el.get_text(" ", strip=True) if jd_el else ""

    for label_el in soup.select("label"):
        label = label_el.get_text(strip=True)
        for_id = label_el.get("for")
        target = soup.find(id=for_id) if for_id else None
        if not target:
            target = label_el.find_next_sibling(["input", "textarea", "select"])
        if not target:
            continue
        tag = target.name
        if tag == "textarea":
            fields.append(_field(target, label, "textarea"))
        elif tag == "select":
            fields.append(_field(target, label, "select"))
        elif tag == "input":
            fields.append(_field(target, label, target.get("type", "text")))

    return fields, jd_text, title_text, company_text


def _parse_workday(html: str, ctx: ApplicationContext):
    # Workday renders via JS; return empty form with a note for the user.
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("title")
    title_text = title_el.get_text(strip=True) if title_el else ctx.job_title
    return (
        [],
        "",
        title_text,
        ctx.company_name,
    )


def _parse_generic(html: str, ctx: ApplicationContext):
    soup = BeautifulSoup(html, "html.parser")
    fields: list[FormField] = []
    title_el = soup.select_one("h1")
    title_text = title_el.get_text(strip=True) if title_el else ctx.job_title
    jd_el = soup.select_one("main") or soup.select_one("article") or soup.body
    jd_text = jd_el.get_text(" ", strip=True) if jd_el else ""

    for label_el in soup.select("label"):
        label = label_el.get_text(strip=True)
        for_id = label_el.get("for")
        target = soup.find(id=for_id) if for_id else label_el.find_next_sibling(
            ["input", "textarea", "select"]
        )
        if not target:
            continue
        tag = target.name
        if tag == "textarea":
            fields.append(_field(target, label, "textarea"))
        elif tag == "select":
            fields.append(_field(target, label, "select"))
        elif tag == "input":
            fields.append(_field(target, label, target.get("type", "text")))

    return fields, jd_text, title_text, ctx.company_name
