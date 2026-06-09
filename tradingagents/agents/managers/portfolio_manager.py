"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call.  The result is rendered
back to markdown for storage in ``final_trade_decision`` so memory log,
CLI display, and saved reports continue to consume the same shape they do
today.  When a provider does not expose structured output, the agent falls
back gracefully to free-text generation.
"""

from __future__ import annotations

from tradingagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )

        prompt = f"""As the Portfolio Manager, synthesize the risk analysts' debate and deliver the final trading decision across three time horizons.

{instrument_context}

---

**A-Stock Trading Constraints** (must factor into your decision):
- T+1 settlement: shares bought today cannot be sold until the next trading day
- Daily price limits: main board ±10%, STAR/ChiNext ±20%, ST stocks ±5%
- Minimum lot size: 100 shares (1 手) for main board; 200 shares for STAR/ChiNext
- Trading hours: 09:30-11:30, 13:00-15:00 (Beijing time)
- ST/delisting risk: ST or *ST status signals regulatory warning; factor into position sizing
- Margin eligibility: not all A-shares are margin-eligible; assume cash-only unless stated

---

**Rating Scale** (use exactly one per time horizon):
- **Buy**: Strong conviction to enter or add to position
- **Overweight**: Favorable outlook, gradually increase exposure
- **Hold**: Maintain current position, no action needed
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry

**Time Horizon Guidance:**
- **Short-term (1-30 trading days)**: Focus on technical analysis, momentum, volume, short-term catalysts, and immediate price action. A-stock T+1 and daily price limits are critical constraints.
- **Medium-term (1-6 months)**: Focus on fundamentals, industry cycle, earnings trajectory, valuation, and macro factors.
- **Long-term (6+ months)**: Focus on competitive moat, growth potential, structural trends, and business transformation.

**Context:**
- Research Manager's investment plan: **{research_plan}**
- Trader's transaction proposal: **{trader_plan}**
{lessons_line}
**Risk Analysts Debate History:**
{history}

---

Be decisive and ground every conclusion in specific evidence from the analysts. Output a separate rating for each time horizon — they may differ.
输出格式要求（请放在回答最前面，每行一条）：
**短线评级**: <Buy/Overweight/Hold/Underweight/Sell>
**中线评级**: <Buy/Overweight/Hold/Underweight/Sell>
**长线评级**: <Buy/Overweight/Hold/Underweight/Sell>
{get_language_instruction()}"""

        final_trade_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pm_decision,
            "Portfolio Manager",
        )

        from tradingagents.agents.utils.rating import parse_ratings, parse_rating

        ratings = parse_ratings(final_trade_decision)
        if not ratings:
            r = parse_rating(final_trade_decision)
            ratings = {"short": r, "medium": r, "long": r}

        new_risk_debate_state = {
            "judge_decision": final_trade_decision,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "short_term_rating": ratings["short"],
            "medium_term_rating": ratings["medium"],
            "long_term_rating": ratings["long"],
            "final_trade_decision": final_trade_decision,
        }

    return portfolio_manager_node
