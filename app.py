# app.py
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_cors import CORS 
import time
import json
import re
import os
import sys
from pathlib import Path

from config import Config
from llm.llm_agent import Agent
from llm.awesome_agent import AwesomeAgent
from llm.awesome_agent_logic import AwesomeAgentLogic
from api.request import InputRequest, AdvancedSearchRequest, AwesomeSearchRequest
from api.response import ProcessResponse 
from pydantic import ValidationError

CFG = Config()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='web')
CORS(app) 

llm_agent = Agent()
awesome_agent = AwesomeAgent()
awesome_agent_logic = AwesomeAgentLogic()

# 前端路由 - 提供Vue构建的静态文件
@app.route('/')
def index():
    # 检查是否存在dist目录（Vue构建后的目录）
    dist_dir = os.path.join('web', 'dist')
    if os.path.exists(dist_dir):
        return send_from_directory(dist_dir, 'index.html')
    else:
        # 开发模式，直接返回web目录下的index.html
        return send_from_directory('web', 'index.html')

# 处理静态文件
@app.route('/<path:path>')
def serve_static(path):
    # 先尝试从dist目录加载
    dist_path = os.path.join('web', 'dist', path)
    if os.path.exists(dist_path):
        dist_dir = os.path.join('web', 'dist')
        filename = path
        return send_from_directory(dist_dir, filename)
    
    # 否则从web根目录加载
    return send_from_directory('web', path)

@app.route('/api/awesome_search', methods=['POST'])
def awesome_search_api():
    """
    API endpoint for Awesome Agent search.
    执行完整的Awesome Agent五步工作流，为用户提供的领域生成高质量GitHub仓库推荐报告。
    
    Takes JSON: {"domain": "领域名称，如'容器化技术'"}
    Returns JSON: ProcessResponse structure containing Markdown report
    """
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"code": 400, "message": ["Bad Request: No JSON data received."]}), 400
        
        # 验证输入
        input_data = AwesomeSearchRequest(**json_data)
    except ValidationError as e:
        logging.error(f"Validation error for awesome_search: {e.errors()}")
        error_messages = [f"{err['loc'][0] if err['loc'] else 'input'}: {err['msg']}" for err in e.errors()]
        return jsonify({"code": 422, "message": error_messages}), 422
    except Exception as e:
        logging.error(f"Error parsing request for awesome_search: {e}")
        return jsonify({"code": 400, "message": [f"Bad Request: {str(e)}"]}), 400
    
    logging.info(f"API /awesome_search: Domain: {input_data.domain}")
    
    try:
        # 执行完整工作流
        report = awesome_agent.run(input_data.domain)
        
        # 返回成功响应
        response_data = ProcessResponse(
            code=200,
            message=report
        )
        return jsonify(response_data.model_dump())
    except Exception as e:
        logging.error(f"Awesome Agent workflow failed: {e}")
        return jsonify({
            "code": 500, 
            "message": f"执行流程时出错: {str(e)}"
        }), 500

@app.route('/api/awesome_search_logic', methods=['POST'])
def awesome_search_logic_api():
    """
    API endpoint for the LLM-driven Awesome Agent Logic.
    
    使用以大模型为大脑的代理执行搜索流程，由LLM动态决定步骤和操作，
    为用户提供的领域生成高质量GitHub仓库推荐报告。
    
    Takes JSON: {"domain": "领域名称，如'容器化技术'"}
    Returns JSON: ProcessResponse structure containing Markdown report
    """
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({"code": 400, "message": ["Bad Request: No JSON data received."]}), 400
        
        # 验证输入
        input_data = AwesomeSearchRequest(**json_data)
    except ValidationError as e:
        logging.error(f"Validation error for awesome_search_logic: {e.errors()}")
        error_messages = [f"{err['loc'][0] if err['loc'] else 'input'}: {err['msg']}" for err in e.errors()]
        return jsonify({"code": 422, "message": error_messages}), 422
    except Exception as e:
        logging.error(f"Error parsing request for awesome_search_logic: {e}")
        return jsonify({"code": 400, "message": [f"Bad Request: {str(e)}"]}), 400
    
    logging.info(f"API /awesome_search_logic: Domain: {input_data.domain}")
    
    try:
        # 执行LLM驱动的工作流
        start_time = time.time()
        report = awesome_agent_logic.run(input_data.domain)
        elapsed_time = time.time() - start_time
        
        logging.info(f"Logic agent completed in {elapsed_time:.2f} seconds")
        
        # 返回成功响应
        response_data = ProcessResponse(
            code=200,
            message=report
        )
        return jsonify(response_data.model_dump())
    except Exception as e:
        logging.error(f"Awesome Agent Logic workflow failed: {e}")
        return jsonify({
            "code": 500, 
            "message": f"执行流程时出错: {str(e)}"
        }), 500


# 提供一个简单的健康检查端点
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": time.time()})

if __name__ == '__main__':
    # 打印启动信息
    print(f"启动 Awesome Agent 服务在 http://{CFG.app_host or '0.0.0.0'}:{CFG.app_port or 7111}")
    print(f"请访问浏览器 http://localhost:{CFG.app_port or 7111} 使用前端界面")
    
    app.run(host=CFG.app_host or '0.0.0.0', port=CFG.app_port or 7111, debug=True)