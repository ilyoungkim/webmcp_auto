// 클라이언트 마운트 시 CSRF 토큰 쿠키를 미리 발급받는다.
// 인증된 요청(GET 으로 세션 확보 후)의 POST 는 DRF 가 CSRF 를 강제하므로,
// 쿠키가 없으면 로그인/프로젝트 생성 등이 403 이 된다. 이 플러그인으로 사전 확보한다.
export default defineNuxtPlugin(() => {
  if (import.meta.client) {
    $fetch('/api/auth/csrf/', { method: 'GET', credentials: 'include' }).catch(
      () => {
        /* 실패는 무시 — 비인증 요청은 CSRF 검증을 타지 않음 */
      },
    )
  }
})
