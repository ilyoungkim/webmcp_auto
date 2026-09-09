<script setup lang="ts">
// 영어 사일로용 — 설치 및 사용 방법 안내
const props = defineProps<{ projectId: string | number; publicId?: string; snippet?: string }>()
</script>

<template>
  <details class="install-accordion">
    <summary>📦 Installation &amp; Usage</summary>
    <div class="install-body">
      <p class="note">Paste the <b>single script line</b> below right before <code>&lt;/body&gt;</code> of the page — the AI Assistant widget will appear. No file upload is needed, so it works even on WordPress and other security-hardened hosts.</p>

      <h3>Step 1: Copy the install code</h3>
      <ol class="install-steps">
        <li><b>Copy</b> the code below.</li>
        <li>Open the HTML source of the page with your site admin tool or an HTML editor.</li>
        <li>Paste it <b>right before</b> the <code>&lt;/body&gt;</code> tag and save.</li>
      </ol>
      <pre><code>{{ snippet }}</code></pre>
      <p class="note">🔑 This project's unique ID (public_id): <code>{{ publicId }}</code></p>

      <h3>WordPress installation</h3>
      <ul class="install-steps">
        <li><b>Custom HTML block</b>: In the post/page editor, add a "Custom HTML" block and paste the code above.</li>
        <li><b>WPCode / Insert Headers and Footers plugin</b>: Install the plugin and paste the code into Header/Footer to apply it site-wide.</li>
        <li><b>Theme editor</b>: Appearance → Theme File Editor → paste into <code>footer.php</code>.</li>
      </ul>

      <h3>How to use</h3>
      <ul class="install-steps">
        <li>Click the 💬 button at the bottom-right to open the chat window.</li>
        <li>Quick menu buttons automatically insert pre-made questions.</li>
        <li>You can also type your own questions. Answers are generated from the collected site information.</li>
        <li>Check ⚙️ How it works for guidance and precautions about the AI assistant.</li>
      </ul>

      <details class="install-advanced">
        <summary>📦 Advanced: self-hosted bundle (bundle.zip)</summary>
        <p class="note">If you prefer to upload and manage the files on your own server, use the bundle below. (For most cases, the one-line install above is recommended.)</p>
        <div class="install-download">
          <a :href="`/api/projects/${projectId}/download/bundle.zip`" class="btn primary">⬇ Download (bundle.zip)</a>
        </div>
      </details>
    </div>
  </details>
</template>