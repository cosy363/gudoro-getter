import requests
import json
import re
import random
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 다양한 User-Agent 리스트 (안티-봇 회피)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
]

def get_random_user_agent():
    """랜덤 User-Agent 반환"""
    return random.choice(USER_AGENTS)

def setup_chrome_options(proxy=None):
    """Chrome 브라우저 옵션 설정 (프록시 지원)"""
    chrome_options = Options()
    
    # 기본 옵션
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 랜덤 User-Agent 설정
    chrome_options.add_argument(f"--user-agent={get_random_user_agent()}")
    
    # 프록시 설정 (선택사항)
    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")
    
    # 추가 안티-봇 회피 설정
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    
    return chrome_options

def get_instagram_posts_advanced(instagram_url, proxy=None):
    """
    개선된 인스타그램 포스트 스크래핑 (프록시 지원)
    
    Args:
        instagram_url (str): 인스타그램 프로필 URL
        proxy (str): 프록시 서버 (예: "http://proxy:port")
        
    Returns:
        str: 최신 포스트의 텍스트 내용
    """
    driver = None
    try:
        # Chrome 옵션 설정
        chrome_options = setup_chrome_options(proxy)
        driver = webdriver.Chrome(options=chrome_options)
        
        # 안티-봇 회피: navigator.webdriver 숨기기
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 페이지 로드
        driver.get(instagram_url)
        
        # 랜덤 지연 (봇 탐지 회피)
        time.sleep(random.uniform(2, 5))
        
        # 쿠키 배너 등 팝업 처리
        try:
            # "나중에 하기" 버튼 클릭 (로그인 팝업)
            later_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '나중에') or contains(text(), 'Not Now')]"))
            )
            later_button.click()
            time.sleep(1)
        except TimeoutException:
            pass  # 팝업이 없으면 계속 진행
        
        # 첫 번째 포스트 찾기 (여러 셀렉터 시도)
        post_selectors = [
            "article div div div div a",
            "div[role='main'] article a",
            "main article a[role='link']",
            "div._ac7v a"  # Instagram의 새로운 클래스명
        ]
        
        first_post = None
        for selector in post_selectors:
            try:
                first_post = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                break
            except TimeoutException:
                continue
        
        if not first_post:
            raise Exception("첫 번째 포스트를 찾을 수 없습니다")
        
        # 포스트 클릭
        driver.execute_script("arguments[0].click();", first_post)
        time.sleep(random.uniform(2, 4))
        
        # 포스트 텍스트 추출 (여러 방법 시도)
        post_text = extract_post_text(driver)
        
        return post_text.strip()
        
    except Exception as e:
        print(f"고급 인스타그램 스크래핑 오류: {e}")
        return ""
        
    finally:
        if driver:
            driver.quit()

def extract_post_text(driver):
    """포스트 텍스트 추출 (여러 방법 시도)"""
    post_text = ""
    
    # 방법 1: 최신 Instagram 구조
    text_selectors = [
        "div[data-testid='post-caption'] span",
        "article div div div div span",
        "div._a9zs span",  # 새로운 클래스명
        "span[dir='auto']"
    ]
    
    for selector in text_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                text = element.text.strip()
                if text and len(text) > 10:
                    post_text += text + "\n"
            
            if post_text:
                break
                
        except Exception as e:
            continue
    
    # 방법 2: 키워드 기반 검색
    if not post_text:
        try:
            all_spans = driver.find_elements(By.TAG_NAME, "span")
            menu_keywords = ['메뉴', '오늘', '음식', '요리', '뷔페', '한식', '반찬', '국', '찌개']
            
            for element in all_spans:
                text = element.text.strip()
                if text and any(keyword in text for keyword in menu_keywords):
                    post_text += text + "\n"
                    
        except Exception as e:
            pass
    
    return post_text

