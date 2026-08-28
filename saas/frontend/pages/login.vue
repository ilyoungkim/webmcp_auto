<script setup lang="ts">
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
    error.value = e?.data?.detail || '로그인 실패'
  }
}
</script>

<template>
  <main class="wrap">
    <h1>로그인</h1>
    <form @submit.prevent="submit">
      <input v-model="email" type="email" placeholder="이메일" required />
      <input v-model="password" type="password" placeholder="비밀번호" required />
      <button type="submit">로그인</button>
      <p v-if="error" class="err">{{ error }}</p>
    </form>
    <NuxtLink to="/signup">회원가입</NuxtLink>
  </main>
</template>

<style scoped>
.wrap { max-width: 360px; margin: 80px auto; padding: 0 24px; }
input, button { width: 100%; padding: 10px; margin: 6px 0; box-sizing: border-box; }
button { background: #0e7490; color: #fff; border: 0; border-radius: 6px; cursor: pointer; }
.err { color: #b91c1c; }
</style>
