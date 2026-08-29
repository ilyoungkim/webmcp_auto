<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
const route = useRoute()
const { t, load: loadSilo } = useSilo()
await useAsyncData('silo-info', async () => { await loadSilo(); return true })
</script>

<template>
  <div class="preview-page">
    <header>
      <NuxtLink to="/dashboard">← {{ t('dash.title') }}</NuxtLink>
      <span>{{ t('preview.liveTag') }}</span>
    </header>
    <!-- 동일 오리진 iframe — Django /preview/<id>/ (쿠키 전달됨) -->
    <iframe :src="`/preview/${route.params.id}/`" />
  </div>
</template>

<style>
.preview-page { height: 100vh; display: flex; flex-direction: column; margin: 0; }
.preview-page header { padding: 8px 16px; background: #0e7490; color: #fff; display: flex; justify-content: space-between; }
.preview-page header a { color: #cffafe; text-decoration: none; }
.preview-page iframe { flex: 1; border: 0; width: 100%; }
</style>
