from pydantic import BaseModel
from typing import List, Optional, Union

from pydantic import Field

class Step(BaseModel):
    title: str = Field(description="步骤标题")
    description: str = Field(description="Specify exactly what data to collect. If the user input contains a link, please retain the full Markdown format when necessary.")
class Plan(BaseModel):
    locale: str = Field(description="e.g. \"en-US\" or \"zh-CN\", based on the user's language or specific request")
    has_enough_context: bool = Field(description="Indicates whether the user input already contains enough context to answer the question.")
    thought: str = Field(description="A brief thought process or reasoning behind the plan.")
    title: str = Field(description="A concise title or summary of the plan.")
    steps: List[Step] = Field(description="Research & Processing steps to get more context")
