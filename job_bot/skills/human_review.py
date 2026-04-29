"""Skill 7 — HumanReview: show all answers and let the user edit before submission."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..context import ApplicationContext
from ..skill import Skill

console = Console()


class HumanReviewSkill(Skill):
    name = "human_review"
    description = "Interactive review and edit of all answers before submission."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        if not ctx.answers:
            return self.skip(ctx, "no answers to review")

        if self.cfg("headless", False):
            # Non-interactive mode (CI / testing)
            ctx.ready_to_submit = True
            return ctx

        console.print(
            Panel(
                f"[bold]Review answers for [cyan]{ctx.job_title}[/cyan] @ [cyan]{ctx.company_name}[/cyan][/bold]",
                border_style="yellow",
            )
        )

        field_index = {f.id: f for f in ctx.form_fields}

        # Build display table
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("#", width=3)
        table.add_column("Field", min_width=20)
        table.add_column("Answer", min_width=40)
        table.add_column("Kind", width=10)

        ids = list(ctx.answers)
        for i, fid in enumerate(ids, 1):
            label = field_index.get(fid, None)
            label_str = label.label if label else fid
            kind = (label.question_kind if label else "?")
            kind_color = "green" if kind == "standard" else "yellow"
            answer = ctx.answers[fid]
            preview = answer[:120] + ("..." if len(answer) > 120 else "")
            table.add_row(
                str(i),
                label_str,
                preview,
                f"[{kind_color}]{kind}[/{kind_color}]",
            )

        console.print(table)
        console.print()

        # Edit loop
        while True:
            choice = Prompt.ask(
                "[bold]Enter field # to edit, [green]ok[/green] to approve, or [red]abort[/red]",
                default="ok",
            )
            if choice.lower() == "ok":
                ctx.ready_to_submit = True
                break
            if choice.lower() == "abort":
                ctx.ready_to_submit = False
                ctx.errors.append("human_review: user aborted")
                break
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(ids):
                    fid = ids[idx]
                    label = field_index.get(fid, None)
                    console.print(
                        Panel(ctx.answers[fid], title=label.label if label else fid)
                    )
                    new_val = Prompt.ask(
                        "New answer (leave blank to keep current)",
                        default="",
                    )
                    if new_val:
                        ctx.answers[fid] = new_val
                        console.print("[green]Updated.[/green]")
                else:
                    console.print("[red]Invalid number.[/red]")
            else:
                console.print("[red]Unrecognized input.[/red]")

        return ctx
