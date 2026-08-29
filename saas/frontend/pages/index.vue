<script setup lang="ts">
const { t, load: loadSilo } = useSilo()
await useAsyncData('silo-info', async () => { await loadSilo(); return true })
</script>

<template>
  <main class="wrap">
    <h1>WebMCP Auto</h1>
    <p>{{ t('index.tagline') }}</p>
    <NuxtLink to="/signup">{{ t('index.cta') }}</NuxtLink>
    <NuxtLink to="/login">{{ t('login.submit') }}</NuxtLink>
  </main>
</template>

<style>
body { font-family: system-ui, sans-serif; margin: 0; }
</style>

<style scoped>
.wrap { max-width: 720px; margin: 80px auto; padding: 0 24px; text-align: center; }
.wrap a { display: inline-block; margin: 8px; padding: 12px 24px; background: #0e7490; color: #fff; border-radius: 8px; text-decoration: none; }
</style>
