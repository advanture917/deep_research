from ast import Str
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.store.base import Op
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import uuid
from datetime import datetime
import logging
from langchain_core.messages import HumanMessage
from langgraph.types import Command
# 导入研究流程组件
from src.graph.node import graph, State
from src.graph.type import Plan
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Deep Research API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    topic: str
    locale: str = "zh-CN"

class ConfirmPlan(BaseModel):
    plan_id: str
    user_confirm: str
    message: Optional[str] = None

class ResearchStatus(BaseModel):
    messages: str =""
    need_plan: bool = False
    plan_id: Optional[str] = None
    status: str = "pending"
    current_stage: Optional[str] = None
    current_plan: Optional[Dict] = None
    research_summary: Optional[str] = None
    step_results: List[Dict] = []
    error: Optional[str] = None
    message: Optional[str] = None  # 添加message字段

# 存储研究状态
research_states: Dict[str, Dict] = {}

@app.get("/")
async def root():
    return {"message": "AI研究助手API服务正在运行"}

@app.post("/api/research/start", response_model=ResearchStatus)
async def start_research(request: ResearchRequest):
    """协调器分析，这里会有两种情况，
    简单问题：直接返回答案
    复杂问题：返回一个研究计划，等待用户确认
    """
    try:
        plan_id = str(uuid.uuid4())
        
        # 创建配置
        config = {
            "configurable": {
                "thread_id": plan_id
            }
        }
        
        # 创建初始状态
        initial_state = State(
            messages=[HumanMessage(content=request.topic, name="用户输入")],
            research_topic=request.topic,
            locale=request.locale
        )
        
        resp = ResearchStatus(messages="研究流程已启动", plan_id=plan_id)
        
        # 执行协调器阶段
        logger.info(f"开始协调器分析: {plan_id}, 用户输入: {request.topic}")
        
        # 存储初始状态
        research_states[plan_id] = {
            "config": config,
            "current_state": initial_state,
            "status": "coordinate",
            "created_at": datetime.now().isoformat()
        }
        
        # 执行graph流程
        all_results = []
        for result in graph.stream(initial_state, config):
            stage_name = list(result.keys())[0]
            logger.info(f"执行阶段: {stage_name}")
            all_results.append(result)
            
            # 处理协调器结果
            if stage_name == "coordinate":
                coordinate_result = result[stage_name]
                if "messages" in coordinate_result:
                    # 简单问题：直接返回答案
                    # 提取消息内容（messages是一个消息对象列表）
                    messages_list = coordinate_result["messages"]
                    if messages_list and len(messages_list) > 0:
                        # 获取最后一条消息的内容
                        last_message = messages_list[-1]
                        if hasattr(last_message, 'content'):
                            resp.messages = last_message.content
                        elif isinstance(last_message, dict) and 'content' in last_message:
                            resp.messages = last_message['content']
                        else:
                            resp.messages = str(last_message)
                    else:
                        resp.messages = "协调器没有返回有效消息"
                    
                    resp.status = "completed"
                    resp.current_stage = "coordinate"
                    resp.need_plan = False  # 简单问题不需要计划
                    
                    # 更新状态
                    research_states[plan_id]["status"] = "completed"
                    research_states[plan_id]["current_state"] = coordinate_result
                    break  # 简单问题直接返回，不继续执行
            
            # 处理计划生成结果
            elif stage_name == "generate_plan":
                plan_result = result[stage_name]
                if "current_plan" in plan_result:
                    resp.need_plan = True
                    resp.status = "plan_generated"
                    resp.current_stage = "generate_plan"
                    resp.current_plan = plan_result["current_plan"]
                    
                    # 更新状态
                    research_states[plan_id]["status"] = "plan_generated"
                    research_states[plan_id]["current_state"] = plan_result
                    research_states[plan_id]["current_plan"] = plan_result["current_plan"]
                    
                    # 复杂问题需要用户确认，中断流程
                    continue
            
            # 处理中断（用户反馈）
            elif stage_name == "__interrupt__":
                resp.need_plan = True
                resp.status = "awaiting_confirmation"
                resp.current_stage = "human_feedback"
                msg =""
                for i in plan_result["current_plan"].steps:
                        msg += f"{i.title}\n\n{i.description}\n\n"
                resp.messages = f"我已经生成了一个研究计划: 如下 \n\n{msg}"
                # 更新状态
                research_states[plan_id]["status"] = "awaiting_confirmation"
                research_states[plan_id]["current_stage"] = "human_feedback"
                break
            
        return resp
        
    except Exception as e:
        logger.error(f"开始研究流程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research/confirm-plan", response_model=ResearchStatus)
