<script setup lang="ts">
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
    error.value = typeof data === 'object' ? Object.values(data).flat().join(' ') : '가입 실패'
  }
}
</script>

<template>
  <main class="wrap">
    <h1>회원가입</h1>
    <form @submit.prevent="submit">
      <input v-model="email" type="email" placeholder="이메일" required />
      <input v-model="name" type="text" placeholder="이름" />
      <input v-model="password" type="password" placeholder="비밀번호 (8자 이상)" required minlength="8" />
      <button type="submit">가입</button>
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
