<template>
  <div class="search-form">
    <div class="form-group">
      <label for="domainInput" class="form-label">请输入您感兴趣的领域或技术</label>
      <textarea 
        id="domainInput"
        v-model="domain"
        class="form-input" 
        placeholder="例如：容器化技术、前端框架、人工智能应用..."
        :disabled="loading"
        rows="3"
        @keydown.enter.ctrl="submitSearch"
      ></textarea>
      <p class="form-hint">输入您想了解的领域，Awesome Agent 将为您推荐最优质的相关GitHub仓库</p>
    </div>

    <div class="mode-selector">
      <label class="mode-label">
        <input 
          type="radio" 
          name="search-mode" 
          value="standard" 
          v-model="searchMode"
          :disabled="loading"
        />
        <span>传统工作流</span>
      </label>
      <label class="mode-label">
        <input 
          type="radio" 
          name="search-mode" 
          value="logic" 
          v-model="searchMode"
          :disabled="loading"
        />
        <span>大模型驱动 <small class="badge">新</small></span>
      </label>
    </div>

    <div class="form-actions">
      <button 
        class="btn" 
        @click="submitSearch" 
        :disabled="!domain || loading"
      >
        <span v-if="!loading">开始搜索</span>
        <span v-else>搜索中...</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SearchForm',
  props: {
    loading: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      domain: '',
      searchMode: 'standard' // 默认使用标准工作流
    };
  },
  methods: {
    submitSearch() {
      if (!this.domain || this.loading) return;
      this.$emit('search', this.domain, this.searchMode);
    }
  }
};
</script>

<style scoped>
.search-form {
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.form-group {
  margin-bottom: 1.2rem;
}

.form-label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #2d3748;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 1rem;
  font-family: 'Noto Sans SC', sans-serif;
  transition: border-color 0.2s;
  resize: vertical;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(58, 123, 213, 0.1);
}

.form-input:disabled {
  background-color: #edf2f7;
  cursor: not-allowed;
}

.form-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #718096;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}

.mode-selector {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.2rem;
  padding: 0.75rem 0;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

.mode-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.mode-label input {
  margin-right: 0.5rem;
}

.badge {
  display: inline-block;
  background-color: var(--primary-color);
  color: white;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
  margin-left: 0.5rem;
  vertical-align: top;
}

@media (max-width: 480px) {
  .mode-selector {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style> 