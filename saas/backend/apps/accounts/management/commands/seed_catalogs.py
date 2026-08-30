from django.core.management.base import BaseCommand
from django.db import models

from apps.catalogs.models import DomainType, QuickMenu

# ── 언어별 필수 메뉴("AI비서란?" / "About AI Assistant?") 정의 ──
# 각 언어 사일로가 자체 언어로 필수 메뉴를 가진다 (DB 공통 답변).
REQUIRED_MENUS = {
    'ko': {
        'label': 'AI비서란?',
        'question': 'AI비서가 무엇이고, 어떻게 사용하나요?',
        'hint': 'AI비서의 소개·사용 방법·문의 안내 중심',
        'answer': (
            '**AI비서란?**\n\n'
            'AI비서는 홈페이지에 설치된 인공지능 상담 챗봇입니다. '
            '홈페이지의 정보를 학습하여 방문자에게 빠르고 정확한 답변을 제공합니다.\n\n'
            '**사용 방법**\n'
            '- 우하단 **AI** 버튼을 클릭하면 채팅창이 열립니다.\n'
            '- 빠른 메뉴(퀵 질문) 버튼을 누르면 자동으로 질문이 입력됩니다.\n'
            '- 직접 질문을 입력하거나 **음성 입력**으로 질문할 수 있습니다.\n'
            '- 답변은 수집된 홈페이지 정보를 기반으로 생성됩니다.\n\n'
            '**문의 안내**\n'
            '- 궁금한 점이 있으면 홈페이지의 **고객센터 Q&A**에 질문을 남겨주세요.\n'
            '- 또는 [AI 아카이브](https://ai-archive.co.kr/ko)에서 더 자세한 정보를 확인하실 수 있습니다.'
        ),
    },
    'en': {
        'label': 'About AI Assistant',
        'question': 'What is the AI assistant and how do I use it?',
        'hint': 'Intro to the AI assistant, usage guidance and support contacts',
        'answer': (
            '**What is the AI Assistant?**\n\n'
            'The AI Assistant is an AI-powered chat bot installed on your website. '
            'It learns from the information on your website and provides visitors with fast, accurate answers.\n\n'
            '**How to use**\n'
            '- Click the **AI** button at the bottom-right corner to open the chat window.\n'
            '- Quick menu buttons automatically insert pre-made questions.\n'
            '- You can type a question directly or use **voice input**.\n'
            '- Answers are generated from the information collected from your website.\n\n'
            '**Support**\n'
            '- If you have questions, please post them on the **Customer Center Q&A**.\n'
            '- Or visit [AI Archive](https://ai-archive.co.kr) for more information.'
        ),
    },
}

