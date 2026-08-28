// ============================================================================
// widget.js — AI 비서 웹 위젯 (공통 라이브러리 로더)
// ============================================================================
// 실제 위젯 로직은 공통 라이브러리 webmcp-widget.js 에 있습니다.
// 이 파일은 webmcp-widget.js 를 동적으로 로드하는 얇은 래퍼입니다.
//
// 사용법:
//   <script src="webmcp.js"></script>          // 프록시 호출
//   <script src="widget.js"></script>          // 공통 위젯 로더 (webmcp-widget.js 로드)
//
// ────────────────────────────────────────────────────────────────────────────
// 2개 JS 파일의 역할과 특징
// ────────────────────────────────────────────────────────────────────────────
// [1] webmcp.js — 공용 WebMCP 라이브러리 (프록시 연동)
//   역할:
//     - Gemini API 키를 직접 들고 있지 않고, 모든 질문을 백엔드 프록시
//       (POST /api/chat)로 전송하는 "통신 계층" 담당
//     - window.WebMCP.callGeminiViaProxy(prompt) 를 전역에 노출
//   특징:
//     - 키 노출 없음 → 보안 안전 (키는 서버 DB에만 존재)
//     - Origin 헤더를 브라우저가 자동 첨부 → 서버가 도메인(테넌트) 판별
//     - 프록시 엔드포인트는 WebMCPConfig.proxyEndpoint 로 오버라이드 가능
//     - 사이트 공통으로 1회만 로드하면 되는 "공용 통신 라이브러리"
//
// [2] widget.js — AI 비서 웹 위젯 (공통 라이브러리 로더)
//   역할:
//     - 실제 위젯 UI(마크다운 렌더링, 픽스, 상태 배지, 아코디언 등)를
//       담은 webmcp-widget.js 를 동적으로 로드하는 "얇은 래퍼"
//     - window.WebMCPWidgetLoaded 플래그로 중복 로드 방지
//   특징:
//     - 로더 역할만 하므로 매우 가볍고(약 1KB) 사이트별 수정이 거의 없음
//     - DOMContentLoaded 이후에 공통 라이브러리를 안전하게 로드
//     - 사이트별 제목/픽스는 WebMCPConfig(예: hospital-config.js)에서 주입
//
// ※ 결론: webmcp.js = "통신", widget.js = "로더", webmcp-widget.js = "UI"
//   세 파일이 분리되어 있어 사이트마다 webmcp.js + widget.js 만 붙이면
//   동일한 AI 비서 위젯을 재사용할 수 있습니다.
// ============================================================================
(function () {
  'use strict';

  // 공통 라이브러리 로드 (이미 로드되어 있으면 스킵)
  // 💡 ?v= 버전 쿼리스트링: common 라이브러리(webmcp-widget.js)를 수정&배포했을 때
  //    브라우저 캐시가 구버전을 반환하는 문제를 방지합니다. widget.js를 수정했으면
  //    아래 버전 값을 올리세요. (yonja/hospital/genisev 모두 이 파일을 공유)
  //    SaaS가 생성한 config는 WebMCPConfig.widgetVersion 을 내장하므로 이를 우선 사용합니다.
  function loadCommonWidget() {
    if (window.WebMCPWidgetLoaded) return;
    var cfg = window.WebMCPConfig || {};
    var v = cfg.widgetVersion || '1';
    var base = cfg.assetBase || '';
    var s = document.createElement('script');
    s.src = base + 'webmcp-widget.js?v=' + v;
    s.async = false;
    document.body.appendChild(s);
    window.WebMCPWidgetLoaded = true;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadCommonWidget);
  } else {
    loadCommonWidget();
  }
})();
