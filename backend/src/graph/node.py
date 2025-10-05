from src.tools.search_with_image import TavilySearchWithImages
from src.llms.llm import get_llm
from langgraph.prebuilt import create_react_agent
llm = get_llm()
tools = [TavilySearchWithImages()]
react_agent = create_react_agent(
    llm, 
    tools)
res = react_agent.invoke({"messages": [{"role": "user", "content": "Search for images of cats"}]})
import re

content = res["messages"][-1].content

pattern = re.compile(r'\[.*?\]\((https?://[^\s)]+)\)')

# 替换成 Markdown 图片语法
def replace_with_img(match):
    url = match.group(1)
    return f'![]({url})'  # 可以加描述，如 ![Cat](url)

new_content = pattern.sub(replace_with_img, content)

# 如果文本里还有裸 URL，也可以额外匹配
url_pattern = re.compile(r'(?<!\]\()(?<!["\'])https?://[^\s]+')
new_content = url_pattern.sub(lambda m: f'![]({m.group(0)})', new_content)

# 写入 Markdown 文件
with open("test.md", "w", encoding="utf-8") as f:
    f.write(new_content)

