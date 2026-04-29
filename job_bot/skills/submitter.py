"""Skill 8 — Submitter: export the filled answers (human submit for now)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ..context import ApplicationContext
from ..skill import Skill

console = Console()


class SubmitterSkill(Skill):
    name = "submitter"
    description = "Export completed answers for human submission."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        if not ctx.ready_to_submit:
            return self.skip(ctx, "not marked ready_to_submit by human_review")

        output_dir = Path(self.cfg("output_dir", "submissions"))
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = (ctx.company_name or "unknown").replace(" ", "_").lower()
        safe_title = (ctx.job_title or "role").replace(" ", "_").lower()
        filename = output_dir / f"{timestamp}_{safe_company}_{safe_title}.json"

        payload = {
            "generated_at": timestamp,
            "job_url":       ctx.job_url,
            "job_title":     ctx.job_title,
            "company_name":  ctx.company_name,
            "platform":      ctx.platform,
            "answers":       ctx.answers,
        }

        with filename.open("w") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        console.print(
            Panel(
                f"[bold green]Submission package saved:[/bold green]\n{filename}\n\n"
                f"[yellow]Review the file and submit manually in the browser.[/yellow]",
                border_style="green",
            )
        )

        ctx.metadata["submission_file"] = str(filename)
        return ctx
