# from src.tools.search import TavilySearchAPI
# api = TavilySearchAPI()
# query = "images of cats"
# results = api.raw_results(query)
# print(results)
from src.tools.search_with_image import TavilySearchWithImages
tool = TavilySearchWithImages()
query = "images of cats"
results = tool.invoke(query)
print(results)