async def confirm_plan(request: ConfirmPlan):
    """接收用户反馈，修改plan或者确认plan"""
    try:
        plan_id = request.plan_id
        
        if plan_id not in research_states:
            raise HTTPException(status_code=404, detail="研究计划不存在")
        
        # 获取存储的状态
        stored_state = research_states[plan_id]
        config = stored_state["config"]
        
        resp = ResearchStatus(messages="处理用户确认中", plan_id=plan_id)
        
        # 创建恢复命令
        if request.user_confirm == "confirm":
            cmd = Command(
                resume={
                    "user_confirm": "confirm",
                }
            )
            resp.messages = "研究计划已确认，开始执行研究"
        elif request.user_confirm == "modify":
            cmd = Command(
                resume={
                    "user_confirm": "modify",
                    "message": request.message 
                }
            )
            resp.messages = "研究计划已修改，重新生成计划"
        else:
            raise HTTPException(status_code=400, detail="无效的用户确认类型")
        
        # 继续执行graph流程
        async for result in graph.astream(cmd, config):
            stage_name = list(result.keys())[0]
            logger.info(f"继续执行阶段: {stage_name}")
            
            # 处理研究节点结果
            if stage_name == "research_node":
                research_result = result[stage_name]
                resp.status = "research_completed"
                resp.current_stage = "research_node"
                if "research_summary" in research_result:
                    resp.research_summary = research_result["research_summary"]
                if "step_results" in research_result:
                    resp.step_results = research_result["step_results"]
                
                # 更新状态
                research_states[plan_id]["status"] = "completed"
                research_states[plan_id]["current_state"] = research_result
                break
            
            # 处理重新生成计划
            elif stage_name == "generate_plan":
                plan_result = result[stage_name]
                if "current_plan" in plan_result:
                    resp.need_plan = True
                    resp.status = "plan_generated"
                    resp.current_stage = "generate_plan"
                    resp.current_plan = plan_result["current_plan"]
                    
                    # 更新状态
                    research_states[plan_id]["status"] = "plan_generated"
                    research_states[plan_id]["current_state"] = plan_result
                    research_states[plan_id]["current_plan"] = plan_result["current_plan"]
                    break
        
        return resp
        
    except Exception as e:
        logger.error(f"确认研究计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/status/{plan_id}", response_model=ResearchStatus)
async def get_research_status(plan_id: str):
    """获取研究状态"""
    if plan_id not in research_states:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    
    stored_state = research_states[plan_id]
    
    # 处理current_plan，如果是Plan对象则转换为字典
    current_plan = stored_state.get("current_plan")
    if hasattr(current_plan, 'dict'):
        current_plan = current_plan.dict()
    elif hasattr(current_plan, '__dict__'):
        current_plan = current_plan.__dict__
    
    resp = ResearchStatus(
        plan_id=plan_id,
        status=stored_state["status"],
        current_stage=stored_state.get("current_stage"),
        current_plan=current_plan,
        need_plan=stored_state.get("status") in ["plan_generated", "awaiting_confirmation"],
        messages=""  # 添加默认消息
    )
    
    # 根据状态设置消息
    if stored_state["status"] == "completed":
        resp.messages = "研究已完成"
        if "research_summary" in stored_state.get("current_state", {}):
            resp.research_summary = stored_state["current_state"]["research_summary"]
        if "step_results" in stored_state.get("current_state", {}):
            resp.step_results = stored_state["current_state"]["step_results"]
    elif stored_state["status"] == "need_plan":
        resp.messages = "需要生成研究计划"
    elif stored_state["status"] == "plan_generated":
        resp.messages = "研究计划已生成，等待用户确认"
        resp.need_plan = True
    elif stored_state["status"] == "awaiting_confirmation":
        resp.messages = "等待用户确认研究计划"
        resp.need_plan = True
    else:
        resp.messages = "研究进行中"
    
    return resp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
