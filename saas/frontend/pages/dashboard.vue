<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Project {
  id: number
  publicId: string
  name: string
  url: string
  domainTypeCode: string
  status: string
  progress: number
}

const projects = ref<Project[]>([])
const editingId = ref<number | null>(null)
const editForm = ref({ name: '', url: '', domainTypeCode: 'hospital' })
const domainTypes = ref<any[]>([])
const saving = ref(false)
const isAdmin = ref(false)
const userEmail = ref('')

const { t, load: loadSilo } = useSilo()

// 사용자 메뉴 (비밀번호 변경 / 로그아웃)
const userMenuOpen = ref(false)
const pwModalOpen = ref(false)
const pwForm = ref({ current: '', new: '', confirm: '' })
const pwSaving = ref(false)
const pwError = ref('')
const pwSuccess = ref('')

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    queued: t('proj.status.queued'),
    crawling: t('proj.status.crawling'),
    generating: t('proj.status.generating'),
    completed: t('proj.status.completed'),
    failed: t('proj.status.failed'),
  }
  return map[s] || s
}

async function loadProjects() {
  projects.value = await useApi('/api/projects/')
  try {
    const me = await useApi('/api/auth/me/')
    isAdmin.value = me?.role === 'admin'
    userEmail.value = me?.email || ''
  } catch {
    isAdmin.value = false
  }
}

// ── 사용자 메뉴 ──────────────────────────────────────────────
function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function openPwModal() {
  pwForm.value = { current: '', new: '', confirm: '' }
  pwError.value = ''
  pwSuccess.value = ''
  pwModalOpen.value = true
  userMenuOpen.value = false
}

async function changePassword() {
  pwError.value = ''
  pwSuccess.value = ''
  if (pwForm.value.new !== pwForm.value.confirm) {
    pwError.value = t('dash.pw.mismatch')
    return
  }
  if (pwForm.value.new.length < 8) {
    pwError.value = t('dash.pw.tooShort')
    return
  }
  pwSaving.value = true
  try {
    await useApi('/api/auth/password/', {
      method: 'POST',
      body: { current: pwForm.value.current, new: pwForm.value.new },
    })
    pwSuccess.value = t('dash.pw.changed')
    pwForm.value = { current: '', new: '', confirm: '' }
  } catch (e: any) {
    pwError.value = e?.data?.detail || e?.data?.current?.[0] || t('dash.pw.failed')
  } finally {
    pwSaving.value = false
  }
}

async function logout() {
  try {
    await useApi('/api/auth/logout/', { method: 'POST' })
  } catch {
    // 로그아웃 실패해도 로컬 세션 정리 후 이동
  }
  // 세션 쿠키(sessionid)를 명시적으로 삭제해 비정상 접속을 차단
  document.cookie = 'sessionid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  navigateTo('/login')
}

