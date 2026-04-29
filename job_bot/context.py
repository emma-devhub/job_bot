from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FormField:
    id: str
    label: str
    field_type: str  # text | textarea | select | checkbox | radio | file
    required: bool = False
    options: list[str] = field(default_factory=list)
    # set by QuestionClassifier
    question_kind: str = "standard"  # standard | open


@dataclass
class ApplicationContext:
    # ── Input ──────────────────────────────────────────────────────────────
    job_url: str = ""
    job_title: str = ""
    company_name: str = ""
    platform: str = ""  # greenhouse | ashby | gem | workday | unknown

    # ── Profile & resume material ──────────────────────────────────────────
    profile: dict[str, Any] = field(default_factory=dict)
    resume_text: str = ""          # full resume as plain text
    experience_corpus: list[str] = field(default_factory=list)  # PAR/STAR stories

    # ── Parsed application form ────────────────────────────────────────────
    form_fields: list[FormField] = field(default_factory=list)
    job_description: str = ""

    # ── Classified questions ───────────────────────────────────────────────
    standard_fields: list[FormField] = field(default_factory=list)
    open_fields: list[FormField] = field(default_factory=list)

    # ── Answers (field.id → answer string) ────────────────────────────────
    answers: dict[str, str] = field(default_factory=dict)

    # ── Research ───────────────────────────────────────────────────────────
    company_research: str = ""

    # ── Pipeline state ─────────────────────────────────────────────────────
    ready_to_submit: bool = False
    skipped_skills: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
