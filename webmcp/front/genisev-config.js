// ============================================================================
// genisev-config.js — 제니스코리아(Genis EV) 기준 WebMCPConfig + 시스템 프롬프트
// ============================================================================
// - window.WebMCPConfig : webmcp.js가 툴 등록에 사용 (genisev)
// - window.GENISEV_SYSTEM_PROMPT : AI 비서에게 제니스코리아 지식을 주입
// ============================================================================
window.WebMCPConfig = {
  siteNs: 'genisev',
  lang: 'ko',
  debug: true,
  proxyEndpoint: '/api/chat',
  // ── 고객 사이트별 색상표 (CSS 변수) ─────────────────────────
  // 제미니(제니스) 브랜드: 붉은색 바탕 + 옅은 하늘색 조합
  theme: {
    primary:    '#c62828',   // 메인 브랜드 색 (제미니 레드)
    primary2:   '#e53935',   // 그라디언트 보조 색 (밝은 레드)
    bg:         '#e3f2fd',   // 패널 바탕색 (옅은 하늘색)
    surface:    '#ffffff',   // 봇 말풍선/입력바 배경
    text:       '#1f2937',   // 기본 텍스트
    textMuted:  '#6b7280',   // 보조 텍스트
    textFaint:  '#9ca3af',   // 약한 텍스트
    border:     '#e5e7eb',   // 테두리
    codeBg:     '#f3f4f6',   // 코드 블록 배경
    pillBg:     '#ffebee',   // 픽스 칩 배경 (옅은 레드)
    errorBg:    '#fef2f2',   // 오류 말풍선 배경
    errorBorder: '#fca5a5',  // 오류 말풍선 테두리
    errorText:  '#b91c1c',   // 오류 말풍선 텍스트
  },
  // ── 빠른 메뉴 (퀵 질문 pill) ────────────────────────────────
  names: {
    intro:    { names: ['get_info'], description: '제니스코리아 회사 소개', label: '제니스코리아 소개', question: '제니스코리아 회사를 소개해줘' },
    charging: { names: ['get_info'], description: '충전 솔루션(SECC/EVCC) 안내', label: 'Charging', question: '충전 솔루션(SECC, EVCC)에 대해 알려줘' },
    bms:      { names: ['get_info'], description: 'BMS(배터리 관리 시스템) 안내', label: 'BMS', question: 'BMS(배터리 관리 시스템)에 대해 알려줘' },
    contact: { names: ['get_info'], description: '계약/문의 안내', label: 'Contact', question: '계약 및 문의 방법을 알려줘' },
  },
  items: [
    {
      group: 'intro',
      name: 'get_info',
      title: '제니스코리아 소개',
      description: '제니스코리아의 회사 개요, 사업 분야, 연락처를 조회합니다.',
      getData: {
        name: '㈜제니스코리아 (Genis Korea)',
        intro: '전기차 부품 및 솔루션 전문 기업입니다.',
        vision: {
          deployedUnits: '국내외 10,000개 이상의 GENIS Device/System이 사용되며 고객에게 지원하고 있습니다.',
          projects: '34개의 프로젝트를 성공적으로 수행하여 전문성과 기술력을 입증했습니다.',
          customers: '전기차 충전 솔루션과 배터리 관리 시스템 분야에서 50개의 고객사와 협력하고 있습니다.',
        },
        customers: [
          {
            group: '충전 사업자 & 충전기 제조사',
            desc: '국내 전기차 충전기 제조사들에게 2000대가 넘는 PLC 모뎀을 제공하고 있습니다. 제니스 PLC 통신 모뎀(CSM)을 적용하면 DIN70121 / ISO15118을 지원하는 국제표준기반 전기차 충전기를 생산할 수 있습니다.',
          },
          {
            group: '전기차 OEM & Partners',
            desc: '국내 초소형 자동차 및 상용자동차에 제니스 PLC 통신 모뎀이 제공되며, DIN70121 / ISO15118 스펙 기반으로 동작합니다. 초기 전장 설계 시 제니스 엔지니어의 개발 경험을 적용하여 성공적인 전기차 개발이 이루어질 수 있습니다.',
          },
          {
            group: 'BMS 고객사',
            desc: '전기스쿠터, 전기버스, 상용차 등 다양한 분야의 BMS 경험이 있습니다. Automotive 스펙으로 하드웨어가 설계되어 있으며 신뢰성 높은 소프트웨어 로직으로 BMS 솔루션을 제공합니다.',
          },
        ],
        address: '본사: [13646] 경기도 성남시 수정구 위례광장로19 아이페리온 1103호',
        factory: '공장: [54158] 전북 군산시 동장산 2길 6 자동차융합기술원 본관동 2207호',
        sales: 'sales@genisev.com | Tel: +82-70-8836-8365',
        url: 'http://genisev.com',
      },
    },
    {
      group: 'charging',
      name: 'get_info',
      title: '충전 솔루션 (Communication Controller)',
      description: '전기차 충전 통신 제어기(SECC, EVCC) 정보를 조회합니다.',
      getData: {
        secc: {
          name: 'SECC (Supply Equipment Communication Controller)',
          desc: 'CSM은 전기차와 PLC 통신을 이용하여 충전제어 메시지를 송수신하는 통신 모뎀입니다. 국제 표준 기반 충전 프로토콜이 적용되어 있습니다.',
          spec: {
            'Interface to connect with EVSE': 'CAN 2.0 B, 500KBps, Sampling Point 75%',
            'Communication': 'PLC: HomePlug Green PHY™ / Wi-Fi: ISO/IEC 15118-8 (Opt.) / PWM / CAN, RS-232',
            'SECC Function': 'IEC61851, DIN70121, ISO/IEC 15118 AC/DC EIM, PnC',
            'Debug Interface': 'RS-232, CAN',
            'Operating Voltage': '9V ~ 38V',
            'Operating Temperature': '-20℃ ~ 85℃',
            'OS': 'Linux 4.1.18',
            'Security': 'Hardware Security Module (Opt.)',
            'Dimensions': '88mm x 90mm x 29mm(H)',
          },
          url: 'http://genisev.com/secc/',
        },
        evcc: {
          name: 'EVCC (Electric Vehicle Communication Controller)',
          desc: 'CEM은 전기차 충전기와 충전제어 메시지를 송수신하는 전기차 PLC 통신 모뎀입니다. VCU, BMS, OBC와 통신하여 충전에 필요한 정보를 수집하여 충전을 제어합니다.',
          spec: {
            'Interface': 'CAN 2.0 B, 500KBps',
            'PLC Communication': 'HPGP (HomePlug Green PHY™), ISO/IEC 15118-3 표준 준수',
            'EVCC Function': 'IEC 61851, DIN 70121, ISO15118 AC/DC Charging Control, Inlet-Temperature Sensing, Actuator Control (Opt.)',
            'Debug Interface': 'RS-232, CAN',
            'Operating Voltage': '9V ~ 38V',
            'Operating Temperature': '-40℃ ~ 125℃',
            'OS': 'RTOS',
            'Dimension': '160 * 120 * 40',
            'IP': 'IPX5',
            'Case': 'Aluminum',
          },
          url: 'http://genisev.com/evcc/',
        },
      },
    },
    {
      group: 'bms',
      name: 'get_info',
      title: 'BMS 솔루션',
      description: 'BMS(배터리 관리 시스템) 솔루션 정보를 조회합니다.',
      getData: {
        name: 'Battery Management System',
        desc: '기능별로 모듈화하여 유연한 개발 환경 & 확장성을 제공합니다.',
        architecture: 'BMS 아키텍처는 지게차, 전기버스, 전기스쿠터, 초소형 전기차용 배터리 시스템 및 에너지 저장 시스템을 위한 혁신적인 하드웨어를 제공합니다. 소프트웨어 솔루션에서 10년 이상 개발한 결과를 반영하여 안정적인 솔루션을 제공합니다. 초기 전장 설계 시 제니스 엔지니어의 개발 경험을 적용하여 성공적인 전기차 개발이 이루어질 수 있습니다.',
        url: 'http://genisev.com/battery-management-system/',
      },
    },
    {
      group: 'contact',
      name: 'get_info',
      title: '계약/문의',
      description: '계약 및 문의 방법을 조회합니다.',
      getData: {
        hq: '[13646] 경기도 성남시 수정구 위례광장로19 아이페리온 1103호',
        factory: '[54158] 전북 군산시 동장산 2길 6 자동차융합기술원 본관동 2207호',
        sales: 'sales@genisev.com',
        phone: '+82-70-8836-8365',
        contactUrl: 'http://genisev.com/contact/',
      },
    },
  ],
};

