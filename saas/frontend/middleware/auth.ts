// sessionid 쿠키는 HttpOnly 라 JS 에서 읽을 수 없으므로,
// /api/auth/me/ 호출로 인증 여부를 판단한다(SSR 비활성 라우트에서 클라이언트 실행).
export default defineNuxtRouteMiddleware(async (to) => {
  try {
    const user = await useApi('/api/auth/me/')
    if (!user) {
      return navigateTo('/login?next=' + encodeURIComponent(to.fullPath))
    }
  } catch {
    return navigateTo('/login?next=' + encodeURIComponent(to.fullPath))
  }
})
