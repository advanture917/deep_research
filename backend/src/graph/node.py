from langgraph.types import Command ,interrupt 
from src.tools.search_with_image import TavilySearchWithImages
from src.llms.llm import get_llm
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState,StateGraph , START , END
from typing import  List, Optional, Union, Tuple
from typing_extensions import Annotated
import operator
import re
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.tools import tool
from datetime import datetime
from src.prompts.template import render_prompt_template
from src.graph.type import Plan
import json
import logging
import asyncio
from langgraph.prebuilt import create_react_agent
from src.utils.content import ContextManager
logger = logging.getLogger(__name__)
# config = {"thread_id"}
class State(MessagesState):
    # ========== 用户输入 ==========
    research_topic: str = ""                         # 研究主题 / 用户问题
    locale: str = "zh-CN"                                # 输出语言 (en-US, zh-CN 等)
    current_plan: Optional[Plan] = None                         # 研究计划
    
    # ========== 搜索阶段 ==========
    search_queries: Annotated[List[str], operator.add] = []  # 已生成的查询
    web_results: Annotated[List[dict], operator.add] = []     # 原始搜索结果 (title, url, snippet)
    sources: Annotated[List[dict], operator.add] = []         # 过滤/提炼后的资料
    
    # ========== 推理 & 计划 ==========
    observations: Annotated[List[str], operator.add] = []   # 每轮研究的发现/结论
    plan_iterations: int = 0                                # 迭代次数
    auto_accept_plan: bool = False                          # 是否自动接受生成的计划
    
    # ========== 背景调查 ==========
    enable_background_investigation: bool = False        # 是否开启并行背景调查
    background_info: Optional[str] = None                # 背景信息（维基百科等）
    
    # ========== 研究执行阶段 ==========
    research_summary: Optional[str] = None              # 研究总结报告
    step_results: Annotated[List[dict], operator.add] = []     # 每个研究步骤的详细结果
    
    # ========== 控制参数 ==========
    research_loop_count: int = 0                        # 当前研究循环数
    max_research_loops: int = 3                                    # 最大循环数

llm = get_llm()
@tool 
def handoff_to_planner(
    research_topic: Annotated[str, "交给planner处理的研究主题/用户问题"],
    locale: Annotated[str, "用户输入语言 (en-US, zh-CN 等)"],
):
    """
    交给planner处理研究主题
    """
    # 这个工具不需要返回值，只要被调用就表示需要进入研究计划阶段
    pass 

def coordinate_node(state: State) -> Command:
    """
    协调，处理简单的用户查询，对于研究、计划、复杂的任务交给planner处理
    轻问题 → 直接回答
    重问题 → 交给 planner
    """
    # 获取用户输入的研究主题
    research_topic = state.get("research_topic", "")
    locale = state.get("locale", "zh-CN")
    
    # 如果没有研究主题，使用用户最后一条消息作为输入
    if not research_topic:
        # 从消息历史中获取最后一条用户消息
        messages = state["messages"][-1]
        research_topic = messages.content

    # 准备协调器提示模板
    template_vars = {
        "CURRENT_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # "research_topic": research_topic,
    }
    # 使用协调器提示模板
    system_prompt = render_prompt_template("coordinate", **template_vars)
    llm_with_tools = llm.bind_tools([handoff_to_planner])
    
    # 运行协调器代理
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": research_topic}
    ]
    
    result = llm_with_tools.invoke(messages)
    goto = "__end__"
    # 检查工具调用
    tool_calls = []
    n = len(result.tool_calls)

    if n ==0 :
        print(f"goto: {goto}")
    # 直接回答简单问题，返回最后一条消息
        return Command(
            update={
                "messages": [{"role": "assistant", "content": result.content}]
            },
            goto= goto,
        )

    tool_calls.extend(result.tool_calls)
    goto = "generate_plan"    
    # 检查是否调用了handoff_to_planner工具
    handoff_calls = [call for call in tool_calls if call["name"] == "handoff_to_planner"]
    print(f"handoff_calls: {handoff_calls}")
    if handoff_calls:
        # 提取工具调用的参数并填充到state中
        tool_call = handoff_calls[-1]  # 使用最后一次调用的参数
        args = tool_call["args"] if "args" in tool_call else {}

        research_topic = args.get("research_topic", research_topic)
        locale = args.get("locale", locale)
        
        # 需要进入研究计划阶段，返回更新后的状态
        return Command(
            update={
                "research_topic": research_topic,
                "locale": locale,
            },
            goto= goto,
            
        )
    


