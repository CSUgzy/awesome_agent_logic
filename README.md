# awesome_agent

## 准备API KEY
更名 `.envtemplate` 文件为 `.env` 文件
替换该文件中相应的 api key 和地址

## 部署
(建议关闭 flask 的debug模式, 即app.py文件中将debug改为False)

> 启动后端

```
# 进入项目目录
cd awesome_agnent
# 安装项目依赖
pip install -r requirements.txt
# 启动服务
python app.py
```

> 启动前端

``````
# 进入项目目录
cd web
# 安装项目依赖
npm install
# 启动服务
npm run serve
``````

