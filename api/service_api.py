from typing import List, Union, Dict
from fastapi import APIRouter, Body, Request, HTTPException
import logging
from config import Config
from llm.llm_agent import Agent
from llm.awesome_agent import AwesomeAgent
from api.request import InputRequest, AdvancedSearchRequest, AwesomeSearchRequest
from api.response import ProcessResponse
import requests

logging.basicConfig(level=logging.INFO)
router = APIRouter()

CFG = Config()

@router.post("/api/get_keywords", response_model=ProcessResponse)
async def get_keywords_and_suggestions(request_data: InputRequest) -> ProcessResponse:
    logging.info(f"Input text for keyword extraction: {request_data.text}")
    
    # 使用AwesomeAgent的第一步而不是旧的Agent
    try:
        awesome_agent = AwesomeAgent()
        keywords = awesome_agent.step_1_generate_keywords(request_data.text)
        
        # 分为主要关键词和建议关键词
        primary_keywords = keywords[:2] if len(keywords) >= 2 else keywords
        suggested_keywords = keywords[2:] if len(keywords) > 2 else []
        
        response = ProcessResponse(
            code=200,
            message={
                "primary_keywords": primary_keywords,
                "suggested_keywords": suggested_keywords
            }
        )
        
        logging.info(f"Keywords extracted: Primary: {primary_keywords}, Suggested: {suggested_keywords}")
        return response
    except Exception as e:
        logging.error(f"Keyword extraction failed: {e}")
        return ProcessResponse(code=500, message=[f"Error generating keywords: {str(e)}"])

@router.post("/api/awesome_search", response_model=ProcessResponse)
async def awesome_search(request_data: AwesomeSearchRequest) -> ProcessResponse:
    """
    执行完整的Awesome Agent五步工作流，为用户提供的领域生成高质量GitHub仓库推荐报告。
    
    Args:
        request_data (AwesomeSearchRequest): 包含用户查询领域的请求数据
        
    Returns:
        ProcessResponse: 包含最终Markdown报告的响应
    """
    domain = request_data.domain
    logging.info(f"Executing Awesome Agent workflow for domain: {domain}")
    
    try:
        # 实例化AwesomeAgent
        agent = AwesomeAgent()
        
        # 执行完整工作流
        report = agent.run(domain)
        
        # 返回成功响应
        return ProcessResponse(
            code=200,
            message=report
        )
    except Exception as e:
        logging.error(f"Awesome Agent workflow failed: {e}")
        return ProcessResponse(
            code=500,
            message=f"执行流程时出错: {str(e)}"
        )