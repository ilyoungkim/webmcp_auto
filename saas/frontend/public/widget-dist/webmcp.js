// ============================================================================
// webmcp.js — WebMCP Auto SaaS 통신 계층 (v2.2) + Model Context 도구 등록
// ============================================================================
// 2계층 지식 구조 (v2.2):
//   - Tier 1: 빠른메뉴(중요 정보) = 개별 WebMCP 도구. 도구명/설명은 서버가
//     config.names[*].names[0] / description 으로 결정해 전달한다
//     (예: get_contact_information). JS 는 이를 그대로 사용한다.
//   - Tier 2: 나머지 전체 페이지 = get_page_answer(page, question) 도구로
//     페이지별 지식 검색 (config.pages 목록 노출, /api/chat/page-answer/ 호출).
//   - 자유 질문: ask_site_ai (항상 제공) — 기존과 동일.
// 계약 변경 (SaaS 플랫폼):
//   - body는 {question, publicId} 만 전송. 시스템 프롬프트는 서버가 부착.
//   - publicId는 window.WebMCPConfig.publicId 에서 읽음.
//   - 응답은 Gemini candidates 형태 또는 {text} 를 모두 지원.
// Chrome WebMCP 지원 (Chrome 150+ "WebMCP for testing" 플래그) 시:
//   - 빠른메뉴 질문을 document.modelContext 도구로 자동 등록하여
//     Chrome 사이드 패널(Inspector)·Gemini에서 사이트 도구로 실행 가능.
//   - 미지원 브라우저에서는 조용히 건너뛰어 기존 위젯과 100% 동일 동작.
// ============================================================================
(function () {
  'use strict';

  // 위젯은 고객 사이트(다른 오리진)에 임베드되므로 config.proxyEndpoint(절대 URL)를
  // 사용해 WebMCP 서버로 직접 호출한다. 서버가 CORS(Origin 화이트리스트)를 허용한다.
  // proxyEndpoint 가 없으면(구버전 config) 상대경로로 폴백한다.
  function proxyEndpoint() {
    var ep = (window.WebMCPConfig && window.WebMCPConfig.proxyEndpoint) || '';
    if (!ep) return '/api/chat/';
    return ep;
  }

  function publicId() {
    return (window.WebMCPConfig && (window.WebMCPConfig.publicId || window.WebMCPConfig.siteNs)) || '';
  }

  async function askQuestion(question, memory) {
    var res = await fetch(proxyEndpoint(), {
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

  // Tier 2 — 페이지별 지식 검색: {publicId, page, question} → /api/chat/page-answer/
  function pageAnswerEndpoint() {
    var ep = (window.WebMCPConfig && window.WebMCPConfig.pageAnswerEndpoint) || '';
    if (!ep) return '/api/chat/page-answer/';
    return ep;  // 절대 URL 그대로 사용 (서버가 CORS 허용)
  }

  async function askPageAnswer(page, question) {
    var res = await fetch(pageAnswerEndpoint(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ page: page || '', question: question || '', publicId: publicId() }),
    });
    if (!res.ok) {
      var errText = '';
      try { errText = await res.text(); } catch (_) {}
      var friendly = errText;
      try {
        var parsed = JSON.parse(errText);
        if (parsed && typeof parsed.error === 'string' && parsed.error) friendly = parsed.error;
      } catch (_) {}
      throw new Error('프록시 오류 (' + res.status + '): ' + friendly);
    }
    var data = await res.json();
    if (typeof data.text === 'string' && data.text) return data.text;
    var text = (data && data.candidates && data.candidates[0]
      && data.candidates[0].content && data.candidates[0].content.parts
      ? data.candidates[0].content.parts.map(function (p) { return p.text || ''; }).join('')
      : '');
    if (!text) throw new Error('프록시 응답이 비어 있습니다.');
    return text;
  }

  // Google WebMCP 보안 가이드의 도구 출력 문자 예산(1,500자) 준수용 클램프.
  // 에이전트 가드레일 회피 — 긴 LLM 응답을 문장 경계에서 잘라 말줄임 처리한다.
  var MAX_TOOL_OUTPUT = 1500;
  function clampToolOutput(text) {
    var s = String(text || '');
    if (s.length <= MAX_TOOL_OUTPUT) return s;
    var cut = s.slice(0, MAX_TOOL_OUTPUT - 1);
    // 마지막 문장 경계(마침표/물음표/느낌표/줄바꿈)에서 자르되, 너무 짧아지면 그대로 유지
    var last = Math.max(cut.lastIndexOf('.'), cut.lastIndexOf('!'), cut.lastIndexOf('?'), cut.lastIndexOf('。'), cut.lastIndexOf('！'), cut.lastIndexOf('？'), cut.lastIndexOf('\n'));
    if (last > MAX_TOOL_OUTPUT * 0.5) cut = cut.slice(0, last + 1);
    return cut.replace(/\s+$/, '') + '…';
  }

  window.WebMCP = Object.assign(window.WebMCP || {}, {
    askQuestion: askQuestion,
    askPageAnswer: askPageAnswer,
    callGeminiViaProxy: callGeminiViaProxy,
    proxyEndpoint: proxyEndpoint(),
    registerModelTools: registerModelTools,   // 디버깅/수동 재등록용 노출
  });

  // ─────────────────────────────────────────────────────────
  // Model Context 도구 등록 (Chrome WebMCP)
  // ─────────────────────────────────────────────────────────
  // document.modelContext 는 Chrome 150+ "WebMCP for testing" 플래그에서만 존재.
  // 스크립트 로드 시점에 아직 modelContext가 없을 수 있어(≤document_start 배치 순서)
  // 짧게 폴링하며 대기하고, 최대 3초 후 포기한다.
  function registerModelTools() {
    try {
      var cfg = window.WebMCPConfig || {};
      var mc = document.modelContext;
      if (!mc || typeof mc.registerTool !== 'function') return 0;

      // 이미 등록한 경우 중복 등록 방지 (같은 사이트에서 여러 번 로드될 때)
      if (window.WebMCP && window.WebMCP.__modelToolsRegistered) {
        return window.WebMCP.__modelToolsRegistered;
      }

      var registered = 0;
      var names = (cfg && cfg.names) || {};
      var siteName = (cfg && cfg.title) || document.title || 'this site';

      // 1) 빠른메뉴 질문을 도구로 노출 (names: { m0: { label, question }, ... })
      //    도구명은 반드시 고유해야 하므로 names[0]이 중복되면 라벨/key로 대체한다.
      //    한글 라벨은 영숫자로 변환되지 않으므로(빈 값) 후보 전이 소진되면 key 폴백 필수.
      var usedNames = {};
      var slug = function (s) {
        return String(s).toLowerCase()
          .replace(/[^a-z0-9_]+/g, '_')
          .replace(/^_+|_+$/g, '');
      };
      Object.keys(names).forEach(function (key) {
        var m = names[key] || {};
        var question = (m.question || '').trim();
        if (!question) return;
        var toolName = '';
        // 1순위: 서버가 결정한 Tier 1 표준 도구명 (get_contact_information 등)
        var serverName = (m.names && m.names[0]) || '';
        if (serverName && /^[a-z][a-z0-9_]{3,63}$/i.test(serverName) && !usedNames[serverName]) {
          toolName = serverName;
        } else {
          // 후보 순서: names[0] → 라벨 → config 키(m0/m1…) — 유니크 + 비어있지 않아야 채택
          var candidates = [serverName, m.label, 'menu_' + key].filter(Boolean);
          for (var i = 0; i < candidates.length; i++) {
            var cand = ('get_' + slug(String(candidates[i]))).replace(/_+$/, '');
            if (cand.length > 4 && !usedNames[cand]) { toolName = cand; break; }   // 'get_' 이상 유효
          }
        }
        if (!toolName) toolName = 'get_menu_' + Object.keys(usedNames).length;   // 최후 폴백
        toolName = toolName.slice(0, 40).replace(/_+$/, '');
        usedNames[toolName] = true;
        try {
          mc.registerTool({
            name: toolName,
            description: (m.description && String(m.description).trim()) || question,
            inputSchema: { type: 'object', properties: {} },
            annotations: { readOnlyHint: true },
            execute: function () {
              // 도구 실행 = 서버(system_prompt 부착) 프록시 호출 → AI 답변 텍스트 반환 (1,500자 클램프)
              return askQuestion(question).then(clampToolOutput).catch(function () {
                return '';
              });
            },
          });
          registered += 1;
        } catch (_) { /* 개별 도구 등록 실패는 전체 동작에 영향 없음 */ }
      });

      // 2) 사이트 전체 일반 질의 도구 (항상 1개 제공)
      if (!Object.keys(names).length) {
        try {
          mc.registerTool({
            name: 'get_site_info',
            description: 'Ask the AI assistant of ' + siteName + ' about any information on this site',
            inputSchema: {
              type: 'object',
              properties: { question: { type: 'string', description: 'The question to ask the site AI assistant' } },
              required: ['question'],
            },
            annotations: { readOnlyHint: true, untrustedContentHint: true },
            execute: function (args) {
              var q = (args && args.question) || '';
              if (!q) return '';
              return askQuestion(q).then(clampToolOutput).catch(function () {
                return '';
              });
            },
          });
          registered += 1;
        } catch (_) { /* 무시 */ }
      } else {
        // 빠른메뉴가 있어도 자유 질문용은 별도 제공
        try {
          mc.registerTool({
            name: 'ask_site_ai',
            description: 'Ask any free-form question to the AI assistant of ' + siteName,
            inputSchema: {
              type: 'object',
              properties: { question: { type: 'string', description: 'The question to ask' } },
              required: ['question'],
            },
            annotations: { readOnlyHint: true, untrustedContentHint: true },
            execute: function (args) {
              var q = (args && args.question) || '';
              if (!q) return '';
              return askQuestion(q).then(clampToolOutput).catch(function () {
                return '';
              });
            },
          });
          registered += 1;
        } catch (_) { /* 무시 */ }
      }

      window.WebMCP.__modelToolsRegistered = registered;
      if (registered && typeof console !== 'undefined' && console.debug) {
        console.debug('[WebMCP] ' + registered + ' model context tools registered');
      }
      return registered;
    } catch (_) {
      return 0;
    }
  }

  // modelContext는 페이지 로드 후 약간 늦게 노출될 수 있어 폴링으로 대기
  (function waitForModelContext(attempt) {
    var cfg = window.WebMCPConfig || {};
    if (typeof document === 'undefined') return;
    if (document.modelContext && typeof document.modelContext.registerTool === 'function') {
      registerModelTools();
      return;
    }
    if (attempt >= 20) return;   // 최대 ~3초(20×150ms) 후 포기 — 미지원 환경
    setTimeout(function () { waitForModelContext(attempt + 1); }, 150);
  })(0);
})();
