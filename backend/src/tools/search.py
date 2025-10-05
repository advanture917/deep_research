from src.config.loader import load_yaml_config
from langchain_tavily.tavily_search import TavilySearchAPIWrapper 
from langchain_tavily._utilities import TAVILY_API_URL
import requests
import json
from typing import Optional, List, Dict, Any
import aiohttp
from pydantic import PrivateAttr
from src.tools.search_result_processor import SearchResultProcessor
def get_search_conf() :
    config = load_yaml_config("config.yaml")
    search_conf = config.get("search", {})
    return search_conf

class TavilySearchAPI(TavilySearchAPIWrapper):
    _search_conf: dict = PrivateAttr()
    def __init__(self, **kwargs):
        search_conf = get_search_conf()
        api_key = search_conf.get("tavily_api_key")

        super().__init__(tavily_api_key=api_key, **kwargs)

        self._search_conf = search_conf
    def raw_results(
        self,
        query: str,
        max_results: Optional[int] = 5,
        search_depth: Optional[str] = "advanced",
        include_domains: Optional[List[str]] = [],
        exclude_domains: Optional[List[str]] = [],
        include_answer: Optional[bool] = False,
        include_raw_content: Optional[bool] = True,
        include_images: Optional[bool] = True,
        include_image_descriptions: Optional[bool] = True,
    ) -> Dict:
        params = {
            "api_key": self._search_conf["tavily_api_key"],
            "query": query,
            "max_results": 2,
            "search_depth": search_depth,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions,
        }
        response = requests.post(
            # type: ignore
            f"{TAVILY_API_URL}/search",
            json=params,
        )
        response.raise_for_status()
        return response.json()

    async def async_raw_results(
        self,
        query: str,
        max_results: Optional[int] = 5,
        search_depth: Optional[str] = "advanced",
        include_domains: Optional[List[str]] = [],
        exclude_domains: Optional[List[str]] = [],
        include_answer: Optional[bool] = False,
        include_raw_content: Optional[bool] = True,
        include_images: Optional[bool] = True,
        include_image_descriptions: Optional[bool] = True,
    ) -> Dict:
        async def fetch() -> str:
            params = {
                "api_key": self._search_conf["tavily_api_key"],
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images,
                "include_image_descriptions": include_image_descriptions,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    # type: ignore
                    f"{TAVILY_API_URL}/search",
                    json=params,
                ) as response:
                    if response.status != 200:
                        raise requests.exceptions.HTTPError(
                            f"HTTP error {response.status}: {response.text}"
                        )
                    return await response.text()
        return json.loads(await fetch())

    def clean_results_with_images(
        self, raw_results: Dict[str, List[Dict]]
    ) -> List[Dict]:
        # print(f"🤗🤗🤗🤗{raw_results}")
        results = raw_results["results"]
        """Clean results from Tavily Search API."""
        clean_results = []
        for result in results:
            clean_result = {
                "type": "page",
                "title": result["title"],
                "url": result["url"],
                "content": result["content"],
                "score": result["score"],
            }
            if raw_content := result.get("raw_content"):
                clean_result["raw_content"] = raw_content
            clean_results.append(clean_result)
        images = raw_results["images"]
        for image in images:
            clean_result = {
                "type": "image",
                "image_url": image["url"],
                "image_description": image["description"],
            }
            # print(f"🤡🤡🤡🤡{image}")
            clean_results.append(clean_result)

        search_config = self._search_conf
        clean_results = SearchResultProcessor(
            min_score_threshold=search_config.get("min_score_threshold"),
            max_content_length_per_page=search_config.get(
                "max_content_length_per_page"
            ),
        ).process_results(clean_results)

        return clean_results