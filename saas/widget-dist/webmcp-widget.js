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

  var WIDGET_VERSION = '1.2.0'; // 🌐 다국어(i18n) 지원
  var ROOT_ID = 'webmcp-widget';

  // ── 다국어 사전 (config.lang 으로 선택) ──────────────────────
  var I18N = {
    ko: {
      launcherAria: 'AI 비서 열기',
      title: '✨ AI 비서',
      statusChecking: '연결 확인 중...',
      statusOk: '연결됨',
      statusFail: '연결 안 됨',
      statusNoProxy: '프록시 미로드',
      inputPlaceholder: '메시지를 입력하세요...',
      inputBusy: '답변 생성 중...',
      micLabel: '음성<br/>입력',
      loader: '✨ 답변 생성 중...',
      howItWorks: '⚙️ 동작 방식',
      howBody:
        '      • AI비서는 LLM 모델을 사용한 수립, 정렬, 답변 에이전트입니다.' +
        '      <br />• AI비서의 답변은 환각으로 인해 올바르지 않은 정보가 제공될 수 있습니다.' +
        '      <br />• AI비서의 답변 정보는 고객사의 수집된 정보를 기반으로 합니다.' +
        '      <br />• AI비서의 답변 결과에 대해서 개발사는 책임을 지지 않습니다.',
      welcome: '안녕하세요! {title}입니다.\n궁금한 점을 물어보세요.',
      send: '보내기',
      // ── 아래 키는 v1.3.0 에서 하드코딩을 사전으로 이관한 것 ──
      defaultTitle: '✨ AI 비서',
      expandTitle: '크게 보기',
      shrinkTitle: '작게 보기',
      closeTitle: '닫기',
      askForInfo: '{group} 정보를 알려줘',
      reportReceived: '✅ 오류가 접수되었습니다. 빠르게 확인하겠습니다.',
      reportFailed: '⚠️ 오류 접수에 실패했습니다. 잠시 후 다시 시도해주세요.',
      errorOccurred: '⚠️ 오류가 발생했습니다 (클릭하여 상세보기)',
      reportButton: '📮 오류 신고하기',
      errorPrefix: '오류: ',
      proxyNotLoaded: 'webmcp.js(프록시)가 로드되지 않았습니다.',
      micStart: '음성 입력',
      micStop: '음성 입력 중지',
      micInsecure: '⚠️ 음성 입력은 보안 연결(HTTPS)에서만 사용할 수 있습니다. HTTPS 주소로 접속하거나 직접 입력해 주세요.',
      memoryHeader: '[이전 대화 기억]',
      memoryIntro: '사용자가 이전에 비슷한 질문을 한 적이 있습니다. 아래 내용을 참고해 일관되게 답하세요.',
      memoryPrevQ: '이전 질문: ',
      memoryPrevA: '이전 답변: ',
    },
    en: {
      launcherAria: 'Open AI Assistant',
      title: '✨ AI Assistant',
      statusChecking: 'Checking connection...',
      statusOk: 'Connected',
      statusFail: 'Not connected',
      statusNoProxy: 'Proxy not loaded',
      inputPlaceholder: 'Type a message...',
      inputBusy: 'Generating answer...',
      micLabel: 'Voice<br/>input',
      loader: '✨ Generating answer...',
      howItWorks: '⚙️ How it works',
      howBody:
        '      • This assistant is an LLM-based agent for planning, sorting and answering.' +
        '      <br />• Answers may be inaccurate due to model hallucinations.' +
        '      <br />• Answers are based on information collected from the customer website.' +
        '      <br />• The developer is not responsible for generated answers.',
      welcome: 'Hello! This is the {title}.\nAsk me anything.',
      send: 'Send',
      // ── 아래 키는 v1.3.0 에서 하드코딩을 사전으로 이관한 것 ──
      defaultTitle: '✨ AI Assistant',
      expandTitle: 'Expand',
      shrinkTitle: 'Shrink',
      closeTitle: 'Close',
      askForInfo: 'Tell me about {group}',
      reportReceived: '✅ Your report has been received. We will look into it shortly.',
      reportFailed: '⚠️ Failed to submit the report. Please try again later.',
      errorOccurred: '⚠️ An error occurred (click for details)',
      reportButton: '📮 Report this error',
      errorPrefix: 'Error: ',
      proxyNotLoaded: 'webmcp.js (proxy) is not loaded.',
      micStart: 'Voice input',
      micStop: 'Stop voice input',
      micInsecure: '⚠️ Voice input requires a secure connection (HTTPS). Please open this page over HTTPS or type your question.',
      memoryHeader: '[Previous conversation memory]',
      memoryIntro: 'The user has asked a similar question before. Use the context below to answer consistently.',
      memoryPrevQ: 'Previous question: ',
      memoryPrevA: 'Previous answer: ',
    },
  };

  function t(key, params) {
    var lang = (window.WebMCPConfig && window.WebMCPConfig.lang) || 'ko';
    var dict = I18N[lang] || I18N.ko;
    var out = dict[key] !== undefined ? dict[key] : (I18N.ko[key] !== undefined ? I18N.ko[key] : key);
    // {group} / {title} 등 플레이스홀더 치환
    if (params) {
      Object.keys(params).forEach(function (k) {
        out = out.split('{' + k + '}').join(String(params[k]));
      });
    }
    return out;
  }

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
      '<button id="webmcpLauncher" class="wmcp-launcher" type="button" aria-label="' + t('launcherAria') + '">' +
      '  <span class="wmcp-launcher-ai">AI</span>' +
      '  <span class="wmcp-launcher-spark">✦</span>' +
      '</button>' +
      '<div id="webmcpPanel" class="wmcp-panel" hidden>' +
      '  <header class="wmcp-header">' +
      '    <span class="wmcp-header-logo">AI</span>' +
      '    <h1 id="wmcpTitle">' + t('title') + '</h1>' +
      '    <span class="wmcp-status" id="wmcpStatus">' + t('statusChecking') + '</span>' +
      '    <button id="wmcpExpand" class="wmcp-expand" type="button" title="' + t('expandTitle') + '">⤢</button>' +
      '    <button id="wmcpClose" class="wmcp-close" type="button" title="' + t('closeTitle') + '">✕</button>' +
      '  </header>' +
      '  <div id="wmcpChat" class="wmcp-chat" aria-live="polite"></div>' +
      '  <div class="wmcp-inputbar">' +
      '    <div id="wmcpPills" class="wmcp-pills"></div>' +
      '    <div class="wmcp-inputrow">' +
      '      <textarea id="wmcpInput" placeholder="' + t('inputPlaceholder') + '" rows="1"></textarea>' +
      '      <button id="wmcpMic" class="wmcp-mic" type="button" title="' + (t('launcherAria')) + '">' +
      '        <span class="wmcp-mic-text">' + t('micLabel') + '</span>' +
      '      </button>' +
      '      <button id="wmcpAsk" class="wmcp-ask" type="button" title="' + t('send') + '">➤</button>' +
      '    </div>' +
      '    <div class="wmcp-loader" id="wmcpLoader">' + t('loader') + '</div>' +
      '  </div>' +
      '  <details class="wmcp-accordion">' +
      '    <summary>' + t('howItWorks') + '</summary>' +
      '    <div class="wmcp-acc-body">' +
      t('howBody') +
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
    // 데모용 하드코딩 타이틀 — ko 사일로 전용. en은 사전 기본값 사용.
    var titles = {
      ko: {
        yonja: '✨ 연애의 자격 AI 비서',
        hospital: '🏥 생생병원 AI 비서',
        genisev: '🔋 제니스코리아 AI 비서',
      },
      en: {
        yonja: '✨ Dating Qualification AI Assistant',
        hospital: '🏥 Saengsaeng Hospital AI Assistant',
        genisev: '🔋 Genis Korea AI Assistant',
      },
    };
    var lang = cfg.lang || 'ko';
    var byLang = titles[lang] || titles.ko;
    return {
      title: cfg.title || byLang[ns] || t('defaultTitle'),
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
      var question = meta.question || t('askForInfo', { group: group });
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

  // HTML 속성값에 안전하게 넣기 위한 이스케이프
  function escapeAttr(str) {
    return escapeHtml(str).replace(/`/g, '&#96;');
  }

  // ── 오류 신고하기 ────────────────────────────────────────────
  function reportError(errorText) {
    var payload = {
      publicId: (window.WebMCPConfig && (window.WebMCPConfig.publicId || window.WebMCPConfig.siteNs)) || '',
      question: (($('#wmcpInput') || {}).value || '').trim(),
      errorMessage: (errorText || '').slice(0, 2000),
      errorDetail: (errorText || '').slice(0, 8000),
    };
    var endpoint = (window.WebMCPConfig && window.WebMCPConfig.proxyEndpoint)
      ? window.WebMCPConfig.proxyEndpoint.replace(/\/$/, '') + '/report/'
      : '/api/chat/report/';
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    }).then(function (res) {
      if (res.ok) {
        addMsg(t('reportReceived'), 'bot');
      } else {
        addMsg(t('reportFailed'), 'bot', true);
      }
    }).catch(function () {
      addMsg(t('reportFailed'), 'bot', true);
    });
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
        '<summary>' + escapeHtml(t('errorOccurred')) + '</summary>' +
        '<div class="wmcp-error-body">' + escapeHtml(content) + '</div>' +
        '</details>' +
        '<button type="button" class="wmcp-error-report" data-error="' + escapeAttr(content) + '">' + escapeHtml(t('reportButton')) + '</button>';
    } else {
      bubble.innerHTML = markdownToHtml(content);
    }
    wrap.appendChild(bubble);
    var time = document.createElement('div');
    time.className = 'wmcp-time';
    var timeLocale = ((window.WebMCPConfig && window.WebMCPConfig.lang) === 'en') ? 'en-US' : 'ko-KR';
    time.textContent = new Date().toLocaleTimeString(timeLocale, { hour: '2-digit', minute: '2-digit' });
    wrap.appendChild(time);
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function setLoading(on) {
    var loader = $('#wmcpLoader');
    var ask = $('#wmcpAsk');
    var input = $('#wmcpInput');
    var mic = $('#wmcpMic');
    if (loader) loader.classList.toggle('show', on);
    if (ask) ask.disabled = on;
    // 답변 생성 중에는 입력을 받지 않도록 비활성화
    if (input) {
      input.disabled = on;
      input.placeholder = on ? t('inputBusy') : t('inputPlaceholder');
    }
    if (mic) mic.disabled = on;
    // 퀵 메뉴(빠른메뉴 pill)도 비활성화
    var pills = document.querySelectorAll('#webmcp-widget .wmcp-pill');
    for (var i = 0; i < pills.length; i++) pills[i].disabled = on;
  }

  function welcome() {
    var chat = $('#wmcpChat');
    if (!chat) return;
    chat.innerHTML = '';
    var cfg = siteConfig();
    addMsg(t('welcome').replace('{title}', cfg.title), 'bot');
  }

  // ════════════════════════════════════════════════════════════════════════
  // 🧠 대화 기억(Memory) 모듈 — 백엔드 API 없이 로컬스토리지만 사용
  // ────────────────────────────────────────────────────────────────────────
  // 1) 로컬스토리지(localStorage)에 대화를 저장 → 새로고침/재접속 후에도 유지
  // 2) 유사 질문 유추 → 이전에 비슷한 질문을 한 적이 있으면 그 답변을
  //    컨텍스트로 함께 보내 AI가 "기억"한 것처럼 답하게 함
  // ※ 서버 API 없이 동작하므로 별도 백엔드 설정이 필요 없습니다.
  // ════════════════════════════════════════════════════════════════════════
  var MEMORY_KEY = 'wmcpMemory:' + ((window.WebMCPConfig && (window.WebMCPConfig.publicId || window.WebMCPConfig.siteNs)) || 'default'); // publicId 스코프
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
      t('memoryHeader') + '\n' +
      t('memoryIntro') + '\n' +
      t('memoryPrevQ') + similar.q + '\n' +
      t('memoryPrevA') + similar.a + '\n\n'
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
        throw new Error(t('proxyNotLoaded'));
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
      // 시스템 프롬프트는 서버가 부착하므로 여기서는 보내지 않는다.
      // 깨끗한 질문(q)을 보내야 프록시가 DB 캐시(빠른메뉴)를 정확히 매칭한다.
      var memoryContext = buildMemoryContext(q);
      var answer = await window.WebMCP.callGeminiViaProxy(q, memoryContext);
      addMsg(answer, 'bot');
      // 🧠 이번 질문-답변을 메모리에 저장 (로컬 + 서버)
      memoryAdd(q, answer);
    } catch (e) {
      addMsg(t('errorPrefix') + (e.message || e), 'bot', true);
    } finally {
      setLoading(false);
    }
  }

  // ── 채팅 내 링크 새 탭으로 열기 + 오류 신고하기 ──────────────
  function initChatLinks() {
    var chat = $('#wmcpChat');
    if (!chat) return;
    chat.addEventListener('click', function (e) {
      var reportBtn = e.target.closest('.wmcp-error-report');
      if (reportBtn) {
        e.preventDefault();
        var errText = reportBtn.getAttribute('data-error') || '';
        reportError(errText);
        return;
      }
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
    status.textContent = t('statusChecking');
    status.style.background = 'rgba(255,255,255,0.2)';

    // 1) 프록시 라이브러리 로드 여부
    if (typeof window.WebMCP === 'undefined' || typeof window.WebMCP.callGeminiViaProxy !== 'function') {
      setStatus('⚠️ ' + t('statusNoProxy'), false);
      return;
    }

    // 2) 백엔드 헬스체크 (프록시가 실제 응답하는지)
    //    위젯은 같은 오리진에서 서빙되므로 상대경로로 호출한다.
    //    (proxyEndpoint 가 절대 URL(localhost 등)이면 127.0.0.1 접속 시 CORS 로 차단됨)
    try {
      var healthUrl = '/api/health/';
      var res = await fetch(healthUrl, { method: 'GET' });
      if (!res.ok) {
        healthUrl = '/health/';
        res = await fetch(healthUrl, { method: 'GET' });
      }
      if (res.ok) {
        setStatus('✅ ' + t('statusOk'), true);
      } else {
        setStatus('⚠️ ' + t('statusFail'), false);
      }
    } catch (e) {
      setStatus('⚠️ ' + t('statusFail'), false);
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
        if (!panel.hidden) {
          welcome();
          // ⚠️ 모바일에서는 자동 포커스하지 않는다 — 소프트 키보드가 즉시 떠오르면
          // 100dvh 패널이 밀려 인사말이 키보드 뒤로 가려진다. 데스크톱만 자동 포커스.
          var isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
          if (!isTouch && $('#wmcpInput')) $('#wmcpInput').focus();
        }
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
        expand.title = expanded ? t('shrinkTitle') : t('expandTitle');
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
    initMic(); // 음성 입력
    // 사이트별 헤더 제목 설정
    var titleEl = $('#wmcpTitle');
    if (titleEl) titleEl.textContent = siteConfig().title;
    initPills();
    initChatLinks();
    refresh(); // 연결 상태 배지 갱신
  }

  // ── 음성 입력 (Web Speech API) ─────────────────────────────
  var recognition = null;
  var listening = false;

  function initMic() {
    var mic = $('#wmcpMic');
    if (!mic) return;
    // Web Speech API 지원 여부 확인 — Chrome은 http(비보안 콘텍스트)에서 지원해도
    // **마이크 권한 요청이 차단**된다 (getUserMedia = Secure Context 필수).
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    var insecure = (typeof window.isSecureContext === 'boolean' && !window.isSecureContext);
    if (!SR) {
      mic.style.display = 'none'; // 미지원 브라우저에서는 숨김
      return;
    }
    recognition = new SR();
    // 음성 인식 언어도 사일로 언어에 맞춘다 (en 위젯에서 한국어 인식 방지)
    recognition.lang = ((window.WebMCPConfig && window.WebMCPConfig.lang) === 'en') ? 'en-US' : 'ko-KR';
    recognition.interimResults = true;   // 실시간 인식 결과 표시
    recognition.maxAlternatives = 1;
    recognition.continuous = false;      // 말이 끝나면 자동 종료

    recognition.onresult = function (e) {
      var input = $('#wmcpInput');
      if (!input) return;
      var transcript = '';
      for (var i = e.resultIndex; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      input.value = transcript;
      input.focus();
    };
    recognition.onerror = function (e) {
      clearMicTimeout();
      setMicState(false);
      // 실패 사유를 사용자에게 표시 — 갤럭시(안드로이드 크롬)의 http 접속은
      // 마이크 권한이 자동 거부(not-allowed)되어 무음으로 끝난다.
      var code = (e && e.error) || 'unknown';
      var isEn = (window.WebMCPConfig && window.WebMCPConfig.lang) === 'en';
      var msg = MIC_ERRORS[code] !== undefined ? MIC_ERRORS[code] : MIC_ERRORS['unknown'];
      if (typeof msg === 'object') msg = isEn ? msg.en : msg.ko;
      if (msg) addMsg(msg, 'bot', false);
    };
    recognition.onend = function () {
      clearMicTimeout();
      setMicState(false);
      // 음성 인식이 끝나면 입력된 내용이 있으면 자동으로 질문 전송
      var input = $('#wmcpInput');
      if (input && input.value.trim()) {
        handleAsk();
      }
    };

    mic.addEventListener('click', function () {
      if (listening) {
        clearMicTimeout();
        setMicState(false);          // 즉시 UI 해제 (테두리 잔존 방지 — onend보다 우선)
        try { recognition.stop(); } catch (_) {}
      } else {
        // 보안 콘텍스트(http)가 아니면 마이크 권한 요청 자체가 차단되므로 사전 안내
        if (insecure) {
          addMsg(t('micInsecure'), 'bot', false);
          return;
        }
        try {
          recognition.start();
          setMicState(true);
          // some browsers fail silently → 8초 내 결과/에러/종료가 없으면 타임아웃 안내
          clearMicTimeout();
          micTimeoutId = setTimeout(function () {
            if (listening) {
              try { recognition.stop(); } catch (_) {}
              setMicState(false);
            }
          }, 8000);
        } catch (err) {
          setMicState(false);
        }
      }
    });
  }

  function clearMicTimeout() {
    if (micTimeoutId) { clearTimeout(micTimeoutId); micTimeoutId = null; }
  }

  // 오류 코드별 사용자 안내 — ko/en 병기 (config.lang 으로 선택)
  var MIC_ERRORS = {
    'not-allowed': { ko: '⚠️ 마이크 권한이 거부되었습니다. 브라우저 설정에서 마이크 권한을 허용해 주세요.', en: '⚠️ Microphone permission was denied. Allow mic access in browser settings and retry.' },
    'service-not-allowed': { ko: '⚠️ 마이크/서비스 권한이 차단되었습니다. 브라우저 설정 또는 HTTPS 접속을 확인해 주세요.', en: '⚠️ Mic/service permission blocked. Check browser settings or use HTTPS.' },
    'audio-capture': { ko: '⚠️ 마이크를 찾을 수 없습니다. 마이크 연결을 확인해 주세요.', en: '⚠️ No microphone found. Check your device.' },
    'network': { ko: '⚠️ 음성 인식 서비스에 연결할 수 없습니다. 네트워크를 확인해 주세요.', en: '⚠️ Speech service unreachable. Check your network.' },
    'no-speech': { ko: '⚠️ 인식된 음성이 없습니다. 다시 한 번 말씀해 주세요.', en: '⚠️ No speech detected. Please try again.' },
    'aborted': '' , // 사용자가 취소한 경우 — 안내 생략
    'unknown': { ko: '⚠️ 음성 입력에 실패했습니다. 다시 시도해 주세요.', en: '⚠️ Voice input failed. Please try again.' }
  };

  function setMicState(on) {
    listening = on;
    var mic = $('#wmcpMic');
    if (!mic) return;
    // 해제 시 pulse 애니메이션까지 확실히 제거 (브라우저별 애니메이션 상태 잔존 방지)
    mic.classList.remove('wmcp-mic--active');
    if (on) mic.classList.add('wmcp-mic--active');
    mic.title = on ? t('micStop') : t('micStart');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
