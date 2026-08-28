function readCookie(name: string): string {
  if (import.meta.server) return ''
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return m ? decodeURIComponent(m[1]) : ''
}

export async function useApi<T = any>(path: string, opts: any = {}) {
  const config = useRuntimeConfig()
  const isWrite = opts.method && opts.method !== 'GET'
  // CSRF: 쓰기 요청 전에 csrftoken 쿠키가 없으면 먼저 발급받는다.
  // 인증된 요청의 POST 는 DRF 가 CSRF 를 강제하므로 쿠키 누락 시 403 이 난다.
  if (isWrite && !readCookie('csrftoken')) {
    await $fetch('/api/auth/csrf/', { method: 'GET', credentials: 'include' }).catch(
      () => {},
    )
  }
  return await $fetch<T>(path, {
    baseURL: config.public.apiBase,
    credentials: 'include',
    ...opts,
    headers: {
      ...(opts.headers || {}),
      ...(isWrite ? { 'X-CSRFToken': readCookie('csrftoken') } : {}),
    },
    onResponseError({ response }) {
      if (response.status === 401 && import.meta.client) {
        navigateTo('/login')
      }
    },
  })
}