def get_instagram_posts_requests(instagram_url, proxy=None):
    """
    requests + BeautifulSoup을 사용한 개선된 fallback 방법
    """
    try:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 프록시 설정
        proxies = None
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy
            }
        
        # 요청 전 랜덤 지연
        time.sleep(random.uniform(1, 3))
        
        response = requests.get(
            instagram_url, 
            headers=headers, 
            proxies=proxies,
            timeout=15
        )
        
        if response.status_code != 200:
            return f"HTTP 오류: {response.status_code}"
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 방법 1: JSON-LD 데이터 추출
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # 다양한 구조 확인
                    if 'mainEntity' in data and 'text' in data['mainEntity']:
                        return data['mainEntity']['text']
                    elif 'description' in data:
                        return data['description']
                        
            except json.JSONDecodeError:
                continue
        
        # 방법 2: window._sharedData 추출
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and 'window._sharedData' in script.string:
                try:
                    # JSON 데이터 추출 로직
                    json_match = re.search(r'window\._sharedData = ({.*?});', script.string)
                    if json_match:
                        shared_data = json.loads(json_match.group(1))
                        # 포스트 데이터 탐색
                        return extract_from_shared_data(shared_data)
                except:
                    continue
        
        return "requests 방식으로 메뉴 정보를 추출할 수 없습니다."
        
    except Exception as e:
        print(f"requests 스크래핑 오류: {e}")
        return ""

def extract_from_shared_data(shared_data):
    """window._sharedData에서 텍스트 추출"""
    try:
        # Instagram의 복잡한 JSON 구조 탐색
        entry_data = shared_data.get('entry_data', {})
        profile_page = entry_data.get('ProfilePage', [])
        
        if profile_page:
            user_data = profile_page[0].get('graphql', {}).get('user', {})
            media_data = user_data.get('edge_owner_to_timeline_media', {}).get('edges', [])
            
            if media_data:
                latest_post = media_data[0].get('node', {})
                caption = latest_post.get('edge_media_to_caption', {}).get('edges', [])
                
                if caption:
                    return caption[0].get('node', {}).get('text', '')
        
        return ""
        
    except Exception as e:
        return ""

def scrape_menu_from_instagram(instagram_url, use_proxy=False, proxy=None):
    """
    개선된 인스타그램 메뉴 스크래핑 메인 함수
    
    Args:
        instagram_url (str): 인스타그램 프로필 URL
        use_proxy (bool): 프록시 사용 여부
        proxy (str): 프록시 서버 주소
    """
    print(f"📱 인스타그램 스크래핑 시작: {instagram_url}")
    
    if use_proxy and proxy:
        print(f"🌐 프록시 사용: {proxy}")
    
    # 방법 1: 고급 Selenium 스크래핑
    result = get_instagram_posts_advanced(instagram_url, proxy if use_proxy else None)
    
    # 방법 2: requests + BeautifulSoup fallback
    if not result or len(result) < 20:
        print("🔄 Selenium 실패, requests 방식으로 재시도...")
        result = get_instagram_posts_requests(instagram_url, proxy if use_proxy else None)
    
    # 방법 3: 기존 방식 fallback
    if not result or len(result) < 20:
        print("🔄 모든 방식 실패, 기본 스크래퍼로 재시도...")
        from .instagram_scraper_legacy import get_instagram_posts as legacy_scraper
        try:
            result = legacy_scraper(instagram_url)
        except:
            result = ""
    
    # 최종 fallback
    if not result or len(result) < 10:
        result = """
🍽️ 구도 한식뷔페 메뉴 정보
━━━━━━━━━━━━━━━━━━━━

⚠️ 현재 인스타그램에서 메뉴 정보를 자동으로 가져올 수 없습니다.

📱 직접 확인: https://www.instagram.com/sunaedong_buffet/

📞 매장 문의: 구도 한식뷔페
🕒 운영시간: 오전 11시 ~ 오후 9시

━━━━━━━━━━━━━━━━━━━━
        """.strip()
    
    print(f"✅ 스크래핑 완료 (길이: {len(result)}자)")
    return result

# 기존 함수들 (하위 호환성)
def get_instagram_posts(instagram_url):
    """하위 호환성을 위한 래퍼 함수"""
    return scrape_menu_from_instagram(instagram_url)

def get_instagram_posts_fallback(instagram_url):
    """하위 호환성을 위한 래퍼 함수"""
    return get_instagram_posts_requests(instagram_url)

if __name__ == "__main__":
    # 테스트
    url = "https://www.instagram.com/sunaedong_buffet/"
    
    print("=== 기본 스크래핑 테스트 ===")
    content = scrape_menu_from_instagram(url)
    print("스크래핑 결과:")
    print(content)
    
    print("\n=== 프록시 스크래핑 테스트 (주석 해제하여 사용) ===")
    # proxy_server = "http://proxy-server:port"  # 실제 프록시 주소
    # content_with_proxy = scrape_menu_from_instagram(url, use_proxy=True, proxy=proxy_server)
    # print("프록시 스크래핑 결과:")
    # print(content_with_proxy) 