<template>
  <div class="markdown-viewer">
    <div class="markdown-header">
      <div class="header-left">
        <h2 class="markdown-title">搜索结果</h2>
        <span v-if="searchMode" class="search-mode-badge" :class="{'logic-mode': searchMode === 'logic'}">
          {{ searchMode === 'logic' ? '大模型驱动' : '传统工作流' }}
        </span>
      </div>
      <button class="btn btn-secondary btn-export" @click="exportMarkdown">
        <svg class="export-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path>
          <path d="M7 10l5 5 5-5"></path>
          <path d="M12 15V3"></path>
        </svg>
        导出报告
      </button>
    </div>
    <div class="markdown-content" v-html="renderedContent"></div>
  </div>
</template>

<script>
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-dark.css';

export default {
  name: 'MarkdownViewer',
  props: {
    content: {
      type: String,
      required: true
    },
    searchMode: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      renderer: new marked.Renderer()
    };
  },
  computed: {
    renderedContent() {
      if (!this.content) return '';
      
      // 处理来自后端的内容，移除可能包裹的markdown代码块标记
      let processedContent = this.content;
      
      // 检测并移除开头的```markdown或```及结尾的```
      const markdownBlockRegex = /^```(?:markdown)?\s*\n([\s\S]*?)\n```\s*$/;
      const match = processedContent.match(markdownBlockRegex);
      
      if (match) {
        processedContent = match[1];
      }
      
      // 配置marked使用highlight.js进行代码高亮
      marked.setOptions({
        renderer: this.renderer,
        highlight: function(code, lang) {
          const language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-',
        pedantic: false,
        gfm: true,
        breaks: false,
        sanitize: false,
        smartypants: false,
        xhtml: false
      });
      
      return marked(processedContent);
    },
    
    // 用于导出的原始Markdown内容
    rawMarkdown() {
      if (!this.content) return '';
      
      let processedContent = this.content;
      const markdownBlockRegex = /^```(?:markdown)?\s*\n([\s\S]*?)\n```\s*$/;
      const match = processedContent.match(markdownBlockRegex);
      
      if (match) {
        processedContent = match[1];
      }
      
      return processedContent;
    }
  },
  methods: {
    exportMarkdown() {
      // 创建一个Blob对象，包含Markdown内容
      const blob = new Blob([this.rawMarkdown], { type: 'text/markdown;charset=utf-8' });
      
      // 创建下载链接并触发下载
      const link = document.createElement('a');
      const fileName = `awesome-agent-结果-${new Date().toISOString().slice(0, 10)}.md`;
      
      // 创建下载链接
      link.href = URL.createObjectURL(blob);
      link.download = fileName;
      
      // 添加到文档并触发点击
      document.body.appendChild(link);
      link.click();
      
      // 清理
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    }
  }
};
</script>

<style>
.markdown-viewer {
  padding: 2rem;
}

.markdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color, #e2e8f0);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.markdown-title {
  margin: 0;
  color: var(--primary-color, #3a7bd5);
  font-size: 1.5rem;
  font-weight: 600;
}

.search-mode-badge {
  display: inline-block;
  background-color: #64748b;
  color: white;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.search-mode-badge.logic-mode {
  background-color: #7c3aed;
}

.export-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  margin-right: 8px;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.btn-export {
  display: flex;
  align-items: center;
  justify-content: center;
}

.markdown-content {
  line-height: 1.8;
}

/* 移动设备适配 */
@media (max-width: 768px) {
  .markdown-viewer {
    padding: 1.5rem 1rem;
  }
}

@media (max-width: 480px) {
  .markdown-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .markdown-header button {
    width: 100%;
    justify-content: center;
  }
}

/* 自定义样式增强 */
.markdown-content blockquote {
  border-left: 4px solid var(--primary-color);
  padding-left: 1rem;
  color: #4a5568;
  margin: 1rem 0;
  background-color: #f7fafc;
  padding: 0.5rem 1rem;
  border-radius: 0 4px 4px 0;
}

.markdown-content img {
  max-width: 100%;
  border-radius: 6px;
  margin: 1rem 0;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
}

.markdown-content hr {
  height: 1px;
  background-color: var(--border-color);
  border: none;
  margin: 2rem 0;
}

/* 添加特殊样式用于仓库列表 */
.markdown-content h2 {
  color: var(--primary-color);
}

.markdown-content h3 a {
  font-weight: 600;
}

/* 星级评分高亮 */
.markdown-content li strong {
  color: #805ad5;
}

/* 表格美化 */
.markdown-content table {
  border-radius: 5px;
  overflow: hidden;
  box-shadow: 0 0 0 1px var(--border-color);
}

.markdown-content table th {
  background-color: #edf2f7;
  font-weight: 600;
}

.markdown-content table tr:nth-child(even) {
  background-color: #f7fafc;
}
</style> 