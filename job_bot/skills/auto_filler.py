"""Skill 4 — AutoFiller: map standard form fields to profile answers."""
from __future__ import annotations

import re

from ..context import ApplicationContext, FormField
from ..skill import Skill

# Canonical key -> list of label patterns that map to it
_FIELD_MAP: dict[str, list[str]] = {
    "first_name":    [r"first\s*name", r"given\s*name"],
    "last_name":     [r"last\s*name", r"family\s*name", r"surname"],
    "full_name":     [r"full\s*name", r"your\s*name", r"^name$"],
    "email":         [r"email", r"e-mail"],
    "phone":         [r"phone", r"mobile", r"telephone"],
    "linkedin":      [r"linkedin"],
    "github":        [r"github"],
    "website":       [r"website", r"portfolio", r"personal\s*site"],
    "location":      [r"city", r"location", r"address", r"country"],
    "work_auth":     [r"authorized\s*to\s*work", r"work\s*authorization", r"visa\s*status"],
    "sponsorship":   [r"require\s*sponsorship", r"visa\s*sponsorship"],
    "salary":        [r"salary\s*expect", r"compensation"],
    "start_date":    [r"start\s*date", r"available\s*to\s*start", r"earliest\s*start"],
    "years_exp":     [r"years?\s*of\s*experience"],
    "gender":        [r"^gender$", r"gender\s*identity"],
    "ethnicity":     [r"ethnicity", r"race"],
    "veteran":       [r"veteran"],
    "disability":    [r"disability"],
}


def _match_label(label: str, patterns: list[str]) -> bool:
    label_lower = label.lower().strip()
    return any(re.search(p, label_lower) for p in patterns)


def _resolve(field: FormField, profile: dict) -> str | None:
    for canonical_key, patterns in _FIELD_MAP.items():
        if _match_label(field.label, patterns):
            # Try exact key first, then nested lookup
            val = profile.get(canonical_key)
            if val is None and "." in canonical_key:
                parts = canonical_key.split(".")
                sub = profile
                for part in parts:
                    sub = sub.get(part, {})
                val = sub if isinstance(sub, str) else None
            if val is not None:
                return str(val)
    return None


class AutoFillerSkill(Skill):
    name = "auto_filler"
    description = "Autofill standard form fields from the user's profile."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        if not ctx.standard_fields and not ctx.form_fields:
            return self.skip(ctx, "no standard fields to fill")

        fields_to_fill = ctx.standard_fields or [
            f for f in ctx.form_fields if f.question_kind == "standard"
        ]

        for field in fields_to_fill:
            if field.id in ctx.answers:
                continue  # already filled
            answer = _resolve(field, ctx.profile)
            if answer is not None:
                ctx.answers[field.id] = answer

        return ctx
