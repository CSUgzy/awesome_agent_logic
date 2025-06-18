"""
AwesomeAgent逻辑: 代理核心

这个文件实现了一个以大模型为核心的代理，它能够理解用户请求、决定工作流程、
调用适当的工具，并在整个过程中做出智能决策。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import re
import time

from config import Config
from llm.awesome_agent_logic.tools import GithubTools, WebTools, LLMTools

# 设置日志
logger = logging.getLogger(__name__)

class AwesomeAgentLogic:
    """
    AwesomeAgentLogic 是一个以大模型为核心的代理，用于高质量GitHub资源搜索与推荐。
    
    不同于基于固定工作流的AwesomeAgent，这个Logic版本使用大模型来决定:
    1. 需要执行哪些步骤
    2. 什么时候执行这些步骤
    3. 如何使用工具
    4. 如何解释结果
    
    这种方法使得代理更加灵活，能够适应各种情况，并且能够解释其决策过程。
    """
    
    def __init__(self, llm=None):
        """
        初始化AwesomeAgentLogic实例
        
        Args:
            llm: 大语言模型实例，用于代理决策
        """
        self.logger = logger
        self.logger.setLevel(logging.INFO)
        
        # 确保有日志处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            
        # 加载配置
        self.config = Config()
        
        # 初始化LLM
        if llm:
            self.llm = llm
        else:
            # 如果没有提供LLM，使用默认的Agent中的LLM
            from llm.llm_agent import Agent
            agent = Agent()
            self.llm = agent.llm
            
        # 工具集合
        self.github_tools = GithubTools()
        self.web_tools = WebTools()
        self.llm_tools = LLMTools()
        
        # 存储标志
        self.history = []
        self.last_action = None
        
        self.logger.info("AwesomeAgentLogic初始化完成")
    
    def run(self, domain: str) -> str:
        """
        执行由LLM控制的代理逻辑，搜索给定领域的高质量GitHub仓库
        
        Args:
            domain: 用户感兴趣的领域或主题
            
        Returns:
            str: Markdown格式的最终报告
        """
        self.logger.info(f"开始为领域 '{domain}' 执行AwesomeAgentLogic")
        
        # 记录开始时间
        start_time = time.time()
        
        # 清空历史记录
        self.history = []
        self.last_action = None
        
        try:
            # 初始化会话并获取LLM的首次执行计划
            plan = self._plan_execution(domain)
            self.logger.info(f"LLM执行计划: {plan}")
            
            # 创建工作状态字典，保存整个过程中的数据
            state = {
                "domain": domain,
                "keywords": [],
                "github_repos": [],
                "web_search_results": [],
                "candidate_repos": [],
                "ranked_repos": [],
                "final_report": ""
            }
            
            # 执行循环，由LLM决定下一步行动，直到完成
            max_iterations = 10  # 防止无限循环
            iterations = 0
            
            while iterations < max_iterations:
                iterations += 1
                
                # 让LLM决定下一步行动
                action, params = self._decide_next_action(domain, state)
                
                if action == "COMPLETE":
                    self.logger.info("LLM决定任务已完成")
                    break
                    
                # 执行LLM选择的行动，并更新状态
                result = self._execute_action(action, params, state)
                state = self._update_state(state, action, result)
                
                # 记录历史
                self.history.append({
                    "action": action,
                    "params": params,
                    "result_summary": self._summarize_result(result)
                })
                self.last_action = action
                
                self.logger.info(f"完成行动: {action}, 进度: {iterations}/{max_iterations}")
            
            # 如果没有最终报告，生成一个
            if not state.get("final_report") and state.get("ranked_repos"):
                state["final_report"] = self.llm_tools.generate_final_report(
                    state["ranked_repos"], domain, self.llm
                )
                
            # 记录总用时
            total_time = time.time() - start_time
            self.logger.info(f"任务完成，总用时: {total_time:.2f}秒")
            
            return state.get("final_report", f"未能为 '{domain}' 找到相关的GitHub仓库。")
            
        except Exception as e:
            self.logger.error(f"执行过程中出错: {e}")
            return f"搜索过程中出错: {str(e)}"
    
    def _plan_execution(self, domain: str) -> str:
        """
        让LLM根据用户提供的领域规划执行步骤
        
        Args:
            domain: 用户感兴趣的领域
            
        Returns:
            str: LLM的执行计划
        """
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        
        prompt_template = """
        你是一个精通GitHub资源搜索和评估的AI助手。用户希望你帮助他们为这个领域找到最好的GitHub仓库: "{domain}"。
        
        你可以使用以下工具:
        1. 生成关键词 - 为GitHub搜索生成相关的英文关键词
        2. 搜索GitHub - 使用关键词在GitHub上搜索仓库
        3. 生成网络搜索查询 - 创建网络搜索查询来寻找推荐仓库的文章
        4. 搜索网络 - 使用查询搜索网页
        5. 提取GitHub链接 - 从网页中提取GitHub仓库URL
        6. 获取仓库详情 - 获取特定GitHub仓库的完整元数据
        7. 计算仓库分数 - 根据多种指标为仓库评分
        8. 生成最终报告 - 为用户创建Markdown格式的最终报告
        
        请制定一个执行计划，描述你将如何使用这些工具来找到最优质的GitHub仓库，并为用户生成一份报告。
        
        回答格式:
        
        执行计划:
        1. [首先我会做什么]
        2. [然后我会做什么]
        ...
        """
        
        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()
        
        return chain.invoke({"domain": domain})
    
    def _decide_next_action(self, domain: str, state: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        让LLM决定下一步行动
        
        Args:
            domain: 用户感兴趣的领域
            state: 当前的工作状态
            
        Returns:
            Tuple[str, Dict]: 行动名称和参数
        """
        from langchain_core.prompts import PromptTemplate
        
        # 准备当前状态的摘要
        state_summary = self._format_state_summary(state)
        history_summary = self._format_history_summary()
        
        prompt_template = """
        你是一个精通GitHub资源搜索和评估的AI助手。你正在帮助用户为这个领域寻找最好的GitHub仓库: "{domain}"。
        
        当前的状态:
        {state_summary}
        
        已执行的操作历史:
        {history_summary}
        
        可用的行动:
        1. GENERATE_KEYWORDS - 生成GitHub搜索关键词（无需参数）
        2. SEARCH_GITHUB - 在GitHub上搜索仓库（需要keywords参数，是关键词列表）
        3. GENERATE_WEB_QUERIES - 创建网络搜索查询（无需参数）
        4. SEARCH_WEB - 执行网页搜索（需要query参数，是搜索字符串）
        5. EXTRACT_GITHUB_LINKS - 从网页提取GitHub仓库链接（需要url参数，是网页URL）
        6. GET_REPO_DETAILS - 获取仓库详情（需要repo_url参数，是仓库URL）
        7. CALCULATE_SCORES - 为收集的仓库计算分数（无需参数）
        8. GENERATE_REPORT - 生成最终报告（无需参数）
        9. COMPLETE - 标记任务已完成（无需参数）

        请分析当前状态，并决定下一步最佳行动。必须严格按照以下JSON格式返回你的决定，不要添加任何其他文本:
        
        {{
            "action": "行动名称",
            "params": {{
                "参数名": "参数值"
            }},
            "reasoning": "你做出这个决定的简短理由"
        }}
        
        注意事项:
        - 必须严格按照上述JSON格式返回，不带任何额外解释或代码块标记
        - 如果没有参数，返回空对象 {{}}
        - 确保选择的行动有意义，考虑已经完成的工作和可用的数据
        - 必须先计算仓库分数(CALCULATE_SCORES)，然后再生成报告(GENERATE_REPORT)
        - 只有在有排名后的仓库时，才能生成报告
        
        所有可用行动的示例格式:
        
        示例1 - 生成关键词:
        {{
            "action": "GENERATE_KEYWORDS",
            "params": {{}},
            "reasoning": "首先需要为搜索生成相关关键词"
        }}
        
        示例2 - 搜索GitHub:
        {{
            "action": "SEARCH_GITHUB",
            "params": {{
                "keywords": ["machine learning", "tensorflow", "deep learning"]
            }},
            "reasoning": "已有关键词，现在需要搜索相关GitHub仓库"
        }}
        
        示例3 - 生成网络搜索查询:
        {{
            "action": "GENERATE_WEB_QUERIES",
            "params": {{}},
            "reasoning": "需要创建网络搜索查询来寻找社区推荐的仓库"
        }}
        
        示例4 - 执行网络搜索:
        {{
            "action": "SEARCH_WEB",
            "params": {{
                "query": "best github repositories for machine learning"
            }},
            "reasoning": "使用查询在网络上搜索相关信息"
        }}
        
        示例5 - 提取GitHub链接:
        {{
            "action": "EXTRACT_GITHUB_LINKS",
            "params": {{
                "url": "https://example.com/best-ml-repos"
            }},
            "reasoning": "从搜索结果中提取GitHub仓库链接"
        }}
        
        示例6 - 获取仓库详情:
        {{
            "action": "GET_REPO_DETAILS",
            "params": {{
                "repo_url": "https://github.com/username/repo"
            }},
            "reasoning": "需要获取此仓库的更详细信息"
        }}
        
        示例7 - 计算仓库评分:
        {{
            "action": "CALCULATE_SCORES",
            "params": {{}},
            "reasoning": "已收集了足够的仓库信息，现在需要评分和排名"
        }}
        
        示例8 - 生成报告:
        {{
            "action": "GENERATE_REPORT",
            "params": {{}},
            "reasoning": "已完成仓库评分和排名，现在生成最终报告"
        }}
        
        示例9 - 完成任务:
        {{
            "action": "COMPLETE",
            "params": {{}},
            "reasoning": "所有必要的步骤已完成，任务结束"
        }}
        
        请只返回包含行动决策的JSON对象，不要添加任何额外的文本、解释或代码块标记。
        """
        
        prompt = PromptTemplate.from_template(prompt_template)
        
        # 执行LLM调用并解析结果
        try:
            # 调用LLM
            result = self.llm.invoke(prompt.format(
                domain=domain, 
                state_summary=state_summary,
                history_summary=history_summary
            ))
            
            # 获取LLM响应的内容
            content = result.content if hasattr(result, 'content') else str(result)
            
            # 使用健壮的JSON解析函数
            decision = self._try_parse_json_from_llm_response(content)
            
            # 如果成功解析出决策
            if decision and "action" in decision:
                action = decision.get("action", "")
                params = decision.get("params", {})
                reasoning = decision.get("reasoning", "未提供推理")
                
                # 验证决策合法性
                if action != "GENERATE_REPORT" or state.get("ranked_repos"):
                    self.logger.info(f"LLM决定的下一步行动: {action}, 原因: {reasoning}")
                    return action, params
                else:
                    self.logger.warning("LLM决定生成报告，但没有排名的仓库。使用默认决策。")
            else:
                self.logger.warning("无法从LLM响应中解析有效的决策JSON")
            
        except Exception as e:
            self.logger.error(f"决定下一步行动时出错: {str(e)}")
        
        # 如果所有解析方法都失败或发生异常，使用基于状态的默认决策逻辑
        self.logger.info("使用基于状态的默认决策逻辑")
        
        # 明确的决策树，确保流程的正确顺序
        if not state.get("keywords"):
            return "GENERATE_KEYWORDS", {}
            
        elif not state.get("github_repos") and state.get("keywords"):
            return "SEARCH_GITHUB", {"keywords": state.get("keywords", [])}
            
        elif not state.get("web_queries") and state.get("keywords"):
            return "GENERATE_WEB_QUERIES", {}
            
        elif not state.get("web_search_results") and state.get("web_queries"):
            # 使用第一个web查询
            web_queries = state.get("web_queries", [])
            if web_queries:
                return "SEARCH_WEB", {"query": web_queries[0]}
            else:
                return "SEARCH_WEB", {"query": f"best github repositories for {state['domain']}"}
                
        elif state.get("web_search_results") and not state.get("candidate_repos"):
            # 从第一个搜索结果提取GitHub链接
            web_results = state.get("web_search_results", [])
            if web_results and "url" in web_results[0]:
                return "EXTRACT_GITHUB_LINKS", {"url": web_results[0]["url"]}
            
        # 重要：确保有GitHub仓库后，进行分数计算
        elif (state.get("github_repos") or state.get("candidate_repos")) and not state.get("ranked_repos"):
            return "CALCULATE_SCORES", {}
            
        # 只有在有排名仓库时，才生成报告
        elif state.get("ranked_repos") and not state.get("final_report"):
            return "GENERATE_REPORT", {}
            
        else:
            return "COMPLETE", {}
    
    def _execute_action(self, action: str, params: Dict[str, Any], state: Dict[str, Any]) -> Any:
        """
        执行LLM决定的行动
        
        Args:
            action: 行动名称
            params: 行动参数
            state: 当前工作状态
            
        Returns:
            Any: 行动的结果
        """
        self.logger.info(f"执行行动: {action}, 参数: {params}")
        
        try:
            if action == "GENERATE_KEYWORDS":
                return self.llm_tools.generate_keywords(state["domain"], self.llm)
                
            elif action == "SEARCH_GITHUB":
                keywords = params.get("keywords", state.get("keywords", []))
                if not keywords:
                    self.logger.warning("搜索GitHub的关键词为空")
                    return []
                return self.github_tools.search_github_repositories(
                    keywords, 
                    self.config.github_access_token
                )
                
            elif action == "GENERATE_WEB_QUERIES":
                return self.llm_tools.generate_web_queries(state["domain"], self.llm)
                
            elif action == "SEARCH_WEB":
                query = params.get("query", "")
                if not query and state.get("web_queries"):
                    query = state["web_queries"][0]  # 使用第一个查询
                if not query:
                    query = f"best github repositories for {state['domain']}"
                    
                tavily_api_key = getattr(self.config, 'tavily_api_key', None)
                return self.web_tools.search_web(query, tavily_api_key)
                
            elif action == "EXTRACT_GITHUB_LINKS":
                url = params.get("url", "")
                if not url and state.get("web_search_results"):
                    # 从搜索结果中提取第一个URL
                    for result in state["web_search_results"]:
                        if result.get("url"):
                            url = result["url"]
                            break
                if not url:
                    return []
                    
                return self.web_tools.extract_github_links(url)
                
            elif action == "GET_REPO_DETAILS":
                repo_url = params.get("repo_url", "")
                if not repo_url:
                    self.logger.warning("获取仓库详情的URL为空")
                    return {}
                    
                return self.github_tools.get_repo_details(
                    repo_url, 
                    self.config.github_access_token
                )
                
            elif action == "CALCULATE_SCORES":
                self.logger.info("计算仓库评分...")
                # 获取所有仓库URL
                candidate_repos = []
                
                # 从GitHub搜索结果添加
                github_repos = state.get("github_repos", [])
                if github_repos:
                    self.logger.info(f"处理 {len(github_repos)} 个GitHub搜索结果...")
                    
                    # 确保每个结果都有必要的字段
                    for repo in github_repos:
                        # 检查是否是有效的仓库对象
                        if not isinstance(repo, dict):
                            continue
                            
                        # 检查必要字段
                        html_url = repo.get("html_url")
                        if not html_url:
                            continue
                            
                        # 创建规范化的仓库对象
                        candidate_repos.append({
                            "url": html_url,
                            "name": repo.get("name", ""),
                            "full_name": repo.get("full_name", ""),
                            "description": repo.get("description", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "forks": repo.get("forks_count", 0),
                            "pushed_at": repo.get("pushed_at", ""),
                            "language": repo.get("language", "")
                        })
                
                # 从候选池中添加URL
                candidate_urls = state.get("candidate_repos", [])
                if candidate_urls:
                    self.logger.info(f"处理 {len(candidate_urls)} 个候选仓库URL...")
                    
                    # 对于每个URL，尝试获取详细信息
                    for repo_url in candidate_urls:
                        # 跳过已处理的URL
                        if any(repo.get("url") == repo_url for repo in candidate_repos):
                            continue
                            
                        try:
                            # 获取仓库详情
                            details = self.github_tools.get_repo_details(
                                repo_url, 
                                self.config.github_access_token
                            )
                            
                            if details and "url" in details:
                                candidate_repos.append(details)
                        except Exception as e:
                            self.logger.error(f"获取仓库 {repo_url} 详情时出错: {e}")
                
                # 如果没有找到任何仓库，记录警告并返回空列表
                if not candidate_repos:
                    self.logger.warning("没有找到任何有效的仓库进行评分")
                    return []
                
                # 计算每个仓库的分数
                self.logger.info(f"为 {len(candidate_repos)} 个仓库计算评分...")
                ranked_repos = []
                for repo in candidate_repos:
                    try:
                        score = self.github_tools.calculate_repo_score(repo)
                        repo_with_score = repo.copy()
                        repo_with_score["score"] = score
                        ranked_repos.append(repo_with_score)
                    except Exception as e:
                        self.logger.error(f"计算仓库 {repo.get('full_name', 'unknown')} 评分时出错: {e}")
                
                # 按分数降序排序
                ranked_repos.sort(key=lambda x: x.get("score", 0), reverse=True)
                self.logger.info(f"评分完成，得到 {len(ranked_repos)} 个排名仓库")
                
                # 返回排序后的仓库（最多前10个）
                return ranked_repos[:10]
                
            elif action == "GENERATE_REPORT":
                ranked_repos = state.get("ranked_repos", [])
                if not ranked_repos:
                    self.logger.warning("生成报告的仓库列表为空")
                    return f"未能为领域 '{state['domain']}' 找到相关的GitHub仓库。请尝试使用其他关键词或领域名称。"
                    
                return self.llm_tools.generate_final_report(
                    ranked_repos, 
                    state["domain"], 
                    self.llm
                )
                
            elif action == "COMPLETE":
                return None
                
            else:
                self.logger.warning(f"未知的行动: {action}")
                return None
                
        except Exception as e:
            self.logger.error(f"执行行动 {action} 时出错: {e}")
            return None
    
    def _update_state(self, state: Dict[str, Any], action: str, result: Any) -> Dict[str, Any]:
        """
        根据执行结果更新状态
        
        Args:
            state: 当前状态
            action: 执行的行动
            result: 行动的结果
            
        Returns:
            Dict[str, Any]: 更新后的状态
        """
        new_state = state.copy()
        
        try:
            if action == "GENERATE_KEYWORDS" and result:
                new_state["keywords"] = result
                self.logger.info(f"状态更新: 添加了 {len(result)} 个关键词")
                
            elif action == "SEARCH_GITHUB" and result:
                new_state["github_repos"] = result
                self.logger.info(f"状态更新: 添加了 {len(result)} 个GitHub仓库搜索结果")
                
            elif action == "GENERATE_WEB_QUERIES" and result:
                new_state["web_queries"] = result
                self.logger.info(f"状态更新: 添加了 {len(result)} 个网络搜索查询")
                
            elif action == "SEARCH_WEB" and result:
                new_state["web_search_results"] = result
                self.logger.info(f"状态更新: 添加了 {len(result)} 个网络搜索结果")
                
            elif action == "EXTRACT_GITHUB_LINKS" and result:
                # 合并新链接，并去重
                candidate_repos = new_state.get("candidate_repos", [])
                new_links = 0
                
                for url in result:
                    if url and url not in candidate_repos:
                        candidate_repos.append(url)
                        new_links += 1
                        
                new_state["candidate_repos"] = candidate_repos
                self.logger.info(f"状态更新: 添加了 {new_links} 个新的候选仓库URL")
                
            elif action == "GET_REPO_DETAILS" and result:
                # 将详情添加到候选池
                url = result.get("url")
                if url:
                    candidate_repos = new_state.get("candidate_repos", [])
                    if url not in candidate_repos:
                        candidate_repos.append(url)
                        new_state["candidate_repos"] = candidate_repos
                        self.logger.info(f"状态更新: 添加了一个新的候选仓库URL: {url}")
                
            elif action == "CALCULATE_SCORES" and result:
                new_state["ranked_repos"] = result
                self.logger.info(f"状态更新: 添加了 {len(result)} 个排序后的仓库")
                
                # 确保我们有排名后的仓库
                if not result:
                    self.logger.warning("警告: 排序后的仓库列表为空")
                
            elif action == "GENERATE_REPORT" and result:
                new_state["final_report"] = result
                report_len = len(result) if result else 0
                self.logger.info(f"状态更新: 添加了最终报告 ({report_len} 字符)")
            
            else:
                self.logger.debug(f"行动 {action} 未改变状态或未返回结果")
            
        except Exception as e:
            self.logger.error(f"更新状态时出错: {e}")
            
        return new_state
    
    def _format_state_summary(self, state: Dict[str, Any]) -> str:
        """
        将当前状态格式化为LLM可读的摘要
        
        Args:
            state: 当前工作状态
            
        Returns:
            str: 格式化的状态摘要
        """
        summary = []
        
        # 添加领域信息
        summary.append(f"- 目标领域: {state.get('domain', '未知')}")
        
        # 添加关键词
        keywords = state.get("keywords", [])
        if keywords:
            summary.append(f"- 已生成关键词: {', '.join(keywords[:5])}{' 等' if len(keywords) > 5 else ''}")
        else:
            summary.append("- 尚未生成关键词")
        
        # GitHub仓库数量
        github_repos = state.get("github_repos", [])
        if github_repos:
            summary.append(f"- 从GitHub搜索到的仓库: {len(github_repos)} 个")
        else:
            summary.append("- 尚未从GitHub搜索仓库")
        
        # Web搜索结果
        web_results = state.get("web_search_results", [])
        if web_results:
            summary.append(f"- 网络搜索结果数量: {len(web_results)} 个")
        
        # 候选仓库
        candidate_repos = state.get("candidate_repos", [])
        if candidate_repos:
            summary.append(f"- 候选仓库数量: {len(candidate_repos)} 个")
        
        # 排名仓库
        ranked_repos = state.get("ranked_repos", [])
        if ranked_repos:
            summary.append(f"- 已排序的仓库: {len(ranked_repos)} 个")
            # 添加前三名的信息
            top3 = ranked_repos[:3]
            if top3:
                summary.append("- 排名前三的仓库:")
                for i, repo in enumerate(top3, 1):
                    name = repo.get("full_name", "Unknown")
                    stars = repo.get("stars", 0)
                    summary.append(f"  {i}. {name} (⭐ {stars})")
        
        # 最终报告
        if state.get("final_report"):
            summary.append("- 已生成最终报告")
        else:
            summary.append("- 尚未生成最终报告")
        
        return "\n".join(summary)
    
    def _format_history_summary(self) -> str:
        """
        将执行历史格式化为LLM可读的摘要
        
        Returns:
            str: 格式化的历史摘要
        """
        if not self.history:
            return "尚未执行任何操作"
        
        summary = []
        for i, entry in enumerate(self.history, 1):
            action = entry.get("action", "Unknown")
            params = entry.get("params", {})
            result_summary = entry.get("result_summary", "无结果")
            
            param_str = ""
            if params:
                param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                param_str = f" (参数: {param_str})"
            
            summary.append(f"{i}. 执行了 {action}{param_str}，结果: {result_summary}")
        
        return "\n".join(summary)
    
    def _summarize_result(self, result: Any) -> str:
        """
        将执行结果简化为简短摘要
        
        Args:
            result: 执行结果
            
        Returns:
            str: 简短摘要
        """
        if result is None:
            return "无结果"
            
        if isinstance(result, list):
            return f"获取了 {len(result)} 个项目"
            
        if isinstance(result, dict):
            keys = list(result.keys())
            return f"获取了包含 {', '.join(keys[:3])}{' 等' if len(keys) > 3 else ''} 的对象"
            
        if isinstance(result, str):
            if len(result) > 100:
                return f"生成了一段长文本 ({len(result)} 字符)"
            else:
                return f"结果: {result}"
                
        return f"结果类型: {type(result).__name__}"
    
    def _try_parse_json_from_llm_response(self, text: str) -> Dict[str, Any]:
        """
        尝试从LLM响应中提取有效的JSON
        
        使用多种方法尝试从文本中提取有效的JSON对象，特别是带有"action"字段的决策对象
        
        Args:
            text: LLM生成的文本
            
        Returns:
            Dict: 解析出的JSON对象，或空字典(如果解析失败)
        """
        self.logger.debug(f"尝试解析JSON，原始文本: {text[:100]}...")
        
        # 移除可能的代码块标记
        cleaned_text = text.replace('```json', '').replace('```', '')
        
        # 尝试方法1: 直接解析整个文本
        try:
            json_obj = json.loads(cleaned_text)
            self.logger.debug("方法1成功: 直接解析整个文本")
            return json_obj
        except json.JSONDecodeError:
            pass
        
        # 尝试方法2: 使用正则查找第一个 { 到最后一个 } 之间的内容
        try:
            json_pattern = r'(\{.*\})'
            match = re.search(json_pattern, cleaned_text, re.DOTALL)
            if match:
                json_obj = json.loads(match.group(1))
                self.logger.debug("方法2成功: 使用正则表达式提取大括号内容")
                return json_obj
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 尝试方法3: 查找包含 "action" 的JSON对象
        try:
            action_pattern = r'(\{[^{]*"action"[^}]*\})'
            match = re.search(action_pattern, cleaned_text, re.DOTALL)
            if match:
                json_obj = json.loads(match.group(1))
                self.logger.debug("方法3成功: 提取包含action的对象")
                return json_obj
        except (json.JSONDecodeError, AttributeError):
            pass
            
        # 尝试方法4: 处理转义问题，双大括号转单大括号
        try:
            fixed_text = cleaned_text.replace('{{', '{').replace('}}', '}')
            json_obj = json.loads(fixed_text)
            self.logger.debug("方法4成功: 修复双大括号问题")
            return json_obj
        except json.JSONDecodeError:
            pass
            
        # 尝试方法5: 使用更宽松的方式提取键值对
        try:
            # 查找 "action": "值" 模式
            action_match = re.search(r'"action"\s*:\s*"([^"]+)"', cleaned_text)
            if action_match:
                action = action_match.group(1)
                
                # 查找 "params": {值} 或 "params": {} 模式
                params = {}
                params_match = re.search(r'"params"\s*:\s*(\{[^}]*\})', cleaned_text)
                if params_match:
                    try:
                        params_text = params_match.group(1).replace('{{', '{').replace('}}', '}')
                        params = json.loads(params_text)
                    except json.JSONDecodeError:
                        pass
                        
                # 查找 reasoning
                reasoning = "通过正则表达式提取的决策"
                reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', cleaned_text)
                if reasoning_match:
                    reasoning = reasoning_match.group(1)
                
                self.logger.debug("方法5成功: 使用正则表达式提取键值对")
                return {
                    "action": action,
                    "params": params,
                    "reasoning": reasoning
                }
        except Exception as e:
            self.logger.warning(f"方法5失败: {e}")
            pass
            
        # 尝试方法6: 使用LLM再次处理，提取结构化信息（此方法仅在紧急情况下使用）
        if self.last_action and self.last_action == "GENERATE_KEYWORDS":
            self.logger.info("使用默认决策: SEARCH_GITHUB")
            return {
                "action": "SEARCH_GITHUB",
                "params": {},
                "reasoning": "关键词已生成，需要执行GitHub搜索"
            }
        
        if self.last_action and self.last_action == "SEARCH_GITHUB":
            self.logger.info("使用默认决策: CALCULATE_SCORES")
            return {
                "action": "CALCULATE_SCORES",
                "params": {},
                "reasoning": "GitHub搜索已完成，需要计算仓库评分"
            }
            
        # 所有方法都失败，记录原始文本并返回空字典
        self.logger.error(f"所有JSON解析方法都失败，原始文本: {text[:300]}...")
        return {} 