def generate_plan(state: State) -> dict:
    """
    第一个节点：生成研究计划
    使用模板系统获取系统提示词，并通过Jinja2模板替换变量
    """
    # 准备模板变量
    template_vars = {
        "CURRENT_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "research_topic": state.get("research_topic", ""),
        "locale": state.get("locale", "zh-CN")
    }
    
    # 使用封装的render_prompt_template方法渲染模板
    system_prompt = render_prompt_template("planner", **template_vars)
    
    # 创建消息列表
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{state.get('research_topic', '')}"}
    ]
    
    # 调用LLM生成响应
    struct_llm = llm.with_structured_output(Plan)
    response = struct_llm.invoke(messages)
    response_str = response.model_dump_json(indent=4)
    # 返回字典用于更新状态
    return {
        "current_plan": response,
        "plan_iterations": state.get("plan_iterations", 0) + 1,
        "messages": [{"role": "assistant", "content": response_str}]
    }

def human_back_node(state: State) -> Command:
    """
    用户是否确认planner 生成的研究计划，如果用户有补充输入，
    则更新研究计划
    """

    feedback = interrupt("Please Review the Plan.")
    logger.info(f"用户反馈: {feedback}")
    if feedback["user_confirm"] == "confirm":
        logger.info(f"用户确认计划，继续执行研究")
        goto = "research_node"
    else:
        goto = "generate_plan"
        logger.info(f"用户要求修改计划，重新生成")
        return Command(
            update={
            "messages": HumanMessage(content=feedback["message"],name = "feedback"),
            },
            goto = goto,
        )
    return Command(
        goto = goto,
    )
def critic_node(state: State) -> Command:
    """
    批判节点：
    对研究结果进行批判，判断是否符合预期。
    """
    pass
# langgraph 回溯机制：
# 1. 当批判节点判断研究结果不符合预期时，
#    会触发回溯机制，将当前研究节点的状态回滚到上一个状态。
# 2. 回溯机制会根据当前状态中的 messages 列表，
#    找到最近的一次研究节点的状态，
#    并将其作为当前状态。


def _extract_links_and_images_from_md(md: str) -> Tuple[List[str], List[str]]:
    """
    从 Markdown 中提取链接和图片 URL（去重，按出现顺序）。
    - 链接格式 [text](http...)
    - 图片格式 ![alt](http...)
    - 也尝试匹配裸 URL
    """
    if not md:
        return [], []
    links = []
    images = []
    # 图片优先（它也是链接形式）
    for m in re.finditer(r'!\[[^\]]*\]\((https?://[^\s)]+)\)', md):
        url = m.group(1).strip()
        if url not in images:
            images.append(url)
        if url not in links:
            links.append(url)
    # 普通链接
    for m in re.finditer(r'\[[^\]]*\]\((https?://[^\s)]+)\)', md):
        url = m.group(1).strip()
        if url not in links:
            links.append(url)
    # 裸 url（避免重复）
    for m in re.finditer(r'(https?://[^\s\)\]]+)', md):
        url = m.group(1).strip().rstrip(').,')
        if url not in links:
            links.append(url)
    return links, images


