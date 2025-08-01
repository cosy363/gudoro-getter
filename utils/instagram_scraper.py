import requests
import json
import re
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_instagram_posts(instagram_url):
    """
    인스타그램 계정의 최신 포스트 내용을 가져옵니다.
    
    Args:
        instagram_url (str): 인스타그램 프로필 URL
        
    Returns:
        str: 최신 포스트의 텍스트 내용
    """
    
    # Chrome 옵션 설정 (headless 모드)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(instagram_url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 첫 번째 포스트 클릭
        first_post = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "article div div div div a"))
        )
        first_post.click()
        
        # 포스트 내용 로딩 대기
        time.sleep(2)
        
        # 포스트 텍스트 추출
        post_text = ""
        try:
            # 포스트 설명 텍스트 찾기
            text_elements = driver.find_elements(By.CSS_SELECTOR, "article div div div div span")
            for element in text_elements:
                text = element.text.strip()
                if text and len(text) > 10:  # 의미있는 텍스트만
                    post_text += text + "\n"
                    
            # 대안: 다른 셀렉터로 시도
            if not post_text:
                text_elements = driver.find_elements(By.TAG_NAME, "span")
                for element in text_elements:
                    text = element.text.strip()
                    if text and any(keyword in text for keyword in ['메뉴', '오늘', '음식', '요리']):
                        post_text += text + "\n"
                        
        except Exception as e:
            print(f"텍스트 추출 중 오류: {e}")
            
        return post_text.strip()
        
    except Exception as e:
        print(f"인스타그램 스크래핑 오류: {e}")
        return ""
        
    finally:
        if driver:
            driver.quit()

def get_instagram_posts_fallback(instagram_url):
    """
    Selenium이 실패할 경우를 위한 fallback 함수
    requests + BeautifulSoup 사용 (제한적)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(instagram_url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Instagram의 JSON 데이터 추출 시도
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if 'mainEntity' in data and 'text' in data['mainEntity']:
                    return data['mainEntity']['text']
            except:
                continue
                
        return "fallback으로 메뉴 정보를 가져올 수 없습니다."
        
    except Exception as e:
        print(f"Fallback 스크래핑 오류: {e}")
        return ""

# 메인 함수
def scrape_menu_from_instagram(instagram_url):
    """
    인스타그램에서 메뉴 정보를 스크래핑하는 메인 함수
    """
    print(f"인스타그램 스크래핑 시작: {instagram_url}")
    
    # 먼저 Selenium으로 시도
    result = get_instagram_posts(instagram_url)
    
    # 실패하면 fallback 사용
    if not result:
        print("Selenium 스크래핑 실패, fallback 시도...")
        result = get_instagram_posts_fallback(instagram_url)
    
    # 여전히 실패하면 더미 데이터 반환
    if not result:
        result = "오늘의 메뉴 정보를 가져올 수 없습니다. 직접 인스타그램을 확인해주세요."
    
    return result

if __name__ == "__main__":
    # 테스트
    url = "https://www.instagram.com/sunaedong_buffet/"
    content = scrape_menu_from_instagram(url)
    print("스크래핑 결과:")
    print(content) 