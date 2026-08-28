export default defineNuxtRouteMiddleware(async () => {
  try {
    const user = await useApi('/api/auth/me/')
    if (!user || user.role !== 'admin') {
      return navigateTo('/dashboard')
    }
  } catch {
    return navigateTo('/dashboard')
  }
})
