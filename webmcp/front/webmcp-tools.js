// ============================================================================
// webmcp-tools.js — Google 표준 WebMCP 도구 등록 (점진적 개선)
// ============================================================================
// Google(Chrome)이 제안하는 표준 WebMCP API(document.modelContext)로
// window.WebMCPConfig.items 에 정의된 툴들을 등록합니다.
//
//   - 기존 위젯(Gemini 프록시 채팅)과 완전히 독립적으로 동작 (공존 가능)
//   - document.modelContext 가 나중에 준비될 수 있으므로 폴링(재시도) 처리
//   - 표준 API 미지원 브라우저에서는 조용히 무시 (점진적 개선 방식)
//   - Chrome 149+ / chrome://flags/#enable-webmcp-testing 활성화 필요
//
// 사용법 (각 config.js 다음, widget.js 이전에 로드):
//   <script src="hospital-config.js"></script>
//   <script src="webmcp.js"></script>
//   <script src="webmcp-tools.js"></script>
//   <script src="widget.js"></script>
// ============================================================================
(function () {
  'use strict';

  var DEBUG = true; // 콘솔 상세 로그 (배포 시 false 로 변경 가능)

  function log(level, msg) {
    if (!DEBUG && level === 'info') return;
    var fn = level === 'warn' ? console.warn : level === 'error' ? console.error : console.info;
    fn('[webmcp-tools] ' + msg);
  }

  function getModelContext() {
    // Chrome 150+ : document.modelContext
    // (navigator.modelContext 는 지원 중단됨)
    return document.modelContext || null;
  }

  function isSupported(mc) {
    return !!(mc && typeof mc.registerTool === 'function');
  }

  // JSON.stringify 안전 처리 (undefined/function 제거)
  function safeStringify(value, fallback) {
    try {
      if (value === undefined || value === null) return '';
      if (typeof value === 'string') return value;
      return JSON.stringify(value);
    } catch (e) {
      return fallback || String(value);
    }
  }

  // 시도 횟수 추적 (중복 등록 방지)
  var _registered = false;
  var _attempts = 0;
  var _maxAttempts = 20;   // 최대 폴링 횟수
  var _interval = 250;     // 250ms 간격 (총 약 5초)

  async function registerTools() {
    // 이미 등록됐으면 스킵
    if (_registered) return;

    var mc = getModelContext();
    var cfg = window.WebMCPConfig || {};
    var items = cfg.items || [];

    // ── 1) 표준 API 아직 미준비 → 폴링 재시도 ──
    if (!isSupported(mc)) {
      _attempts++;
      if (_attempts <= _maxAttempts) {
        if (_attempts === 1) {
          log('info', 'document.modelContext 아직 준비 안 됨 → ' + _interval + 'ms 간격으로 ' + _maxAttempts + '회 대기 중...');
        }
        setTimeout(registerTools, _interval);
        return;
      }
      // 최대 시도 초과
      log('warn', '표준 WebMCP API(document.modelContext)를 찾지 못했습니다. ' +
          'Chrome 149+ 에서 chrome://flags/#enable-webmcp-testing 을 활성화했는지 확인하세요.');
      return;
    }

    // ── 2) items 비어있으면 대기 (config 로딩 지연 대비) ──
    if (!items.length) {
      _attempts++;
      if (_attempts <= _maxAttempts) {
        setTimeout(registerTools, _interval);
        return;
      }
      log('warn', 'WebMCPConfig.items 가 비어 있습니다. config 스크립트 로딩을 확인하세요.');
      return;
    }

    // ── 3) 도구 등록 ──
    _registered = true;
    var siteNs = cfg.siteNs || 'site';
    var registered = 0;

    log('info', '도구 등록 시작 (siteNs: ' + siteNs + ', 총 ' + items.length + '개)');

    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var toolName = siteNs + '.' + item.group + '.' + item.name;

      try {
        await mc.registerTool({
          name: toolName,
          description: item.description || item.title || toolName,
          inputSchema: item.inputSchema || { type: 'object', properties: {} },
          execute: async function (args) {
            try {
              var data = (typeof item.getData === 'function')
                ? item.getData(args)
                : item.getData;
              return safeStringify(data, '조회 결과 없음');
            } catch (e) {
              return '도구 실행 오류: ' + (e && e.message ? e.message : e);
            }
          },
        });
        registered++;
        log('info', '✅ 도구 등록됨: ' + toolName);
      } catch (e) {
        log('error', '❌ 도구 등록 실패: ' + toolName + ' — ' + (e && e.message ? e.message : e));
      }
    }

    log('info', '총 ' + registered + '/' + items.length + '개 도구 등록 완료');

    // 디버그용: 실제 등록된 도구 목록 출력
    if (DEBUG && typeof mc.getTools === 'function') {
      try {
        mc.getTools().then(function (tools) {
          log('info', '브라우저가 인식한 도구 목록: ' + tools.map(function (t) { return t.name; }).join(', '));
        }).catch(function () {});
      } catch (_) {}
    }
  }

  // ── 실행: DOMContentLoaded 이후 + 즉시 둘 다 시도 ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', registerTools);
  }
  // 즉시도 시도 (config가 이미 로드된 경우 빠르게 등록)
  registerTools();
})();