# ── 한국어 카탈로그 (lang='ko') — 도메인 유형 세분화 템플릿 ────
SEED_KO = [
    ('hospital', '병원', '종합·전문 병원 사이트 (진료과·의사·치료 중심)', '🏥', [
        ('병원정보', '병원 소개와 특징을 알려줘', '병원의 연혁·규모·특징·철학 중심'),
        ('의료진', '의료진 정보를 알려줘', '의료진 이름·전문분야·경력 중심'),
        ('치료방법', '주요 치료·진료 정보를 알려줘', '진료과·시술·수술·특성화 센터 중심'),
        ('연락처', '연락처와 오시는 길을 알려줘', '전화번호·주소·찾아오는 길·주차·예약 중심'),
    ]),
    ('hospital_dental', '치과', '치과의원·치과병원 사이트 (진료·교정·임플란트 중심)', '🦷', [
        ('병원정보', '치과 소개와 특징을 알려줘', '치과의 연혁·규모·진료철학 중심'),
        ('의료진', '치과 의료진 정보를 알려줘', '치과의사 이름·전문분야·경력 중심'),
        ('치료방법', '주요 치과 치료·진료 정보를 알려줘', '교정·임플란트·보철·미백 등 진료 항목 중심'),
        ('연락처', '연락처와 예약·오시는 길을 알려줘', '전화번호·주소·예약 방법·주차 중심'),
    ]),
    ('hospital_beauty', '미용', '피부과·성형외과·미용의원 사이트 (시술·관리 중심)', '✨', [
        ('병원정보', '미용의원 소개와 특징을 알려줘', '의원의 연혁·규모·철학·안전 중심'),
        ('의료진', '의료진 정보를 알려줘', '의사 이름·전문분야·경력 중심'),
        ('시술정보', '주요 시술·관리 프로그램을 알려줘', '시술 종류·효과·비용·주의사항 중심'),
        ('연락처', '연락처와 예약·오시는 길을 알려줘', '전화번호·주소·예약 방법 중심'),
    ]),
    ('hospital_oriental', '한의원', '한의원·한방병원 사이트 (한방진료·침·약침 중심)', '🌿', [
        ('병원정보', '한의원 소개와 특징을 알려줘', '한의원의 연혁·규모·진료철학 중심'),
        ('의료진', '한의사 정보를 알려줘', '한의사 이름·전문분야·경력 중심'),
        ('치료방법', '주요 한방 치료·진료 정보를 알려줘', '침·약침·한약·추나 등 치료 항목 중심'),
        ('연락처', '연락처와 예약·오시는 길을 알려줘', '전화번호·주소·예약 방법 중심'),
    ]),

    # ── 법률·전문자격 계열 ─────────────────────────────────────
    ('law', '변호사', '법무법인·로펌 사이트 (변호사·소송 중심)', '⚖️', [
        ('회사소개', '법무법인 소개를 알려줘', '사무소 연혁·구성·철학 중심'),
        ('변호사', '변호사 정보를 알려줘', '변호사 이름·전문 분야·경력 중심'),
        ('사건', '주요 취급 사건 분야를 알려줘', '취급 사건 유형·승소 사례 중심'),
        ('연락처', '연락처와 상담 예약을 알려줘', '전화·이메일·상담 예약 방법·주소 중심'),
    ]),
    ('law_labor', '노무', '노무법인·공인노무사 사무소 사이트 (노무·인사 중심)', '👥', [
        ('회사소개', '노무법인 소개를 알려줘', '사무소 연혁·구성·철학 중심'),
        ('전문가', '노무사 구성원 정보를 알려줘', '노무사 이름·전문분야·경력 중심'),
        ('업무영역', '주요 업무·서비스 영역을 알려줘', '급여·근로계약·산재·4대보험 등 중심'),
        ('연락처', '연락처와 상담 예약을 알려줘', '전화·이메일·상담 예약 방법·주소 중심'),
    ]),
    ('law_accounting', '회계', '회계·세무법인 사무소 사이트 (세무·기장 중심)', '🧾', [
        ('회사소개', '회계법인 소개를 알려줘', '사무소 연혁·구성·철학 중심'),
        ('전문가', '회계사·세무사 정보를 알려줘', '전문가 이름·전문분야·경력 중심'),
        ('서비스', '주요 서비스·업무를 알려줘', '기장·세무신고·세무조사 대응·경영자문 중심'),
        ('연락처', '연락처와 상담 예약을 알려줘', '전화·이메일·상담 예약 방법·주소 중심'),
    ]),
    ('law_realestate', '부동산', '부동산 중개·컨설팅 사무소 사이트', '🏠', [
        ('회사소개', '부동산 사무소 소개를 알려줘', '사무소 연혁·구성·전문성 중심'),
        ('전문가', '중개사·컨설턴트 정보를 알려줘', '담당자 이름·전문분야·경력 중심'),
        ('서비스', '주요 서비스·거래 분야를 알려줘', '매매·임대·분양·투자 컨설팅 중심'),
        ('연락처', '연락처와 상담 예약을 알려줘', '전화·이메일·상담 예약 방법·주소 중심'),
    ]),

    # ── 교육·상담 계열 ───────────────────────────────────────
    ('edu_counsel', '상담', '심리상담·코칭 센터 사이트 (상담 프로그램 중심)', '💬', [
        ('기관소개', '상담센터 소개와 특징을 알려줘', '센터의 연혁·철학·전문성 중심'),
        ('상담사', '상담사·전문가 정보를 알려줘', '상담사 이름·전문분야·자격·경력 중심'),
        ('프로그램', '상담 프로그램 서비스를 알려줘', '상담 종류·대상·진행방식·비용 중심'),
        ('연락처', '연락처와 예약·오시는 길을 알려줘', '전화·이메일·예약 방법·주소 중심'),
    ]),
    ('edu_care', '요양', '요양원·요양병원·실버케어 시설 사이트', '🏡', [
        ('기관소개', '요양시설 소개와 특징을 알려줘', '시설의 연혁·규모·운영철학 중심'),
        ('시설', '시설·입소 환경을 알려줘', '시설 규모·생활환경·식사·의료지원 중심'),
        ('서비스', '요양 서비스·프로그램을 알려줘', '요양등급·케어 프로그램·비용 중심'),
        ('연락처', '연락처와 입소상담·오시는 길을 알려줘', '전화·이메일·입소상담·주소 중심'),
    ]),
    ('edu_college', '대학', '대학교·대학원 사이트 (학과·입학 중심)', '🎓', [
        ('대학소개', '대학 소개와 특징을 알려줘', '대학의 연혁·이념·규모 중심'),
        ('학과', '학과·전공 정보를 알려줘', '학과 구성·특성화 분야·교수진 중심'),
        ('입학', '입학·전형 정보를 알려줘', '입시 전형·모집 일정·장학금 중심'),
        ('연락처', '연락처와 오시는 길을 알려줘', '전화·이메일·주소·캠퍼스 안내 중심'),
    ]),

    # ── 일반회사·산업 계열 ─────────────────────────────────────
    ('company', '일반회사', '회사·서비스·제품 중심 사이트', '🏢', [
        ('회사정보', '회사 정보를 알려줘', '회사 연혁·비전·규모·조직 중심'),
        ('서비스', '제공하는 서비스를 알려줘', '서비스 종류·특징·강점 중심'),
        ('제품', '제품 정보를 알려줘', '제품군·스펙·활용 분야 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소·찾아오는 길 중심'),
    ]),
    ('company_construction', '건설', '건설·시공·엔지니어링 회사 사이트', '🏗️', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·시공능력 중심'),
        ('사업분야', '주요 사업·시공 분야를 알려줘', '토목·건축·주택·플랜트 등 수행 분야 중심'),
        ('실적', '주요 시공 실적·프로젝트를 알려줘', '대표 프로젝트·수주 실적·기술력 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소·지사 안내 중심'),
    ]),
    ('company_chemical', '화학', '화학·소재 제조 회사 사이트', '🧪', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·연구역량 중심'),
        ('제품', '주요 제품·소재를 알려줘', '제품군·특성·적용 분야 중심'),
        ('기술', '핵심 기술·연구개발을 알려줘', '공정기술·특허·R&D 역량 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소·사업장 안내 중심'),
    ]),
    ('company_bio', '생명', '바이오·생명과학 회사 사이트 (연구·진단 중심)', '🧬', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·비전·연구역량 중심'),
        ('기술', '핵심 기술·연구개발을 알려줘', '연구 분야·원천기술·특허 중심'),
        ('제품', '주요 제품·서비스를 알려줘', '진단·치료제·연구솔루션 등 제품 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소 중심'),
    ]),
    ('company_health', '보건', '보건·의료기기·헬스케어 회사 사이트', '🩺', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·비전 중심'),
        ('서비스', '주요 서비스·사업을 알려줘', '헬스케어 서비스·관리 프로그램 중심'),
        ('제품', '주요 제품·장비를 알려줘', '의료기기·헬스 제품군·특징 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소 중심'),
    ]),
    ('company_pharma', '제약', '제약·의약품 회사 사이트 (의약품·R&D 중심)', '💊', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·비전 중심'),
        ('제품', '주요 의약품·제품을 알려줘', '의약품·건강기능식품 제품군 중심'),
        ('연구개발', '연구개발·파이프라인을 알려줘', '신약 개발·임상·연구역량 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소 중심'),
    ]),
    ('company_electronics', '전자', '전자·전기·반도체 회사 사이트 (제품·기술 중심)', '🔌', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·비전 중심'),
        ('제품', '주요 전자제품·부품을 알려줘', '제품군·스펙·적용 분야 중심'),
        ('기술', '핵심 기술·연구개발을 알려줘', '반도체·디스플레이·공정기술 중심'),
        ('연락처', '연락처와 위치를 알려줘', '전화·이메일·주소·사업장 안내 중심'),
    ]),
    ('company_logistics', '운송', '운송·물류·택배 회사 사이트 (배송·물류 중심)', '🚚', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·물류 네트워크 중심'),
        ('서비스', '주요 운송·물류 서비스를 알려줘', '택배·화물·국제운송·보관 등 서비스 중심'),
        ('이용안내', '배송·이용 방법을 알려줘', '배송 조회·요금·이용 절차·고객센터 중심'),
        ('연락처', '연락처와 고객센터를 알려줘', '전화·이메일·고객센터·지점 안내 중심'),
    ]),
