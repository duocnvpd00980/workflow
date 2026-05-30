from langchain_core.tools import tool
import logging

from app.tools.web_search import web_search_tool

log = logging.getLogger(__name__)


# Danh sách các tool mà cậu sẽ bind vào LLM
tools = [web_search_tool]
