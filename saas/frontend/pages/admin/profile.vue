<script setup lang="ts">
// 관리자 프로필 — 일반 프로필 + 사이트 대표 연락처(오류 안내 문구에 노출) 관리.
// 사용자 전화번호/엔터프라이즈 결제금액 개별 설정은 관리 화면(/admin/projects)에서.
definePageMeta({ middleware: 'admin' })

const { t, load: loadSilo, locale } = useSilo()

interface ProfileData {
  email: string
  name: string
  role: string
  plan: string
  phone1: string
  phone2: string
  billing_company: string
  billing_contact: string
  billing_email: string
  billing_address: string
  billing_note: string
  monthlyPrice: number | null
  monthlyCurrency: string
  billing: {
    defaultCurrency: string
    defaultPrice: number
    amount: number
    currency: string
    isEnterprise: boolean
    paymentReady: boolean
  }
  supportPhone: string
}

const profile = ref<ProfileData | null>(null)
const form = ref({
  name: '',
  phone1: '',
  phone2: '',
  billing_company: '',
  billing_contact: '',
  billing_email: '',
  billing_address: '',
  billing_note: '',
})
const supportPhone = ref('')
const supportPhoneDefault = ref('')
const supportSaving = ref(false)
const supportMessage = ref('')
const supportError = ref('')

const loading = ref(true)
const saving = ref(false)
const message = ref('')
const error = ref('')

const pwForm = ref({ current: '', new: '', confirm: '' })
const pwSaving = ref(false)
const pwError = ref('')
const pwSuccess = ref('')

async function loadProfile() {
  loading.value = true
  try {
    profile.value = await useApi('/api/auth/profile/')
    const p = profile.value
    form.value = {
      name: p.name || '',
      phone1: p.phone1 || '',
      phone2: p.phone2 || '',
      billing_company: p.billing_company || '',
      billing_contact: p.billing_contact || '',
      billing_email: p.billing_email || '',
      billing_address: p.billing_address || '',
      billing_note: p.billing_note || '',
    }
    supportPhone.value = p.supportPhone || ''
  } catch (e: any) {
    error.value = e?.data?.detail || t('prof.loadFailed')
  } finally {
    loading.value = false
  }
}

async function loadSettings() {
  try {
    const res = await useApi('/api/admin/settings/')
    supportPhoneDefault.value = res?.defaultSupportPhone || ''
    if (supportPhone.value === '') supportPhone.value = res?.supportPhone || ''
  } catch {
    // 설정 값은 빈 값 유지
  }
}

async function saveProfile() {
  message.value = ''
  error.value = ''
  saving.value = true
  try {
    profile.value = await useApi('/api/auth/profile/', { method: 'PATCH', body: form.value })
    message.value = t('prof.saved')
  } catch (e: any) {
    error.value = e?.data?.detail || Object.values(e?.data || {})[0] || t('prof.loadFailed')
  } finally {
    saving.value = false
  }
}

