<template>
  <main class="wrap">
    <h1>{{ t('manual.title') }}</h1>
    <h2>{{ t('manual.recommended') }}</h2>
    <pre><code>&lt;script src="https://&lt;saas-host&gt;/embed/&lt;publicId&gt;.js" async&gt;&lt;/script&gt;</code></pre>
    <h2>{{ t('manual.bundle') }}</h2>
    <p>{{ t('manual.bundleDesc') }}</p>
    <pre><code>&lt;script src="webmcp-config.js"&gt;&lt;/script&gt;
&lt;script src="webmcp.js"&gt;&lt;/script&gt;
&lt;link rel="stylesheet" href="widget.css" /&gt;
&lt;script src="widget.js"&gt;&lt;/script&gt;</code></pre>
    <h2>{{ t('manual.origin') }}</h2>
    <p>{{ t('manual.originDesc') }}</p>
    <h2>{{ t('manual.troubleshoot') }}</h2>
    <ul>
      <li><b>403</b>: {{ t('manual.ts403') }}</li>
      <li><b>429</b>: {{ t('manual.ts429') }}</li>
      <li><b>CSP</b>: {{ t('manual.tsCsp') }}</li>
    </ul>
  </main>
</template>

<script setup lang="ts">
// 사일로 언어별 문구 — useSilo 는 useState 싱글턴이므로 컴포저블에서 한 번만 호출한다.
const { t } = useSilo()
</script>

<style>
.wrap { max-width: 720px; margin: 48px auto; padding: 0 24px; }
pre { background: #f3f4f6; padding: 12px; border-radius: 8px; overflow-x: auto; }
</style>
