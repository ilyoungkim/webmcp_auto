<script setup lang="ts">
// 영어 사일로용 — 설치 및 사용 방법 안내
const props = defineProps<{ projectId: string | number }>()
</script>

<template>
  <details class="install-accordion">
    <summary>📦 Installation & Usage</summary>
    <div class="install-body">
      <p class="note">Upload the <b>5 files</b> below to your website server and add the script right before <code>&lt;/body&gt;</code> of the page — the AI Assistant widget will appear.</p>

      <h3>Step 1: Upload files (hosting server)</h3>
      <ol class="install-steps">
        <li>Download <code>bundle.zip</code> with the <b>⬇ Download</b> button and extract it.</li>
        <li>Upload <b>all 5 files</b> to your website root (<code>public_html</code>, <code>www</code>, <code>html</code>) via FTP/SFTP or your hosting file manager.</li>
        <li>After uploading, check that <code>https://your-domain/webmcp-config.js</code> opens in a browser and shows the settings.</li>
      </ol>

      <h3>Step 2: Edit HTML (insert widget)</h3>
      <ol class="install-steps">
        <li>Open the HTML source of the page with your site admin tool or an HTML editor.</li>
        <li>Paste the code below <b>right before</b> the <code>&lt;/body&gt;</code> tag.</li>
      </ol>
      <pre><code>&lt;!-- WebMCP AI Assistant --&gt;
&lt;script src="webmcp-config.js"&gt;&lt;/script&gt;
&lt;script src="webmcp.js"&gt;&lt;/script&gt;
&lt;link rel="stylesheet" href="widget.css" /&gt;
&lt;script src="widget.js"&gt;&lt;/script&gt;</code></pre>
      <p class="note">💡 If you uploaded the files to a sub-folder (e.g. <code>/widget/</code>), update the <code>src</code> paths like <code>widget/webmcp-config.js</code>.</p>

      <h3>How to use</h3>
      <ul class="install-steps">
        <li>Click the 💬 button at the bottom-right to open the chat window.</li>
        <li>Quick menu buttons automatically insert pre-made questions.</li>
        <li>You can also type your own questions. Answers are generated from the collected site information.</li>
        <li>Check ⚙️ How it works for guidance and precautions about the AI assistant.</li>
      </ul>

      <div class="install-download">
        <a :href="`/api/projects/${projectId}/download/bundle.zip`" class="btn primary">⬇ Download (bundle.zip)</a>
      </div>
    </div>
  </details>
</template>