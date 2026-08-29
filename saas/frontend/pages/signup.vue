<script setup lang="ts">
const { t, load: loadSilo } = useSilo()
await useAsyncData('silo-info', async () => { await loadSilo(); return true })

const email = ref('')
const name = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await useApi('/api/auth/signup/', {
      method: 'POST',
      body: { email: email.value, name: name.value, password: password.value },
    })
    navigateTo('/dashboard')
  } catch (e: any) {
    const data = e?.data
    error.value = typeof data === 'object' ? Object.values(data).flat().join(' ') : t('signup.failed')
  }
}
</script>

<template>
  <main class="wrap">
    <h1>{{ t('signup.title') }}</h1>
    <form @submit.prevent="submit">
      <input v-model="email" type="email" :placeholder="t('login.email')" required />
      <input v-model="name" type="text" :placeholder="t('signup.name')" />
      <input v-model="password" type="password" :placeholder="t('signup.pwPlaceholder')" required minlength="8" />
      <button type="submit">{{ t('signup.submit') }}</button>
      <p v-if="error" class="err">{{ error }}</p>
    </form>
  </main>
</template>

<style scoped>
.wrap { max-width: 360px; margin: 80px auto; padding: 0 24px; }
input, button { width: 100%; padding: 10px; margin: 6px 0; box-sizing: border-box; }
button { background: #0e7490; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }
.err { color: #b91c1c; }
</style>