async function saveSupportPhone() {
  supportMessage.value = ''
  supportError.value = ''
  supportSaving.value = true
  try {
    const res = await useApi('/api/admin/settings/', {
      method: 'PATCH',
      body: { supportPhone: supportPhone.value },
    })
    supportPhone.value = res?.supportPhone || supportPhone.value
    supportMessage.value = t('prof.saved') + ' — ' + t('prof.supportPhone', { default: '' }).replace(/ \(.*\)$/, '')
  } catch (e: any) {
    supportError.value = e?.data?.detail || e?.data?.supportPhone?.[0] || '저장에 실패했습니다.'
  } finally {
    supportSaving.value = false
  }
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

function fmtPrice(amount: number, currency: string): string {
  // 숫자 구분 기호는 사일로 로케일을 따른다.
  if (currency === 'KRW') return `${Math.round(amount).toLocaleString(locale.value)}원`
  if (currency === 'USD') return `$${amount.toLocaleString(locale.value)}`
  return `${amount.toLocaleString(locale.value)} ${currency}`
}

onMounted(async () => {
  await loadSilo()
  await loadProfile()
  await loadSettings()
})
</script>

<template>
  <main class="wrap">
    <header>
      <h1>{{ t('prof.adminTitle') }}</h1>
      <div class="head-actions">
        <NuxtLink to="/admin/projects" class="btn-link">{{ t('dash.adminProjects') }}</NuxtLink>
        <NuxtLink to="/dashboard" class="back">{{ t('prof.backToDash') }}</NuxtLink>
      </div>
    </header>

    <p v-if="loading" class="muted">{{ t('common.loading') }}</p>
    <template v-else-if="profile">
      <!-- ── 사이트 대표 연락처 (관리자 전용) ──────────── -->
      <section class="card highlight">
        <h2>{{ t('prof.section.support') }}</h2>
        <div class="grid2">
          <label>
            <span class="label">{{ t('prof.supportPhone') }}</span>
            <input v-model="supportPhone" :placeholder="supportPhoneDefault" />
            <span class="hint">{{ t('prof.supportPhoneNote', { default: supportPhoneDefault }) }}</span>
          </label>
          <div class="save-col">
            <button class="btn primary" :disabled="supportSaving" @click="saveSupportPhone">
              {{ supportSaving ? t('prof.saving') : t('prof.save') }}
            </button>
            <p v-if="supportMessage" class="ok">{{ supportMessage }}</p>
            <p v-if="supportError" class="err">{{ supportError }}</p>
          </div>
        </div>
      </section>

      <!-- ── 계정 정보 ─────────────────────────────── -->
      <section class="card">
        <h2>{{ t('prof.section.account') }}</h2>
        <div class="grid2">
          <label>
            <span class="label">{{ t('prof.email') }}</span>
            <input :value="profile.email" disabled />
            <span class="hint">{{ t('prof.emailNote') }}</span>
          </label>
          <label>
            <span class="label">{{ t('prof.name') }}</span>
            <input v-model="form.name" :placeholder="t('prof.name')" />
          </label>
        </div>

        <h3 class="sub">🔒 {{ t('dash.changePw') }}</h3>
        <div class="grid3">
          <label>
            <span class="label">{{ t('dash.pw.current') }}</span>
            <input v-model="pwForm.current" type="password" autocomplete="current-password" />
          </label>
          <label>
            <span class="label">{{ t('dash.pw.new') }}</span>
            <input v-model="pwForm.new" type="password" autocomplete="new-password" :placeholder="t('dash.pw.newPlaceholder')" />
          </label>
          <label>
            <span class="label">{{ t('dash.pw.confirm') }}</span>
            <input v-model="pwForm.confirm" type="password" autocomplete="new-password" :placeholder="t('dash.pw.confirmPlaceholder')" />
          </label>
        </div>
        <p v-if="pwError" class="err">{{ pwError }}</p>
        <p v-if="pwSuccess" class="ok">{{ pwSuccess }}</p>
        <div class="row">
          <button class="btn" :disabled="pwSaving || !pwForm.current || !pwForm.new" @click="changePassword">
            {{ pwSaving ? t('dash.pw.changing') : t('dash.changePw') }}
          </button>
        </div>
      </section>

      <!-- ── 연락처 ─────────────────────────────────── -->
      <section class="card">
        <h2>{{ t('prof.section.contact') }}</h2>
        <div class="grid2">
          <label>
            <span class="label">{{ t('prof.phone1') }}</span>
            <input v-model="form.phone1" placeholder="02-888-9999" />
          </label>
          <label>
            <span class="label">{{ t('prof.phone2') }}</span>
            <input v-model="form.phone2" placeholder="010-1234-5678" />
          </label>
        </div>
        <p class="hint">{{ t('prof.phoneHint') }}</p>
      </section>

      <!-- ── 결제 정보 ──────────────────────────────── -->
      <section class="card">
        <h2>{{ t('prof.section.billing') }}</h2>

        <div class="price-box" :class="{ enterprise: profile.billing.isEnterprise }">
          <div class="price-main">
            <span class="price-label">{{ t('prof.billing.amount') }}</span>
            <span class="price-value">
              {{ fmtPrice(profile.billing.amount, profile.billing.currency) }}
            </span>
          </div>
          <span class="price-note">
            {{ profile.billing.isEnterprise
              ? t('prof.billing.enterprise')
              : `기본 요금: ${fmtPrice(profile.billing.defaultPrice, profile.billing.defaultCurrency)} / 월` }}
          </span>
        </div>

        <p class="gateway-note">
          💳 {{ t('prof.billing.gateway') }}: PayPal / Stripe — {{ t('prof.billing.gatewayPrep') }}
        </p>

        <div class="grid2">
          <label>
            <span class="label">{{ t('prof.billing.company') }}</span>
            <input v-model="form.billing_company" />
          </label>
          <label>
            <span class="label">{{ t('prof.billing.contact') }}</span>
            <input v-model="form.billing_contact" />
          </label>
          <label>
            <span class="label">{{ t('prof.billing.email') }}</span>
            <input v-model="form.billing_email" type="email" />
          </label>
          <label>
            <span class="label">{{ t('prof.billing.address') }}</span>
            <input v-model="form.billing_address" />
          </label>
        </div>
        <label class="full">
          <span class="label">{{ t('prof.billing.note') }}</span>
          <textarea v-model="form.billing_note" rows="2" />
        </label>
      </section>

      <p v-if="message" class="ok center">{{ message }}</p>
      <p v-if="error" class="err center">{{ error }}</p>

      <div class="row end">
        <button class="btn primary" :disabled="saving" @click="saveProfile">
          {{ saving ? t('prof.saving') : t('prof.save') }}
        </button>
      </div>
    </template>
  </main>
</template>

<style scoped>
.wrap { max-width: 760px; margin: 40px auto; padding: 0 24px; }
header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
h1 { margin: 0; font-size: 22px; }
h2 { margin: 0 0 14px; font-size: 16px; color: #111827; }
.head-actions { display: flex; gap: 14px; align-items: center; }
.btn-link { color: #0e7490; text-decoration: none; font-size: 13px; font-weight: 600; }
.back { color: #0e7490; text-decoration: none; font-size: 13px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px 20px; margin-bottom: 16px; }
.card.highlight { border-color: #fcd34d; background: #fffbeb; }
.sub { margin: 18px 0 10px; font-size: 14px; color: #374151; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
label { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
label.full { display: flex; }
.label { font-size: 12px; font-weight: 600; color: #374151; }
input, textarea { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; font-family: inherit; }
input:disabled { background: #f3f4f6; color: #6b7280; }
.hint { font-size: 11px; color: #9ca3af; }
.save-col { display: flex; align-items: flex-start; gap: 10px; flex-direction: column; padding-top: 18px; }
.row { display: flex; justify-content: flex-start; margin-top: 8px; }
.row.end { justify-content: flex-end; }
.btn { padding: 8px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; color: #111827; cursor: pointer; font-size: 13px; }
.btn.primary { background: #0e7490; color: #fff; border-color: #0e7490; }
.btn:disabled { opacity: 0.5; cursor: default; }
.price-box { padding: 12px 16px; border: 1px solid #bae6fd; background: #f0f9ff; border-radius: 8px; margin-bottom: 14px; display: flex; flex-direction: column; gap: 4px; }
.price-box.enterprise { border-color: #fcd34d; background: #fffbeb; }
.price-main { display: flex; align-items: baseline; gap: 10px; }
.price-label { font-size: 12px; color: #374151; font-weight: 600; }
.price-value { font-size: 20px; font-weight: 700; color: #0c4a6e; }
.price-box.enterprise .price-value { color: #92400e; }
.price-note { font-size: 12px; color: #6b7280; }
.gateway-note { margin: 0 0 14px; padding: 8px 12px; background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 6px; font-size: 12px; color: #6b7280; }
.muted { color: #6b7280; font-size: 13px; }
.err { color: #b91c1c; font-size: 13px; margin: 6px 0; }
.ok { color: #047857; font-size: 13px; margin: 6px 0; }
.center { text-align: center; }

@media (max-width: 640px) {
  .grid2, .grid3 { grid-template-columns: 1fr; }
}
</style>