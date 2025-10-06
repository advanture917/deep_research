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
    print(result.tool_calls)
    print(n)

    if n > 0:
        tool_calls.extend(result.tool_calls)
        goto = "generate_plan"
    # 检查是否调用了handoff_to_planner工具
    handoff_calls = [call for call in tool_calls if call["name"] == "handoff_to_planner"]
    
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
    else:
        # 直接回答简单问题，返回最后一条消息
        return Command(
            update={
                "messages": [{"role": "assistant", "content": result.content}]
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
    if feedback["response"] and str(feedback["response"]).lower() in ["确认", "ok", "好的", "同意", "accept"]:
        logger.info(feedback["response"])
        goto = "research_node"
    else:
        goto = "generate_plan"
        logger.info(feedback["response"])
        return Command(
            update={
            "messages": HumanMessage(content=feedback["response"],name = "feedback"),
            },
            goto = goto,
        )
    return Command(
        goto = goto,
    )

def research_node(state: State) -> Command:
    """
    研究节点：根据计划进行研究
    遍历每个研究步骤，使用React Agent进行迭代研究，
    并整合每次的输入输出，形成完整的研究结果
    """
    tools = [TavilySearchWithImages()]
    
    # 获取当前状态中的消息历史
    messages = state.get("messages", [])
    
    # 存储每个步骤的研究结果
    step_results = []
    all_research_messages = []
    
    # 遍历研究计划的每个步骤
    for i, step in enumerate(state["current_plan"].steps[:2]):
        logger.info(f"执行研究步骤 {i+1}: {step.title}")
        
        # 创建React Agent
        agent = create_react_agent(
            model=llm,
            tools=tools,
        )
        
        # 构建当前步骤的查询消息
        step_query = f"""
        研究步骤 {i+1}: {step.title}
        
        描述: {step.description}
        
        请基于前面的研究结果（如果有）进行深入研究，并提供详细的发现。
        """
        
        # 将步骤查询添加到消息历史中
        current_messages = messages.copy()
        current_messages.append({"role": "user", "content": step_query})
        
        try:
            # 执行Agent研究
            result = agent.invoke({"messages": current_messages})
            
            if result and result.get("messages"):
                # 获取最后一条AI消息（研究结果）
                last_msg = result["messages"][-1]
                
                # 记录步骤结果
                step_result = {
                    "step_index": i,
                    "step_title": step.title,
                    "step_description": step.description,
                    "research_result": last_msg.content,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                step_results.append(step_result)
                
                # 将AI响应添加到消息历史中，用于下一步的上下文
                messages.append({"role": "user", "content": step_query})
                messages.append({"role": "assistant", "content": last_msg.content})
                all_research_messages.append(last_msg.content)
                
                logging.info(f"步骤 {i+1} 完成研究结果")
                
        except Exception as e:
            print(f"执行步骤 {i+1} 时出错: {e}")
            # 记录错误信息
            error_result = {
                "step_index": i,
                "step_title": step.title,
                "step_description": step.description,
                "research_result": f"研究步骤执行失败: {str(e)}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": True
            }
            step_results.append(error_result)
    
    # 整合所有研究结果
    research_summary = f"""
# 研究报告: {state['current_plan'].title}

## 研究背景
{state['current_plan'].thought}

## 详细研究步骤与发现

"""
    
    for result in step_results:
        research_summary += f"""
### 步骤 {result['step_index'] + 1}: {result['step_title']}

**描述**: {result['step_description']}

**研究发现**:
{result['research_result']}

---

"""
    
    research_summary += f"""
## 研究总结

本次研究共执行了 {len(step_results)} 个步骤，形成了完整的研究报告。
研究完成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    # 返回更新后的状态
    return Command(
        update={
            "messages": messages,  # 更新完整的消息历史
            "observations": state.get("observations", []) + all_research_messages,  # 添加研究发现
            "research_summary": research_summary,  # 添加研究总结
            "step_results": step_results,  # 添加每个步骤的详细结果
            "research_loop_count": state.get("research_loop_count", 0) + 1  # 增加研究循环计数
        },
        goto="__end__"  # 研究完成后结束流程
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
graph_build.add_edge("coordinate", "generate_plan")
graph_build.add_edge("generate_plan", "human_feedback")
graph_build.add_edge("human_feedback", "research_node")
graph_build.add_edge("research_node", END)


# 配置检查点
from langgraph.checkpoint.memory import InMemorySaver
memory = InMemorySaver()

# 编译图时配置检查点
graph = graph_build.compile(checkpointer=memory)

def test_research_flow(research_topic: str = "2025年token2049大会有哪些重要议题和演讲？", locale: str = "zh-CN"):
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
    
    # 保存流程图
    try:
        with open("graph.md", "wb") as f:
            f.write(graph.get_graph().draw_mermaid().encode("utf-8"))
            print("✅ 流程图已保存为 graph.md")
    except Exception as e:
        print(f"⚠️  保存流程图失败: {e}")
    
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
            print(f"   ✅ {stage_name}")
        
        # 阶段2: 计划生成
        print("\n📝 阶段2: 生成研究计划...")
        for result in graph.stream(test_state, config):
            if "generate_plan" in result:
                plan = result["generate_plan"]["current_plan"]
                print(f"   ✅ 计划标题: {plan.title}")
                print(f"   ✅ 计划包含 {len(plan.steps)} 个研究步骤")
                results["plan"] = {
                    "title": plan.title,
                    "thought": plan.thought,
                    "steps_count": len(plan.steps),
                    "steps": [{"title": step.title, "description": step.description} for step in plan.steps]
                }
        
        # 阶段3: 用户确认（模拟）
        print("\n👤 阶段3: 用户确认研究计划...")
        from langgraph.types import Command
        for chunk in graph.stream(Command(resume={"response": "确认"}), config):
            if "human_feedback" in chunk:
                print("   ✅ 用户已确认计划")
        
        # 阶段4: 研究执行
        print("\n🔍 阶段4: 执行研究计划...")
        final_state = None
        research_results = graph.invoke(Command(resume={"response": "确认"}), config)
        results["final_state"] = research_results
        results["success"] = True
        return results
        # for chunk in graph.stream(Command(resume={"response": "确认"}), config):
        #     if "research_node" in chunk:
        #         final_state = chunk["research_node"]
        #         results["final_state"] = final_state
                
        #         print(f"   ✅ 研究执行完成")
        #         print(f"   📊 研究循环数: {final_state.get('research_loop_count', 0)}")
        #         print(f"   📊 研究发现数量: {len(final_state.get('observations', []))}")
        #         print(f"   📊 步骤结果数量: {len(final_state.get('step_results', []))}")
                
        #         if "research_summary" in final_state:
        #             summary_length = len(final_state["research_summary"])
        #             print(f"   📊 研究总结长度: {summary_length} 字符")
                
        #         results["success"] = True
        #         break
        
        # print("\n🎉 研究流程测试完成！")
        # return results
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        results["error"] = str(e)
        import traceback
        traceback.print_exc()
        return results

def run_specific_test():
    """运行特定的测试用例"""
    print("=== 运行特定测试 ===")
    
    # 测试用例1: 简单问题
    print("\n🧪 测试用例1: 简单研究问题")
    result1 = test_research_flow("什么是区块链技术？", "zh-CN")
    
    # 测试用例2: 复杂问题
    print("\n🧪 测试用例2: 复杂研究问题")
    result2 = test_research_flow("2024年人工智能在医疗领域的最新发展和应用案例", "zh-CN")
    
    # 测试用例3: 英文问题
    print("\n🧪 测试用例3: 英文研究问题")
    result3 = test_research_flow("What are the latest developments in quantum computing?", "en-US")
    
    # 总结测试结果
    print("\n📈 测试结果总结:")
    for i, result in enumerate([result1, result2, result3], 1):
        status = "✅ 成功" if result["success"] else "❌ 失败"
        print(f"   测试用例{i}: {status}")
        if result["success"] and "plan" in result:
            print(f"     - 计划步骤: {result['plan']['steps_count']} 个")
            print(f"     - 研究发现: {len(result['final_state']['observations'])} 条")

# 测试运行
if __name__ == "__main__":
    import sys
    
    # # 检查命令行参数
    # if len(sys.argv) > 1:
    #     if sys.argv[1] == "test":
    #         # 运行基础测试
    #         if len(sys.argv) > 2:
    #             # 自定义测试问题
    #             research_topic = " ".join(sys.argv[2:])
    #             result = test_research_flow(research_topic)
    #         else:
    #             # 默认测试
    #             result = test_research_flow()
    #     elif sys.argv[1] == "full_test":
    #         # 运行完整测试套件
    #         run_specific_test()
    #     else:
    #         print("用法:")
    #         print("  python node.py test [研究问题]    - 运行单个测试")
    #         print("  python node.py full_test          - 运行完整测试套件")
    #         print("  python node.py                    - 运行默认测试")
    # else:
        # 默认行为：运行基础测试
    print("运行默认测试...")
    result = test_research_flow()
    
    # 如果测试成功，显示研究总结预览
    if result["success"] and result["final_state"] :
        print("\n=== 研究总结预览 ===")
        summary = result["final_state"]
        print(summary)
    # # 测试2: 需要研究的问题
    # print("\n--- 测试需要研究的问题 ---")
    # test_state2 = State(
    #     research_topic="2025年token2049大会有哪些重要议题和演讲？",
    #     locale="zh-CN"
    # )
    # result2 = graph.invoke(test_state2)
    # print(f"协调器响应: {result2['messages'][-1]['content']}")
    
    # # 如果有研究计划，继续测试研究流程
    # if result2.get("current_plan"):
    #     print(f"\n生成的研究计划:")
    #     print(f"标题: {result2['current_plan'].title}")
    #     print(f"思考过程: {result2['current_plan'].thought}")
    #     print("研究步骤:")
    #     for i, step in enumerate(result2['current_plan'].steps):
    #         print(f"  {i+1}. {step.title}: {step.description}")
        
    #     # 测试研究执行
    #     print("\n--- 执行研究步骤 ---")
    #     tools = [TavilySearchWithImages()]
    #     agent = create_react_agent(llm, tools)
        
    #     for i, step in enumerate(result2["current_plan"].steps):
    #         print(f"\n执行步骤 {i+1}: {step.title}")
    #         try:
    #             res = agent.invoke({"messages": [{"role": "user", "content": step.description}]})
    #             if res and res.get("messages"):
    #                 last_msg = res["messages"][-1]
    #                 print(f"研究结果: {last_msg.content[:200]}...")  # 只显示前200字符
    #         except Exception as e:
    #             print(f"执行步骤时出错: {e}")
    
    # print("\n=== 测试完成 ===")


# # 工具函数：用于后续处理
# def process_search_results(content: str) -> str:
#     """
#     处理搜索结果中的图片链接，转换为Markdown格式
#     """
#     import re
    
#     # 匹配链接模式
#     pattern = re.compile(r'\[.*?\]\((https?://[^\s)]+)\)')
    
#     # 替换成 Markdown 图片语法
#     def replace_with_img(match):
#         url = match.group(1)
#         return f'![]({url})'
    
#     new_content = pattern.sub(replace_with_img, content)
    
#     # 如果文本里还有裸 URL，也可以额外匹配
#     url_pattern = re.compile(r'(?<!\]\()(?<!["\'])https?://[^\s]+')
#     new_content = url_pattern.sub(lambda m: f'![]({m.group(0)})', new_content)
    
#     return new_content

# def create_research_plan(state: State) -> dict:
#     """
#     创建研究计划节点
#     生成研究计划并更新状态
#     """
#     # 生成研究查询
#     plan_content = generate_query(state)
    
#     # 处理搜索结果中的图片链接
#     processed_content = process_search_results(plan_content)
    
#     # 更新状态
#     return {
#         "current_plan": processed_content,
#         "plan_iterations": state.get("plan_iterations", 0) + 1,
#         "messages": [{"role": "assistant", "content": processed_content}]
#     }

