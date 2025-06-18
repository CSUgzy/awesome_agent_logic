"""
AwesomeAgent逻辑: 工具集

这个文件定义了AwesomeAgentLogic可以使用的各种工具。这些工具被设计为可以由大模型调用的函数，
每个工具都有明确的输入和输出，以及详细的文档说明。
"""

import logging
import requests
import re
import math
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Union, Tuple

# 设置日志
logger = logging.getLogger(__name__)

class GithubTools:
    """GitHub相关工具集"""
    
    @staticmethod
    def search_github_repositories(keywords: List[str], access_token: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        使用关键词搜索GitHub仓库

        Args:
            keywords: 搜索关键词列表
            access_token: GitHub API访问令牌
            limit: 每个关键词返回的最大结果数量

        Returns:
            List[Dict]: 包含仓库信息的字典列表
        """
        logger.info(f"搜索GitHub仓库，关键词: {keywords}")
        
        all_repos = []
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        for keyword in keywords:
            try:
                # 构建搜索查询，按星数排序
                query = f"{keyword} sort:stars"
                url = f"https://api.github.com/search/repositories?q={query}&per_page={limit}"
                
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                repos = response.json().get('items', [])
                all_repos.extend(repos)
                
                logger.info(f"关键词 '{keyword}' 返回 {len(repos)} 个结果")
                
                # 避免触发GitHub API限速
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"搜索关键词 '{keyword}' 失败: {e}")
        
        return all_repos
    
    @staticmethod
    def get_repo_details(repo_url: str, access_token: str) -> Dict[str, Any]:
        """
        获取GitHub仓库的详细信息

        Args:
            repo_url: GitHub仓库URL
            access_token: GitHub API访问令牌

        Returns:
            Dict: 包含仓库详细信息的字典
        """
        logger.info(f"获取仓库详情: {repo_url}")
        
        try:
            # 从URL提取用户名和仓库名
            match = re.search(r'github.com/([^/]+)/([^/]+)', repo_url)
            if not match:
                logger.error(f"无法从URL解析仓库信息: {repo_url}")
                return {}
            
            owner, repo = match.groups()
            
            # 请求仓库详情
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                'url': data['html_url'],
                'name': data['name'],
                'full_name': data['full_name'],
                'description': data.get('description', ''),
                'stars': data['stargazers_count'],
                'forks': data['forks_count'],
                'pushed_at': data['pushed_at'],
                'created_at': data['created_at'],
                'updated_at': data['updated_at'],
                'language': data.get('language')
            }
            
        except Exception as e:
            logger.error(f"获取仓库详情失败: {e}")
            return {}
    
    @staticmethod
    def calculate_repo_score(repo: Dict[str, Any]) -> float:
        """
        计算仓库分数

        评分公式: (0.7 * log(Stars + 1) + 0.3 * log(Forks + 1)) * RecencyScore

        Args:
            repo: 包含仓库信息的字典

        Returns:
            float: 计算得出的分数
        """
        try:
            stars = repo.get('stars', 0) or repo.get('stargazers_count', 0)
            forks = repo.get('forks', 0) or repo.get('forks_count', 0)
            pushed_at = repo.get('pushed_at', '')
            
            # 计算新近度分数
            recency_score = 0.1  # 默认很低
            if pushed_at:
                # 解析日期
                pushed_date = datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                days_diff = (datetime.utcnow() - pushed_date).days
                
                # 根据更新时间计算新近度得分
                if days_diff <= 30:  # 1个月内
                    recency_score = 1.0
                elif days_diff <= 180:  # 6个月内
                    recency_score = 0.8
                elif days_diff <= 365:  # 1年内
                    recency_score = 0.5
                elif days_diff <= 730:  # 2年内
                    recency_score = 0.2
                else:  # 超过2年
                    recency_score = 0.05
            
            # 计算综合分数
            score = (0.7 * math.log(stars + 1) + 0.3 * math.log(forks + 1)) * recency_score
            return score
            
        except Exception as e:
            logger.error(f"计算仓库分数失败: {e}")
            return 0.0


class WebTools:
    """网络搜索和处理工具集"""
    
    @staticmethod
    def search_web(query: str, tavily_api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        使用网络搜索查询相关内容

        Args:
            query: 搜索查询
            tavily_api_key: Tavily搜索API密钥(可选)

        Returns:
            List[Dict]: 搜索结果列表
        """
        logger.info(f"执行网络搜索: {query}")
        
        results = []
        
        # 如果提供了Tavily API密钥，尝试使用Tavily
        if tavily_api_key:
            try:
                from tavily import TavilyClient
                client = TavilyClient(api_key=tavily_api_key)
                
                response = client.search(query=query, search_depth="basic", max_results=5)
                for result in response.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("content", "")
                    })
                    
                if results:
                    return results
                    
            except Exception as e:
                logger.warning(f"Tavily搜索失败: {e}")
        
        # 回退到简单的DuckDuckGo搜索
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                for result in data.get("Results", []):
                    results.append({
                        "title": result.get("Text", ""),
                        "url": result.get("FirstURL", ""),
                        "snippet": ""
                    })
        except Exception as e:
            logger.error(f"DuckDuckGo搜索失败: {e}")
        
        return results
    
    @staticmethod
    def extract_github_links(url: str) -> List[str]:
        """
        从网页中提取GitHub仓库链接

        Args:
            url: 网页URL

        Returns:
            List[str]: 提取的GitHub仓库URL列表
        """
        logger.info(f"从URL提取GitHub链接: {url}")
        github_urls = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"获取页面失败，状态码: {response.status_code}")
                return []
                
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 正则表达式匹配GitHub仓库链接
            pattern = r'https?://github\.com/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-\._]+'
            
            # 查找所有链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                if re.match(pattern, href):
                    # 规范化URL
                    clean_url = re.sub(r'[#?].*$', '', href).rstrip('/')
                    if clean_url not in github_urls:
                        github_urls.append(clean_url)
            
            logger.info(f"从URL提取了 {len(github_urls)} 个GitHub链接")
            
        except Exception as e:
            logger.error(f"提取GitHub链接失败: {e}")
        
        return github_urls