function startEdit(p: Project) {
  editingId.value = p.id
  editForm.value = {
    name: p.name,
    url: p.url,
    domainTypeCode: p.domainTypeCode || 'hospital',
  }
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(id: number) {
  saving.value = true
  try {
    await useApi(`/api/projects/${id}/`, {
      method: 'PATCH',
      body: editForm.value,
    })
    editingId.value = null
    await loadProjects()
  } finally {
    saving.value = false
  }
}

async function removeProject(p: Project) {
  if (!confirm(t('proj.edit.deleteConfirm', { name: p.name }))) return
  await useApi(`/api/projects/${p.id}/`, { method: 'DELETE' })
  await loadProjects()
}

onMounted(async () => {
  await loadSilo()
  domainTypes.value = await useApi('/api/domain-types/')
  await loadProjects()
})
</script>

<template>
  <main class="wrap">
    <header>
      <h1>{{ t('dash.title') }}</h1>
      <div class="head-actions">
        <NuxtLink v-if="isAdmin" to="/admin/projects" class="btn">🛠 {{ t('dash.adminProjects') }}</NuxtLink>
        <NuxtLink v-if="isAdmin" to="/admin/chat-errors" class="btn">📮 {{ t('dash.errorReports') }}</NuxtLink>
        <NuxtLink to="/projects/new" class="btn primary">+ {{ t('dash.newProject') }}</NuxtLink>
        <div class="user-menu">
          <button class="btn user-btn" @click="toggleUserMenu">
            👤 {{ userEmail || t('dash.myAccount') }} ▾
          </button>
          <div v-if="userMenuOpen" class="user-dropdown">
            <NuxtLink to="/profile" class="menu-item">👤 {{ t('prof.title') }}</NuxtLink>
            <NuxtLink v-if="isAdmin" to="/admin/profile" class="menu-item">⚙️ {{ t('prof.adminTitle') }}</NuxtLink>
            <button class="menu-item" @click="openPwModal">🔑 {{ t('dash.changePw') }}</button>
            <button class="menu-item danger" @click="logout">🚪 {{ t('common.logout') }}</button>
          </div>
        </div>
      </div>
    </header>

    <p class="plan-note">{{ t('dash.planNote') }}</p>

    <!-- 비밀번호 변경 모달 -->
    <div v-if="pwModalOpen" class="modal-overlay" @click.self="pwModalOpen = false">
      <div class="modal-card">
        <header class="modal-header">
          <h3>{{ t('dash.changePw') }}</h3>
          <button class="close-btn" @click="pwModalOpen = false">&times;</button>
        </header>
        <div class="modal-body">
          <label>{{ t('dash.pw.current') }}
            <input v-model="pwForm.current" type="password" :placeholder="t('dash.pw.current')" />
          </label>
          <label>{{ t('dash.pw.new') }}
            <input v-model="pwForm.new" type="password" :placeholder="t('dash.pw.newPlaceholder')" />
          </label>
          <label>{{ t('dash.pw.confirm') }}
            <input v-model="pwForm.confirm" type="password" :placeholder="t('dash.pw.confirmPlaceholder')" />
          </label>
          <p v-if="pwError" class="err">{{ pwError }}</p>
          <p v-if="pwSuccess" class="ok">{{ pwSuccess }}</p>
        </div>
        <footer class="modal-footer">
          <button class="btn" @click="pwModalOpen = false">{{ t('proj.edit.cancel') }}</button>
          <button class="btn primary" :disabled="pwSaving" @click="changePassword">
            {{ pwSaving ? t('dash.pw.changing') : t('dash.changePw') }}
          </button>
        </footer>
      </div>
    </div>

    <ul class="project-list">
      <li v-for="p in projects" :key="p.id" class="project-item">
        <!-- 일반 보기 모드 -->
        <div v-if="editingId !== p.id" class="item-view">
          <div class="item-main">
            <NuxtLink :to="`/projects/${p.id}`" class="item-title">{{ p.name }}</NuxtLink>
            <span class="item-url">{{ p.url }}</span>
          </div>
          <div class="item-actions">
            <span class="badge" :class="p.status">{{ statusLabel(p.status) }} {{ p.progress }}%</span>
            <span v-if="p.status === 'failed'" class="fail-msg">{{ t('proj.edit.failMsg') }}</span>
            <button class="btn sm" @click="startEdit(p)">{{ t('proj.btn.edit') }}</button>
            <button class="btn sm danger" @click="removeProject(p)">{{ t('proj.btn.delete') }}</button>
          </div>
        </div>

        <!-- 인라인 수정 모드 -->
        <div v-else class="item-edit">
          <div class="form-row">
            <label>{{ t('dash.pw.nameLabel') }} <input v-model="editForm.name" /></label>
            <label>URL <input v-model="editForm.url" /></label>
            <label>{{ t('proj.edit.domainType') }}
              <select v-model="editForm.domainTypeCode">
                <option v-for="dt in domainTypes" :key="dt.code" :value="dt.code">{{ dt.name }}</option>
              </select>
            </label>
          </div>
          <div class="edit-actions">
            <button class="btn sm" @click="cancelEdit">{{ t('proj.edit.cancel') }}</button>
            <button class="btn sm primary" :disabled="saving" @click="saveEdit(p.id)">
              {{ saving ? t('proj.edit.saving') : t('proj.edit.save') }}
            </button>
          </div>
        </div>
      </li>
    </ul>

    <p v-if="!projects.length" class="empty">{{ t('dash.empty') }}</p>
  </main>
</template>

<style>
.wrap { max-width: 780px; margin: 48px auto; padding: 0 24px; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.head-actions { display: flex; gap: 8px; align-items: center; }
.head-actions .btn { text-decoration: none; padding: 8px 14px; font-size: 13px; }
.plan-note { margin: 0 0 20px; padding: 10px 14px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; font-size: 13px; color: #0c4a6e; }
.plan-note b { color: #0369a1; }

/* 사용자 메뉴 */
.user-menu { position: relative; }
.user-btn { white-space: nowrap; }
.user-dropdown { position: absolute; right: 0; top: calc(100% + 6px); background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); min-width: 160px; z-index: 100; overflow: hidden; }
.menu-item { display: block; width: 100%; text-align: left; padding: 10px 14px; border: none; background: none; cursor: pointer; font-size: 13px; color: #111827; }
.menu-item:hover { background: #f9fafb; }
.menu-item.danger { color: #b91c1c; }
.menu-item.danger:hover { background: #fef2f2; }

/* 비밀번호 변경 모달 */
.modal-body label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: #374151; }
.modal-body input { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.err { color: #b91c1c; font-size: 13px; margin: 4px 0 0; }
.ok { color: #047857; font-size: 13px; margin: 4px 0 0; }

.project-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 12px; }
.project-item { padding: 14px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.item-view { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.item-main { display: flex; flex-direction: column; gap: 4px; }
.item-title { font-size: 16px; font-weight: 600; color: #111827; text-decoration: none; }
.item-title:hover { color: #0e7490; }
.item-url { font-size: 12px; color: #6b7280; word-break: break-all; }
.item-actions { display: flex; gap: 6px; align-items: center; }
.badge { color: #0e7490; font-size: 12px; padding: 2px 8px; background: #f0f9ff; border-radius: 9999px; }
.badge.failed { color: #b91c1c; background: #fef2f2; }
.badge.completed { color: #047857; background: #ecfdf5; }
.fail-msg { color: #b91c1c; font-size: 12px; }
.btn { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; text-decoration: none; display: inline-block; }
.btn.sm { padding: 4px 8px; font-size: 12px; }
.btn.primary { background: #0e7490; color: #fff; border-color: #0e7490; }
.btn.danger { color: #b91c1c; border-color: #fca5a5; }
.btn:disabled { opacity: 0.5; cursor: default; }
.item-edit { display: flex; flex-direction: column; gap: 10px; }
.form-row { display: grid; grid-template-columns: 1fr 1.5fr 1fr; gap: 8px; }
.form-row label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #374151; }
.form-row input, .form-row select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }
.edit-actions { display: flex; justify-content: flex-end; gap: 6px; }
.empty { color: #6b7280; text-align: center; margin-top: 32px; }

/* 모달 스타일 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.modal-card { background: #fff; border-radius: 12px; width: 640px; max-width: 90vw; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
.modal-header h3 { margin: 0; font-size: 16px; font-weight: 600; }
.close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280; }
.modal-desc { padding: 12px 20px 0 20px; font-size: 13px; color: #4b5563; margin: 0; }
.modal-loading { padding: 40px 20px; text-align: center; color: #6b7280; font-size: 14px; }
.modal-body { padding: 12px 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 8px; }
.modal-footer { padding: 12px 20px; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 8px; }
</style>
