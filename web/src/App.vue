<template>
  <div class="app-container">
    <header class="header">
      <div class="header-content">
        <h1 class="title">Awesome Agent</h1>
        <p class="subtitle">发现最优质的GitHub仓库</p>
      </div>
    </header>
    
    <main class="main-content">
      <search-form @search="handleSearch" :loading="loading" />
      
      <div class="results-container" v-if="searchPerformed">
        <div v-if="loading" class="loading-container">
          <div class="loading-spinner"></div>
          <p class="loading-text">正在分析您的请求，请稍候...</p>
        </div>
        
        <div v-else-if="error" class="error-message">
          <p>{{ error }}</p>
        </div>
        
        <markdown-viewer v-else :content="resultContent" :search-mode="searchMode" />
      </div>
    </main>
    
    <footer class="footer">
      <p>&copy; {{ new Date().getFullYear() }} Awesome Agent</p>
    </footer>
  </div>
</template>

<script>
import axios from 'axios';
import SearchForm from './components/SearchForm.vue';
import MarkdownViewer from './components/MarkdownViewer.vue';

export default {
  name: 'App',
  components: {
    SearchForm,
    MarkdownViewer
  },
  data() {
    return {
      loading: false,
      error: null,
      resultContent: '',
      searchPerformed: false,
      searchMode: 'standard' // 默认使用标准工作流
    };
  },
  methods: {
    async handleSearch(domain, mode = 'standard') {
      this.searchPerformed = true;
      this.loading = true;
      this.error = null;
      this.resultContent = '';
      this.searchMode = mode;
      
      const apiEndpoint = mode === 'logic' 
        ? '/api/awesome_search_logic' 
        : '/api/awesome_search';
      
      try {
        const startTime = Date.now();
        const response = await axios.post(apiEndpoint, { domain });
        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);
        
        if (response.data && response.data.code === 200) {
          this.resultContent = response.data.message;
          console.log(`搜索完成，用时: ${duration}秒, 使用模式: ${mode}`);
        } else {
          this.error = '请求失败: ' + (response.data?.message || '未知错误');
        }
      } catch (err) {
        this.error = '请求出错: ' + (err.message || '未知错误');
        console.error('Search error:', err);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Noto Sans SC', sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f8f9fa;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  background: linear-gradient(135deg, #3a7bd5, #00d2ff);
  color: white;
  padding: 2rem 0;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.title {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.9;
  font-weight: 300;
}

.main-content {
  flex: 1;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.results-container {
  margin-top: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #3a7bd5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: #666;
}

.error-message {
  padding: 2rem;
  text-align: center;
  color: #e53e3e;
}

.footer {
  background-color: #2c3e50;
  color: white;
  text-align: center;
  padding: 1.2rem 0;
  margin-top: auto;
  font-size: 0.9rem;
}
</style> 