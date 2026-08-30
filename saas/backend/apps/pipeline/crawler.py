"""크롤러 — crawl4ai 우선, httpx 폴백. sitemap.xml 기반 다중 페이지 크롤 지원."""
from __future__ import annotations

import html
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import httpx

TAG_RE = re.compile(r'<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>', re.S | re.I)
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)
# 내비게이션/메뉴/푸터/사이드 등 공통 보일러플레이트 블록 제거
NAV_BLOCK_RE = re.compile(
    r'<(div|ul|nav|aside)[^>]*class=["\'][^"\']*(?:gnb|menu|nav|hd_|quick|side|footer|header|top_|m_)[^"\']*["\'][^>]*>.*?</\1>',
    re.S | re.I,
)
BLOCK_RE = re.compile(r'</(p|div|h[1-6]|li|tr|section|article)>', re.I)
STRIP_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\n{3,}')


ANCHOR_RE = re.compile(r'<a\s+([^>]*?)>(.*?)</a>', re.I | re.S)
_HREF_RE = re.compile(r'href=["\'](.*?)["\']', re.I)
_IGNORE_HREF = ('javascript:', 'mailto:', 'tel:', '#')


def _preserve_links(page_html: str) -> str:
    """<a href> 링크 보존 정책.

    - 절대 http(s) URL(예: https://pf.kakao.com/..)만 마크다운 링크
      [텍스트](url)로 보존한다. — 위젯이 사용자 도메인이 아닌 로컬(127.0.0.1)로
      오해석하는 것을 막기 위해 **상대경로는 링크로 만들지 않는다**.
    - 상대경로(/reserve/..), tel:, mailto:, javascript:, # 는 텍스트만 남긴다.
    - 호스트가 127.0.0.1 / localhost 인 링크도 제외한다.
    """
    def _repl(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        href_m = _HREF_RE.search(attrs)
        if not href_m:
            return inner
        href = html.unescape(href_m.group(1).strip())
        if not href or href.startswith(_IGNORE_HREF):
            return inner
        # 상대경로(스킴 없음)는 링크로 만들지 않음
        if not href.startswith(('http://', 'https://')):
            return inner
        # 로컬/사설 호스트 제외
        if re.match(r'https?://(?:localhost|127\.0\.0\.1)(?:[:/]|$)', href, re.I):
            return inner
        text = re.sub(r'<[^>]+>', ' ', inner)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if not text or text.lower() in ('', 'home', 'logo', '바로가기', '메뉴'):
            return f'{href}'
        return f'[{text}]({href})'

    return ANCHOR_RE.sub(_repl, page_html)


def _html_to_text(html: str) -> str:
    html = COMMENT_RE.sub('', html)
    html = _preserve_links(html)  # 링크 보존 (NAV 제거 전) — 예약/문의 링크 유지
    html = TAG_RE.sub(' ', html)
    html = NAV_BLOCK_RE.sub(' ', html)
    text = BLOCK_RE.sub('\n', html)
    text = STRIP_RE.sub('', text)
    return WS_RE.sub('\n\n', text).strip()


# 식별 가능한 커스텀 봇 UA (기본) — robots.txt를 준수하는 사이트에서는 이것으로 충분.
# Akamai/Cloudflare 등 WAF가 커스텀/비표준 UA를 차단하는 사이트가 많아,
# 차단 응답(짧은 본문 + unavailable/denied)을 감지하면 브라우저 UA로 폴백한다.
# (robots.txt의 User-agent 규칙은 httpx 기본 UA와 동일하게 무해하게 사용)
_UA = {'User-Agent': 'Mozilla/5.0 (WebMCPAutoBot/1.0)'}

# WAF 차단 폴백용 — 일반 브라우저 UA + 표준 헤더. robots.txt Disallow는 사이트맵
# 수집 이전에 validate_crawl_url 등 상위 정책으로 통제하며, 크롤 본문(대상 사이트
# 콘텐츠)도 운영자 동의 기반 SaaS이므로 정상 페이지만 수집 된다.
# 주의: Sec-Fetch-* 등 모든 브라우저 표준 헤더를 갖춰야 Akamai가 통과시킨다
# (실측: UA만으로는 3762B 차단 페이지, 전체 헤더 시 499KB+ 정상 응답).
_UA_BROWSER = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1',
}

