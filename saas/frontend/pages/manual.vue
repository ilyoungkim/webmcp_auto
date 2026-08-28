<template>
  <main class="wrap">
    <h1>적용 매뉴얼</h1>
    <h2>1. 권장 설치 (호스팅 1줄)</h2>
    <pre><code>&lt;script src="https://&lt;saas-host&gt;/embed/&lt;publicId&gt;.js" async&gt;&lt;/script&gt;</code></pre>
    <h2>2. 자체 호스팅 번들</h2>
    <p>bundle.zip을 홈페이지 루트에 풀고:</p>
    <pre><code>&lt;script src="webmcp-config.js"&gt;&lt;/script&gt;
&lt;script src="webmcp.js"&gt;&lt;/script&gt;
&lt;link rel="stylesheet" href="widget.css" /&gt;
&lt;script src="widget.js"&gt;&lt;/script&gt;</code></pre>
    <h2>3. Origin 등록</h2>
    <p>프로젝트 URL의 Origin은 자동 등록됩니다. www/스테이징 도메인은 콘솔에서 추가하세요.</p>
    <h2>4. 문제 해결</h2>
    <ul>
      <li><b>403</b>: 위젯을 붙인 도메인이 Origin 화이트리스트에 없음</li>
      <li><b>429</b>: 플랜 호출 한도 초과</li>
      <li><b>CSP 오류</b>: 고객 사이트 CSP에 SaaS 호스트를 script-src에 추가</li>
    </ul>
  </main>
</template>

<style>
.wrap { max-width: 720px; margin: 48px auto; padding: 0 24px; }
pre { background: #f3f4f6; padding: 12px; border-radius: 8px; overflow-x: auto; }
</style>
