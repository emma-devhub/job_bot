"""Skill 6 — AnswerWriter: draft open-ended answers via Claude API with anti-AI style."""
from __future__ import annotations

import os

import anthropic

from ..context import ApplicationContext, FormField
from ..skill import Skill

# The system prompt is the key tool for producing human-sounding text.
# Rules encode what "AI writing" typically looks like so the model avoids it.
_SYSTEM_PROMPT = """You are writing job application answers on behalf of the applicant.
Your output will be read by humans, so it must sound like a real person wrote it.

HARD RULES — violating any of these is a failure:
- No em dashes (—). Use a comma, period, or rewrite the clause instead.
- No semicolons in casual prose. Use two sentences.
- No filler openers: "In today's world", "I am excited to", "I am passionate about", "It is worth noting", "I look forward to"
- No buzzwords: leverage, synergy, robust, cutting-edge, seamlessly, delve, spearhead, cultivate, foster, paradigm, holistic, dynamic, transformative, impactful
- No vague superlatives: "extremely", "highly motivated", "results-driven", "detail-oriented"
- Don't start consecutive sentences with "I". Vary the sentence subject.

STYLE GUIDE:
- First person, conversational but professional
- Use contractions naturally (I've, we've, it's, I'm)
- Mix sentence lengths: punchy short sentences next to longer ones
- Lead with a specific detail, number, or example — not a thesis statement
- If you have PAR/STAR stories from the corpus, use them directly
- Under the word limit. Concise beats comprehensive.

You will receive: the question, the applicant's profile, their experience corpus, company research, and a word limit.
Output only the answer text — no labels, no headers, no meta-commentary."""


def _build_user_message(
    field: FormField,
    ctx: ApplicationContext,
    word_limit: int,
) -> str:
    parts = [
        f"QUESTION: {field.label}",
        f"WORD LIMIT: {word_limit}",
        "",
        "APPLICANT PROFILE:",
        _dict_to_text(ctx.profile),
        "",
        "RESUME SUMMARY:",
        ctx.resume_text[:1500] if ctx.resume_text else "(not provided)",
    ]

    if ctx.experience_corpus:
        parts += ["", "EXPERIENCE STORIES (use these when relevant):"]
        for story in ctx.experience_corpus[:5]:
            parts.append(f"- {story}")

    if ctx.company_research:
        parts += ["", "COMPANY & JOB CONTEXT:"]
        parts.append(ctx.company_research[:1500])

    return "\n".join(parts)


def _dict_to_text(d: dict, indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(_dict_to_text(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}{k}: {', '.join(str(i) for i in v)}")
        else:
            lines.append(f"{prefix}{k}: {v}")
    return "\n".join(lines)


class AnswerWriterSkill(Skill):
    name = "answer_writer"
    description = "Draft open-ended answers using Claude with anti-AI style constraints."

    def run(self, ctx: ApplicationContext) -> ApplicationContext:
        fields = ctx.open_fields or [
            f for f in ctx.form_fields if f.question_kind == "open"
        ]
        if not fields:
            return self.skip(ctx, "no open-ended fields to write")

        api_key = self.cfg("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            ctx.errors.append("answer_writer: ANTHROPIC_API_KEY not set")
            return ctx

        model = self.cfg("model", "claude-opus-4-7")
        word_limit = self.cfg("word_limit", 150)
        client = anthropic.Anthropic(api_key=api_key)

        for field in fields:
            if field.id in ctx.answers:
                continue

            user_msg = _build_user_message(field, ctx, word_limit)
            response = client.messages.create(
                model=model,
                max_tokens=600,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            ctx.answers[field.id] = response.content[0].text.strip()

        return ctx
