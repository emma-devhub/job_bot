"""Streamlit UI for job_bot pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
import yaml

from job_bot.context import ApplicationContext, FormField
from job_bot.skills import (
    AutoFillerSkill,
    AnswerWriterSkill,
    CompanyResearcherSkill,
    PlatformAdapterSkill,
    ProfileLoaderSkill,
    QuestionClassifierSkill,
)

st.set_page_config(page_title="Job Bot", page_icon="🤖", layout="wide")

# ── Session state init ─────────────────────────────────────────────────────
for key, default in {
    "ctx": None,
    "step": 0,       # 0=setup 1=parsed 2=written 3=done
    "profile_data": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ────────────────────────────────────────────────────────────────

def load_profile_from_upload(uploaded_file) -> dict:
    return yaml.safe_load(uploaded_file.read())


def fresh_ctx(job_url: str, profile: dict) -> ApplicationContext:
    ctx = ApplicationContext(job_url=job_url)
    ctx.profile = profile.get("personal", {})
    ctx.resume_text = profile.get("resume_text", "")
    ctx.experience_corpus = profile.get("experience_corpus", [])
    return ctx


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ 配置")

    gemini_key = st.text_input(
        "Gemini API Key",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
    )
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key

    model_name = st.selectbox(
        "模型",
        ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    )
    word_limit = st.slider("每题字数上限", 50, 400, 150, step=25)

    st.divider()
    st.caption("Profile YAML")
    uploaded = st.file_uploader("上传 profile.yaml", type=["yaml", "yml"])
    if uploaded:
        st.session_state.profile_data = load_profile_from_upload(uploaded)
        st.success("Profile 已加载")

    if not st.session_state.profile_data:
        example_path = Path("profiles/example.yaml")
        if example_path.exists():
            with example_path.open() as f:
                st.session_state.profile_data = yaml.safe_load(f)
            st.info("使用 example profile")

    if st.button("🔄 重置", use_container_width=True):
        st.session_state.ctx = None
        st.session_state.step = 0
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────

st.title("🤖 Job Bot")
st.caption("自动填写求职申请 · Greenhouse / Ashby / Gem / Workday")

# ── Step 0: 输入 ───────────────────────────────────────────────────────────

job_url = st.text_input(
    "Job URL",
    placeholder="https://boards.greenhouse.io/company/jobs/123",
)

if st.button("🔍 解析申请表", disabled=not job_url or not st.session_state.profile_data, use_container_width=True):
    if not st.session_state.profile_data:
        st.error("请先上传 profile.yaml")
        st.stop()

    ctx = fresh_ctx(job_url, st.session_state.profile_data)

    with st.spinner("正在抓取并解析表单..."):
        ctx = PlatformAdapterSkill().run(ctx)
        ctx = QuestionClassifierSkill().run(ctx)
        ctx = AutoFillerSkill().run(ctx)
        ctx = CompanyResearcherSkill().run(ctx)

    if ctx.errors:
        for e in ctx.errors:
            st.warning(e)

    st.session_state.ctx = ctx
    st.session_state.step = 1
    st.rerun()


# ── Step 1+: 展示解析结果 ──────────────────────────────────────────────────

ctx: ApplicationContext | None = st.session_state.ctx

if ctx is None:
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("平台", ctx.platform or "unknown")
col2.metric("标准字段", len(ctx.standard_fields))
col3.metric("开放题", len(ctx.open_fields))

if ctx.job_title:
    st.subheader(f"{ctx.job_title}  ·  {ctx.company_name}")

st.divider()

# ── Step 1: 自动填写预览 ───────────────────────────────────────────────────

with st.expander("📋 标准字段（自动填写）", expanded=False):
    if ctx.standard_fields:
        for field in ctx.standard_fields:
            val = ctx.answers.get(field.id, "")
            new_val = st.text_input(
                field.label + (" *" if field.required else ""),
                value=val,
                key=f"std_{field.id}",
            )
            ctx.answers[field.id] = new_val
    else:
        st.caption("没有识别到标准字段")

# ── Step 1→2: 生成开放题答案 ──────────────────────────────────────────────

if ctx.open_fields:
    if st.session_state.step < 2:
        if st.button(
            f"✍️ 用 Gemini 写 {len(ctx.open_fields)} 道开放题",
            disabled=not gemini_key,
            use_container_width=True,
        ):
            if not gemini_key:
                st.error("请先在左侧填入 Gemini API Key")
                st.stop()

            with st.spinner("AI 写作中..."):
                ctx = AnswerWriterSkill({"model": model_name, "word_limit": word_limit}).run(ctx)

            if ctx.errors:
                for e in ctx.errors:
                    st.error(e)
            else:
                st.session_state.ctx = ctx
                st.session_state.step = 2
                st.rerun()

# ── Step 2: 开放题编辑 ────────────────────────────────────────────────────

if st.session_state.step >= 2:
    st.subheader("✏️ 开放题答案（可直接编辑）")

    for field in ctx.open_fields:
        draft = ctx.answers.get(field.id, "")
        edited = st.text_area(
            field.label,
            value=draft,
            height=150,
            key=f"open_{field.id}",
        )
        ctx.answers[field.id] = edited

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔁 重新生成全部答案", use_container_width=True):
            for field in ctx.open_fields:
                ctx.answers.pop(field.id, None)
            st.session_state.step = 1
            st.rerun()

    with col_b:
        if st.button("✅ 确认，导出提交包", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()


# ── Step 3: 导出 ──────────────────────────────────────────────────────────

if st.session_state.step >= 3:
    st.success("答案已确认！")

    payload = {
        "job_url":      ctx.job_url,
        "job_title":    ctx.job_title,
        "company_name": ctx.company_name,
        "platform":     ctx.platform,
        "answers":      ctx.answers,
    }
    json_str = json.dumps(payload, indent=2, ensure_ascii=False)

    st.download_button(
        label="⬇️ 下载提交 JSON",
        data=json_str,
        file_name=f"{ctx.company_name or 'job'}_{ctx.job_title or 'application'}.json".replace(" ", "_"),
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("预览 JSON"):
        st.code(json_str, language="json")
