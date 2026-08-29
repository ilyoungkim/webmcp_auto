export default defineNuxtConfig({
  ssr: true,
  devServer: { port: 53300 },
  app: {
    head: {
      meta: [
        // 기본적으로 모든 페이지를 검색엔진 색인·추적에서 제외
        { name: 'robots', content: 'noindex, nofollow' },
      ],
    },
  },
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