class LLMTools:
    """大语言模型工具集"""
    
    @staticmethod
    def generate_keywords(domain: str, llm) -> List[str]:
        """
        使用LLM生成搜索关键词

        Args:
            domain: 用户感兴趣的领域
            llm: 大语言模型接口

        Returns:
            List[str]: 生成的关键词列表
        """
        logger.info(f"使用LLM为领域 '{domain}' 生成关键词")
        
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            prompt_template = """
            作为一名专业的搜索优化专家，请为用户提供的领域生成5-8个用于在GitHub上搜索高质量仓库的关键词或短语。

            用户感兴趣的领域是: "{domain}"

            请确保:
            1. 生成的关键词必须是英文的，无论用户输入什么语言
            2. 关键词应该多样化，覆盖不同的学习资源类型(如教程、指南、awesome列表、最佳实践等)
            3. 关键词应包括领域特定的术语

            如果用户输入的领域是中文或其他非英文语言，请先理解其含义，然后生成对应的英文关键词。

            请只返回一个JSON格式的关键词数组，不要包含任何解释或前导文本。
            格式示例:
            ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
            """
            
            prompt = PromptTemplate.from_template(prompt_template)
            chain = prompt | llm | StrOutputParser()
            
            result = chain.invoke({"domain": domain})
            
            # 清理结果
            cleaned_result = result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result.removeprefix("```json").removesuffix("```")
            elif cleaned_result.startswith("```"):
                cleaned_result = cleaned_result.removeprefix("```").removesuffix("```")
            
            # 解析JSON
            keywords = json.loads(cleaned_result)
            if not isinstance(keywords, list):
                raise ValueError("生成的关键词不是列表格式")
                
            return keywords
            
        except Exception as e:
            logger.error(f"生成关键词失败: {e}")
            # 返回基础关键词以确保流程继续
            return ["awesome repositories", "tutorial", "guide", "examples", "resources"]
    
    @staticmethod
    def generate_web_queries(domain: str, llm) -> List[str]:
        """
        使用LLM为网络搜索生成查询语句

        Args:
            domain: 用户感兴趣的领域
            llm: 大语言模型接口

        Returns:
            List[str]: 生成的查询语句列表
        """
        logger.info(f"使用LLM为领域 '{domain}' 生成网络搜索查询")
        
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            prompt_template = """
            作为一名搜索专家，你的任务是为寻找GitHub上优质仓库资源生成有效的网络搜索查询。
            
            用户对这个领域感兴趣: "{domain}"
            
            请生成3-5个不同的搜索查询，这些查询必须是英文的，无论用户输入的是什么语言。
            这些查询应该能帮助找到推荐GitHub仓库的高质量文章或资源列表。
            
            如果用户输入的领域是中文，请先理解该领域的含义，然后生成对应的英文搜索查询。
            
            查询应该多样化，覆盖不同角度，例如：
            - 寻找"最佳/顶级/推荐"仓库列表
            - 寻找学习路径或教程集合
            - 寻找专家推荐或精选资源
            
            可以使用一些简单的模板，如"best llm repositories github"。也使用更有针对性的搜索语句，但是语句应该尽量的短，最好不要超过5个词。
            考虑特定领域的术语和常见搜索模式。
            
            你的输出必须是一个JSON格式的字符串数组，仅包含生成的英文查询，不要有额外的解释。
            
            示例输出格式:
            ["machine learning github repositories", "top rated deep learning frameworks", "github collections for AI beginners"]
            """
            
            prompt = PromptTemplate.from_template(prompt_template)
            chain = prompt | llm | StrOutputParser()
            
            result = chain.invoke({"domain": domain})
            
            # 清理结果
            cleaned_result = result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result.removeprefix("```json").removesuffix("```")
            elif cleaned_result.startswith("```"):
                cleaned_result = cleaned_result.removeprefix("```").removesuffix("```")
            
            # 解析JSON
            queries = json.loads(cleaned_result)
            if not isinstance(queries, list):
                raise ValueError("生成的查询不是列表格式")
                
            return queries
            
        except Exception as e:
            logger.error(f"生成网络搜索查询失败: {e}")
            # 返回基础查询以确保流程继续
            return [
                f"best github repositories for {domain}",
                f"top {domain} projects on github",
                f"recommended {domain} libraries github"
            ]
    
    @staticmethod
    def generate_final_report(repos: List[Dict], domain: str, llm) -> str:
        """
        使用LLM为排序后的仓库生成最终报告

        Args:
            repos: 排序后的仓库信息列表
            domain: 用户感兴趣的领域
            llm: 大语言模型接口

        Returns:
            str: Markdown格式的最终报告
        """
        logger.info(f"使用LLM为 {len(repos)} 个仓库生成最终报告")
        
        try:
            from langchain_core.prompts import PromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            # 格式化仓库信息
            repos_text = ""
            for i, repo in enumerate(repos[:5], 1):  # 只取前5个
                # 格式化日期
                pushed_at = repo.get('pushed_at', '')
                if pushed_at:
                    try:
                        date = datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                        pushed_at = date.strftime("%Y年%m月%d日")
                    except:
                        pass
                
                repos_text += f"## 仓库 {i}\n"
                repos_text += f"名称: {repo.get('full_name', 'Unknown')}\n"
                repos_text += f"URL: {repo.get('url', '')}\n"
                repos_text += f"描述: {repo.get('description', '')}\n"
                repos_text += f"Stars: {repo.get('stars', 0)}\n"
                repos_text += f"Forks: {repo.get('forks', 0)}\n"
                repos_text += f"最近更新: {pushed_at}\n"
                repos_text += f"主要语言: {repo.get('language', 'Unknown')}\n\n"
            
            prompt_template = """
            你是一位专业的AI技术分析师。你的任务是为用户准备一份关于"{domain}"领域的顶尖 GitHub 学习资源报告。

            我已经为你提供了排名最高的 {top_n} 个仓库的详细信息（名称、URL、描述、Star数、Fork数、最近更新时间）。

            **仓库信息**:
            {ranked_top_n_repos_details}

            请根据以上信息，生成一份精炼、易读的 Markdown 格式报告，要严格符合markdown的语法。报告应包含以下要素：

            1.  一个引人注目的标题，点明报告主题（例如：" Top 5 GitHub 宝藏项目推荐）。
            2.  一段简短的引言，说明这份报告是如何通过多维度评估得出的，强调其客观性和时效性。
            3.  对每一个推荐仓库的独立介绍，包括：
                - **项目名称和链接**: 作为二级或三级标题。
                - **核心指标**: `Stars`, `Forks`, `最近更新`。
                - **一句话总结**: 精准概括这个项目是什么。
                - **推荐理由**: 详细解释为什么这个项目值得关注。它解决了什么问题？是教程、工具还是资源库？（例如："这是一个官方维护的入门指南，内容权威且更新频繁，非常适合初学者。"或"该项目提供了一套完整的最佳实践，可以帮助开发者在生产环境中避免常见错误。"）
            4.  一个总结性的结尾，鼓励用户探索这些资源。

            报告必须使用清晰、专业的语言撰写，并以用户的视角出发，重点突出每个项目的实际价值，要严格符合markdown的语法。
            """
            
            # 填充提示词模板
            prompt = PromptTemplate.from_template(prompt_template)
            chain = prompt | llm | StrOutputParser()
            
            report = chain.invoke({
                "domain": domain,
                "top_n": min(5, len(repos)),
                "ranked_top_n_repos_details": repos_text
            })
            
            return report
            
        except Exception as e:
            logger.error(f"生成最终报告失败: {e}")
            
            # 创建一个基本的报告作为后备
            report = f"# {domain} 领域 GitHub 优质资源推荐\n\n"
            report += "## 简介\n\n"
            report += f"本报告为您精选了 {domain} 领域中最具价值的GitHub仓库，基于Star数量、Fork数量和更新频率等多维度指标进行评估和排序。\n\n"
            
            for i, repo in enumerate(repos[:5], 1):
                pushed_at = repo.get('pushed_at', '')
                if pushed_at:
                    try:
                        date = datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                        pushed_at = date.strftime("%Y年%m月%d日")
                    except:
                        pass
                        
                report += f"## {i}. {repo.get('full_name', 'Unknown')}\n\n"
                report += f"**链接**: {repo.get('url', '')}\n\n"
                report += f"**描述**: {repo.get('description', '')}\n\n"
                report += f"**核心指标**: ⭐ {repo.get('stars', 0)} | 🍴 {repo.get('forks', 0)} | 📅 {pushed_at}\n\n"
                report += f"**主要语言**: {repo.get('language', 'Unknown')}\n\n"
                report += "---\n\n"
            
            report += "## 总结\n\n"
            report += f"以上就是我们为您精选的 {domain} 领域优质GitHub资源。这些项目经过精心筛选，涵盖了从入门到进阶的多种资源。希望这份推荐能够帮助您更深入地学习和探索此领域。\n"
            
            return report 