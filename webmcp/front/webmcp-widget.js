// ============================================================================
// webmcp-widget.js — 공통 AI 비서 웹 위젯 라이브러리
// ============================================================================
// 버전: v1.1.0 (2026-08-22)
//   - v1.1.0: 🧠 대화 기억(Memory) 기능 추가
//     · 로컬스토리지(localStorage)에 질문-답변 쌍 저장 → 새로고침 후에도 유지
//     · 유사 질문 유추(단어 겹침 기반, 임계값 0.35) → 이전 답변을 컨텍스트로 사용
//     · 백엔드 API 없이 프론트엔드만으로 동작
//   - v1.0.0: 최초 공통 위젯 (마크다운 렌더링, pill, 상태 배지, 아코디언)
//
// 여러 도메인(yonja, hospital 등)이 공용으로 사용하는 위젯 로직.
// 사이트별 설정은 window.WebMCPConfig 에서 읽어옵니다.
//
//   - 마크다운 렌더링 (봇 답변)
//   - 퀵 질문 pill 버튼 (WebMCPConfig.names 기반)
//   - 상태 배지 (연결/AI)
//   - 동작 방식 아코디언
//   - 백엔드 프록시(webmcp.js) 호출
//   - 🧠 대화 기억(Memory) — 로컬스토리지 기반 유사 질문 유추
//
// 사용법:
//   <script src="webmcp.js"></script>          // 프록시 호출
//   <script src="webmcp-widget.js"></script>   // 공통 위젯
// ============================================================================
(function () {
  'use strict';

  var WIDGET_VERSION = '1.1.0'; // 🧠 메모리 기능 추가
  var ROOT_ID = 'webmcp-widget';

  function mount() {
    if (document.getElementById(ROOT_ID)) return;
    var root = document.createElement('div');
    root.id = ROOT_ID;
    root.innerHTML = widgetTemplate();
    document.body.appendChild(root);
    init();
  }

  function widgetTemplate() {
    return (
      '<button id="webmcpLauncher" class="wmcp-launcher" type="button" aria-label="AI 비서 열기">💬</button>' +
      '<div id="webmcpPanel" class="wmcp-panel" hidden>' +
      '  <header class="wmcp-header">' +
      '    <h1 id="wmcpTitle">💘 AI 비서</h1>' +
      '    <span class="wmcp-status" id="wmcpStatus">연결 확인 중...</span>' +
      '    <button id="wmcpExpand" class="wmcp-expand" type="button" title="크게 보기">⤢</button>' +
      '    <button id="wmcpClose" class="wmcp-close" type="button" title="닫기">✕</button>' +
      '  </header>' +
      '  <div id="wmcpChat" class="wmcp-chat" aria-live="polite"></div>' +
      '  <div class="wmcp-inputbar">' +
      '    <div id="wmcpPills" class="wmcp-pills"></div>' +
      '    <div class="wmcp-inputrow">' +
      '      <textarea id="wmcpInput" placeholder="메시지를 입력하세요..." rows="1"></textarea>' +
      '      <button id="wmcpAsk" class="wmcp-ask" type="button" title="보내기">➤</button>' +
      '    </div>' +
      '    <div class="wmcp-loader" id="wmcpLoader">💬 답변 생성 중...</div>' +
      '  </div>' +
      '  <details class="wmcp-accordion">' +
      '    <summary>⚙️ 동작 방식</summary>' +
      '    <div class="wmcp-acc-body">' +
      '      • AI비서는 LLM 모델을 사용한 수립, 정렬, 답변 에이전트입니다.' +
      '      <br />• AI비서의 답변은 환각으로 인해 올바르지 않은 정보가 제공될 수 있습니다.' +
      '      <br />• AI비서의 답변 정보는 고객사의 수집된 정보를 기반으로 합니다.' +
      '      <br />• AI비서의 답변 결과에 대해서 개발사는 책임을 지지 않습니다.' +
      '    </div>' +
      '  </details>' +
      '</div>'
    );
  }

  function $(sel) { return document.querySelector(sel); }

  // ── 사이트별 설정 (WebMCPConfig 기반) ────────────────────────
  // SaaS가 생성한 config는 siteNs='p{id}' 이므로 하드코딩 titles 맵에 의존하지 않고,
  // WebMCPConfig.title / names[group].label 을 우선 사용한다.
  function siteConfig() {
    var cfg = window.WebMCPConfig || {};
    var ns = cfg.siteNs || 'home';
    var names = cfg.names || {};
    // 사이트별 헤더 제목 — SaaS 생성 config.title 우선, 없으면 기존 하드코딩 폴백
    var titles = {
      yonja: '💘 연애의 자격 AI 비서',
      hospital: '🏥 생생병원 AI 비서',
      genisev: '🔋 제니스코리아 AI 비서',
    };
    return {
      title: cfg.title || titles[ns] || '💘 AI 비서',
      ns: ns,
      names: names,
      theme: cfg.theme || {},
    };
  }

  // ── 고객 사이트별 색상표(CSS 변수) 적용 ──────────────────────
  // WebMCPConfig.theme 에 정의된 색을 #webmcp-widget 의 CSS 변수로 주입.
  // theme 을 생략하거나 일부 키만 넣으면 나머지는 widget.css 기본값 사용.
  //   window.WebMCPConfig = {
  //     theme: {
  //       primary: '#85176d', primary2: '#e91b65', bg: '#f7f7fb',
  //       surface: '#ffffff', text: '#1f2937', textMuted: '#6b7280',
  //       textFaint: '#9ca3af', border: '#e5e7eb', codeBg: '#f3f4f6',
  //       pillBg: '#f3e8ff', errorBg: '#fef2f2', errorBorder: '#fca5a5',
  //       errorText: '#b91c1c',
  //     },
  //   };
  var THEME_MAP = {
    primary: '--wmcp-primary',
    primary2: '--wmcp-primary2',
    bg: '--wmcp-bg',
    surface: '--wmcp-surface',
    text: '--wmcp-text',
    textMuted: '--wmcp-text-muted',
    textFaint: '--wmcp-text-faint',
    border: '--wmcp-border',
    codeBg: '--wmcp-code-bg',
    pillBg: '--wmcp-pill-bg',
    errorBg: '--wmcp-error-bg',
    errorBorder: '--wmcp-error-border',
    errorText: '--wmcp-error-text',
  };
  function applyTheme() {
    var root = document.getElementById(ROOT_ID);
    if (!root) return;
    var theme = siteConfig().theme;
    Object.keys(THEME_MAP).forEach(function (key) {
      if (theme[key]) root.style.setProperty(THEME_MAP[key], theme[key]);
    });
  }

  // ── WebMCPConfig.names 로 pill 생성 ─────────────────────────
  function initPills() {
    var wrap = $('#wmcpPills');
    if (!wrap) return;
    var cfg = siteConfig();
    var names = cfg.names;
    Object.keys(names).forEach(function (group) {
      var meta = names[group];
      var label = meta.label || group;
      var question = meta.question || (group + ' 정보를 알려줘');
      var b = document.createElement('button');
      b.className = 'wmcp-pill';
      b.type = 'button';
      b.textContent = label;
      b.addEventListener('click', function () {
        var input = $('#wmcpInput');
        if (input) { input.value = question; handleAsk(); }
      });
      wrap.appendChild(b);
    });
  }

  // ── 마크다운 → HTML (확장 popup.js 와 동일) ──────────────────
  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function markdownToHtml(md) {
    var html = escapeHtml(md);
    html = html.replace(/```([\s\S]*?)```/g, function (_, code) {
      return '<pre class="md-code">' + code.trim() + '</pre>';
    });
    html = html.replace(/`([^`]+)`/g, '<code class="md-inline">$1</code>');
    html = html.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    // ── 자동 링크(autolink): 일반 URL(https://...) 을 링크로 변환 ──
    // 이미 마크다운 링크로 변환된 <a> 태그는 보호한 뒤, 나머지 URL만 링크화합니다.
    var protectedLinks = [];
    html = html.replace(/<a\s[^>]*>.*?<\/a>/g, function (m) {
      protectedLinks.push(m);
      return '\u0000' + (protectedLinks.length - 1) + '\u0000';
    });
    html = html.replace(
      /(https?:\/\/[^\s<]+)/g,
      '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    html = html.replace(/\u0000(\d+)\u0000/g, function (_, i) {
      return protectedLinks[+i];
    });
    // ── 마크다운 표(| ... |) → <table> 변환 ──
    // 구분선(|---|) 행은 헤더/본문 구분자로 사용하고, 첫 행은 <th> 로 처리합니다.
    html = html.replace(/(?:^\|.+\|\s*$\n?)+/gm, function (table) {
      var rows = table.trim().split('\n');
      var out = '<table class="md-table">';
      var isHeader = true;
      rows.forEach(function (row) {
        if (/^\|[\s:|-]+\|$/.test(row)) return; // 구분선 건너뛰기
        var cells = row.replace(/^\||\|$/g, '').split('|');
        var tag = isHeader ? 'th' : 'td';
        out += '<tr>' + cells.map(function (c) {
          return '<' + tag + '>' + c.trim() + '</' + tag + '>';
        }).join('') + '</tr>';
        isHeader = false;
      });
      out += '</table>';
      return out;
    });
    html = html.replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
    // ── 연속된 <li> 블록을 <ul>로 감싸고, <li> 사이의 줄바꿈만 제거 ──
    // (CSS 에 ul/ol/li 스타일이 정의되어 있어 들여쓰기가 적용됩니다)
    html = html.replace(/(?:<li>.*?<\/li>)(?:\n<li>.*?<\/li>)*/g, function (m) {
      return '<ul>' + m.replace(/\n/g, '') + '</ul>';
    });
    html = html.replace(/\n{2,}/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    return '<p>' + html + '</p>';
  }

  function addMsg(text, role, isError) {
    var chat = $('#wmcpChat');
    if (!chat) return;
    var wrap = document.createElement('div');
    wrap.className = 'wmcp-msg ' + (role || 'bot') + (isError ? ' error' : '');
    var bubble = document.createElement('div');
    bubble.className = 'wmcp-bubble';
    var content = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
    if (role === 'user') {
      bubble.textContent = content;
    } else if (isError) {
      // 오류는 아코디언(<details>)으로 감춰서 상세 내용을 접어둡니다.
      bubble.innerHTML =
        '<details class="wmcp-error-details">' +
        '<summary>⚠️ 오류가 발생했습니다 (클릭하여 상세보기)</summary>' +
        '<div class="wmcp-error-body">' + escapeHtml(content) + '</div>' +
        '</details>';
    } else {
      bubble.innerHTML = markdownToHtml(content);
    }
    wrap.appendChild(bubble);
    var time = document.createElement('div');
    time.className = 'wmcp-time';
    time.textContent = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    wrap.appendChild(time);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function setLoading(on) {
    var loader = $('#wmcpLoader');
    var ask = $('#wmcpAsk');
    if (loader) loader.classList.toggle('show', on);
    if (ask) ask.disabled = on;
  }

  function welcome() {
    var chat = $('#wmcpChat');
    if (!chat) return;
    chat.innerHTML = '';
    var cfg = siteConfig();
    addMsg('안녕하세요! ' + cfg.title + '입니다.\n궁금한 점을 물어보세요.', 'bot');
  }

  // ════════════════════════════════════════════════════════════════════════
  // 🧠 대화 기억(Memory) 모듈 — 백엔드 API 없이 로컬스토리지만 사용
  // ────────────────────────────────────────────────────────────────────────
  // 1) 로컬스토리지(localStorage)에 대화를 저장 → 새로고침/재접속 후에도 유지
  // 2) 유사 질문 유추 → 이전에 비슷한 질문을 한 적이 있으면 그 답변을
  //    컨텍스트로 함께 보내 AI가 "기억"한 것처럼 답하게 함
  // ※ 서버 API 없이 동작하므로 별도 백엔드 설정이 필요 없습니다.
  // ════════════════════════════════════════════════════════════════════════
  var MEMORY_KEY = 'wmcpMemory';          // 로컬스토리지 키
  var MEMORY_MAX = 50;                    // 보관할 최대 대화 쌍(질문-답변) 수
  var MEMORY_SIMILARITY = 0.35;           // 유사 질문 판단 임계값(0~1)

  // ── 메모리 읽기/쓰기 (로컬스토리지) ─────────────────────────
  function memoryLoad() {
    try {
      var raw = localStorage.getItem(MEMORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }
  function memorySave(list) {
    try { localStorage.setItem(MEMORY_KEY, JSON.stringify(list)); } catch (e) {}
  }

  // ── 대화 쌍(질문-답변) 추가 ─────────────────────────────────
  function memoryAdd(q, a) {
    var list = memoryLoad();
    list.push({ q: q, a: a, ts: new Date().toISOString() });
    if (list.length > MEMORY_MAX) list = list.slice(-MEMORY_MAX);
    memorySave(list);
  }

  // ── 유사 질문 찾기 (키워드 겹침 기반) ────────────────────────
  // 질문을 토큰(단어)으로 쪼개 이전 질문들과 겹치는 비율을 계산합니다.
  // 임계값(MEMORY_SIMILARITY) 이상 겹치면 "유사 질문"으로 간주해
  // 그때의 답변을 컨텍스트로 사용합니다.
  function tokenize(text) {
    return (text || '')
      .toLowerCase()
      .replace(/[^\w\s가-힣]/g, ' ')
      .split(/\s+/)
      .filter(function (t) { return t.length > 1; });
  }
  function similarity(a, b) {
    var ta = tokenize(a), tb = tokenize(b);
    if (!ta.length || !tb.length) return 0;
    var set = {};
    ta.forEach(function (t) { set[t] = true; });
    var hit = 0;
    tb.forEach(function (t) { if (set[t]) hit++; });
    return hit / Math.max(ta.length, tb.length);
  }
  function findSimilar(q) {
    var list = memoryLoad();
    var best = null, bestScore = 0;
    list.forEach(function (item) {
      var s = similarity(q, item.q);
      if (s > bestScore) { bestScore = s; best = item; }
    });
    return bestScore >= MEMORY_SIMILARITY ? best : null;
  }

  // ── 메모리 컨텍스트 조립 ────────────────────────────────────
  // 유사 질문이 있으면 "이전 대화 기억"을 프롬프트 앞에 붙여
  // AI가 이전 답변을 참고해 일관되게 답하도록 합니다.
  function buildMemoryContext(q) {
    var similar = findSimilar(q);
    if (!similar) return '';
    return (
      '[이전 대화 기억]\n' +
      '사용자가 이전에 비슷한 질문을 한 적이 있습니다. 아래 내용을 참고해 일관되게 답하세요.\n' +
      '이전 질문: ' + similar.q + '\n' +
      '이전 답변: ' + similar.a + '\n\n'
    );
  }

  async function handleAsk() {
    var input = $('#wmcpInput');
    var q = (input.value || '').trim();
    if (!q) return;
    addMsg(q, 'user');
    input.value = '';
    setLoading(true);
    try {
      if (typeof window.WebMCP === 'undefined' || typeof window.WebMCP.callGeminiViaProxy !== 'function') {
        throw new Error('webmcp.js(프록시)가 로드되지 않았습니다.');
      }
      // 사이트별 시스템 프롬프트 자동 선택
      // 1순위: SaaS가 생성한 window.P{siteNs}_SYSTEM_PROMPT (예: P12_SYSTEM_PROMPT)
      // 2순위: WebMCPConfig.systemPrompt (config에 직접 내장된 경우)
      // 3순위: 기존 하드코딩 전역변수 (yonja/hospital/genisev)
      var ns = siteConfig().ns;
      var saasPrompt = window['P' + ns + '_SYSTEM_PROMPT'];
      var systemPrompt = (saasPrompt
        || (window.WebMCPConfig && window.WebMCPConfig.system_prompt)
        || window.YONJA_SYSTEM_PROMPT
        || window.HOSPITAL_SYSTEM_PROMPT
        || window.GENISEV_SYSTEM_PROMPT
        || '') + '\n\n';
      // 🧠 이전 대화 기억 컨텍스트 (유사 질문이 있으면 자동 포함)
      var memoryContext = buildMemoryContext(q);
      var answer = await window.WebMCP.callGeminiViaProxy(memoryContext + systemPrompt + '사용자 질문: ' + q);
      addMsg(answer, 'bot');
      // 🧠 이번 질문-답변을 메모리에 저장 (로컬 + 서버)
      memoryAdd(q, answer);
    } catch (e) {
      addMsg('오류: ' + (e.message || e), 'bot', true);
    } finally {
      setLoading(false);
    }
  }

  // ── 채팅 내 링크 새 탭으로 열기 ──────────────────────────────
  function initChatLinks() {
    var chat = $('#wmcpChat');
    if (!chat) return;
    chat.addEventListener('click', function (e) {
      var anchor = e.target.closest('a');
      if (!anchor) return;
      e.preventDefault();
      var url = anchor.getAttribute('href');
      if (url && /^https?:\/\//i.test(url)) window.open(url, '_blank', 'noopener');
    });
  }

  // ── 연결 상태 확인 (헤더 배지) ───────────────────────────────
  function setStatus(text, ok) {
    var status = $('#wmcpStatus');
    if (!status) return;
    status.textContent = text;
    status.style.background = ok ? 'rgba(22,163,74,0.3)' : 'rgba(220,38,38,0.3)';
  }

  async function refresh() {
    var status = $('#wmcpStatus');
    if (!status) return;
    status.textContent = '연결 확인 중...';
    status.style.background = 'rgba(255,255,255,0.2)';

    // 1) 프록시 라이브러리 로드 여부
    if (typeof window.WebMCP === 'undefined' || typeof window.WebMCP.callGeminiViaProxy !== 'function') {
      setStatus('⚠️ 프록시 미로드', false);
      return;
    }

    // 2) 백엔드 헬스체크 (프록시가 실제 응답하는지)
    try {
      var proxy = window.WebMCP.proxyEndpoint || '/api/chat';
      var healthUrl = proxy.replace(/\/api\/chat$/, '/health');
      var res = await fetch(healthUrl, { method: 'GET' });
      if (res.ok) {
        setStatus('✅ 연결됨', true);
      } else {
        setStatus('⚠️ 연결 안 됨', false);
      }
    } catch (e) {
      setStatus('⚠️ 연결 안 됨', false);
    }
  }

  function init() {
    applyTheme(); // 고객 사이트별 색상표(CSS 변수) 적용
    var launcher = $('#webmcpLauncher');
    var panel = $('#webmcpPanel');
    var close = $('#wmcpClose');
    if (launcher && panel) {
      launcher.addEventListener('click', function () {
        panel.hidden = !panel.hidden;
        if (!panel.hidden) { welcome(); $('#wmcpInput').focus(); }
      });
    }
    if (close && panel) {
      close.addEventListener('click', function () { panel.hidden = true; });
    }
    var expand = $('#wmcpExpand');
    if (expand && panel) {
      expand.addEventListener('click', function () {
        var expanded = panel.classList.toggle('wmcp-panel--expanded');
        expand.textContent = expanded ? '⤣' : '⤢';
        expand.title = expanded ? '작게 보기' : '크게 보기';
      });
    }
    var input = $('#wmcpInput');
    if (input) {
      input.addEventListener('keydown', function (e) {
        if (e.isComposing) return;
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); }
      });
    }
    var ask = $('#wmcpAsk');
    if (ask) ask.addEventListener('click', handleAsk);
    // 사이트별 헤더 제목 설정
    var titleEl = $('#wmcpTitle');
    if (titleEl) titleEl.textContent = siteConfig().title;
    initPills();
    initChatLinks();
    refresh(); // 연결 상태 배지 갱신
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
