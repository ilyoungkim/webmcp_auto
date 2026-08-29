// ============================================================================
// webmcp.js — WebMCP Auto SaaS 통신 계층 (v2.0)
// ============================================================================
// 계약 변경 (SaaS 플랫폼):
//   - body는 {question, publicId} 만 전송. 시스템 프롬프트는 서버가 부착.
//   - publicId는 window.WebMCPConfig.publicId 에서 읽음.
//   - 응답은 Gemini candidates 형태 또는 {text} 를 모두 지원.
// ============================================================================
(function () {
  'use strict';

  // 위젯은 같은 오리진에서 서빋되므로 상대경로로 호출한다.
  // (proxyEndpoint 가 절대 URL(localhost 등)이면 127.0.0.1 접속 시 CORS 로 차단됨)
  var PROXY_ENDPOINT = '/api/chat/';

  function publicId() {
    return (window.WebMCPConfig && (window.WebMCPConfig.publicId || window.WebMCPConfig.siteNs)) || '';
  }

  async function askQuestion(question, memory) {
    var res = await fetch(PROXY_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ question: question, publicId: publicId(), memory: memory || '' }),
    });
    if (!res.ok) {
      var errText = '';
      try { errText = await res.text(); } catch (_) {}
      // 오류 응답이 JSON 이면 error 필드의 실제 텍스트를 추출한다.
      // (Django JsonResponse 는 한글을 \uXXXX 로 이스케이프하므로 그대로 보이면 안 됨)
      var friendly = errText;
      try {
        var parsed = JSON.parse(errText);
        if (parsed && typeof parsed.error === 'string' && parsed.error) {
          friendly = parsed.error;
        }
      } catch (_) { /* JSON 이 아니면 원본 텍스트 사용 */ }
      throw new Error('프록시 오류 (' + res.status + '): ' + friendly);
    }
    var data = await res.json();
    // 신규 계약: {text}
    if (typeof data.text === 'string' && data.text) return data.text;
    // 레거시 호환: Gemini candidates
    var text = (data && data.candidates && data.candidates[0]
      && data.candidates[0].content && data.candidates[0].content.parts
      ? data.candidates[0].content.parts.map(function (p) { return p.text || ''; }).join('')
      : '');
    if (!text) throw new Error('프록시 응답이 비어 있습니다.');
    return text;
  }

  // 레거시 함수명 유지 (기존 webmcp-widget.js 호환)
  // question: 깨끗한 사용자 질문, memory: 이전 대화 기억 컨텍스트(선택)
  async function callGeminiViaProxy(question, memory) {
    return askQuestion(question, memory);
  }

  window.WebMCP = Object.assign(window.WebMCP || {}, {
    askQuestion: askQuestion,
    callGeminiViaProxy: callGeminiViaProxy,
    proxyEndpoint: PROXY_ENDPOINT,
  });
})();
