"""Sidebar: stock input, LLM config, and history list."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import streamlit as st

from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from web.history import delete_analysis, get_history

_UI_CONFIG_PATH = Path.home() / ".tradingagents" / "ui_config.json"

# Provider display names in recommended order
_PROVIDERS: list[tuple[str, str]] = [
    ("MiniMax（推荐·国内直连）", "minimax"),
    ("DeepSeek", "deepseek"),
    ("通义千问 Qwen", "qwen"),
    ("智谱 GLM", "glm"),
    ("OpenAI", "openai"),
    ("Anthropic", "anthropic"),
    ("Google Gemini", "google"),
    ("xAI Grok", "xai"),
    ("Ollama（本地）", "ollama"),
]

_PROVIDER_DISPLAY = [name for name, _ in _PROVIDERS]
_PROVIDER_KEYS = [key for _, key in _PROVIDERS]


def _resolve_user_input(raw: str) -> tuple[str, str | None]:
    """Resolve raw user input to (ticker_code, error_msg).

    Accepts 6-digit codes or Chinese stock names (e.g. '宝光股份').
    Returns (code, None) on success or ("", error_msg) on failure.
    """
    from tradingagents.dataflows.a_stock import resolve_ticker

    try:
        code = resolve_ticker(raw)
        return code, None
    except ValueError as e:
        return "", str(e)


def _load_llm_config() -> None:
    """Restore LLM config from local file into session state (page refresh)."""
    if not _UI_CONFIG_PATH.exists():
        return
    try:
        cfg = json.loads(_UI_CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return
    p = cfg.get("llm_provider", "")
    if p in _PROVIDER_KEYS:
        st.session_state.setdefault("llm_provider", p)
        st.session_state.setdefault("llm_provider_idx", _PROVIDER_KEYS.index(p))
        if p in MODEL_OPTIONS:
            qm = cfg.get("quick_think_llm", "")
            if qm:
                q_vals = [v for _, v in MODEL_OPTIONS[p]["quick"]]
                if qm in q_vals:
                    st.session_state.setdefault("quick_model_idx", q_vals.index(qm))
            dm = cfg.get("deep_think_llm", "")
            if dm:
                d_vals = [v for _, v in MODEL_OPTIONS[p]["deep"]]
                if dm in d_vals:
                    st.session_state.setdefault("deep_model_idx", d_vals.index(dm))
    if "llm_base_url" in cfg:
        st.session_state.setdefault("llm_base_url", cfg["llm_base_url"])


def _save_llm_config() -> None:
    """Save current LLM config to local file for cross-refresh persistence."""
    cfg = {
        "llm_provider": st.session_state.get("llm_provider", "minimax"),
        "quick_think_llm": st.session_state.get("quick_think_llm", ""),
        "deep_think_llm": st.session_state.get("deep_think_llm", ""),
    }
    if base_url := st.session_state.get("llm_base_url"):
        cfg["llm_base_url"] = base_url
    try:
        _UI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _UI_CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False))
    except OSError:
        pass


def _render_llm_config() -> None:
    """Render LLM provider and model selection controls."""
    _load_llm_config()

    provider_idx = st.selectbox(
        "LLM 供应商",
        range(len(_PROVIDERS)),
        format_func=lambda i: _PROVIDER_DISPLAY[i],
        key="llm_provider_idx",
        help="选择你配置了 API Key 的供应商",
    )
    provider_key = _PROVIDER_KEYS[provider_idx]
    st.session_state["llm_provider"] = provider_key

    if provider_key in MODEL_OPTIONS:
        quick_options = MODEL_OPTIONS[provider_key]["quick"]
        deep_options = MODEL_OPTIONS[provider_key]["deep"]

        quick_labels = [label for label, _ in quick_options]
        quick_values = [value for _, value in quick_options]
        deep_labels = [label for label, _ in deep_options]
        deep_values = [value for _, value in deep_options]

        quick_idx = st.selectbox(
            "快速思考模型",
            range(len(quick_options)),
            format_func=lambda i: quick_labels[i],
            key="quick_model_idx",
            help="用于常规分析任务，速度优先",
        )
        st.session_state["quick_think_llm"] = quick_values[quick_idx]

        deep_idx = st.selectbox(
            "深度思考模型",
            range(len(deep_options)),
            format_func=lambda i: deep_labels[i],
            key="deep_model_idx",
            help="用于辩论/决策等需要深度推理的任务",
        )
        st.session_state["deep_think_llm"] = deep_values[deep_idx]
    else:
        custom_quick = st.text_input("快速思考模型 ID", key="custom_quick_model")
        custom_deep = st.text_input("深度思考模型 ID", key="custom_deep_model")
        st.session_state["quick_think_llm"] = custom_quick
        st.session_state["deep_think_llm"] = custom_deep

    st.text_input(
        "API Base URL（第三方/代理，可选）",
        key="llm_base_url",
        placeholder="例: https://your-proxy.com/v1",
        help=(
            "通过第三方中转/代理访问 Claude、OpenAI 等模型时填写网关地址；"
            "留空则用所选供应商的官方地址。API Key 仍从 .env 读取，"
            "且每个供应商用各自的环境变量——"
            "OpenAI=OPENAI_API_KEY、DeepSeek=DEEPSEEK_API_KEY、"
            "通义=DASHSCOPE_API_KEY、智谱=ZHIPU_API_KEY、MiniMax=MINIMAX_API_KEY、"
            "Claude=ANTHROPIC_API_KEY、OpenRouter=OPENROUTER_API_KEY、xAI=XAI_API_KEY。"
            "也可在 .env 里设 BACKEND_URL 代替此处。"
        ),
    )

    _save_llm_config()


def render_sidebar() -> None:
    """Render the sidebar with input controls and history."""

    st.markdown(
        """
        <div style="text-align:center; margin-bottom:1.5rem;">
            <span style="font-size:2rem; font-weight:800; color:#ff5a1f;">Trading</span><span style="font-size:2rem; font-weight:800; color:#f5f1eb;">Agents</span><span style="font-size:2rem; font-weight:800; color:#f5f1eb;">-</span><span style="font-size:2rem; font-weight:800; color:#ff5a1f;">Astock</span>
            <div style="font-size:0.85rem; color:#888; margin-top:0.2rem;">
                A股多Agent投研系统
            </div>
            <div style="font-size:0.7rem; color:#555; margin-top:0.3rem;">
                by <a href="https://github.com/simonlin1212" style="color:#ff5a1f; text-decoration:none;">simonlin1212</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("#### 新建分析")

    ticker = st.text_input(
        "股票代码",
        placeholder="例: 300750 或 宁德时代",
        key="input_ticker",
        help="输入6位A股代码或中文股票全称",
    )

    trade_date = st.date_input(
        "分析日期",
        value=date.today(),
        key="input_date",
    )

    with st.expander("⚙️ 模型配置", expanded=False):
        _render_llm_config()

    tracker = st.session_state.get("tracker")
    is_busy = tracker is not None and tracker.is_running

    if st.button(
        "开始分析" if not is_busy else "分析进行中...",
        use_container_width=True,
        disabled=is_busy or not ticker,
        type="primary",
    ):
        resolved_code, err = _resolve_user_input(ticker)
        if err:
            st.error(f"❌ {err}")
        else:
            if resolved_code != ticker.strip():
                st.success(f"✅ {ticker.strip()} → {resolved_code}")
            st.session_state["start_analysis"] = {
                "ticker": resolved_code,
                "trade_date": trade_date.strftime("%Y-%m-%d"),
            }
            st.session_state["viewing_history"] = None

    st.markdown("---")
    st.markdown("#### 历史记录")

    history = get_history()
    if not history:
        st.caption("暂无历史记录")
        return

    for entry in history[:20]:
        t, d, p = entry["ticker"], entry["date"], entry["path"]
        cols = st.columns([5, 1])
        with cols[0]:
            if st.button(f"{t}  ·  {d}", key=f"hist_{t}_{d}", use_container_width=True):
                st.session_state["viewing_history"] = p
                st.session_state["start_analysis"] = None
        with cols[1]:
            if st.button("🗑️", key=f"del_{t}_{d}", help="删除此记录"):
                st.session_state["pending_delete"] = {"ticker": t, "date": d, "path": p}
                st.rerun()

    pending = st.session_state.get("pending_delete")
    if pending:
        st.markdown("---")
        st.warning(f"确认删除 {pending['ticker']} · {pending['date']} 的分析记录？此操作不可撤销。")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 确认删除", key="confirm_delete_yes", type="primary"):
                delete_analysis(pending["path"])
                st.session_state.pop("pending_delete", None)
                st.rerun()
        with c2:
            if st.button("取消", key="confirm_delete_no"):
                st.session_state.pop("pending_delete", None)
                st.rerun()

    st.markdown("---")
    st.caption("⚠️ 仅供学习研究，不构成投资建议")
