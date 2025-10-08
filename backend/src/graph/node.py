from langgraph.types import Command ,interrupt 
from src.tools.search_with_image import TavilySearchWithImages
from src.llms.llm import get_llm
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState,StateGraph , START , END
from typing import  List, Optional, Union
from typing_extensions import Annotated
import operator
from langchain_core.messages import HumanMessage
from langchain.tools import tool
from datetime import datetime
from src.prompts.template import render_prompt_template
from src.graph.type import Plan
import json
import logging
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
    print(result)
    print(result.tool_calls)
    print(n)

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

def research_node(state: State) -> Command:
    """
    分段式研究节点：
    每个步骤完成后动态生成报告段落，
    使用 ContextManager 压缩上下文。
    """
    tools = [TavilySearchWithImages()]
    messages = state.get("messages", [])
    all_research_messages = []
    step_results = []
    research_summary_parts = []

    context_manager = ContextManager(llm, max_tokens=32768)
    messages = context_manager.compress(messages)

    for i, step in enumerate(state["current_plan"].steps[:2]):
        logger.info(f"执行研究步骤 {i+1}: {step.title}")

        # 构建步骤提示
        step_prompt = f"""
        当前研究步骤 {i+1}: {step.title}
        描述: {step.description}

        请根据前面的研究发现（如有）继续分析。
        输出：逻辑清晰、专业化的研究结论。
        """

        # 构建消息上下文
        current_messages = messages + [{"role": "user", "content": step_prompt}]
        agent = create_react_agent(model=llm, tools=tools)

        try:
            # 调用 LLM agent
            result = agent.invoke({"messages": current_messages})
            ai_message = result["messages"][-1]
            raw_result = ai_message.content

            # 保存原始结果
            step_results.append({
                "step_index": i,
                "title": step.title,
                "description": step.description,
                "result": raw_result,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # 让 ContextManager 生成该步骤的"报告段落"
            from langchain_core.messages import SystemMessage, HumanMessage
            section_prompt = [
                SystemMessage(content="你是科研报告撰写专家。"),
                HumanMessage(content=f"请将以下研究结果转化为结构化报告段落，风格正式且逻辑连贯：\n\n{raw_result}")
            ]
            section = llm.invoke(section_prompt).content
            research_summary_parts.append(section)

            # 压缩上下文
            messages = context_manager.compress(
                messages + [
                    {"role": "user", "content": step_prompt},
                    {"role": "assistant", "content": raw_result}
                ]
            )

            all_research_messages.append(raw_result)
            logger.info(f"步骤 {i+1} 完成")

        except Exception as e:
            logger.exception(f"执行步骤 {i+1} 出错: {e}")
            step_results.append({
                "step_index": i,
                "title": step.title,
                "description": step.description,
                "result": f"研究失败: {str(e)}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": True
            })

    # 拼接报告
    research_summary = f"# 研究报告: {state['current_plan'].title}\n\n"
    research_summary += f"## 背景与研究动机\n{state['current_plan'].thought}\n\n"

    for idx, section in enumerate(research_summary_parts, start=1):
        research_summary += f"## {section}\n\n"

    research_summary += f"---\n研究完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    return Command(
        update={
            "messages": messages,
            "observations": state.get("observations", []) + all_research_messages,
            "research_summary": research_summary,
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
graph_build.add_node("research_node", research_node)

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

# 通过 langgraph dev 启动 ，langgraph API 会自动处理持久化，不需要自定义检查点
# graph = graph_build.compile()
def test_research_flow(research_topic: str = "2025 年 token2049大会的内容和愿景", locale: str = "zh-CN"):
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
        for result in graph.stream(test_state, config):
            stage_name = list(result.keys())[0]
            results["stages"].append(stage_name)
            print(f"✅ {stage_name}")   
        for chunk in graph.stream(Command(resume={
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

    result = test_research_flow()
    