_BLOCK_MARKERS = ('unavailable', 'access denied', 'denied', 'captcha',
                  'blocked', 'verify you are', 'attention required')


def _looks_blocked(text: str) -> bool:
    """짧은 본문 + 차단 키워드 조합으로 WAF 차단 페이지를 판별."""
    if not text or len(text) > 20_000:
        return False
    lower = text.lower()
    return any(k in lower for k in _BLOCK_MARKERS)


def _headers_with_fallback(base_headers: dict, response_text: str) -> dict:
    """차단 페이지로 판단되면 브라우저 UA 헤더로 교체해 반환."""
    if _looks_blocked(response_text):
        return dict(_UA_BROWSER)
    return base_headers


def _url_depth_score(target_url: str, base_url: str) -> tuple[int, int, int]:
    """root URL에서 가까운 낮은 depth 순으로 정렬하기 위한 점수 계산.

    반환: (is_not_base, slash_depth, length)
    1. base_url 자신은 최우선 (is_not_base = 0)
    2. path의 슬래시(/) 개수가 적을수록 depth가 낮음
    3. 동일 depth 내에서는 URL 길이가 짧은 것을 우선 (메인 카테고리/섹션 페이지 우선)
    """
    p_target = urlparse(target_url)
    p_base = urlparse(base_url)

    # 기본 URL과 동일한지 여부 (정규화된 경로 기준)
    is_exact_root = 0 if target_url.rstrip('/') == base_url.rstrip('/') else 1

    # 경로 내 슬래시 개수 (앞뒤 슬래시 제외)
    path = p_target.path.strip('/')
    depth = 0 if not path else len(path.split('/'))

    # 쿼리스트링이나 해시가 있으면 depth 페널티 부여
    has_query = 1 if p_target.query else 0

    return (is_exact_root, depth + has_query, len(target_url))


def fetch_sitemap_urls(url: str, limit: int = 30) -> list[str]:
    """입력 URL의 사이트에서 sitemap.xml을 찾아 root URL에 가까운(낮은 depth) 상위 `limit`개 페이지 URL 반환.

    - robots.txt의 Sitemap 지시 → {origin}/sitemap.xml 순으로 탐색.
    - sitemap index면 하위 sitemap을 재귀(1단계) 탐색.
    - 사이트맵이 없거나 URL을 찾지 못한 경우, 홈페이지 HTML 내 내부 링크(`<a>` 태그)를 수집하여 폴백.
    - 같은 origin의 http(s) URL만 수집.
    - root URL에서 depth가 얕은 순서(메인, 1차 메뉴 등)로 정렬하여 반환.
    - 실패 시 [url] 반환.
    """
    items = fetch_sitemap_items(url, limit=limit)
    return [item['url'] for item in items]


