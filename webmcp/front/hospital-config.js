// ============================================================================
// hospital-config.js — 생생병원 기준 WebMCPConfig + 시스템 프롬프트
// ============================================================================
// - window.WebMCPConfig : webmcp.js가 툴 등록에 사용 (hospital/doctor/appointment)
// - window.HOSPITAL_SYSTEM_PROMPT : AI 비서에게 병원 지식을 주입
// ============================================================================
window.WebMCPConfig = {
  siteNs: 'hospital',
  lang: 'ko',
  debug: true,
  proxyEndpoint: '/api/chat',
  // ── 고객 사이트별 색상표 (CSS 변수) ─────────────────────────
  // 이 theme 을 바꾸면 위젯 전체 색이 변경됩니다. 생략하면 기본 브랜드 색.
  // (예: 생생병원 브랜드 컬러로 변경)
  theme: {
    primary:    '#0e7490',   // 메인 브랜드 색 (청록)
    primary2:   '#06b6d4',   // 그라디언트 보조 색
    bg:         '#f0f9ff',   // 패널 바탕색
    surface:    '#ffffff',   // 봇 말풍선/입력바 배경
    text:       '#1f2937',   // 기본 텍스트
    textMuted:  '#6b7280',   // 보조 텍스트
    textFaint:  '#9ca3af',   // 약한 텍스트
    border:     '#e5e7eb',   // 테두리
    codeBg:     '#f3f4f6',   // 코드 블록 배경
    pillBg:     '#cffafe',   // 픽스 칩 배경
    errorBg:    '#fef2f2',   // 오류 말풍선 배경
    errorBorder: '#fca5a5',  // 오류 말풍선 테두리
    errorText:  '#b91c1c',   // 오류 말풍선 텍스트
  },
  names: {
    hospital:    { names: ['get_info'], description: '병원 기본정보 · 진료과 · 위치 · 운영시간 조회', label: '병원 정보', question: '병원 정보를 알려줘' },
    doctor:      { names: ['get_info'], description: '의사 · 전문분야 · 진료시간 · 소속 진료과 조회', label: '의사 정보', question: '의사 정보를 알려줘' },
    appointment: { names: ['get_current'], description: '진료 예약 안내', label: '진료 예약', question: '진료 예약은 어떻게 하나요?' },
    special:     { names: ['get_info'], description: '특성화 치료센터 정보 조회', label: '특성화 센터', question: '특성화 치료센터를 알려줘' },
    treatment:   { names: ['get_info'], description: '부위별 질환 치료 정보 조회', label: '부위별 치료', question: '부위별 질환 치료를 알려줘' },
  },
  items: [
    {
      group: 'hospital',
      name: 'get_info',
      title: '병원 정보',
      description: '병원의 기본 정보(이름, 주소, 전화번호), 진료과, 규모, 특징을 조회합니다.',
      getData: {
        name: '생생병원',
        intro: '당신의 생생한 일상을 돕는 척추·관절 특화 병원입니다.',
        address: '경기도 부천시 소사구 경인옛로 3, 5-8층(소사본동)',
        phone: '032-230-0700',        // 전화상담
        customerCenter: '1670-0711',  // 고객센터
        representative: '오종양, 박범용',
        businessNumber: '672-17-00332',
        size: '64병상, 1300평 규모의 척추·관절 병원',
        departments: ['신경외과', '정형외과', '내과', '마취통증의학과', '영상의학과'],
        doctorsCount: '5개과 13명의 전문의 협진진료 가능',
        features: [
          '가톨릭대학교 의학박사 출신의 대표원장 - 대학병원 전임의, 임상강사과정을 거친 10년 이상 경력의 전문의만 진료',
          '감염률 0% 도전하는 무균 수술실 - 양압시스템 24시간 운영, 개원 이래 7년간 감염률 제로',
          '간호간병 통합서비스 최고 등급 A등급',
          '대학병원급 첨단장비(MRI, CT, 초음파기) 보유 - ONE-STOP 검사',
          '로봇 인공관절 무릎 수술, 최소침습 척추내시경 수술(7mm 미만 절개), 고관절 내시경 수술',
          '단방향, 양방향 모든 척추내시경 수술 가능',
        ],
        departments_tel: {
          '검진센터': '032-230-0735',
          '원무과': '032-230-0703',
          '재활치료(도수치료)': '032-230-0752',
          '7병동': '032-230-0740',
          '8병동': '032-230-0754',
        },
        kakaoTalk: 'http://pf.kakao.com/_ZxdBgu/chat',
        naverBooking: 'https://m.booking.naver.com/booking/13/bizes/193210?theme=place',
        reservationUrl: 'https://www.saengsaenghospital.com/04_reservation_consultation/01experience_online_reserve.php',
        url: 'https://www.saengsaenghospital.com',
      },
    },
    {
      group: 'doctor',
      name: 'get_info',
      title: '의사 정보',
      description: '의사의 전문분야, 센터, 진료시간 정보를 조회합니다.',
      inputSchema: {
        type: 'object',
        properties: { doctorId: { type: 'string', description: '의사 식별자' } },
        required: [],
      },
      getData: function () {
        return {
          doctors: [
            { id: '1', name: '오종양', center: '척추센터', role: '대표원장', specialty: '신경외과 전문의', education: '의학박사', schedule: '월/화/목 오전 진료' },
            { id: '2', name: '조정기', center: '척추센터', role: '병원장', specialty: '신경외과 전문의', education: '의학박사', schedule: '월/수/목 오전·오후 진료' },
            { id: '3', name: '김상돈', center: '척추센터', role: '의무원장', specialty: '신경외과 전문의', education: '의학박사', schedule: '화/수/금 오전·월 오후 진료 (2,4,5주)' },
            { id: '4', name: '박준희', center: '척추센터', role: '부병원장', specialty: '신경외과 전문의', schedule: '월/수/금 오전·화/목 오후 진료' },
            { id: '5', name: '송교준', center: '척추센터', role: '원장', specialty: '신경외과 전문의', schedule: '화/목/금 오전·월/수 오후 진료' },
            { id: '6', name: '박범용', center: '관절센터', role: '대표원장', specialty: '정형외과 전문의', schedule: '화/목 오전·월/금 오후 진료' },
            { id: '7', name: '조현민', center: '관절센터', role: '원장', specialty: '정형외과 전문의', schedule: '월/화/목 오전·화/수/금 오후 진료' },
            { id: '8', name: '배태용', center: '관절센터', role: '원장', specialty: '정형외과 전문의', schedule: '월/수/금 오전·월/화/목 오후 진료' },
            { id: '9', name: '강민구', center: '관절센터', role: '원장', specialty: '정형외과 전문의', schedule: '화/수/금 오전·월/수/목 오후 진료' },
            { id: '10', name: '조주연', center: '비수술치료센터', role: '원장', specialty: '마취통증의학과 전문의', schedule: '월~금 오전·오후 치료' },
            { id: '11', name: '이재호', center: '영상의학센터', role: '원장', specialty: '영상의학과 전문의', schedule: '월~금 오전·오후 진료' },
            { id: '12', name: '송준화', center: '내과·건강증진센터', role: '원장', specialty: '내과 전문의', schedule: '월~금 오전·오후 진료 (격주)' },
          ],
          // 원장님별 상세 정보
          details: [
            {
              name: '오종양',
              role: '대표원장',
              centers: ['척추센터', '뇌신경센터'],
              specialty: '신경외과 전문의',
              education: '의학박사',
              schedule: '월/화/목 오전 진료',
              note: '생생병원 대표원장으로, 신경외과 전문 진료를 담당합니다. 뇌신경센터와 척추센터에서 진료합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '조정기',
              role: '병원장',
              centers: ['척추센터', '뇌신경센터'],
              specialty: '신경외과 전문의',
              education: '의학박사',
              schedule: '월/수/목 오전·오후 진료',
              note: '생생병원 병원장으로, 척추센터에서 신경외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '김상돈',
              role: '의무원장',
              centers: ['척추센터', '뇌신경센터'],
              specialty: '신경외과 전문의',
              education: '의학박사',
              schedule: '화/수/금 오전·월 오후 진료 (2,4,5주)',
              note: '생생병원 의무원장으로, 신경외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '박준희',
              role: '부병원장',
              centers: ['척추센터', '뇌신경센터'],
              specialty: '신경외과 전문의',
              schedule: '월/수/금 오전·화/목 오후 진료',
              note: '생생병원 부병원장으로, 척추센터에서 신경외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '송교준',
              role: '원장',
              centers: ['척추센터', '뇌신경센터'],
              specialty: '신경외과 전문의',
              schedule: '화/목/금 오전·월/수 오후 진료',
              note: '척추센터에서 신경외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '박범용',
              role: '대표원장',
              centers: ['관절센터'],
              specialty: '정형외과 전문의',
              schedule: '화/목 오전·월/금 오후 진료',
              note: '생생병원 대표원장으로, 관절센터에서 정형외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '조현민',
              role: '원장',
              centers: ['관절센터'],
              specialty: '정형외과 전문의',
              schedule: '월/화/목 오전·화/수/금 오후 진료',
              note: '관절센터에서 정형외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '배태용',
              role: '원장',
              centers: ['관절센터'],
              specialty: '정형외과 전문의',
              schedule: '월/수/금 오전·월/화/목 오후 진료',
              note: '관절센터에서 정형외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '강민구',
              role: '원장',
              centers: ['관절센터'],
              specialty: '정형외과 전문의',
              schedule: '화/수/금 오전·월/수/목 오후 진료',
              note: '관절센터에서 정형외과 전문 진료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '조주연',
              role: '원장',
              centers: ['척추센터', '관절센터', '비수술센터'],
              specialty: '마취통증의학과 전문의',
              schedule: '월~금 오전·오후 치료',
              note: '비수술치료센터에서 신경주사치료 등 비수술적 치료를 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '이재호',
              role: '원장',
              centers: ['척추센터', '관절센터', '뇌신경센터', '비수술센터', '내과·건강증진센터', '영상진단센터'],
              specialty: '영상의학과 전문의',
              schedule: '월~금 오전·오후 진료',
              note: '영상의학센터에서 MRI, CT, 초음파 등 영상 진단을 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
            {
              name: '송준화',
              role: '원장',
              centers: ['내과·건강증진센터'],
              specialty: '내과 전문의',
              schedule: '월~금 오전·오후 진료 (격주)',
              note: '내과·건강증진센터에서 내과 진료와 건강검진을 담당합니다.',
              url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
            },
          ],
          note: '진료 스케줄은 병원 사정에 따라 변동될 수 있습니다. 정확한 진료시간은 고객센터(1670-0711)로 문의하세요.',
          scheduleUrl: 'https://www.saengsaenghospital.com/01_operation_guide/01time.php',
        };
      },
    },
    {
      group: 'special',
      name: 'get_info',
      title: '특성화 치료센터',
      description: '생생병원의 특성화 치료센터(척추센터, 관절센터, 뇌신경센터, 재활치료센터, 건강검진센터) 정보를 조회합니다.',
      inputSchema: {
        type: 'object',
        properties: {
          center: { type: 'string', enum: ['척추센터', '관절센터', '뇌신경센터', '재활치료센터', '건강검진센터'], description: '특성화 센터 이름' },
        },
        required: [],
      },
      getData: function (args) {
        var centers = {
          '척추센터': {
            name: '척추센터',
            description: '척추 질환(허리디스크, 척추관협착증 등)을 전문적으로 치료하는 센터입니다.',
            doctors: ['오종양(대표원장)', '조정기(병원장)', '김상돈(의무원장)', '박준희(부병원장)', '송교준(원장)'],
            treatments: [
              '신경주사 (디스크·협착으로 눌린 신경에 직접 약물 투여)',
              '신경성형술',
              'PSLD (경피적 내시경적 요추 디스크 절제술)',
              'UBE (단방향/양방향 척추내시경 수술)',
              '미세현미경 수술',
              '경추 감압술',
              '최소침습 척추내시경 수술 (7mm 미만 절개)',
            ],
            url: 'https://www.saengsaenghospital.com/07_treatment2/02treatment1_1.php',
          },
          '관절센터': {
            name: '관절센터',
            description: '관절 질환(무릎, 고관절 등)을 전문적으로 치료하는 센터입니다.',
            doctors: ['박범용(대표원장)', '조현민(원장)', '배태용(원장)', '강민구(원장)'],
            treatments: [
              '로봇 인공관절 무릎 수술 (개인 맞춤형)',
              '고관절 내시경 수술 (1cm 미만 2~3개 구멍)',
              '관절 보존 치료',
            ],
            url: 'https://www.saengsaenghospital.com/07_treatment2/02treatment1_1.php',
          },
          '뇌신경센터': {
            name: '뇌신경센터',
            description: '뇌신경 질환을 전문적으로 진료하는 센터입니다.',
            doctors: ['오종양(대표원장)', '조정기(병원장)', '김상돈(의무원장)', '박준희(부병원장)', '송교준(원장)'],
            treatments: ['뇌신경 질환 진단 및 치료'],
            url: 'https://www.saengsaenghospital.com/02_experience/03doctor.php',
          },
          '재활치료센터': {
            name: '재활치료센터',
            description: '수술 후 재활과 도수치료를 전문으로 하는 센터입니다. (7층)',
            treatments: ['물리치료', '재활운동치료', '도수치료'],
            tel: '032-230-0752',
            url: 'https://www.saengsaenghospital.com/01_operation_guide/02floor.php',
          },
          '건강검진센터': {
            name: '건강검진센터',
            description: '종합 건강검진을 제공하는 센터입니다. (4층)',
            treatments: ['종합 건강검진', '검진센터 상담'],
            tel: '032-230-0735',
            url: 'https://www.saengsaenghospital.com/01_operation_guide/02floor.php',
          },
        };
        var name = (args && args.center) || '';
        if (name && centers[name]) return centers[name];
        return {
          centers: Object.keys(centers).map(function (k) { return { name: k, description: centers[k].description }; }),
          url: 'https://www.saengsaenghospital.com/07_treatment2/02treatment1_1.php',
        };
      },
    },
    {
      group: 'treatment',
      name: 'get_info',
      title: '부위별 질환 치료',
      description: '부위별(허리, 무릎, 목, 어깨, 족부, 팔꿈치, 내과, 물리치료) 질환의 원인, 증상, 치료 방법을 조회합니다.',
      inputSchema: {
        type: 'object',
        properties: {
          part: { type: 'string', enum: ['허리', '무릎', '목', '어깨', '족부', '팔꿈치', '내과', '물리치료'], description: '치료 부위/질환' },
        },
        required: [],
      },
      getData: function (args) {
        var treatments = {
          '허리': {
            name: '허리 (요추간판 탈출증·허리디스크)',
            cause: '반복되는 잘못된 자세·생활습관으로 허리에 부담이 축적되거나, 허리 근육이 약해진 상태에서 무리가 가해지거나, 지속적·반복적인 잘못된 작업 습관이 원인입니다.',
            symptoms: '허리가 아프고, 다리가 당기고 찌릿찌릿하거나 감각이 둔해지며, 누워서 무릎을 편 상태에서 다리를 들어올리지 못하고, 앉거나 활동하면 통증이 심해집니다. 심한 경우 하반신 마비나 대소변 장애가 발생할 수 있습니다.',
            treatments: [
              '보존적 치료: 약물(진통소염제·근육이완제·신경통약), 물리치료, 운동치료, 도수치료, 신경차단 주사치료',
              '비수술 치료: 신경성형술, 고주파 수핵 성형술, 내시경 디스크 성형술, 꼬리뼈 내시경시술(SELD), 추간공 경막외강 레이저 시술(TELA)',
              '수술 치료: 내시경 수핵 제거술(7mm 절개, 다음날 퇴원 가능), 현미경 수핵 제거술(2cm 절개), 추체간 유합술 및 나사고정술',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '무릎': {
            name: '무릎 (관절 질환)',
            cause: '무릎 관절의 퇴행성 변화, 반복적인 사용, 부상 등이 원인입니다.',
            symptoms: '무릎 통증, 부종, 뻣뻣함, 보행 시 소리, 계단 오르내리기 어려움 등이 나타납니다.',
            treatments: [
              '보존적 치료: 약물, 물리치료, 주사치료',
              '로봇 인공관절 무릎 수술 (개인 맞춤형)',
              '고관절 내시경 수술 (1cm 미만 2~3개 구멍)',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '목': {
            name: '목 (경추 질환)',
            cause: '잘못된 자세(스마트폰·컴퓨터 사용), 목 근육 약화, 퇴행성 변화 등이 원인입니다.',
            symptoms: '목 통증, 어깨 결림, 팔 저림, 두통, 어지럼증 등이 나타납니다.',
            treatments: [
              '보존적 치료: 약물, 물리치료, 도수치료, 신경주사',
              '경추 감압술',
              '경추 수술 (필요 시)',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '어깨': {
            name: '어깨 (회전근개 질환 등)',
            cause: '어깨 관절의 반복 사용, 부상, 퇴행성 변화 등이 원인입니다.',
            symptoms: '어깨 통증, 팔을 들어올리기 어려움, 야간 통증, 관절 운동 제한 등이 나타납니다.',
            treatments: [
              '보존적 치료: 약물, 물리치료, 주사치료, 도수치료',
              '어깨 관절 내시경 수술 (필요 시)',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '족부': {
            name: '족부 (발 질환)',
            cause: '발의 과사용, 잘못된 신발 착용, 퇴행성 변화 등이 원인입니다.',
            symptoms: '발 통증, 부종, 보행 시 통증, 발가락 변형 등이 나타납니다.',
            treatments: [
              '보존적 치료: 약물, 물리치료, 깔창, 주사치료',
              '족부 수술 (필요 시)',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '팔꿈치': {
            name: '팔꿈치 (테니스엘보 등)',
            cause: '팔꿈치의 반복적인 사용, 과도한 힘, 부상 등이 원인입니다.',
            symptoms: '팔꿈치 통증, 손목·팔 저림, 물건을 쥐기 어려움 등이 나타납니다.',
            treatments: [
              '보존적 치료: 약물, 물리치료, 주사치료, 도수치료',
              '팔꿈치 수술 (필요 시)',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '내과': {
            name: '내과 (내과 질환)',
            cause: '내과 질환은 다양한 원인(감염, 생활습관, 만성질환 등)에 의해 발생합니다.',
            symptoms: '발열, 기침, 복통, 소화불량, 피로 등 다양한 증상이 나타납니다.',
            treatments: [
              '내과 진료 (송준화 원장)',
              '건강검진',
              '만성질환 관리',
            ],
            url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
          },
          '물리치료': {
            name: '물리치료 (재활치료)',
            cause: '수술 후 회복, 통증 완화, 기능 회복을 위해 시행합니다.',
            symptoms: '수술 후 통증, 관절 운동 제한, 근력 저하 등이 있을 때 시행합니다.',
            treatments: [
              '물리치료',
              '재활운동치료',
              '도수치료 (7층, 032-230-0752)',
            ],
            url: 'https://www.saengsaenghospital.com/01_operation_guide/02floor.php',
          },
        };
        var part = (args && args.part) || '';
        if (part && treatments[part]) return treatments[part];
        return {
          parts: Object.keys(treatments).map(function (k) { return { name: k, description: treatments[k].name }; }),
          url: 'https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php',
        };
      },
    },
    {
      group: 'appointment',
      name: 'get_current',
      title: '진료 예약 안내',
      description: '생생병원의 온라인 진료예약 방법, 진료시간, 네이버 예약 링크를 안내합니다.',
      inputSchema: {
        type: 'object',
        properties: { userId: { type: 'string', description: '예약자를 식별하는 사용자 ID' } },
        required: [],
      },
      getData: function () {
        return {
          title: '온라인 진료예약',
          description: '쉽고 편리한 진료예약시스템. 생생병원은 고객과 가까이 함께 합니다.',
          hours: {
            '평일 오전진료': '08:30 ~ 12:30',
            '평일 오후진료': '13:30 ~ 17:30',
            '평일 점심시간': '12:30 ~ 13:30',
            '평일 연장진료': '17:30 ~ 19:00',
            '토요일 진료': '08:30 ~ 12:30 (점심시간 없음)',
          },
          process: [
            '원하시는 진료 날짜 2일 전까지 예약해주시면 친절하게 진료해드립니다.',
            '근무시간 내 예약 시 최대한 당일에 연락드립니다.',
            '근무시간 외 또는 휴일 예약 시 다음날 근무시간 중에 전화드립니다.',
            '담당자의 예약 확인 전화 통화 후 일시 변경 또는 예약이 확정됩니다.',
          ],
          onlineReserveUrl: 'https://www.saengsaenghospital.com/04_reservation_consultation/01experience_online_reserve.php',
          naverReserveUrl: 'https://m.booking.naver.com/booking/13/bizes/193210?theme=place',
          phone: '1670-0711',
        };
      },
    },
  ],
};

// AI 비서에게 주입할 병원 지식
window.HOSPITAL_SYSTEM_PROMPT =
  '당신은 생생병원(saengsaenghospital) 웹사이트의 AI 비서입니다. ' +
  '사용자의 질문에 친절하고 정확하게 답변하세요. ' +
  '병원/의사/예약 관련 질문에는 제공된 정보를 바탕으로 답하고, ' +
  '필요하면 다음 기능을 안내하세요: 병원 정보 조회, 의사 정보 조회, 예약 정보 조회. ' +
  '항상 한국어로 자연스럽게 답변하세요. ' +
  '⚠️ 절대 내부 API 이름(hospital.get_info, hospital.doctor.get_info, hospital.appointment.get_current 등)을 사용자에게 노출하지 마세요. 기능명만 자연스럽게 안내하세요.\n' +
  '⚠️ 링크는 반드시 마크다운 링크 문법 [표시할 텍스트](URL) 형태로 출력하세요. URL 주소를 그대로 노출하지 마세요.\n\n' +
  '=== 생생병원 소개 ===\n' +
  '생생병원은 "당신의 생생한 일상을 돕는" 척추·관절 특화 병원입니다.\n' +
  '주소: 경기도 부천시 소사구 경인옛로 3, 5-8층(소사본동)\n' +
  '규모: 64병상, 1300평 규모의 척추·관절 병원\n' +
  '대표: 오종양, 박범용 (사업자등록번호: 672-17-00332)\n' +
  '고객센터: 1670-0711\n' +
  '검진센터: 032-230-0735 / 원무과: 032-230-0703 / 재활치료: 032-230-0752 / 7병동: 032-230-0740 / 8병동: 032-230-0754\n' +
  '카카오톡 상담: [카카오톡 상담](http://pf.kakao.com/_ZxdBgu/chat)\n' +
  '네이버예약: [네이버 예약](https://m.booking.naver.com/booking/13/bizes/193210?theme=place)\n' +
  '온라인예약: [온라인 예약](https://www.saengsaenghospital.com/04_reservation_consultation/01experience_online_reserve.php)\n\n' +
  '=== 병원 특징 ===\n' +
  '- 가톨릭대학교 의학박사 출신의 대표원장: 대학병원 전임의·임상강사과정을 거친 10년 이상 경력의 전문의만 진료 (5개과 13명 협진)\n' +
  '- 감염률 0% 무균 수술실: 양압시스템 24시간 운영, 개원 이래 7년간 감염률 제로\n' +
  '- 간호간병 통합서비스 최고 등급 A등급\n' +
  '- 대학병원급 첨단장비(MRI, CT, 초음파기) ONE-STOP 검사\n' +
  '- 로봇 인공관절 무릎 수술, 최소침습 척추내시경 수술(7mm 미만), 고관절 내시경 수술\n' +
  '- 단방향·양방향 모든 척추내시경 수술 가능\n\n' +
  '=== 특성화 치료센터 ===\n' +
  '- 척추센터: 허리디스크·척추관협착증 등 척추 질환 전문. 신경주사, 신경성형술, PSLD, UBE(단방향/양방향 척추내시경), 미세현미경 수술, 경추 감압술, 최소침습 척추내시경(7mm 미만) 시행. 담당의: 오종양·조정기·김상돈·박준희·송교준\n' +
  '- 관절센터: 무릎·고관절 등 관절 질환 전문. 로봇 인공관절 무릎 수술, 고관절 내시경 수술(1cm 미만). 담당의: 박범용·조현민·배태용·강민구\n' +
  '- 뇌신경센터: 뇌신경 질환 진단·치료. 담당의: 오종양·조정기·김상돈·박준희·송교준\n' +
  '- 재활치료센터: 물리치료·재활운동치료·도수치료 (7층, 032-230-0752)\n' +
  '- 건강검진센터: 종합 건강검진 (4층, 032-230-0735)\n' +
  '특성화 치료센터 상세: [특성화 치료센터](https://www.saengsaenghospital.com/07_treatment2/02treatment1_1.php)\n\n' +
  '=== 부위별 질환 치료 ===\n' +
  '- 허리(요추간판 탈출증·허리디스크): 잘못된 자세·허리 근육 약화·반복 작업이 원인. 허리 통증, 다리 저림·당김, 다리 들어올리기 어려움. 보존적(약물·물리·도수·신경차단주사) → 비수술(신경성형술·수핵성형술·내시경 디스크 성형술·SELD·TELA) → 수술(내시경 수핵 제거술 7mm·현미경 수핵 제거술 2cm·유합술)\n' +
  '- 무릎(관절 질환): 퇴행성 변화·반복 사용·부상이 원인. 무릎 통증·부종·뻣뻣함. 보존적(약물·물리·주사) → 로봇 인공관절 무릎 수술, 고관절 내시경 수술\n' +
  '- 목(경추 질환): 잘못된 자세·목 근육 약화·퇴행이 원인. 목 통증·어깨 결림·팔 저림·두통. 보존적(약물·물리·도수·신경주사) → 경추 감압술\n' +
  '- 어깨(회전근개 질환 등): 반복 사용·부상·퇴행이 원인. 어깨 통증·팔 들어올리기 어려움·야간 통증. 보존적(약물·물리·주사·도수) → 관절 내시경 수술\n' +
  '- 족부(발 질환): 과사용·잘못된 신발·퇴행이 원인. 발 통증·부종·보행 통증. 보존적(약물·물리·깔창·주사) → 족부 수술\n' +
  '- 팔꿈치(테니스엘보 등): 반복 사용·과도한 힘·부상이 원인. 팔꿈치 통증·손목 저림·쥐기 어려움. 보존적(약물·물리·주사·도수) → 팔꿈치 수술\n' +
  '- 내과: 감염·생활습관·만성질환이 원인. 발열·기침·복통·소화불량·피로. 내과 진료(송준화 원장)·건강검진·만성질환 관리\n' +
  '- 물리치료: 수술 후 회복·통증 완화·기능 회복. 물리치료·재활운동치료·도수치료 (7층, 032-230-0752)\n' +
  '부위별 치료 상세: [부위별 치료](https://www.saengsaenghospital.com/03_treatment/01treatment1_1.php)\n\n' +
  '=== 진료 스케줄 (병원이용안내) ===\n' +
  '- 오종양(대표원장, 척추·뇌신경센터, 신경외과 전문의, 의학박사): 월/화/목 오전 진료\n' +
  '- 조정기(병원장, 척추·뇌신경센터, 신경외과 전문의, 의학박사): 월/수/목 오전·오후 진료\n' +
  '- 김상돈(의무원장, 척추·뇌신경센터, 신경외과 전문의, 의학박사): 화/수/금 오전·월 오후 (2,4,5주)\n' +
  '- 박준희(부병원장, 척추·뇌신경센터, 신경외과 전문의): 월/수/금 오전·화/목 오후 진료\n' +
  '- 송교준(원장, 척추·뇌신경센터, 신경외과 전문의): 화/목/금 오전·월/수 오후 진료\n' +
  '- 박범용(대표원장, 관절센터, 정형외과 전문의): 화/목 오전·월/금 오후 진료\n' +
  '- 조현민(원장, 관절센터, 정형외과 전문의): 월/화/목 오전·화/수/금 오후 진료\n' +
  '- 배태용(원장, 관절센터, 정형외과 전문의): 월/수/금 오전·월/화/목 오후 진료\n' +
  '- 강민구(원장, 관절센터, 정형외과 전문의): 화/수/금 오전·월/수/목 오후 진료\n' +
  '- 조주연(원장, 비수술치료센터, 마취통증의학과 전문의): 월~금 오전·오후 치료\n' +
  '- 이재호(원장, 영상의학센터, 영상의학과 전문의): 월~금 오전·오후 진료\n' +
  '- 송준화(원장, 내과·건강증진센터, 내과 전문의): 월~금 오전·오후 진료 (격주)\n' +
  '진료 스케줄은 변동될 수 있으니 정확한 시간은 고객센터(1670-0711)로 안내하세요.\n' +
  '진료시간 상세: [진료시간 안내](https://www.saengsaenghospital.com/01_operation_guide/01time.php)\n' +
  '의료진소개: [의료진 소개](https://www.saengsaenghospital.com/02_experience/03doctor.php)\n\n' +
  '=== 진료 예약 안내 ===\n' +
  '생생병원은 쉽고 편리한 온라인 진료예약시스템을 운영합니다.\n' +
  '진료시간: 평일 오전 08:30~12:30, 오후 13:30~17:30, 연장진료 17:30~19:00, 점심 12:30~13:30 / 토요일 08:30~12:30 (점심 없음)\n' +
  '예약 방법: 원하시는 진료 날짜 2일 전까지 예약. 근무시간 내 예약 시 당일 연락, 근무시간 외·휴일 예약 시 다음날 근무시간 중 연락. 담당자 확인 전화 후 예약 확정.\n' +
  '온라인 진료예약: [온라인 진료예약](https://www.saengsaenghospital.com/04_reservation_consultation/01experience_online_reserve.php)\n' +
  '네이버 예약: [네이버 예약](https://m.booking.naver.com/booking/13/bizes/193210?theme=place)\n' +
  '빠른 예약: 대표전화 1670-0711\n\n' +
  '⚠️ 답변 마지막에 기능 목록이나 안내 문구를 추가하지 마세요. 사용자가 요청한 내용에 대해서만 간결하게 답변하세요.';
