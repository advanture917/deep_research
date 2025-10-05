from langchain.chat_models import init_chat_model
from langchain.chat_models.base import BaseChatModel
from src.config.loader import load_yaml_config
from pathlib import Path
def _get_conf_path() -> Path:
    return Path(__file__).parent.parent.parent / "config.yaml"
def _create_chat_model(config: dict) -> BaseChatModel:
    if "openai" in config["llm"]:
        model_provider = "openai"
        return init_chat_model(model=config["llm"]["openai"]["model"],
                               model_provider=model_provider,
                               base_url=config["llm"]["openai"]["base_url"],
                               api_key=config["llm"]["openai"]["api_key"])
    else:
        raise ValueError("LLM type not supported")

def get_llm() -> BaseChatModel:
    config_path = _get_conf_path()
    config = load_yaml_config(config_path)
    llm = _create_chat_model(config)
    return llm