async def _async_add_summary_and_references(report_md: str) -> str:
    """
    异步版本：为研究报告添加总结和引用。
    """
    # 使用llm 总结
    prompt = render_prompt_template("summary")
    
    # 异步调用llm 总结报告
    sys_msg = SystemMessage(content=prompt)
    human_msg = HumanMessage(content=report_md)
    summary_result = await llm.ainvoke([sys_msg, human_msg])
    summary_md = summary_result.content
    
    # 提取报告中的链接和图片
    links, images = _extract_links_and_images_from_md(report_md)
    # 生成引用列表
    references = []
    for i, url in enumerate(links + images):
        references.append(f"[{i+1}] {url}")
    # 合并引用
    references_md = "## 引用列表:\n\n" + "\n".join(references)


    # 合并到报告
    report_md = report_md + "\n\n" + summary_md + "\n\n" + references_md
    return report_md


async def async_research_node(state: State) -> Command:
    """
    异步并行版本：
    - research_agent 与 report_agent 并行
    - report-agent 串行依赖：必须等待前一步的report结果
    step1.research  ──────┐
                      │  (生成结果传入report队列)
                      ▼
             step1.report ──────┐
                      |          ▼
step2.research  ──────┐        合并report
                      │
                      ▼
             step2.report ──────┐
                                ▼
                          最终汇总

    """
    tools = [TavilySearchWithImages()]
    messages = state.get("messages", []) or []
    research_context_manager = ContextManager(llm, max_tokens=32768)
    report_context_manager = ContextManager(llm, max_tokens=163840)

    existing_report = state.get("research_summary", "")
    if not existing_report:
        existing_report = f"# 研究报告: {state['current_plan'].title}\n\n" \
                          f"## 背景与研究动机\n{state['current_plan'].thought}\n\n"
    report_md = existing_report

    RESEARCH_AGENT_SYSTEM = render_prompt_template("research")
    REPORT_AGENT_SYSTEM = render_prompt_template("report")

    step_results = []
    all_research_messages = []

    # 队列与同步锁
    report_queue = asyncio.Queue()
    report_lock = asyncio.Lock()  # 确保report串行执行

    async def research_worker(step_index, step):
        """执行单个research step并推入report_queue"""
        nonlocal messages
        try:
            logger.info(f"[research] 执行步骤 {step_index}: {step.title}")
            step_user_prompt = f"""
当前研究步骤 {step_index}: {step.title}
描述: {step.description}

要求：
- 输出为 Markdown（包含标题、分析、结论）。
- 正文中使用 Markdown 链接格式 `[描述文字](URL)` 标注引用。
- **保持 Markdown 格式**: 图片使用标准 Markdown 语法 `![描述文字](图片URL)`。
"""
            current_messages = messages + [
                SystemMessage(content=RESEARCH_AGENT_SYSTEM),
                HumanMessage(content=step_user_prompt)
            ]
            current_messages = research_context_manager.compress_messages(current_messages)

            research_agent = create_react_agent(model=llm, tools=tools)
            result = await research_agent.ainvoke({"messages": current_messages})
            step_md = result["messages"][-1].content if isinstance(result["messages"][-1], AIMessage) else str(result["messages"][-1])

            links, images = _extract_links_and_images_from_md(step_md)

            await report_queue.put({
                "step_index": step_index,
                "title": step.title,
                "description": step.description,
                "step_md": step_md,
                "sources": links,
                "images": images
            })

            logger.info(f"[research] 步骤 {step_index} 完成，已推入report队列")

        except Exception as e:
            logger.exception(f"[research] 步骤 {step_index} 出错: {e}")
            step_results.append({
                "step_index": step_index,
                "title": step.title,
                "description": step.description,
                "result_markdown": f"研究失败: {str(e)}",
                "sources": [],
                "images": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": True
            })

    async def report_worker():
        """按队列顺序串行整合报告"""
        nonlocal report_md
        while True:
            item = await report_queue.get()
            if item is None:
                break  # 结束信号
            async with report_lock:
                step_index = item["step_index"]
                step_md = item["step_md"]
                logger.info(f"[report] 合并步骤 {step_index}")

                report_user_prompt = f"""
previous_report: '''{report_md}'''
latest_step: '''{step_md}'''

请输出增量内容：仅包含最新 step 的 Markdown。
"""
                report_messages = messages + [
                    SystemMessage(content=REPORT_AGENT_SYSTEM),
                    HumanMessage(content=report_user_prompt)
                ]
                report_messages = report_context_manager.compress_messages(report_messages)

                report_result = await llm.ainvoke(report_messages)
                increment_md = report_result.content
                print(f"[report] 步骤 {step_index} 增量内容: {increment_md}")
                # 检查 increment_md 是否包含 existing_report 的标题+背景
                existing_header = f"# 研究报告: {state['current_plan'].title}\n\n" \
                                f"## 背景与研究动机\n{state['current_plan'].thought}\n\n"
                if increment_md.startswith(existing_header):
                    report_md = ""  # 清空已有 report_md，避免重复
                report_md += "\n\n" + increment_md
                step_results.append({
                    **item,
                    "result_markdown": step_md,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error": False
                })
                logger.info(f"[report] 步骤 {step_index} 已合并完成")

    # 创建任务
    research_tasks = [
        asyncio.create_task(research_worker(i + 1, step))
        for i, step in enumerate(state["current_plan"].steps[:2])
    ]
    report_task = asyncio.create_task(report_worker())

    # 等待research完成
    await asyncio.gather(*research_tasks)
    # 发出结束信号
    await report_queue.put(None)
    # 等待report完成
    await report_task

    summary = await _async_add_summary_and_references(report_md)
    final_report = summary + f"\n\n---\n研究完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return Command(
        update={
            "messages": messages,
            "observations": state.get("observations", []) + all_research_messages,
            "research_summary": final_report,
            "step_results": step_results,
            "research_loop_count": state.get("research_loop_count", 0) + 1,
        },
        goto="__end__"
    )
      
