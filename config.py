import os
from utils.singleton import Singleton
from dotenv import load_dotenv
load_dotenv()

class Config(metaclass=Singleton):
    def __init__(self) -> None:
        self.llm_model = "qwen-plus"
        self.temperature = 0.3
        self.api_key = os.getenv("llm_api_key")
        self.llm_url = os.getenv("llm_url")
        self.llm_max_tokens = 5000
        self.server_post = 7111
        self.host = "0.0.0.0"
        self.github_url = os.getenv('github_url')
        self.github_access_token = os.getenv('github_api_key')
        self.app_host = "0.0.0.0"
        self.app_port = 7111
        # Tavily API配置
        self.tavily_api_key = os.getenv('tavily_api_key')