('company_retail', '리테일', '유통·리테일·쇼핑몰 회사 사이트 (판매·매장 중심)', '🛒', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·브랜드 중심'),
        ('매장', '매장·지점 정보를 알려줘', '매장 위치·영업시간·지점 안내 중심'),
        ('제품', '판매 제품·상품을 알려줘', '상품군·브랜드·카테고리 중심'),
        ('연락처', '연락처와 고객센터를 알려줘', '전화·이메일·고객센터·매장 문의 중심'),
    ]),    ('company_sales', '영업', '영업·판매·고객사 대상 서비스 팀 사이트 (영업·제안 중심)', '📈', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·영업 조직 중심'),
        ('제품·서비스', '판매 제품·서비스를 알려줘', '제품·서비스 구성·가격·구매 절차 중심'),
        ('제안·견적', '제안·견적 받는 방법을 알려줘', '견적 요청·제안서·도입 문의 중심'),
        ('연락처', '영업 담당자와 연락처를 알려줘', '영업팀·지역 담당·전화·이메일 중심'),
    ]),    ('company_research', '연구회사', '연구소·연구개발 전문 회사 (연구·기술 중심)', '🔬', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·연구 분야 중심'),
        ('연구분야', '주요 연구 분야를 알려줘', '연구 주제·기술·특허·성과 중심'),
        ('성과', '연구 성과·논문·특허를 알려줘', '대표 성과·논문·특허·수상 중심'),
        ('연락처', '연락처와 협업 문의를 알려줘', '전화·이메일·협업·제휴 문의 중심'),
    ]),
    ('company_investment', '투자회사', '투자·자산운용·벤처캐피탈 회사 (투자 중심)', '💰', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·투자 철학 중심'),
        ('투자분야', '주요 투자 분야를 알려줘', '투자 섹터·포트폴리오·전략 중심'),
        ('포트폴리오', '투자 포트폴리오를 알려줘', '투자 기업·펀드·성과 중심'),
        ('연락처', '연락처와 투자 문의를 알려줘', '전화·이메일·투자·제안 문의 중심'),
    ]),
    ('company_consulting', '컨설팅회사', '경영·전략·전문 컨설팅 회사 (자문 중심)', '📊', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·전문성 중심'),
        ('서비스', '주요 컨설팅 서비스를 알려줘', '경영·전략·재무·인사 등 서비스 중심'),
        ('전문가', '컨설턴트·전문가 정보를 알려줘', '컨설턴트 이름·전문분야·경력 중심'),
        ('연락처', '연락처와 상담 문의를 알려줘', '전화·이메일·상담·제안 문의 중심'),
    ]),
    ('company_knowledge', '지식산업', '지식·정보·콘텐츠 산업 회사 (지식서비스 중심)', '🧠', [
        ('회사정보', '회사 소개와 특징을 알려줘', '회사 연혁·규모·비전 중심'),
        ('서비스', '주요 지식·정보 서비스를 알려줘', '교육·정보·콘텐츠·플랫폼 서비스 중심'),
        ('콘텐츠', '주요 콘텐츠·자료를 알려줘', '강의·자료·리포트·데이터 중심'),
        ('연락처', '연락처와 문의를 알려줘', '전화·이메일·고객센터·문의 중심'),
    ]),

    # ── 기타 계열 ─────────────────────────────────────────────
    ('blog', '블로그', '개인·기업 블로그 사이트 (글·콘텐츠 중심)', '📝', [
        ('블로그소개', '블로그 소개와 특징을 알려줘', '블로그의 주제·운영자·철학 중심'),
        ('카테고리', '주요 글 카테고리를 알려줘', '글 주제·카테고리·연재 시리즈 중심'),
        ('최신글', '최신 글·인기 글을 알려줘', '최신 포스트·인기 콘텐츠·주요 글 중심'),
        ('연락처', '연락처와 소통 방법을 알려줘', '이메일·SNS·댓글·구독 방법 중심'),
    ]),
]

