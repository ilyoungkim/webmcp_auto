<script setup lang="ts">
definePageMeta({ middleware: 'admin' })

const { t, load: loadSilo, formatDate } = useSilo()

interface ChatError {
  id: number
  publicId: string
  projectName: string
  origin: string
  question: string
  errorMessage: string
  errorDetail: string
  ip: string
  userAgent: string
  status: string
  createdAt: string
}

const errors = ref<ChatError[]>([])
const loading = ref(false)
const filter = ref('')
const expanded = ref<Set<number>>(new Set())

const STATUS_LABELS = computed<Record<string, string>>(() => ({
  new: t('admin.errors.new'),
  read: t('admin.errors.read'),
  resolved: t('admin.errors.resolved'),
}))

async function load() {
  loading.value = true
  try {
    const q = filter.value ? `?status=${filter.value}` : ''
    errors.value = await useApi(`/api/admin/chat-errors/${q}`)
  } finally {
    loading.value = false
  }
}

async function setStatus(r: ChatError, status: string) {
  await useApi(`/api/admin/chat-errors/${r.id}/`, {
    method: 'PATCH',
    body: { status },
  })
  r.status = status
}

function toggle(id: number) {
  const s = new Set(expanded.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expanded.value = s
}

function fmtTime(iso: string): string {
  return formatDate(iso)
}

onMounted(async () => {
  await loadSilo()
  load()
})
</script>

<template>
  <main class="wrap">
    <header class="head">
      <NuxtLink to="/dashboard" class="back-link">{{ t('prof.backToDash') }}</NuxtLink>
      <h1>{{ t('admin.errors.title') }}</h1>
      <div class="filters">
        <select v-model="filter" @change="load">
          <option value="">{{ t('admin.errors.all') }}</option>
          <option value="new">{{ t('admin.errors.new') }}</option>
          <option value="read">{{ t('admin.errors.read') }}</option>
          <option value="resolved">{{ t('admin.errors.resolved') }}</option>
        </select>
        <button class="btn" @click="load">{{ t('admin.projects.refresh') }}</button>
      </div>
    </header>

    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <p v-else-if="errors.length === 0" class="muted">{{ t('admin.errors.empty') }}</p>

    <div v-else class="error-list">
      <div v-for="r in errors" :key="r.id" class="error-card" :class="r.status">
        <div class="error-head" @click="toggle(r.id)">
          <span class="badge" :class="r.status">{{ STATUS_LABELS[r.status] || r.status }}</span>
          <span class="msg">{{ r.errorMessage }}</span>
          <span class="time">{{ fmtTime(r.createdAt) }}</span>
        </div>

        <div v-if="expanded.has(r.id)" class="error-detail">
          <dl>
            <dt>{{ t('admin.errors.project') }}</dt>
            <dd>{{ r.projectName || r.publicId || '-' }}</dd>
            <dt>Origin</dt>
            <dd>{{ r.origin || '-' }}</dd>
            <dt>{{ t('admin.errors.question') }}</dt>
            <dd>{{ r.question || '-' }}</dd>
            <dt>IP</dt>
            <dd>{{ r.ip || '-' }}</dd>
            <dt>User-Agent</dt>
            <dd class="wrap-text">{{ r.userAgent || '-' }}</dd>
            <dt>{{ t('admin.errors.detail') }}</dt>
            <dd><pre class="err-pre">{{ r.errorDetail || r.errorMessage }}</pre></dd>
          </dl>
          <div class="actions">
            <button class="btn" :class="{ active: r.status === 'read' }" @click="setStatus(r, 'read')">{{ t('admin.errors.read') }}</button>
            <button class="btn" :class="{ active: r.status === 'resolved' }" @click="setStatus(r, 'resolved')">{{ t('admin.errors.resolved') }}</button>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.wrap { max-width: 860px; margin: 40px auto; padding: 0 24px; }
.head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.head h1 { margin: 0; font-size: 22px; flex: 1; }
.back-link { color: #0e7490; text-decoration: none; font-size: 13px; }
.filters { display: flex; gap: 8px; align-items: center; }
.filters select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
.btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; }
.btn.active { background: #0e7490; color: #fff; border-color: #0e7490; }
.muted { color: #6b7280; font-size: 13px; }

.error-list { display: flex; flex-direction: column; gap: 10px; }
.error-card { border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; overflow: hidden; }
.error-card.new { border-left: 4px solid #dc2626; }
.error-card.read { border-left: 4px solid #d97706; }
.error-card.resolved { border-left: 4px solid #059669; }
.error-head { display: flex; align-items: center; gap: 10px; padding: 12px 14px; cursor: pointer; }
.error-head:hover { background: #f9fafb; }
.badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; flex-shrink: 0; }
.badge.new { background: #fee2e2; color: #b91c1c; }
.badge.read { background: #fef3c7; color: #92400e; }
.badge.resolved { background: #d1fae5; color: #065f46; }
.msg { flex: 1; font-size: 13px; color: #111827; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.time { font-size: 11px; color: #9ca3af; flex-shrink: 0; }

.error-detail { padding: 12px 14px; border-top: 1px solid #f3f4f6; background: #fafafa; }
.error-detail dl { margin: 0; display: grid; grid-template-columns: 90px 1fr; gap: 6px 12px; font-size: 13px; }
.error-detail dt { color: #6b7280; font-weight: 600; }
.error-detail dd { margin: 0; color: #1f2937; word-break: break-all; }
.wrap-text { word-break: break-all; }
.err-pre { margin: 0; padding: 8px 10px; background: #111827; color: #f9fafb; border-radius: 6px; font-size: 11px; white-space: pre-wrap; word-break: break-all; max-height: 240px; overflow-y: auto; }
.actions { display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end; }
</style>