def fetch_sitemap_items(url: str, limit: int = 30) -> list[dict[str, str]]:
    """입력 URL의 사이트에서 sitemap/링크를 찾아 [{'url': ..., 'title': ...}] 목록 반환."""
    origin = f'{urlparse(url).scheme}://{urlparse(url).netloc}'
    candidates: list[str] = []
    urls: list[str] = []
    discovered_labels: dict[str, str] = {}
    try:
        # UA 폴백 관리 — robots/sitemap 요청마다 차단 상태를 확인해 헤더 교체
        headers = dict(_UA)
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            # 세션 워밍업 — Akamai 등 WAF는 홈페이지(Under Attack 우회)에서 _abck 쿠키를
            # 발급한 뒤에만 robots/sitemap을 정상 응답한다. 직행 요청은 차단페이지(3.7KB,
            # HTTP 200 위장)를 반환한다. 커스텀 UA 홈 요청이 차단되면 브라우저 UA로
            # 홈을 다시 방문해 유효 세션 쿠키를 확보한 뒤 진행한다.
            try:
                warm = client.get(url, headers=headers)
                if _looks_blocked(warm.text):
                    headers = _headers_with_fallback(headers, warm.text)
                    time.sleep(0.5)
                    client.get(url, headers=headers)
            except httpx.HTTPError:
                pass
            try:
                robots = client.get(f'{origin}/robots.txt', headers=headers)
                if _looks_blocked(robots.text):
                    # robots.txt 자체가 WAF 차단이면 브라우저 UA로 전환
                    headers = _headers_with_fallback(headers, robots.text)
                    robots = client.get(f'{origin}/robots.txt', headers=headers)
                if robots.status_code == 200:
                    for line in robots.text.splitlines():
                        if line.lower().startswith('sitemap:'):
                            candidates.append(line.split(':', 1)[1].strip())
            except httpx.HTTPError:
                pass
            candidates.extend([
                f'{origin}/sitemap.xml',
                f'{origin}/sitemap_index.xml',
                f'{origin}/sitemap-index.xml',
                f'{origin}/sitemapindex.xml',
                f'{origin}/sitemaps/sitemap.xml',
            ])

            # 후보 정렬: 같은 호스트의 sitemap을 우선 시도한다.
            # Hopkinsmedicine처럼 robots.txt에 다른 호스트 sitemap(profiles.xxx.org)이 먼저
            # 나와도, 그것이 성공하는 순간 중단하지 않고 동일 호스트 sitemap까지 시도한다.
            base_host = urlparse(origin).netloc
            ordered: list[str] = []
            for c in dict.fromkeys(candidates):
                if urlparse(c).netloc == base_host:
                    ordered.append(c)
            for c in dict.fromkeys(candidates):
                if urlparse(c).netloc != base_host:
                    ordered.append(c)
            candidates = ordered

            seen_sitemaps: set[str] = set()
            cap = limit * 20  # 후보군을 충분히 수집 후 depth 정렬
            for sm in candidates:
                _collect_sitemap(client, sm, urls, seen_sitemaps, depth=0, cap=cap, headers=headers)
                if not urls:
                    continue
                host_matched = any(urlparse(u).netloc == base_host for u in urls)
                if host_matched:
                    break

            # sitemap에서 URL을 찾지 못했거나, sitemap URL의 호스트가
            # 입력 URL의 호스트와 다른 경우(punycode 도메인 등) 홈페이지 HTML 폴백
            host_matched = any(urlparse(u).netloc == base_host for u in urls)
            if not host_matched:
                _collect_html_links_with_labels(client, url, urls, discovered_labels, cap=cap)
    except Exception:  # noqa: BLE001
        if not urls:
            return [{'url': url, 'title': ''}]

    base_host = urlparse(origin).netloc
    clean: list[str] = []
    for u in urls:
        p = urlparse(u)
        if p.scheme in ('http', 'https') and p.netloc == base_host and u not in clean:
            clean.append(u)

    # 입력 URL을 기본 포함
    if url not in clean:
        clean.append(url)

    # root URL에 가까운 낮은 depth 순으로 정렬
    clean.sort(key=lambda u: _url_depth_score(u, url))
    target_urls = clean[:limit]

    # 각 페이지 제목(Title) 추출 (sitemap 탐색 시 or 메뉴 텍스트 부족 시 병렬 fetch)
    titles = _fetch_titles_for_urls(target_urls, discovered_labels)
    return [{'url': u, 'title': titles.get(u, '')} for u in target_urls]


_IGNORE_EXTS = (
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
    '.css', '.js', '.map', '.woff', '.woff2', '.ttf', '.eot',
    '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
    '.mp4', '.mp3', '.avi', '.mov', '.wmv',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
)