# 构建完整的研究流程图
graph_build = StateGraph(State)

# 添加节点
graph_build.add_node("coordinate", coordinate_node)
graph_build.add_node("generate_plan", generate_plan)
graph_build.add_node("human_feedback", human_back_node)
graph_build.add_node("research_node", async_research_node)

# 定义流程
graph_build.add_edge(START, "coordinate")

graph_build.add_edge("generate_plan", "human_feedback")
graph_build.add_edge("human_feedback", "research_node")
graph_build.add_edge("research_node", END)
graph_build.add_edge("coordinate", END)
# 正常启动
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver() 
graph = graph_build.compile(checkpointer=checkpointer)

# 通过 langgraph dev 启动 ，langgraph API 会自动处理持久化，不需要自定义检查点，否则报错
# graph = graph_build.compile()
async def test_research_flow(research_topic: str = "2025 年 token2049大会的内容和愿景", locale: str = "zh-CN"):
    """
    测试完整的研究流程
    
    Args:
        research_topic: 研究主题
        locale: 语言设置
    
    Returns:
        dict: 包含测试结果和最终状态的字典
    """
    print("=== 研究流程测试开始 ===")
    print(f"研究主题: {research_topic}")
    print(f"语言设置: {locale}")
    
    config = {
        "configurable": {
            "thread_id": "test_research"
        }
    }
    
    
    # 创建测试状态
    test_state = State(
        messages=[HumanMessage(content=research_topic, name="用户输入")],
        research_topic=research_topic,
        locale=locale
    )
    
    results = {
        "research_topic": research_topic,
        "locale": locale,
        "stages": [],
        "final_state": None,
        "success": False,
        "error": None
    }
    
    try:
        # 阶段1: 协调器
        print("\n📋 阶段1: 协调器分析...")
        async for result in graph.astream(test_state, config):
            stage_name = list(result.keys())[0]
            results["stages"].append(stage_name)
            print(f"✅ {stage_name}")   
        async for chunk in graph.astream(Command(resume={
                    "user_confirm": "confirm",
                    # "message": 
                }), config):
            print(chunk)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        results["error"] = str(e)
        import traceback
        traceback.print_exc()
        return results


# 测试运行
if __name__ == "__main__":
    import asyncio
    
    result = asyncio.run(test_research_flow())
    