import logging
import json
import math
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import requests

from api.response import ProcessResponse
from llm.prompt import prompt
from utils.parse import BaseOutputParser
from config import Config
from typing import List, Dict, Union, Any
from llm.filter_keywords import FilterKeywords


CFG = Config()

class Agent:
    """
    一个提供GitHub搜索和关键词生成等功能的工具集。
    这个类被重构为一个无状态的工具提供者，专注于为AwesomeAgent提供基础能力。
    """
    
    def __init__(self):
        """初始化Agent，设置LLM和解析器"""
        self.llm = ChatOpenAI(
            streaming=False,
            verbose=True,
            model_name = CFG.llm_model,
            temperature=CFG.temperature,
            openai_api_key=CFG.api_key,
            openai_api_base=CFG.llm_url,
            max_tokens=CFG.llm_max_tokens,
            openai_proxy=None
        )
        self.parse = BaseOutputParser()
        logging.info("llm agent init successfully!!!")
    
    def generate_keywords(self, domain: str) -> List[str]:
        """
        根据用户提供的领域，生成一个多样化的GitHub搜索关键词列表。
        
        使用prompt.md中第1步的提示词模板，让LLM生成关键词，覆盖教程、指南、
        路线图和资源集合等不同方面。
        
        Args:
            domain (str): 用户感兴趣的领域，例如"容器化技术"或"量化金融"
            
        Returns:
            List[str]: 生成的关键词列表，例如["docker tutorial", "kubernetes guide"]
        
        Raises:
            Exception: 如果LLM调用或解析失败
        """
        logging.info(f"为领域 '{domain}' 生成关键词")
        
        # 使用prompt.md中的第1步提示词
        keyword_prompt_template = """
        作为一名AI助手，你的任务是帮助用户发现指定技术领域的优秀 GitHub 资源。用户提供了一个领域："{domain}"。

        请你生成一个包含5个多样化搜索关键词的列表。这些关键词必须是英文的，无论用户输入的是什么语言。
        这些关键词应该覆盖不同类型的资源，例如：
        - 教程 (tutorials)
        - 指南 (guides)
        - 学习路线图 (roadmaps)
        - 资源集合 (awesome lists)
        - 最佳实践 (best practices)
        - 实例或项目 (examples/projects)

        如果用户输入的领域是中文，请先理解该领域的含义，然后生成对应的英文关键词。
        例如，如果用户输入"机器学习"，你应该生成"machine learning tutorial"而不是"机器学习 tutorial"。

        你的输出必须是一个 JSON 格式的字符串数组，只包含英文关键词。

        示例输入: "容器化技术"
        示例输出:
        ["docker tutorial", "kubernetes guide", "containerization roadmap", "awesome containers", "docker best practices"]
        
        示例输入: "机器学习"
        示例输出:
        ["machine learning tutorial", "deep learning guide", "AI roadmap", "awesome ML repositories", "neural networks examples"]
        """
        
        chat_prompt = PromptTemplate.from_template(keyword_prompt_template)
        output_parser = StrOutputParser()
        chain = chat_prompt | self.llm | output_parser
        
        try:
            raw_res = chain.invoke({"domain": domain})
            logging.debug(f"LLM raw response for keywords: {raw_res}")
            
            # 清理响应，确保是有效的JSON
            cleaned_res_str = raw_res.strip()
            if cleaned_res_str.startswith("```json"):
                cleaned_res_str = cleaned_res_str.removeprefix("```json").removesuffix("```")
            elif cleaned_res_str.startswith("```"):
                cleaned_res_str = cleaned_res_str.removeprefix("```").removesuffix("```")
            
            # 解析关键词列表
            keywords = json.loads(cleaned_res_str)
            
            if not isinstance(keywords, list) or not all(isinstance(kw, str) for kw in keywords):
                raise ValueError("Generated keywords are not a list of strings.")
                
            logging.info(f"成功生成关键词: {keywords}")
            return keywords
            
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"关键词生成失败: {e}. Raw response: {raw_res if 'raw_res' in locals() else 'N/A'}")
            raise Exception(f"Failed to generate keywords: {str(e)}")
    
    def search_github_repositories(self, keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        使用关键词搜索GitHub仓库，并返回原始结果。
        
        这个方法是一个简化版的search_github，移除了与评估相关的参数(Star数、更新日期等)，
        因为这些将在第4步的评估阶段处理。
        
        Args:
            keywords (List[str]): 要搜索的关键词列表
            max_results (int, optional): 每个关键词返回的最大结果数。默认为10。
            
        Returns:
            List[Dict[str, Any]]: 仓库信息的列表，每个仓库包含GitHub API返回的基本信息
            
        Raises:
            Exception: 如果GitHub API调用失败
        """
        if not keywords:
            logging.warning("尝试搜索GitHub时提供了空的关键词列表")
            return []
        
        all_repos = []
        
        for keyword in keywords:
            logging.info(f"搜索GitHub，关键词: '{keyword}'")
            
            # 构建查询
            github_query = keyword
            
            headers = {
                'Authorization': f'token {CFG.github_access_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            params = {
                'q': github_query,
                'sort': 'stars',  # 确保按星级排序
                'order': 'desc',
                'per_page': max_results  # 限制每个关键词最多返回10个结果
            }
            
            try:
                response = requests.get(CFG.github_url, headers=headers, params=params)
                response.raise_for_status()
                
                raw_repos = response.json().get('items', [])
                logging.info(f"关键词 '{keyword}' 返回了 {len(raw_repos)} 个仓库")
                
                # 过滤政治或敏感内容
                filtered_repos = self._filter_sensitive_repos(raw_repos)
                logging.info(f"关键词 '{keyword}' 过滤后剩余 {len(filtered_repos)} 个仓库")
                
                all_repos.extend(filtered_repos)
                
            except requests.exceptions.RequestException as e:
                logging.error(f"GitHub API调用失败: {e}")
                raise Exception(f"GitHub API error: {str(e)}")
        
        # 去重（基于仓库URL）
        unique_repos = []
        seen_urls = set()
        
        for repo in all_repos:
            url = repo.get('html_url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_repos.append(repo)
        
        # 再次按星级排序
        sorted_repos = sorted(unique_repos, key=lambda x: x.get('stargazers_count', 0), reverse=True)
        
        # 限制最终返回的总数为10个
        final_repos = sorted_repos[:10] if len(sorted_repos) > 10 else sorted_repos
        
        logging.info(f"所有关键词搜索后，得到 {len(final_repos)} 个唯一仓库")
        return final_repos
    
    def _filter_sensitive_repos(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤掉包含敏感或政治关键词的仓库。
        
        Args:
            repos (List[Dict[str, Any]]): 原始仓库列表
            
        Returns:
            List[Dict[str, Any]]: 过滤后的仓库列表
        """
        filtered_repos = []
        
        for repo in repos:
            repo_name_str = repo.get('full_name', '')
            repo_desc_str = repo.get('description') or '' 

            repo_name_lower = repo_name_str.lower()
            repo_desc_lower = repo_desc_str.lower()

            is_political = False
            for p_kw in FilterKeywords().combined_filter_keywords:
                is_english_kw = all(ord(char) < 128 for char in p_kw) and any(char.isalpha() for char in p_kw)

                if is_english_kw: 
                    if p_kw in repo_name_lower or p_kw in repo_desc_lower:
                        is_political = True
                        logging.info(f"过滤政治内容 (英文匹配): {repo.get('full_name')} 因关键词 '{p_kw}'")
                        break
                else: 
                    if p_kw in repo_name_str or p_kw in repo_desc_str or \
                       p_kw in repo_name_lower or p_kw in repo_desc_lower: 
                        is_political = True
                        logging.info(f"过滤政治内容 (中文/混合匹配): {repo.get('full_name')} 因关键词 '{p_kw}'")
                        break
            
            if not is_political:
                # 只保留必要的字段
                repo_info = {
                    'full_name': repo['full_name'],
                    'description': repo['description'],
                    'html_url': repo['html_url'],
                    'stargazers_count': repo['stargazers_count'],
                    'forks_count': repo['forks_count'],
                    'open_issues_count': repo['open_issues_count'],
                    'pushed_at': repo.get('pushed_at'),
                    'created_at': repo.get('created_at'),
                    'updated_at': repo.get('updated_at'),
                }
                filtered_repos.append(repo_info)
                
        return filtered_repos
    
    # 为了保持与旧API的兼容性，保留这些方法，但将它们实现为调用新方法
    
    def get_keyword(self, text: str) -> ProcessResponse:
        """
        兼容性方法，调用新的generate_keywords方法，并格式化为旧的返回格式。
        """
        try:
            keywords = self.generate_keywords(text)
            # 分为主要关键词和建议关键词
            primary_keywords = keywords[:2] if len(keywords) >= 2 else keywords
            suggested_keywords = keywords[2:] if len(keywords) > 2 else []
            
            return ProcessResponse(
                code=200,
                message={
                    "primary_keywords": primary_keywords,
                    "suggested_keywords": suggested_keywords
                }
            )
        except Exception as e:
            return ProcessResponse(code=500, message=[f"Keywords generation failed: {str(e)}"])
    
    def search_github(self, 
                      keywords: List[str], 
                      language: str = None,
                      min_stars: int = None,
                      max_stars: int = None,
                      updated_after: str = None,
                      exclude_forks: bool = False,
                      max_results=10) -> ProcessResponse:
        """
        兼容性方法，调用新的search_github_repositories方法，但保留旧的参数。
        """
        try:
            # 简单地调用新方法，忽略大部分过滤参数
            repos = self.search_github_repositories(keywords, max_results)
            
            # 如果需要，这里可以添加其他过滤逻辑
            
            if not repos:
                return ProcessResponse(code=205, message=["No repositories found for the given criteria."])
            
            return ProcessResponse(code=200, message=repos)
        except Exception as e:
            return ProcessResponse(code=503, message=[f"GitHub search failed: {str(e)}"])