def _collect_html_links_with_labels(
    client: httpx.Client, page_url: str, out: list[str], labels_map: dict[str, str], cap: int
) -> None:
    """sitemap이 없을 때 페이지 HTML에서 동일 도메인의 링크와 메뉴 라벨을 추출."""
    headers = dict(_UA)
    # 일시적 네트워크 실패 대비 홈페이지 fetch 재시도 (최대 3회)
    resp = None
    for attempt in range(3):
        try:
            resp = client.get(page_url, headers=headers)
            if _looks_blocked(resp.text):
                # WAF 차단 시 브라우저 UA로 전환 재시도
                headers = _headers_with_fallback(headers, resp.text)
                continue
            if resp.status_code == 200 and 'text/html' in resp.headers.get('content-type', ''):
                break
            resp = None
        except Exception:  # noqa: BLE001
            resp = None
        if attempt < 2:
            time.sleep(1.0)
    if resp is None:
        return
    try:
        origin = f'{urlparse(page_url).scheme}://{urlparse(page_url).netloc}'
        base_netloc = urlparse(origin).netloc

        # <a ...>...</a> 매칭
        pattern = re.compile(r'<a\s+([^>]*?)>(.*?)</a>', re.I | re.S)
        matches = pattern.findall(resp.text)
        for attrs, inner in matches:
            if len(out) >= cap:
                break
            href_m = re.search(r'href=[\"\'](.*?)[\"\']', attrs, re.I)
            if not href_m:
                continue
            h = html.unescape(href_m.group(1).strip())  # &amp; → &
            if not h or h.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            full_url = urljoin(page_url, h).split('#')[0]
            p = urlparse(full_url)
            if p.scheme in ('http', 'https') and p.netloc == base_netloc:
                path_lower = p.path.lower()
                if not any(path_lower.endswith(ext) for ext in _IGNORE_EXTS):
                    if full_url not in out:
                        out.append(full_url)
                    # 텍스트 / title / alt 추출 (alt는 파일명류 제외하고 최후 수단)
                    if full_url not in labels_map:
                        title_m = re.search(r'title=[\"\'](.*?)[\"\']', attrs, re.I)
                        title_attr = html.unescape(title_m.group(1)).strip() if title_m else ''
                        text = re.sub(r'<[^>]+>', ' ', inner)
                        text = html.unescape(text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        best = text or title_attr
                        if not best:
                            img_m = re.search(r'<img[^>]*alt=[\"\'](.*?)[\"\']', inner, re.I)
                            img_alt = html.unescape(img_m.group(1)).strip() if img_m else ''
                            # 이미지 파일명/확장자류 alt는 라벨로 부적합 → 사용하지 않음
                            if img_alt and not any(img_alt.lower().endswith(ext) for ext in _IGNORE_EXTS):
                                best = img_alt
                        if best:
                            labels_map[full_url] = best
    except Exception:  # noqa: BLE001
        return


def _fetch_single_title(client: httpx.Client, page_url: str) -> tuple[str, str]:
    """단일 페이지에서 <title> 또는 <meta og:title> 추출. WAF 차단 시 브라우저 UA 재시도."""
    for headers in (_UA, _UA_BROWSER):
        try:
            r = client.get(page_url, headers=headers, timeout=4)
            if r.status_code == 200 and not _looks_blocked(r.text):
                m = re.search(r'<title[^>]*>(.*?)</title>', r.text, re.I | re.S)
                if m:
                    t = html.unescape(m.group(1))
                    t = re.sub(r'\s+', ' ', t).strip()
                    if t:
                        return page_url, t
                og = re.search(r'<meta[^>]*property=[\"\']og:title[\"\'][^>]*content=[\"\'](.*?)[\"\']', r.text, re.I)
                if not og:
                    og = re.search(r'<meta[^>]*content=[\"\'](.*?)[\"\'][^>]*property=[\"\']og:title[\"\']', r.text, re.I)
                if og:
                    t = html.unescape(og.group(1))
                    t = re.sub(r'\s+', ' ', t).strip()
                    if t:
                        return page_url, t
        except Exception:  # noqa: BLE001
            pass
    return page_url, ''


def _fetch_titles_for_urls(urls: list[str], fallback_labels: dict[str, str]) -> dict[str, str]:
    """URL 목록에 대해 최적의 제목을 결정 (HTML 메뉴 라벨 우선 + 보충 병렬 fetch)."""
    titles: dict[str, str] = {}
    missing_urls: list[str] = []

    # 부적합한 라벨(이미지 alt류, 일반 명칭 등)은 실제 <title>로 대체 대상
    _BAD_LABELS = {'', 'company logo', 'logo', 'home', '홈', '메인'}

    for u in urls:
        label = fallback_labels.get(u, '').strip()
        is_root = u.rstrip('/') == urls[0].rstrip('/') if urls else False
        if label and label.lower() not in _BAD_LABELS and not is_root:
            titles[u] = label
        else:
            missing_urls.append(u)

    # 라벨이 없는 URL(또는 부적합한 라벨)이 있으면 병렬로 가볍게 <title> 태그 조회
    if missing_urls:
        try:
            with httpx.Client(timeout=4, follow_redirects=True) as client:
                with ThreadPoolExecutor(max_workers=min(10, len(missing_urls))) as executor:
                    results = list(executor.map(lambda target: _fetch_single_title(client, target), missing_urls))
                for target_url, t in results:
                    titles[target_url] = t
        except Exception:  # noqa: BLE001
            pass

    return titles


def _collect_sitemap(client: httpx.Client, sm_url: str, out: list[str],
                     seen: set[str], depth: int, cap: int, headers: dict | None = None) -> None:
    if sm_url in seen or depth > 1 or len(out) >= cap:
        return
    seen.add(sm_url)
    try:
        resp = client.get(sm_url, headers=headers or _UA)
        if _looks_blocked(resp.text):
            # sitemap 요청이 WAF 차단이면 브라우저 UA로 재시도 (재귀 시에도 유지됨)
            headers = _headers_with_fallback(headers or _UA, resp.text)
            resp = client.get(sm_url, headers=headers)
        if resp.status_code != 200 or '<' not in resp.text[:100]:
            return
        root = ET.fromstring(resp.content)
    except Exception:  # noqa: BLE001
        return

    def lname(tag: str) -> str:
        return tag.rsplit('}', 1)[-1]

    for child in root:
        kind = lname(child.tag)
        if kind not in ('url', 'sitemap'):
            continue
        loc = next((e.text for e in child if lname(e.tag) == 'loc' and e.text), None)
        if not loc:
            continue
        loc = loc.strip()
        if kind == 'url':
            out.append(loc)
        elif depth == 0:
            _collect_sitemap(client, loc, out, seen, depth + 1, cap, headers)


def crawl_many(url: str, limit: int = 10, per_page_chars: int = 30_000, target_urls: list[str] | None = None) -> dict:
    """sitemap 상위 N개 페이지 또는 지정된 target_urls를 크롤해 하나의 markdown으로 결합."""
    if target_urls:
        pages = target_urls[:limit]
    else:
        pages = fetch_sitemap_urls(url, limit=limit)
    chunks: list[str] = []
    crawled_pages: list[str] = []
    page_titles: dict[str, str] = {}
    failed_pages: list[dict] = []  # 재시도 후에도 실패/건너뛴 페이지 목록
    title = ''
    # 모든 선택 페이지가 들어가도록 총 크기 상한을 페이지 수 기준으로 설정
    total_limit = max(60_000, limit * per_page_chars)
    for idx, page_url in enumerate(pages):
        r = None
        last_err = ''
        # 일시적 네트워크/타임아웃 실패 대비 재시도 (최대 3회)
        for attempt in range(3):
            try:
                r = crawl(page_url)
                break
            except Exception as e:  # noqa: BLE001 — 한 페이지 실패는 재시도 후 기록
                last_err = str(e)
                if attempt < 2:
                    time.sleep(1.5)
        if r is None:
            failed_pages.append({'url': page_url, 'error': last_err[:300]})
            continue
        if not title and r['title']:
            title = r['title']
        page_titles[page_url] = r['title']
        md = r['markdown'][:per_page_chars]
        chunks.append(f'## [페이지] {page_url}\n\n{md}')
        crawled_pages.append(page_url)
        if sum(len(c) for c in chunks) > total_limit:
            # 크기 제한으로 남은 페이지는 건너뛰되, 실패 내역에 명시
            for remaining in pages[idx + 1:]:
                failed_pages.append({'url': remaining, 'error': '본문 크기 제한으로 건너뜀'})
            break
    if not chunks:
        raise RuntimeError('크롤에 성공한 페이지가 없습니다')
    return {
        'title': title,
        'markdown': '\n\n'.join(chunks),
        'pages': crawled_pages,
        'page_titles': page_titles,
        'failed_pages': failed_pages,
    }


def crawl(url: str) -> dict:
    """{title, markdown} 반환. 실패 시 RuntimeError."""
    try:
        return _crawl_crawl4ai(url)
    except Exception:  # noqa: BLE001 — 폴백
        return _crawl_httpx(url)


def _crawl_httpx(url: str) -> dict:
    """단일 페이지 크롤(httpx). 커스텀 UA가 403/차단페이지면 브라우저 헤더로 폴백."""
    html: str | None = None
    last_err: Exception | None = None
    for headers in (_UA, _UA_BROWSER):
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                # 403/401 또는 위장 차단페이지면 다음 UA로 재시도
                if resp.status_code in (403, 401):
                    last_err = RuntimeError(f'HTTP {resp.status_code} (UA: {headers.get("User-Agent", "")[:20]})')
                    continue
                resp.raise_for_status()
                if _looks_blocked(resp.text):
                    last_err = RuntimeError('WAF 차단 페이지 감지')
                    continue
                html = resp.text

                # JS 리다이렉트(document.location.href=...) 추종 — 후보 전부 시도, 가장 큰 본문 채택
                if len(html) < 3000:
                    cands = re.findall(r'location\.href\s*=\s*["\']([^"\']+)["\']', html)
                    for target in dict.fromkeys(cands):
                        if not target.startswith('http'):
                            continue
                        try:
                            resp2 = client.get(target, headers=headers)
                        except httpx.HTTPError:
                            continue
                        if resp2.status_code == 200 and len(resp2.text) > len(html):
                            html = resp2.text
                            break
                break   # 이 UA로 정상 획득
        except httpx.HTTPError as e:
            last_err = e
            continue
    if html is None:
        raise RuntimeError(f'페이지 획득 실패: {last_err}')

    title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    title = title_m.group(1).strip() if title_m else url
    markdown = _html_to_text(html)
    if len(markdown) < 500:
        raise RuntimeError(f'본문이 너무 짧습니다({len(markdown)}자)')
    # 실제 이메일 주소가 HTML에 있으면 마크다운에 보존 (난독화 [email..] 제외)
    emails = _extract_real_emails(html)
    if emails:
        contact_section = '\n\n## 문의 연락처\n' + '\n'.join(f'- 이메일: {e}' for e in emails)
        markdown = smart_trim(markdown + contact_section, 60_000)
    return {'title': title[:255], 'markdown': markdown}


_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
_BAD_EMAIL_TOKENS = ('[email', 'protected', 'domain', 'sitename', 'example.com', 'yourdomain')


def _extract_real_emails(html: str) -> list[str]:
    """raw HTML에서 실제 유효 이메일 주소를 추출한다.

    JS 난독화로 생긴 '[email protected]', 'user@[email protected]' 등의
    걸리쉬 문자열은 제외하고 진짜 이메일만 남긴다.
    """
    found: list[str] = []
    seen: set[str] = set()
    for m in _EMAIL_RE.findall(html):
        e = m.strip()
        low = e.lower()
        if any(t in low for t in _BAD_EMAIL_TOKENS):
            continue
        if e not in seen:
            seen.add(e)
            found.append(e)
    return found[:5]


def _crawl_crawl4ai(url: str) -> dict:
    try:
        from crawl4ai import AsyncWebCrawler  # noqa: PLC0415
    except ImportError as e:
        raise RuntimeError('crawl4ai 미설치') from e
    import asyncio

    async def run():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return result.markdown or ''

    markdown = asyncio.run(run())
    if len(markdown) < 500:
        raise RuntimeError(f'본문이 너무 짧습니다({len(markdown)}자)')
    return {'title': '', 'markdown': smart_trim(markdown, 60_000)}


def smart_trim(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # 헤더/단락 경계를 존중해 앞부분 위주로 축약
    lines = text.split('\n')
    out, size = [], 0
    for line in lines:
        if size + len(line) > limit and size > limit * 0.8:
            break
        out.append(line)
        size += len(line) + 1
    return '\n'.join(out)
