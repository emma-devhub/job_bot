"""Skill 1 — ProfileLoader: load the user's base profile and resume material."""
from __future__ import annotations

from pathlib import Path

import yaml

from ..context import ApplicationContext
from ..skill import Skill


class ProfileLoaderSkill(Skill):
    name = "profile_loader"
    description = "Load basic info and resume material from a YAML profile file."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        profile_path = Path(self.cfg("profile_path", "profiles/default.yaml"))
        if not profile_path.exists():
            ctx.errors.append(f"Profile not found: {profile_path}")
            return ctx

        with profile_path.open() as f:
            data: dict = yaml.safe_load(f)

        ctx.profile = data.get("personal", {})
        ctx.resume_text = data.get("resume_text", "")
        ctx.experience_corpus = data.get("experience_corpus", [])

        # Allow pipeline YAML to override job target fields
        if not ctx.job_url:
            ctx.job_url = data.get("job_url", "")
        if not ctx.company_name:
            ctx.company_name = data.get("company_name", "")
        if not ctx.job_title:
            ctx.job_title = data.get("job_title", "")

        return ctx
