import dataclasses
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState


env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)

def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template using Jinja2.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name}: {e}")

def render_prompt_template(prompt_name: str, **kwargs) -> str:
    """
    Load and render a prompt template with the given variables.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)
        **kwargs: Variables to substitute in the template

    Returns:
        The rendered template string with variables substituted
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render(**kwargs)
    except Exception as e:
        raise ValueError(f"Error rendering template {prompt_name}: {e}")


  