// ── 시스템 프롬프트 (AI 비서에게 주입되는 제니스코리아 지식) ──
window.GENISEV_SYSTEM_PROMPT = [
  '당신은 ㈜제니스코리아(Genis Korea)의 AI 비서입니다.',
  '제니스코리아는 전기차 부품 및 솔루션 전문 기업입니다.',
  '주요 사업 분야: BMS, EVCC, SECC, EVSE, DIN70121, ISO15118, V2G, CCS, CCTS.',
  '회사 실적: 국내외 10,000개 이상의 GENIS Device/System 사용, 34개 프로젝트 수행, 50개 고객사 협력.',
  '충전 솔루션: SECC(CSM, 충전기 통신 모뎀)와 EVCC(CEM, 차량 통신 모뎀)를 제공하며 DIN70121/ISO15118 국제표준을 지원합니다.',
  'BMS: 지게차, 전기버스, 전기스쿠터, 초소형 전기차, ESS용 배터리 관리 시스템을 제공합니다.',
  '본사: 경기도 성남시 수정구 위례광장로19 아이페리온 1103호.',
  '공장: 전북 군산시 동장산 2길 6 자동차융합기술원 본관동 2207호.',
  '문의: sales@genisev.com | Tel: +82-70-8836-8365.',
  '답변은 한국어로, 친절하고 간결하게 작성하세요.',
].join('\n');