# ── 영어 카탈로그 (en 사일로) ──────────────────────────────────
# 한국어 SEED와 동일한 code 체계를 공유하되, 이름/설명/빠른메뉴가 영어다.
# code가 같아도 lang이 다르므로 별도 레코드로 저장되어 사일로가 격리된다.
SEED_EN = [
    # ── Healthcare ─────────────────────────────────────────
    ('hospital', 'Hospital', 'General & specialty hospital sites (departments, doctors, treatments)', '🏥', [
        ('About', 'Tell me about the hospital and its key features', 'History, scale, philosophy of the hospital'),
        ('Doctors', 'Introduce the medical staff and their specialties', 'Doctors, specialties, and experience'),
        ('Treatments', 'What treatments and services do you provide?', 'Departments, procedures, surgeries, specialized centers'),
        ('Contact', 'How can I contact the hospital and get directions?', 'Phone, address, directions, parking, appointments'),
    ]),
    ('hospital_dental', 'Dental', 'Dental clinics & hospitals (orthodontics, implants)', '🦷', [
        ('About', 'Introduce the dental clinic and its features', 'Clinic history, scale, philosophy'),
        ('Doctors', 'Introduce the dentists and their specialties', 'Dentist names, specialties, expertise'),
        ('Treatments', 'What dental treatments and services do you offer?', 'Orthodontics, implants, prosthetics, whitening'),
        ('Contact', 'Contact information and appointment booking', 'Phone, address, booking, parking'),
    ]),
    ('hospital_beauty', 'Aesthetic', 'Dermatology & plastic surgery clinics', '✨', [
        ('About', 'Introduce the clinic and its features', 'Clinic history, philosophy, safety'),
        ('Doctors', 'Introduce the medical team', 'Doctor names, specialties, experience'),
        ('Procedures', 'What treatments and programs are available?', 'Procedure types, effects, pricing, cautions'),
        ('Contact', 'Contact details and booking information', 'Phone, address, booking method'),
    ]),
    ('hospital_oriental', 'Oriental', 'Oriental medicine clinics & hospitals', '🌿', [
        ('About', 'Introduce the clinic and its philosophy', 'Clinic history, scale, philosophy'),
        ('Doctors', 'Introduce the practitioners', 'Practitioner names, specialties, experience'),
        ('Treatments', 'What oriental treatments are offered?', 'Acupuncture, herbal medicine, chuna, moxibustion'),
        ('Contact', 'Contact details and booking/directions', 'Phone, address, booking method'),
    ]),

    # ── 법률/전문자격 (영어) ─────────────────────────────────
    ('law', 'Law Firm', 'Law firm & legal services sites (attorneys, litigation)', '⚖️', [
        ('About', 'Introduce the law firm', 'Firm history, members, philosophy'),
        ('Attorneys', 'Introduce the attorneys and their specialties', 'Attorney names, practice areas, experience'),
        ('Practice', 'What are the main practice areas', 'Case types, notable outcomes'),
        ('Contact', 'Contact information and consultation booking', 'Phone, email, booking, address'),
    ]),
    ('law_labor', 'Labor', 'Labor law & HR consulting firms', '👥', [
        ('About', 'Introduce the labor law firm', 'Firm history, structure, philosophy'),
        ('Experts', 'Introduce the labor attorneys', 'Names, specialties, experience'),
        ('Services', 'What services do you provide?', 'Payroll, contracts, industrial accidents, insurance'),
        ('Contact', 'Contact details and consultation booking', 'Phone, email, booking, address'),
    ]),
    ('law_accounting', 'Accounting', 'Accounting & tax firm sites', '🧾', [
        ('About', 'Introduce the accounting firm', 'History, structure, philosophy'),
        ('Experts', 'Introduce accountants and tax experts', 'Expert names, specialties, experience'),
        ('Services', 'What are your main services?', 'Bookkeeping, tax filing, audits, advisory'),
        ('Contact', 'Contact details and consultation booking', 'Phone, email, booking, address'),
    ]),
    ('law_realestate', 'Real Estate', 'Real estate brokerage & consulting', '🏠', [
        ('About', 'Introduce the real estate agency', 'History, team, philosophy'),
        ('Agents', 'Introduce the agents and consultants', 'Names, specialties, experience'),
        ('Services', 'What services and listings do you offer?', 'Properties, brokerage, consulting'),
        ('Contact', 'Contact details and office location', 'Phone, address, consultation booking'),
    ]),

    # ── 교육·상담 (영어) ──────────────────────────────────────
    ('edu_counseling', 'Counseling', 'Counseling & mental health centers', '💬', [
        ('About', 'Introduce the counseling center', 'History, team, philosophy'),
        ('Counselors', 'Introduce the counselors', 'Names, specialties, credentials'),
        ('Programs', 'What programs and sessions are offered?', 'Program types, sessions, methods'),
        ('Contact', 'Contact and reservation information', 'Phone, email, booking, address'),
    ]),

    # ── 일반회사/산업 (영어) ──────────────────────────────────
    ('company', 'Company', 'General company & corporate sites', '🏢', [
        ('About', 'Introduce the company', 'History, mission, scale, philosophy'),
        ('Team', 'Introduce the executives and team', 'Executives, key staff, careers'),
        ('Services', 'What are the main products and services', 'Services, products, business areas'),
        ('Contact', 'Contact information and office locations', 'Phone, email, address, directions'),
    ]),
    ('company_construction', 'Construction', 'Construction & engineering companies', '🏗', [
        ('About', 'Introduce the construction company', 'History, major projects, capability'),
        ('Projects', 'Show key projects and track record', 'Completed projects, references'),
        ('Services', 'What services and fields do you cover?', 'Business areas, capabilities, certifications'),
        ('Contact', 'Contact information and inquiry process', 'Phone, email, request form'),
    ]),
    ('company_retail', 'Retail', 'Retail & e-commerce sites', '🛍', [
        ('About', 'Introduce the company and store', 'Brand story, store info, philosophy'),
        ('Products', 'What are the main products and categories?', 'Product lines, categories, bestsellers'),
        ('Store', 'Store locations and operating hours', 'Locations, hours, online store'),
        ('Contact', 'Customer service and support contacts', 'Customer service, support channels'),
    ]),
    ('company_tech', 'Tech', 'IT, software & tech companies', '💻', [
        ('About', 'Introduce the company and its mission', 'Company overview, vision, history'),
        ('Solutions', 'What solutions and services do you offer?', 'Products, solutions, tech stack'),
        ('Case Studies', 'Show customer success stories', 'References, case studies, results'),
        ('Contact', 'Contact information and demo requests', 'Contact options, demo requests'),
    ]),
    ('company_sales', 'Sales', 'Sales & customer-facing team sites (quotes, proposals)', '📈', [
        ('About', 'Introduce the company and its sales team', 'Company history, sales organization'),
        ('Products', 'What products and services do you sell?', 'Product lines, pricing, purchase process'),
        ('Quotes', 'How can I request a quote or proposal?', 'Quote requests, proposals, demo requests'),
        ('Contact', 'Introduce the sales contacts', 'Sales team, regional reps, phone, email'),
    ]),

    # ── 교육·상담 (영어) ─────────────────────────────────────
    ('edu_college', 'University', 'Universities & higher education', '🎓', [
        ('About', 'Introduce the university and its mission', 'History, campus, philosophy'),
        ('Faculties', 'List schools and departments', 'Colleges, departments, facilities'),
        ('Admissions', 'What are the admission requirements?', 'Admission criteria, process, scholarships'),
        ('Contact', 'Contact information and campus directions', 'Phone, email, campus locations'),
    ]),

    # ── 기타 (영어) ──────────────────────────────────────────
    ('blog', 'Blog', 'Personal & corporate blog sites', '📝', [
        ('About', 'Introduce the blog and its focus', 'Topics, author, writing philosophy'),
        ('Categories', 'What are the main blog categories', 'Topics, series, themes'),
        ('Posts', 'Show recent and popular posts', 'Latest articles, popular posts'),
        ('Contact', 'How can readers reach the author', 'Email, social media, comments'),
    ]),
]


