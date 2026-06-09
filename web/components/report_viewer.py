"""Render the completed analysis report with clearly structured sections."""

from __future__ import annotations

import re
from typing import Any

import streamlit as st

from web.pdf_export import generate_markdown, generate_pdf

# Keys used in historical log vs real-time state differ for some fields.
_HISTORY_KEY_ALIASES = {
    "trader_investment_decision": "trader_investment_plan",
}


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


def _signal_style(signal: str) -> tuple[str, str]:
    s = signal.upper()
    if "BUY" in s:
        return "#22c55e", "买入"
    if "SELL" in s:
        return "#ef4444", "卖出"
    return "#fbbf24", "持有"


_HORIZON_CN = {"short": "短线", "medium": "中线", "long": "长线"}


_ANALYST_SECTIONS = [
    ("market_report", "📊 技术分析"),
    ("sentiment_report", "💬 市场情绪"),
    ("news_report", "📰 新闻舆情"),
    ("fundamentals_report", "📋 基本面"),
    ("policy_report", "🏛️ 政策分析"),
    ("hot_money_report", "🔥 游资追踪"),
    ("institutional_report", "🏦 主力追踪"),
    ("lockup_report", "🔒 解禁/减持"),
]


def _card(label: str, value: str, color: str) -> str:
    return f"""
        <div style="flex:1; min-width:120px; padding:0.8rem;">
            <div style="font-size:0.7rem; color:#888; letter-spacing:1px;">{label}</div>
            <div style="font-size:2rem; font-weight:900; color:{color}; margin:0.2rem 0;">{value}</div>
        </div>
    """


def render_report(
    final_state: dict[str, Any],
    ticker: str,
    trade_date: str,
    signal: dict[str, str] | str,
    elapsed: float | None = None,
    stock_name: str = "",
) -> None:
    """Render the full analysis report with a clear reading hierarchy.

    Layout (top to bottom):
      1. TRADING SIGNAL — three time-horizon cards
      2. 最终决策       — Portfolio Manager's full decision (THE conclusion)
      3. 交易方案       — Trader's concrete proposal
      4. 多空辩论       — bull/bear debate driving the decision
      5. 分析师报告     — collapsible per-analyst detail
      6. 风控评估       — collapsible risk debate
      7. 数据质量       — collapsible
    """

    # ── helpers ──────────────────────────────────────────────────────────

    def _get(key: str, default: str = "") -> str:
        val = final_state.get(key, "")
        if not val:
            alias = _HISTORY_KEY_ALIASES.get(key, "")
            if alias:
                val = final_state.get(alias, "")
        return str(val) if val else default

    stats_html = ""
    if elapsed is not None:
        m, s = divmod(int(elapsed), 60)
        stats_html = f'<div style="font-size:0.9rem; color:#888; margin-top:0.3rem;">耗时 {m}:{s:02d}</div>'

    stock_name_label = f"（{stock_name}）" if stock_name else ""

    if isinstance(signal, str):
        signals = {"short": signal, "medium": signal, "long": signal}
    else:
        signals = signal

    # ═══════════════════════════════════════════════════════════════════════
    # 1. TRADING SIGNAL
    # ═══════════════════════════════════════════════════════════════════════
    signal_cards = ""
    for key in ("short", "medium", "long"):
        s = signals.get(key, "Hold")
        color, _ = _signal_style(s)
        signal_cards += _card(_HORIZON_CN[key], s.upper(), color)

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #333;
            border-radius: 16px;
            padding: 1.2rem;
            text-align: center;
            margin: 1rem 0 2rem;
        ">
            <div style="font-size:0.9rem; color:#888; letter-spacing:2px;">TRADING SIGNAL</div>
            <div style="display:flex; justify-content:center; gap:0.5rem; flex-wrap:wrap;">
                {signal_cards}
            </div>
            <div style="font-size:1.2rem; color:#f5f1eb; margin-top:0.3rem;">
                {ticker}{stock_name_label} · {trade_date}
            </div>
            {stats_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("⚠️ 本报告由 AI 自动生成，仅供学习研究，不构成投资建议。")

    col_md, col_pdf, col_spacer = st.columns([1, 1, 2])
    with col_md:
        md_text = generate_markdown(final_state, ticker, trade_date, signal)
        st.download_button(
            "📥 下载 Markdown",
            data=md_text.encode("utf-8"),
            file_name=f"TradingAgents-Astock_{ticker}_{trade_date}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_pdf:
        try:
            pdf_bytes = generate_pdf(final_state, ticker, trade_date, signal)
            st.download_button(
                "📄 下载 PDF",
                data=pdf_bytes,
                file_name=f"TradingAgents-Astock_{ticker}_{trade_date}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.button(
                "📄 PDF 不可用",
                disabled=True,
                use_container_width=True,
                help=f"PDF 生成失败，请改用 Markdown 导出。原因：{exc}",
            )

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. 最终决策 — Portfolio Manager (THE conclusion)
    # ═══════════════════════════════════════════════════════════════════════
    final_decision = _get("final_trade_decision")
    if final_decision:
        st.markdown("### 📋 最终决策")
        st.markdown(_strip_think(final_decision))
        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. 交易方案 — Trader
    # ═══════════════════════════════════════════════════════════════════════
    trader_text = _get("trader_investment_decision") or _get("trader_investment_plan")
    if trader_text:
        st.markdown("### 💹 交易方案")
        st.markdown(_strip_think(trader_text))
        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. 多空辩论
    # ═══════════════════════════════════════════════════════════════════════
    debate = final_state.get("investment_debate_state")
    if debate and isinstance(debate, dict):
        st.markdown("### ⚔️ 多空辩论")
        tab_bull, tab_bear, tab_judge = st.tabs(["多方", "空方", "研究经理"])
        with tab_bull:
            st.markdown(_strip_think(debate.get("bull_history", "") or "无数据"))
        with tab_bear:
            st.markdown(_strip_think(debate.get("bear_history", "") or "无数据"))
        with tab_judge:
            st.markdown(_strip_think(debate.get("judge_decision", "") or "无数据"))
        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. 分析师报告 (collapsible detail)
    # ═══════════════════════════════════════════════════════════════════════
    visible_analysts = [(k, t) for k, t in _ANALYST_SECTIONS if final_state.get(k)]
    if visible_analysts:
        st.markdown("### 📊 分析师报告")
        for key, title in visible_analysts:
            with st.expander(title, expanded=False):
                st.markdown(_strip_think(str(final_state[key])))
        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 6. 风控评估 (collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    risk = final_state.get("risk_debate_state")
    if risk and isinstance(risk, dict):
        st.markdown("### 🛡️ 风控评估")
        tab_agg, tab_con, tab_neu, tab_rj = st.tabs(["激进", "保守", "中性", "风控决策"])
        with tab_agg:
            st.markdown(_strip_think(risk.get("aggressive_history", "") or "无数据"))
        with tab_con:
            st.markdown(_strip_think(risk.get("conservative_history", "") or "无数据"))
        with tab_neu:
            st.markdown(_strip_think(risk.get("neutral_history", "") or "无数据"))
        with tab_rj:
            st.markdown(_strip_think(risk.get("judge_decision", "") or "无数据"))
        st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    # 7. 数据质量 (collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    dqs = final_state.get("data_quality_summary", "")
    if dqs:
        with st.expander("✅ 数据质量", expanded=False):
            st.markdown(str(dqs))
