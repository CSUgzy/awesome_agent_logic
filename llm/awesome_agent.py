import logging
from typing import List, Dict, Tuple, Any
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures
import re
import math
from datetime import datetime, timedelta
import time

from llm.llm_agent import Agent

class AwesomeAgent:
    """
    AwesomeAgent类实现了一个完整的五步工作流，用于从GitHub和网络上搜集、评估和排序
    高质量的资源库，并生成一份精炼的报告。
    
    工作流程:
    1. 任务理解与关键词生成: 基于用户输入的领域生成多样化的搜索关键词
    2. 并行信息采集: 同时从GitHub和网络文章中收集资源
    3. 信息清洗与候选池构建: 合并和去重收集到的GitHub仓库链接
    4. 统一量化评估与排序: 根据Star数、Fork数和更新时间等指标对仓库进行评分和排序
    5. 结果提炼与报告生成: 为排名最高的仓库生成一份结构化的Markdown报告
    """
    
    def __init__(self):
        """
        初始化AwesomeAgent实例。
        设置日志记录器和其他必要的工具。
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # 确保日志有处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        # 初始化工具集
        self.agent = Agent()
            
        self.logger.info("AwesomeAgent初始化完成")
    
    def step_1_generate_keywords(self, domain: str) -> List[str]:
        """
        第1步: 任务理解与关键词生成
        
        根据用户输入的领域，生成一个多样化的GitHub搜索关键词列表。
        使用LLM来确保关键词覆盖不同类型的资源(教程、指南、路线图等)。
        
        Args:
            domain (str): 用户感兴趣的领域，例如"容器化技术"或"量化金融"
            
        Returns:
            List[str]: 生成的关键词列表，例如["docker tutorial", "kubernetes guide"]
        """
        self.logger.info(f"开始为领域 '{domain}' 生成关键词")
        
        try:
            # 直接调用Agent中的generate_keywords方法，它已经能处理中英文输入并生成英文关键词
            keywords = self.agent.generate_keywords(domain)
            
            if not keywords:
                self.logger.warning(f"未能为领域 '{domain}' 生成关键词，使用默认关键词")
                # 尝试使用一些通用关键词模板
                # 由于我们不确定domain是什么语言，这里可能不是最佳解决方案
                # 但作为备用方案，确保流程可以继续
                keywords = [
                    "tutorial", 
                    "guide", 
                    "awesome repositories", 
                    "best practices", 
                    "examples"
                ]
            
            self.logger.info(f"成功生成 {len(keywords)} 个关键词: {keywords}")
            return keywords
            
        except Exception as e:
            self.logger.error(f"生成关键词时出错: {e}")
            # 出错时返回一些基本的通用关键词，确保流程可以继续
            return ["awesome repositories", "tutorial", "guide", "examples", "resources"]
    
    def step_2_parallel_gather_info(self, keywords: List[str], domain: str) -> Tuple[List[Any], List[str]]:
        """
        第2步: 并行信息采集
        
        同时从两个渠道收集信息:
        1. GitHub内部搜索: 使用生成的关键词直接搜索GitHub
        2. 互联网外部搜索: 查找推荐GitHub仓库的高质量文章
        
        Args:
            keywords (List[str]): 第1步生成的关键词列表
            domain (str): 原始领域名称，用于构建网络搜索查询
            
        Returns:
            Tuple[List[Any], List[str]]: 包含两部分:
                1. GitHub直接搜索结果列表
                2. 相关文章URL列表
        """
        self.logger.info(f"开始并行收集信息，使用{len(keywords)}个关键词")
        
        # 使用线程池并行执行GitHub搜索和网络搜索
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 提交GitHub搜索任务
            github_future = executor.submit(self._search_github, keywords)
            
            # 提交网络搜索任务 - 直接使用原始domain，generate_web_search_queries方法会处理语言
            web_future = executor.submit(self._search_web, domain)
            
            # 获取结果
            github_results = github_future.result()
            web_urls = web_future.result()
        
        self.logger.info(f"并行收集完成: 获取了 {len(github_results)} 个GitHub仓库和 {len(web_urls)} 个网页URL")
        return github_results, web_urls
    
    def _search_github(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        使用关键词在GitHub上搜索仓库
        
        Args:
            keywords (List[str]): 关键词列表
            
        Returns:
            List[Dict[str, Any]]: GitHub仓库列表
        """
        self.logger.info(f"开始搜索GitHub，使用关键词: {keywords}")
        
        try:
            # 调用Agent中的search_github_repositories方法
            repos = self.agent.search_github_repositories(keywords)
            self.logger.info(f"GitHub搜索完成，找到 {len(repos)} 个仓库")
            return repos
        except Exception as e:
            self.logger.error(f"GitHub搜索失败: {e}")
            return []
    
    def _search_web(self, domain: str) -> List[str]:
        """
        在网络上搜索与领域相关的文章，这些文章可能推荐了GitHub仓库
        
        Args:
            domain (str): 用户感兴趣的领域（已翻译为英文）
            
        Returns:
            List[str]: 文章URL列表
        """
        self.logger.info(f"开始网络搜索，领域: {domain}")
        
        # 生成针对性的搜索查询，而不是简单拼接
        search_queries = self._generate_web_search_queries(domain)
        
        article_urls = []
        
        try:
            # 尝试使用tavily API进行搜索（如果安装了tavily）
            try:
                from tavily import TavilyClient
                from config import Config
                CFG = Config()
                
                if hasattr(CFG, 'tavily_api_key') and CFG.tavily_api_key:
                    self.logger.info("使用Tavily API进行网络搜索")
                    client = TavilyClient(api_key=CFG.tavily_api_key)
                    
                    for query in search_queries:
                        try:
                            response = client.search(query=query, search_depth="basic", max_results=3)
                            for result in response.get("results", []):
                                if "url" in result and result["url"] not in article_urls:
                                    article_urls.append(result["url"])
                            
                            if len(article_urls) >= 5:
                                break
                        except Exception as e:
                            self.logger.error(f"Tavily搜索查询 '{query}' 出错: {e}")
                    
                    if article_urls:
                        self.logger.info(f"Tavily搜索完成，找到 {len(article_urls)} 个文章URL")
                        return article_urls[:5]  # 限制最多返回5个URL
            except ImportError:
                self.logger.warning("未安装tavily库，将使用替代搜索方法")
            
            # 如果tavily不可用或失败，使用DuckDuckGo搜索
            if not article_urls:
                self.logger.info("使用DuckDuckGo API进行网络搜索")
                for query in search_queries:
                    try:
                        url = f"https://api.duckduckgo.com/?q={query}&format=json"
                        response = requests.get(url)
                        
                        if response.status_code == 200:
                            # 解析结果
                            results = response.json()
                            
                            # 提取搜索结果中的URL
                            for result in results.get("Results", []):
                                if "FirstURL" in result and result["FirstURL"] not in article_urls:
                                    article_urls.append(result["FirstURL"])
                            
                            # 限制每个查询最多5个结果
                            if len(article_urls) >= 10:
                                break
                        else:
                            self.logger.warning(f"搜索查询 '{query}' 返回状态码 {response.status_code}")
                    
                    except Exception as e:
                        self.logger.error(f"执行DuckDuckGo搜索时出错: {e}")
        
        except Exception as e:
            self.logger.error(f"网络搜索过程中发生错误: {e}")
        
        # 如果搜索API都失败，使用一些常见的技术博客作为备份
        if not article_urls:
            self.logger.warning("网络搜索未返回结果，使用默认技术博客")
            article_urls = [
                "https://medium.com/topics/programming",
                "https://dev.to/",
                "https://github.blog/",
                "https://www.freecodecamp.org/news/"
            ]
        
        self.logger.info(f"网络搜索完成，找到 {len(article_urls)} 个文章URL")
        return article_urls[:5]  # 确保最多返回5个URL
    
    def _generate_web_search_queries(self, domain: str) -> List[str]:
        """
        为网络搜索生成专门的查询语句，避免简单的领域拼接
        
        Args:
            domain (str): 用户感兴趣的领域（可以是中文或英文）
            
        Returns:
            List[str]: 生成的搜索查询列表
        """
        self.logger.info(f"为领域 '{domain}' 生成网络搜索查询")
        
        try:
            # 使用LLM生成查询
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
            chain = prompt | self.agent.llm | StrOutputParser()
            
            raw_res = chain.invoke({"domain": domain})
            
            # 清理响应，确保是有效的JSON
            cleaned_res_str = raw_res.strip()
            if cleaned_res_str.startswith("```json"):
                cleaned_res_str = cleaned_res_str.removeprefix("```json").removesuffix("```")
            elif cleaned_res_str.startswith("```"):
                cleaned_res_str = cleaned_res_str.removeprefix("```").removesuffix("```")
            
            # 解析查询列表
            queries = json.loads(cleaned_res_str)
            
            if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
                raise ValueError("Generated queries are not a list of strings.")
                
            self.logger.info(f"成功生成搜索查询: {queries}")
            return queries
            
        except Exception as e:
            self.logger.error(f"生成搜索查询时出错: {e}")
            # 出错时返回一些基本的查询模板，确保流程可以继续
            return [
                "best github repositories",
                "github learning resources",
                "top github projects",
                "recommended github libraries"
            ]
    
    def step_3_build_candidate_pool(self, github_results: List[Any], web_urls: List[str]) -> List[str]:
        """
        第3步: 信息清洗与候选池构建
        
        处理从不同渠道收集的原始数据:
        1. 从文章URL中提取GitHub仓库链接
        2. 合并直接搜索结果和从文章中提取的链接
        3. 执行去重，确保每个仓库只出现一次
        
        Args:
            github_results (List[Any]): 从GitHub直接搜索得到的结果
            web_urls (List[str]): 相关文章的URL列表
            
        Returns:
            List[str]: 去重后的GitHub仓库URL列表
        """
        self.logger.info(f"开始构建候选池，处理{len(web_urls)}个文章URL")
        
        # 第1步: 从GitHub直接搜索结果中提取URLs
        github_urls = []
        for repo in github_results:
            url = repo.get('html_url')
            if url and self._is_valid_github_repo_url(url):
                github_urls.append(url)
        
        self.logger.info(f"从GitHub搜索结果中提取了 {len(github_urls)} 个有效仓库URL")
        
        # 第2步: 从网页中提取GitHub仓库链接
        extracted_urls = []
        
        for url in web_urls:
            try:
                web_repo_urls = self._extract_github_urls_from_webpage(url)
                extracted_urls.extend(web_repo_urls)
                # 避免请求过于频繁
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"从URL '{url}' 提取GitHub链接时出错: {e}")
        
        self.logger.info(f"从网页中提取了 {len(extracted_urls)} 个GitHub仓库链接")
        
        # 第3步: 合并所有URL并去重
        all_urls = github_urls + extracted_urls
        unique_urls = list(set(all_urls))
        
        # 第4步: 格式化和验证
        candidate_pool = []
        for url in unique_urls:
            normalized_url = self._normalize_github_url(url)
            if normalized_url and normalized_url not in candidate_pool:
                candidate_pool.append(normalized_url)
        
        self.logger.info(f"最终候选池包含 {len(candidate_pool)} 个唯一的GitHub仓库")
        return candidate_pool
    
    def _extract_github_urls_from_webpage(self, url: str) -> List[str]:
        """
        从网页内容中提取GitHub仓库链接，每个网页最多提取5个链接
        
        Args:
            url (str): 要抓取的网页URL
            
        Returns:
            List[str]: 提取的GitHub仓库URL列表（最多5个）
        """
        github_urls = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.warning(f"获取 '{url}' 失败，状态码: {response.status_code}")
                return []
                
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            for link in soup.find_all('a', href=True):
                href = link['href']
                # 检查是否是GitHub仓库链接
                if self._is_valid_github_repo_url(href):
                    github_urls.append(href)
                    # 达到5个链接后停止提取
                    if len(github_urls) >= 5:
                        self.logger.info(f"从URL '{url}' 已提取5个GitHub链接，停止提取")
                        break
            
            self.logger.info(f"从URL '{url}' 提取了 {len(github_urls)} 个GitHub链接")
            return github_urls
            
        except Exception as e:
            self.logger.error(f"抓取URL '{url}' 时出错: {e}")
            return []
    
    def _is_valid_github_repo_url(self, url: str) -> bool:
        """
        检查URL是否是有效的GitHub仓库链接
        
        Args:
            url (str): 要检查的URL
            
        Returns:
            bool: 是否是有效的GitHub仓库URL
        """
        # 简单的正则表达式检查
        pattern = r'https?://github\.com/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-\._]+/?$'
        return bool(re.match(pattern, url))
    
    def _normalize_github_url(self, url: str) -> str:
        """
        规范化GitHub URL，移除尾部斜杠和不必要的参数
        
        Args:
            url (str): 原始GitHub URL
            
        Returns:
            str: 规范化后的URL，或者空字符串(如果无效)
        """
        # 检查基本模式
        basic_pattern = r'https?://github\.com/[a-zA-Z0-9\-]+/[a-zA-Z0-9\-\._]+'
        if not re.match(basic_pattern, url):
            return ""
            
        # 移除URL参数和锚点
        clean_url = re.sub(r'[#?].*$', '', url)
        
        # 移除尾部斜杠
        clean_url = clean_url.rstrip('/')
        
        return clean_url
    
    def step_4_evaluate_and_rank(self, candidate_pool: List[str]) -> List[Dict]:
        """
        第4步: 统一量化评估与排序
        
        对候选池中的每个仓库进行量化评估:
        1. 获取每个仓库的详细元数据(Star数、Fork数、最近更新日期)
        2. 应用评分公式计算综合分数
        3. 根据分数对仓库进行排序
        
        评分公式: (0.7 * log(Stars + 1) + 0.3 * log(Forks + 1)) * RecencyScore
        
        Args:
            candidate_pool (List[str]): 候选GitHub仓库URL列表
            
        Returns:
            List[Dict]: 包含排序后的仓库详情的字典列表，每个字典包含:
                - url: 仓库URL
                - name: 仓库名称
                - description: 仓库描述
                - stars: Star数量
                - forks: Fork数量
                - pushed_at: 最近更新时间
                - score: 计算的综合分数
        """
        self.logger.info(f"开始评估和排序{len(candidate_pool)}个候选仓库")
        
        # 获取每个仓库的详细信息
        repos_with_metadata = []
        
        for url in candidate_pool:
            try:
                # 从URL中提取用户和仓库名
                parts = url.split('/')
                if len(parts) >= 5:
                    owner = parts[-2]
                    repo_name = parts[-1]
                    
                    # 获取仓库详细信息
                    repo_data = self._get_github_repo_metadata(owner, repo_name)
                    
                    if repo_data:
                        repos_with_metadata.append(repo_data)
                else:
                    self.logger.warning(f"无法从URL '{url}' 解析出所有者和仓库名")
            
            except Exception as e:
                self.logger.error(f"获取仓库 '{url}' 的元数据时出错: {e}")
            
            # 避免API限速
            time.sleep(0.5)
        
        self.logger.info(f"成功获取 {len(repos_with_metadata)} 个仓库的元数据")
        
        # 计算每个仓库的分数
        ranked_repos = []
        for repo in repos_with_metadata:
            if 'stargazers_count' in repo and 'forks_count' in repo and 'pushed_at' in repo:
                # 计算新近度分数
                recency_score = self._calculate_recency_score(repo['pushed_at'])
                
                # 计算综合分数
                comprehensive_score = (
                    0.7 * math.log(repo['stargazers_count'] + 1) + 
                    0.3 * math.log(repo['forks_count'] + 1)
                ) * recency_score
                
                # 添加分数到仓库数据
                repo['score'] = comprehensive_score
                ranked_repos.append(repo)
            else:
                self.logger.warning(f"仓库 '{repo.get('full_name', 'unknown')}' 缺少评分所需的字段")
        
        # 按分数降序排序
        ranked_repos.sort(key=lambda x: x['score'], reverse=True)
        
        self.logger.info(f"评估和排序完成，返回 {len(ranked_repos)} 个排序后的仓库")
        return ranked_repos
    
    def _get_github_repo_metadata(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        从GitHub API获取仓库的详细元数据
        
        Args:
            owner (str): 仓库所有者
            repo (str): 仓库名称
            
        Returns:
            Dict[str, Any]: 仓库元数据，包含name, description, stars, forks, pushed_at等
        """
        from config import Config
        CFG = Config()
        
        url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            'Authorization': f'token {CFG.github_access_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            return {
                'url': data['html_url'],
                'name': data['name'],
                'full_name': data['full_name'],
                'description': data.get('description', ''),
                'stargazers_count': data['stargazers_count'],
                'forks_count': data['forks_count'],
                'pushed_at': data['pushed_at'],
                'created_at': data['created_at'],
                'updated_at': data['updated_at'],
                'language': data.get('language')
            }
            
        except Exception as e:
            self.logger.error(f"获取仓库 '{owner}/{repo}' 的元数据失败: {e}")
            return {}
    
    def _calculate_recency_score(self, pushed_at_str: str) -> float:
        """
        根据最近推送日期计算新近度分数
        
        新近度评分:
        - 1个月内更新: 1.0
        - 6个月内更新: 0.8
        - 1年内更新: 0.5
        - 2年内更新: 0.2
        - 超过2年未更新: 0.05
        
        Args:
            pushed_at_str (str): 最近推送日期字符串，ISO 8601格式
            
        Returns:
            float: 新近度分数 (0.05-1.0)
        """
        try:
            # 解析日期
            pushed_at = datetime.strptime(pushed_at_str, "%Y-%m-%dT%H:%M:%SZ")
            now = datetime.utcnow()
            
            # 计算天数差异
            days_diff = (now - pushed_at).days
            
            # 评分逻辑
            if days_diff <= 30:  # 1个月内
                return 1.0
            elif days_diff <= 180:  # 6个月内
                return 0.8
            elif days_diff <= 365:  # 1年内
                return 0.5
            elif days_diff <= 730:  # 2年内
                return 0.2
            else:  # 超过2年
                return 0.05
                
        except Exception as e:
            self.logger.error(f"计算新近度分数时出错: {e}")
            return 0.1  # 出错时返回一个低分
    
    def step_5_generate_report(self, ranked_repos: List[Dict], domain: str) -> str:
        """
        第5步: 结果提炼与报告生成
        
        选取排名最高的仓库，并生成一份高质量的Markdown格式报告:
        1. 选择排名最高的N个仓库(默认为5个)
        2. 使用LLM生成一份结构化的报告，强调每个仓库的价值和特点
        
        Args:
            ranked_repos (List[Dict]): 排序后的仓库详情列表
            domain (str): 用户原始查询的领域
            
        Returns:
            str: Markdown格式的最终报告
        """
        self.logger.info("开始生成最终报告")
        
        # 选取排名最高的仓库（默认5个，如果不足则全部选取）
        top_n = 5
        top_repos = ranked_repos[:min(top_n, len(ranked_repos))]
        
        if not top_repos:
            self.logger.warning("没有可用的仓库来生成报告")
            return f"# {domain} 领域GitHub资源推荐\n\n很遗憾，我们未能找到符合要求的高质量GitHub仓库。请尝试使用其他关键词或领域。"
        
        self.logger.info(f"为报告选择了排名最高的 {len(top_repos)} 个仓库")
        
        # 格式化仓库信息，准备传递给LLM
        repos_details = []
        for repo in top_repos:
            # 格式化日期
            pushed_at = self._format_date(repo.get('pushed_at', ''))
            
            # 创建详细信息
            repo_detail = {
                "name": repo.get('name', 'Unknown'),
                "full_name": repo.get('full_name', 'Unknown'),
                "url": repo.get('url', ''),
                "description": repo.get('description', 'No description available'),
                "stars": repo.get('stargazers_count', 0),
                "forks": repo.get('forks_count', 0),
                "pushed_at": pushed_at,
                "language": repo.get('language', 'Unknown')
            }
            repos_details.append(repo_detail)
        
        # 准备LLM提示词
        report_prompt = self._create_report_prompt(domain, repos_details)
        
        try:
            # 调用LLM生成报告
            final_report = self._generate_report_with_llm(report_prompt)
            self.logger.info("最终报告生成成功")
            return final_report
        except Exception as e:
            self.logger.error(f"生成报告时出错: {e}")
            # 如果LLM调用失败，生成一个基本的报告
            return self._create_basic_report(domain, repos_details)
    
    def _format_date(self, date_str: str) -> str:
        """格式化ISO 8601日期字符串为更友好的格式"""
        if not date_str:
            return "未知日期"
        
        try:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return date.strftime("%Y年%m月%d日")
        except Exception:
            return date_str
    
    def _create_report_prompt(self, domain: str, repos_details: List[Dict]) -> str:
        """
        创建用于生成报告的LLM提示词
        
        Args:
            domain (str): 用户查询的领域
            repos_details (List[Dict]): 排名最高的仓库详细信息
            
        Returns:
            str: 格式化的提示词
        """
        # 转换仓库详情为格式化文本
        repos_text = ""
        for i, repo in enumerate(repos_details, 1):
            repos_text += f"## 仓库 {i}\n"
            repos_text += f"名称: {repo['full_name']}\n"
            repos_text += f"URL: {repo['url']}\n"
            repos_text += f"描述: {repo['description']}\n"
            repos_text += f"Stars: {repo['stars']}\n"
            repos_text += f"Forks: {repo['forks']}\n"
            repos_text += f"最近更新: {repo['pushed_at']}\n"
            repos_text += f"主要语言: {repo['language']}\n\n"
        
        # 使用prompt.md中为第5步设计的提示词模板
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
        prompt = prompt_template.replace("{domain}", domain)
        prompt = prompt.replace("{top_n}", str(len(repos_details)))
        prompt = prompt.replace("{ranked_top_n_repos_details}", repos_text)
        
        return prompt
    
    def _generate_report_with_llm(self, prompt: str) -> str:
        """
        使用LLM生成最终报告
        
        Args:
            prompt (str): 提示词
            
        Returns:
            str: 生成的Markdown报告
        """
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        # 创建提示词模板
        prompt_template = PromptTemplate.from_template("{prompt}")
        
        # 设置输出解析器
        output_parser = StrOutputParser()
        
        # 创建链
        chain = prompt_template | self.agent.llm | output_parser
        
        # 调用LLM
        report = chain.invoke({"prompt": prompt})
        
        return report
    
    def _create_basic_report(self, domain: str, repos_details: List[Dict]) -> str:
        """
        在LLM调用失败时创建一个基本的报告
        
        Args:
            domain (str): 用户查询的领域
            repos_details (List[Dict]): 仓库详细信息
            
        Returns:
            str: 基本的Markdown报告
        """
        report = f"# {domain} 领域 GitHub 优质资源推荐\n\n"
        
        report += "## 简介\n\n"
        report += f"本报告为您精选了 {domain} 领域中最具价值的GitHub仓库，基于Star数量、Fork数量和更新频率等多维度指标进行评估和排序。\n\n"
        
        for i, repo in enumerate(repos_details, 1):
            report += f"## {i}. {repo['full_name']}\n\n"
            report += f"**链接**: {repo['url']}\n\n"
            report += f"**描述**: {repo['description']}\n\n"
            report += f"**核心指标**: ⭐ {repo['stars']} | 🍴 {repo['forks']} | 📅 {repo['pushed_at']}\n\n"
            report += f"**主要语言**: {repo['language']}\n\n"
            report += "---\n\n"
        
        report += "## 总结\n\n"
        report += f"以上就是我们为您精选的 {domain} 领域优质GitHub资源。这些项目经过精心筛选，涵盖了从入门到进阶的多种资源。希望这份推荐能够帮助您更深入地学习和探索此领域。\n"
        
        return report
    
    def run(self, domain: str) -> str:
        """
        执行完整的五步工作流。
        
        这是用户交互的主要入口点。接收一个领域，按顺序执行所有五个步骤，
        每一步的输出作为下一步的输入，最终返回生成的报告。
        
        Args:
            domain (str): 用户感兴趣的领域
            
        Returns:
            str: 最终生成的Markdown格式报告
        """
        self.logger.info(f"开始为领域 '{domain}' 执行完整的Awesome Agent工作流")
        
        # 执行第1步: 任务理解与关键词生成
        keywords = self.step_1_generate_keywords(domain)
        self.logger.info(f"第1步完成，生成了{len(keywords)}个关键词")
        
        # 执行第2步: 并行信息采集
        github_results, web_urls = self.step_2_parallel_gather_info(keywords, domain)
        self.logger.info(f"第2步完成，获取了{len(github_results)}个GitHub结果和{len(web_urls)}个网页URL")
        
        # 执行第3步: 信息清洗与候选池构建
        candidate_pool = self.step_3_build_candidate_pool(github_results, web_urls)
        self.logger.info(f"第3步完成，构建了包含{len(candidate_pool)}个仓库的候选池")
        
        # 执行第4步: 统一量化评估与排序
        ranked_repos = self.step_4_evaluate_and_rank(candidate_pool)
        self.logger.info(f"第4步完成，评估并排序了{len(ranked_repos)}个仓库")
        
        # 执行第5步: 结果提炼与报告生成
        final_report = self.step_5_generate_report(ranked_repos, domain)
        self.logger.info("第5步完成，生成了最终报告")
        
        return final_report 