from __future__ import annotations

import importlib
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .context import ApplicationContext
from .skill import Skill

console = Console()

# Registry: skill name -> (module path, class name)
SKILL_REGISTRY: dict[str, tuple[str, str]] = {
    "profile_loader":       ("job_bot.skills.profile_loader",      "ProfileLoaderSkill"),
    "platform_adapter":     ("job_bot.skills.platform_adapter",    "PlatformAdapterSkill"),
    "question_classifier":  ("job_bot.skills.question_classifier", "QuestionClassifierSkill"),
    "auto_filler":          ("job_bot.skills.auto_filler",         "AutoFillerSkill"),
    "company_researcher":   ("job_bot.skills.company_researcher",  "CompanyResearcherSkill"),
    "answer_writer":        ("job_bot.skills.answer_writer",       "AnswerWriterSkill"),
    "human_review":         ("job_bot.skills.human_review",        "HumanReviewSkill"),
    "submitter":            ("job_bot.skills.submitter",           "SubmitterSkill"),
}


def load_skill(name: str, config: dict[str, Any] | None = None) -> Skill:
    if name not in SKILL_REGISTRY:
        raise ValueError(
            f"Unknown skill '{name}'. Available: {list(SKILL_REGISTRY)}"
        )
    module_path, class_name = SKILL_REGISTRY[name]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(config)


class Pipeline:
    """
    Ordered sequence of Skill modules.

    Compose declaratively via Pipeline.from_config(dict) or programmatically
    by passing a list of (skill_name, config) tuples.
    """

    def __init__(self, steps: list[tuple[str, dict[str, Any]]]) -> None:
        self.steps = steps
        self.skills: list[Skill] = [load_skill(name, cfg) for name, cfg in steps]

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Pipeline":
        """Load from a parsed YAML/JSON pipeline definition."""
        steps = []
        for entry in config.get("steps", []):
            if isinstance(entry, str):
                steps.append((entry, {}))
            else:
                name = entry["skill"]
                cfg = {k: v for k, v in entry.items() if k != "skill"}
                steps.append((name, cfg))
        return cls(steps)

    # ── Run ────────────────────────────────────────────────────────────────

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        console.print(
            Panel(
                f"[bold cyan]Job Bot Pipeline[/bold cyan]\n"
                f"[dim]{len(self.skills)} skills | {ctx.job_url or 'no URL yet'}[/dim]",
                border_style="cyan",
            )
        )

        for i, (skill, (name, _)) in enumerate(zip(self.skills, self.steps), 1):
            label = f"[{i}/{len(self.skills)}] {name}"
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{label}[/bold] " + "{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("running...", total=None)
                t0 = time.perf_counter()
                try:
                    ctx = skill.run(ctx)
                except Exception as exc:  # noqa: BLE001
                    ctx.errors.append(f"{name}: {exc}")
                    console.print(f"  [red]x {label} FAILED:[/red] {exc}")
                    if self.cfg_abort_on_error(name):
                        break
                    continue
                elapsed = time.perf_counter() - t0
                progress.update(task, description="done")

            skipped = name in ctx.skipped_skills
            status = "[yellow]skipped[/yellow]" if skipped else "[green]done[/green]"
            console.print(f"  {status} {label} ({elapsed:.1f}s)")

        if ctx.errors:
            console.print(
                f"\n[red]{len(ctx.errors)} error(s):[/red] "
                + "; ".join(ctx.errors)
            )
        else:
            console.print("\n[bold green]Pipeline complete.[/bold green]")

        return ctx

    def cfg_abort_on_error(self, skill_name: str) -> bool:
        for name, cfg in self.steps:
            if name == skill_name:
                return cfg.get("abort_on_error", True)
        return True

    # ── Introspection ──────────────────────────────────────────────────────

    def describe(self) -> str:
        lines = ["Pipeline steps:"]
        for i, (name, cfg) in enumerate(self.steps, 1):
            cfg_str = f"  {cfg}" if cfg else ""
            lines.append(f"  {i}. {name}{cfg_str}")
        return "\n".join(lines)
