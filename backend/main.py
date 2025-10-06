from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI研究助手API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class ResearchStep(BaseModel):
    id: str
    title: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ResearchPlan(BaseModel):
    id: str
    topic: str
    steps: List[ResearchStep]
    created_at: datetime
    status: str = "planning"  # planning, running, completed, failed

class ResearchRequest(BaseModel):
    topic: str

class ResearchProgress(BaseModel):
    plan_id: str
    current_step: int
    total_steps: int
    status: str
    current_process: str
    logs: List[str]

# 存储研究计划和进度
research_plans: Dict[str, ResearchPlan] = {}
research_progress: Dict[str, ResearchProgress] = {}

@app.get("/")
async def root():
    return {"message": "AI研究助手API服务正在运行"}

@app.post("/api/research/create-plan", response_model=ResearchPlan)
async def create_research_plan(request: ResearchRequest):
    """创建研究计划"""
    try:
        plan_id = str(uuid.uuid4())
        
        # 模拟生成研究步骤（实际应该调用AI模型）
        steps = [
            ResearchStep(
                id=str(uuid.uuid4()),
                title="问题分析与定义",
                description="明确研究问题的范围和核心要素"
            ),
            ResearchStep(
                id=str(uuid.uuid4()),
                title="文献调研与综述",
                description="收集和分析相关的学术文献和资料"
            ),
            ResearchStep(
                id=str(uuid.uuid4()),
                title="数据收集与整理",
                description="收集研究所需的各类数据和信息"
            ),
            ResearchStep(
                id=str(uuid.uuid4()),
                title="深度分析与推理",
                description="运用AI技术进行深度分析和推理"
            ),
            ResearchStep(
                id=str(uuid.uuid4()),
                title="结论总结与报告",
                description="总结研究结果并生成报告"
            )
        ]
        
        plan = ResearchPlan(
            id=plan_id,
            topic=request.topic,
            steps=steps,
            created_at=datetime.now(),
            status="planning"
        )
        
        research_plans[plan_id] = plan
        logger.info(f"创建研究计划: {plan_id}, 主题: {request.topic}")
        
        return plan
    except Exception as e:
        logger.error(f"创建研究计划失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/plan/{plan_id}", response_model=ResearchPlan)
async def get_research_plan(plan_id: str):
    """获取研究计划"""
    if plan_id not in research_plans:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    return research_plans[plan_id]

@app.post("/api/research/update-plan/{plan_id}", response_model=ResearchPlan)
async def update_research_plan(plan_id: str, updated_plan: ResearchPlan):
    """更新研究计划"""
    if plan_id not in research_plans:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    
    research_plans[plan_id] = updated_plan
    return updated_plan

@app.post("/api/research/start/{plan_id}")
async def start_research(plan_id: str):
    """开始研究"""
    if plan_id not in research_plans:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    
    plan = research_plans[plan_id]
    plan.status = "running"
    
    # 初始化进度
    progress = ResearchProgress(
        plan_id=plan_id,
        current_step=0,
        total_steps=len(plan.steps),
        status="running",
        current_process="准备开始研究...",
        logs=["研究开始"]
    )
    research_progress[plan_id] = progress
    
    # 异步执行研究（这里只是模拟）
    asyncio.create_task(execute_research(plan_id))
    
    return {"message": "研究已开始", "plan_id": plan_id}

@app.post("/api/research/stop/{plan_id}")
async def stop_research(plan_id: str):
    """停止研究"""
    if plan_id not in research_plans:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    
    if plan_id in research_progress:
        research_progress[plan_id].status = "stopped"
        research_progress[plan_id].logs.append("研究已停止")
    
    research_plans[plan_id].status = "stopped"
    return {"message": "研究已停止"}

@app.get("/api/research/progress/{plan_id}", response_model=ResearchProgress)
async def get_research_progress(plan_id: str):
    """获取研究进度"""
    if plan_id not in research_progress:
        raise HTTPException(status_code=404, detail="研究进度不存在")
    return research_progress[plan_id]

@app.get("/api/research/report/{plan_id}")
async def get_research_report(plan_id: str):
    """获取研究报告"""
    if plan_id not in research_plans:
        raise HTTPException(status_code=404, detail="研究计划不存在")
    
    plan = research_plans[plan_id]
    
    # 生成模拟报告
    report = {
        "plan_id": plan_id,
        "topic": plan.topic,
        "created_at": plan.created_at.isoformat(),
        "status": plan.status,
        "summary": f"关于\"{plan.topic}\"的研究报告",
        "content": f"# {plan.topic}\n\n## 研究概述\n\n本研究深入探讨了{plan.topic}的相关问题，通过系统性的分析和研究，得出以下结论...\n\n## 主要发现\n\n1. 重要发现一\n2. 重要发现二\n3. 重要发现三\n\n## 详细分析\n\n### 问题分析与定义\n在这一阶段，我们明确了研究的范围和核心要素...\n\n### 文献调研与综述\n通过广泛的文献调研，我们发现...\n\n### 数据收集与整理\n收集到的数据显示...\n\n### 深度分析与推理\n基于收集到的数据，我们进行了深度分析...\n\n### 结论总结\n综合以上分析，我们得出以下结论...\n\n## 参考资料\n\n1. 相关文献1\n2. 相关文献2\n3. 相关文献3",
        "steps": [
            {
                "title": step.title,
                "description": step.description,
                "status": step.status,
                "result": step.result or "完成分析"
            }
            for step in plan.steps
        ]
    }
    
    return report

async def execute_research(plan_id: str):
    """执行研究（模拟）"""
    try:
        plan = research_plans[plan_id]
        progress = research_progress[plan_id]
        
        for i, step in enumerate(plan.steps):
            if progress.status == "stopped":
                break
                
            # 更新当前步骤
            progress.current_step = i + 1
            progress.current_process = f"正在执行: {step.title}"
            progress.logs.append(f"开始执行步骤 {i+1}: {step.title}")
            
            # 更新步骤状态
            step.status = "in_progress"
            step.started_at = datetime.now()
            
            # 模拟处理时间
            await asyncio.sleep(3)
            
            # 完成步骤
            step.status = "completed"
            step.completed_at = datetime.now()
            step.result = f"步骤 {i+1} 完成: {step.description}"
            
            progress.logs.append(f"步骤 {i+1} 完成")
        
        # 研究完成
        plan.status = "completed"
        progress.status = "completed"
        progress.current_process = "研究已完成"
        progress.logs.append("研究完成")
        
        logger.info(f"研究完成: {plan_id}")
        
    except Exception as e:
        logger.error(f"研究执行失败: {str(e)}")
        if plan_id in research_plans:
            research_plans[plan_id].status = "failed"
        if plan_id in research_progress:
            research_progress[plan_id].status = "failed"
            research_progress[plan_id].logs.append(f"研究失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)