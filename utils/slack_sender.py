import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime

def send_slack_message(message, channel="#lunch-menu"):
    """
    슬랙 채널로 메시지를 전송합니다.
    
    Args:
        message (str): 전송할 메시지
        channel (str): 슬랙 채널명 (기본값: #lunch-menu)
        
    Returns:
        bool: 전송 성공 여부
    """
    
    # 슬랙 토큰 가져오기
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("❌ SLACK_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        return False
    
    try:
        # 슬랙 클라이언트 초기화
        client = WebClient(token=slack_token)
        
        # 현재 시간을 포함한 메시지 포맷팅
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
        
        formatted_message = f"""
🍽️ **구도 한식뷔페 오늘의 메뉴** 🍽️

📅 업데이트 시간: {current_time}

{message}

---
💡 *매일 오전 11시에 자동으로 업데이트됩니다*
        """.strip()
        
        # 메시지 전송
        response = client.chat_postMessage(
            channel=channel,
            text=formatted_message,
            parse="full"
        )
        
        if response["ok"]:
            print(f"✅ 슬랙 메시지 전송 성공: {channel}")
            return True
        else:
            print(f"❌ 슬랙 메시지 전송 실패: {response.get('error', 'Unknown error')}")
            return False
            
    except SlackApiError as e:
        print(f"❌ 슬랙 API 오류: {e.response['error']}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def send_error_notification(error_message, channel="#lunch-menu"):
    """
    에러 발생 시 슬랙으로 알림을 전송합니다.
    
    Args:
        error_message (str): 에러 메시지
        channel (str): 슬랙 채널명
        
    Returns:
        bool: 전송 성공 여부
    """
    
    current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    
    error_notification = f"""
🚨 **메뉴 알림 시스템 오류** 🚨

⏰ 발생 시간: {current_time}

❌ 오류 내용:
{error_message}

🔧 관리자가 확인 중입니다. 잠시 후 다시 시도됩니다.
    """.strip()
    
    return send_slack_message(error_notification, channel)

def send_debug_info(debug_data, channel="#lunch-menu-debug"):
    """
    디버그 정보를 슬랙으로 전송합니다.
    
    Args:
        debug_data (dict): 디버그 정보가 담긴 딕셔너리
        channel (str): 디버그용 슬랙 채널명
        
    Returns:
        bool: 전송 성공 여부
    """
    
    current_time = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    
    debug_message = f"""
🔍 **디버그 정보** 🔍

⏰ 시간: {current_time}

📊 실행 상태:
- 인스타그램 스크래핑: {'✅' if debug_data.get('fetch_success') else '❌'}
- 메뉴 요약: {'✅' if debug_data.get('summarize_success') else '❌'}
- 슬랙 전송: {'✅' if debug_data.get('send_success') else '❌'}

📝 상세 정보:
{debug_data.get('details', '상세 정보 없음')}

🐛 에러 로그:
{chr(10).join(debug_data.get('error_log', ['에러 없음']))}
    """.strip()
    
    return send_slack_message(debug_message, channel)

if __name__ == "__main__":
    # 테스트
    test_message = """
🥘 **오늘의 메뉴**

**주요리**
- 갈비찜
- 불고기
- 생선구이

**밑반찬**
- 김치찌개
- 된장찌개
- 각종 나물류

**후식**
- 과일
- 커피/차
    """.strip()
    
    result = send_slack_message(test_message)
    print(f"테스트 결과: {result}") 