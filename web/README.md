# Awesome Agent 前端

这是Awesome Agent的Vue前端界面，用于与API交互并展示GitHub仓库推荐结果。

## 功能

- 用户可以输入感兴趣的领域或技术
- 系统会分析用户输入，生成相关关键词
- 根据关键词搜索、筛选和排名GitHub仓库
- 以美观的Markdown格式呈现结果

## 开发设置

### 前置条件

- Node.js 14+
- npm 6+

### 安装与运行

```bash
# 进入web目录
cd web

# 安装依赖
npm install

# 启动开发服务器
npm run serve
```

### 生产构建

```bash
# 构建生产版本
npm run build
```

构建后的文件将位于`web/dist`目录，可直接由Flask应用提供服务。

## 与后端集成

前端已配置好API代理，默认指向`http://localhost:7111`，确保后端Flask应用在该地址运行。

## 使用方法

1. 在文本框中输入您感兴趣的技术领域或问题描述
2. 点击"开始搜索"按钮
3. 等待系统分析并生成推荐报告
4. 查看返回的GitHub仓库推荐列表及相关信息

## 技术栈

- Vue 3
- Axios (API请求)
- marked (Markdown渲染)
- highlight.js (代码高亮) 