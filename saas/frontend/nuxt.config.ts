// 백엔드 프록시 대상 — 로컬 개발은 127.0.0.1:8000, Render/클라우드는 서비스 내부 주소
// Dockerfile.frontend의 ARG API_HOST 또는 Render envVars에서 NUXT_API_PROXY_TARGET으로 주입
const API_PROXY_TARGET = process.env.NUXT_API_PROXY_TARGET || 'http://127.0.0.1:8000'

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
    '/api/**': { proxy: `${API_PROXY_TARGET}/api/**` },
    '/preview/**': { proxy: `${API_PROXY_TARGET}/preview/**` },
    '/embed/**': { proxy: `${API_PROXY_TARGET}/embed/**` },
    '/widget-dist/**': { proxy: `${API_PROXY_TARGET}/widget-dist/**` },
    '/django-admin/**': { proxy: `${API_PROXY_TARGET}/django-admin/**` },
    '/health/**': { proxy: `${API_PROXY_TARGET}/health/**` },
    '/ready/**': { proxy: `${API_PROXY_TARGET}/ready/**` },
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
