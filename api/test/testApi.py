import requests
import json

# 尝试两种不同的URL格式
urls = [
    "http://localhost:7111/api/awesome_search",  # 原始路径（带api前缀）
    "http://localhost:7111/awesome_search"       # 修改后的路径（不带api前缀）
]

# 测试数据
payload = {
    "domain": "容器化技术"
}

# 测试所有URL
for url in urls:
    print(f"\n尝试URL: {url}")
    try:
        # 发送请求
        response = requests.post(url, json=payload)
        
        # 打印响应状态码和内容
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"返回信息: {result}")
        else:
            print(f"错误: {response.text[:100]}...")  # 只显示错误信息的前100个字符
    except Exception as e:
        print(f"请求出错: {str(e)}")