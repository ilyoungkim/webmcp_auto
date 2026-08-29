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
    public: {
      apiBase: '',
      // 컨테이너 언어(사일로) — 도커에서 NUXT_PUBLIC_SILO_LANG=en 으로 주입
      // 이 값이 있으면 SSR이 API 호출 없이 해당 언어로 확정 렌더링한다
      siloLang: '',
    },
  },
})
