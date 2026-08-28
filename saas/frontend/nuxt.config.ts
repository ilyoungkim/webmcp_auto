export default defineNuxtConfig({
  ssr: true,
  devServer: { port: 53300 },
  routeRules: {
    '/dashboard/**': { ssr: false },
    '/projects/**': { ssr: false },
    '/admin/**': { ssr: false },
    '/api/**': { proxy: 'http://127.0.0.1:8000/api/**' },
    '/preview/**': { proxy: 'http://127.0.0.1:8000/preview/**' },
    '/embed/**': { proxy: 'http://127.0.0.1:8000/embed/**' },
    '/widget-dist/**': { proxy: 'http://127.0.0.1:8000/widget-dist/**' },
    '/django-admin/**': { proxy: 'http://127.0.0.1:8000/django-admin/**' },
    '/health/**': { proxy: 'http://127.0.0.1:8000/health/**' },
    '/ready/**': { proxy: 'http://127.0.0.1:8000/ready/**' },
  },
  runtimeConfig: {
    public: { apiBase: '' },
  },
})
