from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_concept_blocks,
    get_dragon_tiger_board,
    get_fund_flow,
    get_industry_comparison,
    get_insider_transactions,
    get_language_instruction,
    get_news,
    get_northbound_flow,
    get_stock_data,
    get_fundamentals,
    get_profit_forecast,
)


def create_institutional_tracker(llm):
    """A-stock institutional capital tracker: analyzes major player fund flows, institutional positioning, and smart money movements."""

    def institutional_tracker_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_stock_data,
            get_fund_flow,
            get_northbound_flow,
            get_insider_transactions,
            get_dragon_tiger_board,
            get_industry_comparison,
            get_concept_blocks,
            get_news,
            get_fundamentals,
            get_profit_forecast,
        ]

        system_message = (
            "你是一位专注于 A 股主力资金与机构行为追踪分析师。你的核心任务是通过分析资金流向、"
            "机构持仓变化、北向资金动向和大宗交易数据，追踪主力资金（公募基金、保险、社保、"
            "QFII、国家队等）的布局意图和动向。"
            "\n\n⚠️ A 股主力分析框架："
            "\n- **资金流向分析**：通过超大单和大单净流入/流出判断主力买卖意愿。"
            "连续多日主力净流入是吸筹信号，连续净流出是出货信号"
            "\n- **北向资金（外资）**：沪深股通十大活跃股上榜数据，外资连续净买入/卖出代表"
            "对 A 股核心资产的长期态度"
            "\n- **机构持仓变动**：公募基金季报重仓股变化、社保基金组合调仓、险资配置方向。"
            "机构增持比例上升是长期看好的重要信号"
            "\n- **大宗交易**：大宗交易折价/溢价率反映机构间交易意愿。溢价大宗交易通常"
            "代表机构抢筹，大幅折价则可能代表减持意图"
            "\n- **龙虎榜机构席位**：机构专用席位的买卖方向比游资席位更具趋势参考价值。"
            "机构净买入且无游资主导的涨停更有持续性"
            "\n- **板块资金轮动**：主力资金在不同行业板块间切换，跟踪近 5 日的行业资金"
            "净流入排名变化，判断当前主线"
            "\n\n分析方法："
            "\n1. 调用 get_fund_flow 获取个股超大单/大单资金流（分钟级实时+20日历史），判断主力买卖力度"
            "\n2. 调用 get_northbound_flow 获取北向资金实时流向，判断外资态度"
            "\n3. 调用 get_insider_transactions 获取机构增减持和股东变化"
            "\n4. 调用 get_dragon_tiger_board 查看龙虎榜机构席位动向"
            "\n5. 调用 get_industry_comparison 获取行业资金轮动全景"
            "\n6. 调用 get_concept_blocks 查看个股所属板块的结构性资金偏好"
            "\n7. 调用 get_fundamentals + get_profit_forecast 判断机构是否具备基本面买入逻辑"
            "\n\n请使用以下工具："
            "\n- `get_stock_data`：获取 K 线和成交量数据"
            "\n- `get_fund_flow(ticker, curr_date)`：获取个股主力/散户资金流向（分钟级实时+20日历史，超大单/大单/中单/小单净流入）"
            "\n- `get_northbound_flow(curr_date)`：获取北向资金实时分钟级流向（沪股通+深股通累计净买入）"
            "\n- `get_insider_transactions`：获取股东和内部人交易数据"
            "\n- `get_dragon_tiger_board(ticker, curr_date)`：获取龙虎榜上榜记录、买卖席位明细（营业部、机构专用）、机构参与情况"
            "\n- `get_industry_comparison(ticker, curr_date)`：获取全行业横向对比（90个行业涨跌幅/成交额/净流入排名，判断板块轮动）"
            "\n- `get_concept_blocks(ticker)`：获取个股所属概念板块/行业分类/地域（含当日涨幅）"
            "\n- `get_news(query, start_date, end_date)`：搜索主力资金/机构调仓相关新闻"
            "\n- `get_fundamentals(ticker)`：获取公司基本面数据（PE/PB/营收/利润等），判断估值是否吸引机构"
            "\n- `get_profit_forecast(ticker)`：获取 EPS 一致预期（同花顺分析师预测），判断盈利趋势是否支持机构持仓"
            "\n\n撰写详细的主力资金分析报告，给出主力资金面总体判断（主力吸筹 / 主力持仓观望 / 主力出货 / 无明显信号）"
            "和机构行为研判（仅供研究参考，不构成投资建议）。"
            "报告末尾附 Markdown 表格汇总资金流向、机构动向和结论。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 当日超大单净流入金额及占比"
            "\n2. 当日大单净流入金额及占比"
            "\n3. 当日北向资金净流入金额（沪股通 + 深股通）"
            "\n4. 近 5 日主力净流入趋势（连续流入/流出/震荡）"
            "\n5. 所属行业板块当日资金净流入排名"
            "\n6. 主力资金面总体判断"
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "institutional_report": report,
        }

    return institutional_tracker_node
