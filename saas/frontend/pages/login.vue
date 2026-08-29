<script setup lang="ts">
const { t, load: loadSilo } = useSilo()
await useAsyncData('silo-info', async () => { await loadSilo(); return true })

const email = ref('')
const password = ref('')
const error = ref('')
const route = useRoute()

async function submit() {
  error.value = ''
  try {
    await useApi('/api/auth/login/', {
      method: 'POST',
      body: { email: email.value, password: password.value },
    })
    navigateTo((route.query.next as string) || '/dashboard')
  } catch (e: any) {
    error.value = e?.data?.detail || t('login.failed')
  }
}
</script>

<template>
  <main class="wrap">
    <h1>{{ t('login.title') }}</h1>
    <form @submit.prevent="submit">
      <input v-model="email" type="email" :placeholder="t('login.email')" required />
      <input v-model="password" type="password" :placeholder="t('login.password')" required />
      <button type="submit">{{ t('login.submit') }}</button>
      <p v-if="error" class="err">{{ error }}</p>
    </form>
    <NuxtLink to="/signup">{{ t('login.signupLink') }}</NuxtLink>
  </main>
</template>

<style scoped>
.wrap { max-width: 360px; margin: 80px auto; padding: 0 24px; }
input, button { width: 100%; padding: 10px; margin: 6px 0; box-sizing: border-box; }
button { background: #0e7490; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }
.err { color: #b91c1c; }
</style>