class Command(BaseCommand):
    help = '도메인 유형(언어별) + 빠른메뉴를 시드합니다. --langs ko,en 처럼 언어를 지정할 수 있다.'

    # code 접두사 → 상위 카테고리 매핑
    CATEGORY_BY_PREFIX = [
        ('hospital', 'hospital'),
        ('law', 'law'),
        ('edu', 'edu'),
        ('company', 'company'),
    ]

    def _category_for(self, code: str) -> str:
        for prefix, cat in self.CATEGORY_BY_PREFIX:
            if code == prefix or code.startswith(prefix + '_'):
                return cat
        return 'etc'

    def add_arguments(self, parser):
        parser.add_argument(
            '--langs',
            default='',
            help='시드할 언어(콤마 구분). 비우면 환경 변수 WEBMCP_LANGS(기본 ko) 사용. 예: --langs ko,en',
        )

    def handle(self, *args, **options):
        from core.langsilo import current_lang, configured_langs

        langs_arg = (options.get('langs') or '').strip()
        want = [x.strip().lower() for x in langs_arg.split(',') if x.strip()] if langs_arg else []
        if not want:
            want = configured_langs()
        if not want:
            want = [current_lang()]

        total = 0
        # ── 언어별 카탈로그 시드 (사일로 격리: DomainType.lang 으로 구분) ──
        seeds = {'ko': SEED_KO, 'en': SEED_EN}
        for lang in want:
            seed = seeds.get(lang) or SEED_KO
            for order, (code, name, desc, icon, menus) in enumerate(seed, start=1):
                category = self._category_for(code)
                # code + lang 조합으로 격리 — 같은 code라도 언어별 별도 레코드
                dt, _ = DomainType.objects.get_or_create(
                    code=code, lang=lang,
                    defaults={'name': name, 'description': desc, 'icon': icon, 'category': category,
                              'sort_order': order, 'lang': lang},
                )
                # 재실행 시에도 정렬 순서/이름/카테고리/언어를 최신값으로 갱신
                DomainType.objects.filter(pk=dt.pk).update(
                    name=name, description=desc, icon=icon, category=category, sort_order=order, lang=lang,
                )
                for i, (label, question, hint) in enumerate(menus, start=1):
                    qm, _ = QuickMenu.objects.get_or_create(
                        domain_type=dt, label=label,
                        defaults={'question': question, 'prompt_hint': hint, 'sort_order': i},
                    )
                    QuickMenu.objects.filter(pk=qm.pk).update(
                        question=question, prompt_hint=hint, sort_order=i,
                    )
                # 필수 메뉴 — 언어별 공통 답변으로 마지막에 자동 추가 (편집/삭제 불가)
                self._ensure_required_menu(dt, lang)
            self.stdout.write(self.style.SUCCESS(f'[{lang}] 카탈로그 시드 완료 ({len(seed)}개 도메인)'))
        self.stdout.write(self.style.SUCCESS(f'카탈로그 시드 완료 — 사일로 언어: {",".join(want)}'))

    def _ensure_required_menu(self, dt, lang: str = 'ko'):
        """해당 언어 사일로의 필수 메뉴(한국어='AI비서란?', 영어='About AI Assistant')를 마지막에 추가한다."""
        req = REQUIRED_MENUS.get(lang) or REQUIRED_MENUS['ko']
        label = req['label']
        question = req['question']
        hint = req['hint']
        answer = req['answer']
        # 기존 메뉴 중 마지막 sort_order 다음에 배치
        last_order = QuickMenu.objects.filter(domain_type=dt).aggregate(m=models.Max('sort_order'))['m'] or 0
        qm, created = QuickMenu.objects.get_or_create(
            domain_type=dt, label=label,
            defaults={'question': question, 'prompt_hint': hint, 'sort_order': last_order + 1, 'is_required': True, 'answer_md': answer},
        )
        if created:
            return
        # 이미 존재하면 필수로 표시하고, 공통 답변을 최신값으로 갱신, 마지막 위치로 이동
        QuickMenu.objects.filter(pk=qm.pk).update(
            question=question, prompt_hint=hint, is_required=True, answer_md=answer, sort_order=last_order + 1,
        )
