"""Skill 5 — CompanyResearcher: gather public info about the company for context."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from ..context import ApplicationContext
from ..skill import Skill


def _clean(text: str, max_chars: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _scrape_url(url: str, timeout: int = 10) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/0.1)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


class CompanyResearcherSkill(Skill):
    name = "company_researcher"
    description = "Scrape company About page and LinkedIn summary for writing context."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        company = ctx.company_name
        if not company:
            return self.skip(ctx, "no company_name")

        extra_urls: list[str] = self.cfg("extra_urls", [])
        chunks: list[str] = []

        # Job description is already good context
        if ctx.job_description:
            chunks.append(f"=== Job Description ===\n{_clean(ctx.job_description)}")

        # Try to scrape any extra URLs provided in config (e.g. about page)
        for url in extra_urls:
            try:
                text = _scrape_url(url)
                chunks.append(f"=== {url} ===\n{_clean(text)}")
            except Exception:  # noqa: BLE001
                pass

        ctx.company_research = "\n\n".join(chunks)
        return ctx
