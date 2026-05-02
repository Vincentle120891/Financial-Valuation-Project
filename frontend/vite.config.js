export default {
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    allowedHosts: 'all',
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
}
