"""Skill 3 — QuestionClassifier: split form fields into standard vs open-ended."""
from __future__ import annotations

import re

from ..context import ApplicationContext, FormField
from ..skill import Skill

# Regex patterns that indicate an open-ended question requiring original writing
_OPEN_PATTERNS = [
    r"why\s+(do\s+you\s+want|are\s+you\s+interested|us|this)",
    r"tell\s+us",
    r"describe\s+(your|a\s+time|how)",
    r"what\s+(do\s+you|makes\s+you|sets\s+you|is\s+your)",
    r"how\s+(have\s+you|would\s+you|do\s+you)",
    r"share\s+(a\s+time|an\s+example|your)",
    r"cover\s+letter",
    r"essay",
    r"motivation",
    r"additional\s+information",
    r"anything\s+else",
    r"elaborate",
]

# Field types that are always standard (single value, autofillable)
_ALWAYS_STANDARD_TYPES = {"text", "email", "tel", "date", "number", "url", "select", "radio", "checkbox", "file"}


def is_open_ended(field: FormField) -> bool:
    if field.field_type != "textarea":
        return False
    label_lower = field.label.lower()
    return any(re.search(p, label_lower) for p in _OPEN_PATTERNS)


class QuestionClassifierSkill(Skill):
    name = "question_classifier"
    description = "Label each form field as 'standard' (autofillable) or 'open' (needs writing)."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        if not ctx.form_fields:
            return self.skip(ctx, "no form fields to classify")

        for field in ctx.form_fields:
            if is_open_ended(field):
                field.question_kind = "open"
                ctx.open_fields.append(field)
            else:
                field.question_kind = "standard"
                ctx.standard_fields.append(field)

        return ctx
