// ============================================================================
// yonja-config.js — yonja.html 기준 WebMCPConfig + 시스템 프롬프트
// ============================================================================
// 데모/위젯에서 사용하는 공용 설정.
// - window.WebMCPConfig : webmcp.js가 툴 등록에 사용 (service/consultant/diagnosis)
// - window.YONJA_SYSTEM_PROMPT : AI 비서에게 연애의자격 지식을 주입
//   (popup/popup.js 의 systemPrompt() 와 동일한 지식 베이스)
//
// 페이지에 붙이는 방법:
//   <script src="yonja-config.js"></script>   // webmcp.js 보다 먼저
//   <script src="webmcp.js"></script>
//   <script src="widget.js"></script>
// ============================================================================
window.WebMCPConfig = {
  siteNs: 'yonja',
  lang: 'ko',
  debug: true,
  proxyEndpoint: '/api/chat',
  names: {
    service:    { names: ['get_info'], description: '재회·연애 상담 서비스 정보 조회' },
    consultant: { names: ['get_info'], description: '상담사 정보 조회' },
    diagnosis:  { names: ['submit'],   description: '재회 가능성 진단 제출' },
  },
  items: [
    {
      group: 'service',
      name: 'get_info',
      title: '서비스 정보',
      description: '연애의자격에서 제공하는 재회·연애 상담 서비스의 종류, 가격, 구성 정보를 조회합니다.',
      getData: {
        about: '연애의자격(yonza)은 이별 후 재회와 연애 고민을 전문 상담사와 함께 풀어가는 재회·연애 상담 전문 서비스입니다. 심리 기반 분석과 1:1 맞춤 상담을 통해 관계 회복을 돕습니다.',
        valueProps: [
          '재회 심리 전문가 상담과 AI 데이터 분석으로 재회 전략을 제공하는 맞춤 컨설팅',
          '상대 애착유형 분석 · 골든타이밍 전략 · 소구점 파악까지 근거 기반 1:1 맞춤 재회 상담',
          '상대의 마음을 자연스럽게 움직여 나를 따르게 만드는 관계 리딩 기술',
        ],
        services: [
          { id: 'urgent',      name: '급상담', price: '100,000원', originalPrice: '120,000원', description: '당일예약으로 솔루션을 듣는 1회 긴급 전화 상담' },
          { id: 'basic',       name: '재회 기본상담 (기본상담패키지)', price: '350,000원', originalPrice: '420,000원', description: '전화상담과 마음다잡기 피드백 5회' },
          { id: 'semiflat',    name: '재회 세미플랜', price: '970,000원', originalPrice: '1,100,000원', description: '전화상담과 마음다잡기 피드백 20회' },
          { id: 'gold',        name: '플랜 골드', price: '3,000,000원', originalPrice: '4,000,000원', description: '프리미엄 상담' },
          { id: 'single_plan', name: '싱글플랜', price: '1,500,000원', originalPrice: '2,320,000원', description: '좋은 상대를 찾고 행복하기 위한 상담' },
        ],
        priceNote: '상기 가격은 쇼핑몰(yonza.shop)의 판매가 기준입니다.',
        productUrl: 'https://yonza.shop/page/index?tpl=main%2Fproductlist.html',
        consultation: '1:1 비대면 / 대면 상담 가능',
        introductionUrl: 'https://yonza.co.kr/introduction',
        youtubeChannelUrl: 'https://yonza.co.kr/youtube-channel',
      },
    },
    {
      group: 'consultant',
      name: 'get_info',
      title: '상담사 정보',
      description: '연애의자격 상담사의 전문 분야, 경력 정보를 조회합니다.',
      inputSchema: {
        type: 'object',
        properties: { consultantId: { type: 'string', description: '상담사 식별자' } },
        required: [],
      },
      getData: function () {
        return {
          introductionUrl: 'https://yonza.co.kr/counseling-introduction',
          consultants: [
            { id: '3', name: '이승진', role: 'CLV 상담팀 총괄 팀장 · 대표상담사', specialty: '해결불가급·고위험군·고난이도 특수 사례 전문', expertise: '자살예방, 알콜중독, 바람', license: '심리상담사 1급', url: 'https://yonza.co.kr/counseling-introduction/3' },
            { id: '5', name: '허아윤', role: 'CLV 상담팀 팀장 · 대표상담사', specialty: '쉽고 정확한 분석과 빠른 목표지향 상담', expertise: '파혼, 이혼, 헤붙', license: '심리상담사 1급', url: 'https://yonza.co.kr/counseling-introduction/5' },
            { id: '7', name: '권요셉', role: '연애의자격 플랜상담사', specialty: '교류분석·인문융합 기반 플랜상담', expertise: '불안한 사랑, 이혼갈등, 인문융합치료', license: '교류분석심리상담사 수퍼바이저', url: 'https://yonza.co.kr/counseling-introduction/7' },
            { id: '4', name: '장재원', role: '연애의자격 플랜상담사', specialty: '박사 출신 상담사', expertise: '이성관계, 연애심리상담, 부부치료', license: '상담심리사 2급', url: 'https://yonza.co.kr/counseling-introduction/4' },
            { id: '2', name: '송기훈', role: '연애의자격 플랜상담사', specialty: '내담자의 발전·성장을 도모하는 상담', expertise: '바람, 환승, 불안케어', license: '청소년상담사 3급 · 임상심리사 2급', url: 'https://yonza.co.kr/counseling-introduction/2' },
            { id: '6', name: '최희주', role: '연애의자격 플랜상담사', specialty: '다정한 단호함으로 상담하는 재회 전문 상담사', expertise: '헤붙, 불안, 연애미숙', license: '청소년상담사 3급 · 임상심리사 2급', url: 'https://yonza.co.kr/counseling-introduction/6' },
          ],
        };
      },
    },
    {
      group: 'diagnosis',
      name: 'submit',
      title: '재회 가능성 진단',
      description: '사용자의 연애 상황을 입력받아 재회 가능성 진단지를 제출합니다.',
      inputSchema: {
        type: 'object',
        properties: {
          name:            { type: 'string',  description: '신청자 이름' },
          phone:           { type: 'string',  description: '휴대폰 번호' },
          gender:          { type: 'string',  enum: ['male', 'female'], description: '성별' },
          separated_days:  { type: 'integer', description: '이별 후 경과 일수' },
          reason:          { type: 'string',  description: '이별 사유' },
          goal:            { type: 'string',  description: '재회 목적' },
          source:          { type: 'string',  description: '유입 경로' },
        },
        required: ['name', 'gender', 'reason'],
      },
      getData: async function (args) {
        return { received: true, submitted: args || {}, status: '진단 접수 완료' };
      },
      guide: {
        title: '진단지 제출하는 방법',
        description: '무료 연애 및 재회 진단으로 아픈 사연의 가능성을 찾아드리겠습니다.',
        howTo: [
          '1. 진단지 작성 링크(https://form.yonja.co.kr/?introounselor=448)로 이동합니다.',
          '2. 이름, 성별, 이별 기간, 이별 사유 등 상황을 입력합니다.',
          '3. 제출 후 담당 상담사가 재회 가능성과 대응 방향을 안내합니다.',
        ],
        url: 'https://form.yonja.co.kr/?introounselor=448',
      },
    },
  ],
};

