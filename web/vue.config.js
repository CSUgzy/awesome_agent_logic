module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:7111',
        changeOrigin: true
      }
    }
  }
} 