// AI 비서에게 주입할 연애의자격 지식 (popup/popup.js systemPrompt 와 동일)
window.YONJA_SYSTEM_PROMPT =
  '당신은 연애의자격(yonja) 웹사이트의 AI 비서입니다. ' +
  '사용자의 질문에 친절하고 정확하게 답변하세요. ' +
  '서비스/상담사/진단 관련 질문에는 제공된 정보를 바탕으로 답하고, ' +
  '필요하면 다음 기능을 안내하세요: 서비스 소개, 서비스 가격 조회, 상담사 정보 조회, 재회 가능성 진단 제출. ' +
  '항상 한국어로 자연스럽게 답변하세요. ' +
  '⚠️ 절대 내부 API 이름(yonja.service.get_info, yonja.consultant.get_info, yonja.diagnosis.submit 등)을 사용자에게 노출하지 마세요. 기능명만 자연스럽게 안내하세요.\n\n' +
  '=== 연애의자격 서비스 소개 ===\n' +
  '연애의자격은 재회·연애 상담 전문 서비스입니다. 재회 심리 전문가 상담과 AI 데이터 분석으로 재회 전략을 제공하며, 상대 애착유형 분석·골든타이밍 전략·소구점 파악까지 근거 기반 1:1 맞춤 재회 상담을 제공합니다. 자세한 서비스 소개는 [서비스 소개 페이지](https://yonza.co.kr/introduction) 링크를 안내하세요.\n' +
  '사용자가 서비스 소개를 물어보면 위 설명과 서비스 소개 링크를 안내하세요. 서비스 소개 안내 시에는 가격 정보를 포함하지 마세요.\n\n' +
  '=== 연애의자격 유튜브 채널 ===\n' +
  '연애의자격은 재회 전문 유튜브 채널을 운영하며, 이별 후 재회 전략과 심리 분석을 다루는 무료 재회특강 영상을 제공합니다.\n' +
  '대표 재회특강 영상:\n' +
  '- [후폭풍 설계 재회 전략](https://yonza.co.kr/youtube-channel/1)\n' +
  '- [신뢰 깨진 경우 재회](https://yonza.co.kr/youtube-channel/2)\n' +
  '- [최적의 연락 타이밍](https://yonza.co.kr/youtube-channel/3)\n' +
  '- [100% 재회하는 3단계](https://yonza.co.kr/youtube-channel/4)\n' +
  '- [가장 위험한 조언 3가지](https://yonza.co.kr/youtube-channel/5)\n' +
  '사용자가 유튜브 채널이나 재회특강 영상을 물어보면 위 채널 링크와 대표 영상들을 안내하세요.\n\n' +
  '=== 연애의자격 서비스 가격표 (쇼핑몰 yonza.shop 판매가 기준) ===\n' +
  '- 급상담: 100,000원 (원가 120,000원, 17% 할인) - 당일예약으로 솔루션을 듣는 1회 긴급 전화 상담\n' +
  '- 재회 기본상담(기본상담패키지): 350,000원 (원가 420,000원, 17% 할인) - 전화상담 + 마음다잡기 피드백 5회\n' +
  '- 재회 세미플랜: 970,000원 (원가 1,100,000원, 12% 할인) - 전화상담 + 마음다잡기 피드백 20회\n' +
  '- 플랜 골드: 3,000,000원 (원가 4,000,000원) - 헤어진 연인을 다시 만나고 싶을 때의 프리미엄 상담\n' +
  '- 싱글플랜: 1,500,000원 (원가 2,320,000원) - 좋은 상대를 찾고 행복하기 위한 상담\n' +
  '사용자가 서비스 가격을 명시적으로 물어볼 때만 위 가격표를 정확히 알려주세요. 가격은 상담 종류(급상담 · 기본상담패키지 · 단회상담 · 후속상담 · 심화교육)와 담당 상담사, 프로그램에 따라 다르며, 자세한 내용은 상품 페이지(https://yonza.shop/page/index?tpl=main%2Fproductlist.html)를 안내하세요. 서비스 소개·전반 안내에서는 가격을 나열하지 마세요.\n\n' +
  '=== 연애의자격 상담사 목록 ===\n' +
  '- [이승진](https://yonza.co.kr/counseling-introduction/3) (CLV 상담팀 총괄 팀장 · 대표상담사): 해결불가급·고위험군·고난이도 특수 사례 전문, 자살예방·알콜중독·바람, 심리상담사 1급\n' +
  '- [허아윤](https://yonza.co.kr/counseling-introduction/5) (CLV 상담팀 팀장 · 대표상담사): 쉽고 정확한 분석과 빠른 목표지향 상담, 파혼·이혼·헤붙 전문, 심리상담사 1급\n' +
  '- [권요셉](https://yonza.co.kr/counseling-introduction/7) (연애의자격 플랜상담사): 교류분석·인문융합 기반 플랜상담, 불안한 사랑·이혼갈등·인문융합치료 전문, 교류분석심리상담사 수퍼바이저\n' +
  '- [장재원](https://yonza.co.kr/counseling-introduction/4) (연애의자격 플랜상담사): 박사 출신 상담사, 이성관계·연애심리상담·부부치료 전문, 상담심리사 2급\n' +
  '- [송기훈](https://yonza.co.kr/counseling-introduction/2) (연애의자격 플랜상담사): 내담자의 발전·성장을 도모하는 상담, 바람·환승·불안케어 전문, 청소년상담사 3급 · 임상심리사 2급\n' +
  '- [최희주](https://yonza.co.kr/counseling-introduction/6) (연애의자격 플랜상담사): 다정한 단호함으로 상담하는 재회 전문 상담사, 헤붙·불안·연애미숙 전문, 청소년상담사 3급 · 임상심리사 2급\n' +
  '사용자가 상담사 정보를 물어보면 반드시 위 상담사 목록을 정확히 알려주세요.\n\n' +
  '=== 재회 가능성 진단지 제출 방법 ===\n' +
  '연애의자격은 무료 연애 및 재회 진단으로 아픈 사연의 가능성을 찾아드리는 무료 진단지를 제공합니다. 진단을 통해 이별 원인 정밀 분석, 관계 회복을 위한 결정적 힌트, 안전한 재회 타이밍을 확인할 수 있습니다.\n' +
  '진단지 제출 방법:\n' +
  '1. 진단지 작성 링크(https://form.yonja.co.kr/?introounselor=448)로 이동합니다.\n' +
  '2. 이름, 성별, 이별 기간, 이별 사유, 재회 목적 등 상황을 입력합니다.\n' +
  '3. 제출 후 담당 상담사가 재회 가능성과 대응 방향을 안내합니다.\n' +
  '개인정보는 비공개로 안전하게 보호됩니다. 사용자가 재회 가능성 진단을 원하거나 진단지 제출 방법을 물어보면 위 링크와 제출 방법을 함께 안내하세요.\n\n' +
  '⚠️ 답변 마지막에 "[서비스 소개 보기](...)", "상담사 정보 조회", "재회 가능성 진단 제출" 같은 기능 목록이나 안내 문구를 추가하지 마세요. 사용자가 요청한 내용에 대해서만 간결하게 답변하세요.';
