from pocketflow import Flow
from nodes import FetchMenuNode, SummarizeMenuNode, SendSlackNode, DebugCheckNode
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

def create_menu_notification_flow():
    """
    구도 한식뷔페 메뉴 알림 워크플로우를 생성합니다.
    
    플로우 구조:
    1. FetchMenuNode: 인스타그램에서 메뉴 수집
    2. DebugCheckNode: 수집 상태 확인 및 재시도 결정
    3. SummarizeMenuNode: LLM으로 메뉴 요약
    4. DebugCheckNode: 요약 상태 확인 및 재시도 결정  
    5. SendSlackNode: 슬랙으로 메시지 전송
    6. DebugCheckNode: 전송 상태 확인 및 최종 완료
    """
    
    # 1. 노드 생성 (재시도 옵션 포함)
    fetch_node = FetchMenuNode(max_retries=3, wait=5)
    summarize_node = SummarizeMenuNode(max_retries=2, wait=3)
    send_node = SendSlackNode(max_retries=2, wait=2)
    
    # 디버그 체크 노드들 (각 단계마다)
    debug_fetch = DebugCheckNode()
    debug_summarize = DebugCheckNode()  
    debug_send = DebugCheckNode()
    
    # 2. 플로우 연결
    # 메뉴 수집 -> 디버그 체크
    fetch_node >> debug_fetch
    
    # 디버그 결과에 따른 분기
    debug_fetch - "success" >> summarize_node  # 성공시 요약 단계로
    debug_fetch - "retry" >> fetch_node        # 재시도시 다시 수집
    debug_fetch - "fail" >> send_node          # 실패시에도 에러 메시지라도 전송 시도
    
    # 메뉴 요약 -> 디버그 체크
    summarize_node >> debug_summarize
    
    # 요약 디버그 결과에 따른 분기
    debug_summarize - "success" >> send_node    # 성공시 전송 단계로
    debug_summarize - "retry" >> summarize_node # 재시도시 다시 요약
    debug_summarize - "fail" >> send_node       # 실패시에도 fallback 메시지 전송
    
    # 슬랙 전송 -> 최종 디버그 체크
    send_node >> debug_send
    
    # 전송 디버그 결과 (최종 단계)
    debug_send - "success" >> None  # 성공시 종료
    debug_send - "retry" >> send_node    # 재시도시 다시 전송
    debug_send - "fail" >> None     # 실패시 종료 (더 이상 할 수 있는 것 없음)
    
    # 3. 플로우 생성 (fetch_node부터 시작)
    flow = Flow(start=fetch_node)
    
    logging.info("📋 메뉴 알림 워크플로우 생성 완료")
    logging.info("🔗 플로우 구조: fetch -> debug -> summarize -> debug -> send -> debug")
    
    return flow

def create_simple_menu_flow():
    """
    디버그 없는 간단한 메뉴 워크플로우 (테스트용)
    """
    fetch_node = FetchMenuNode(max_retries=2)
    summarize_node = SummarizeMenuNode(max_retries=2)
    send_node = SendSlackNode(max_retries=2)
    
    # 단순 순차 연결
    fetch_node >> summarize_node >> send_node
    
    return Flow(start=fetch_node)

def get_default_shared_store():
    """
    기본 shared store 구조를 반환합니다.
    """
    return {
        "config": {
            "instagram_url": "https://www.instagram.com/sunaedong_buffet/",
            "slack_channel": "#lunch-menu",
            "debug_mode": True
        },
        "menu_data": {
            "raw_content": "",
            "extracted_menu": "",
            "summary": ""
        },
        "status": {
            "fetch_success": False,
            "summarize_success": False,
            "send_success": False,
            "last_run": None,
            "error_log": []
        }
    }

# 기본 워크플로우 생성
menu_flow = create_menu_notification_flow()
simple_flow = create_simple_menu_flow()

if __name__ == "__main__":
    # 테스트 실행
    print("=== 메뉴 알림 워크플로우 테스트 ===")
    
    # 테스트용 shared store
    shared = get_default_shared_store()
    
    # 간단한 플로우로 테스트
    print("간단한 플로우로 테스트 실행...")
    try:
        simple_flow.run(shared)
        print(f"✅ 테스트 완료")
        print(f"📊 최종 상태: {shared['status']}")
        print(f"📝 요약 결과: {shared['menu_data']['summary'][:100]}...")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        
    print("\n" + "="*50)
    print("실제 워크플로우를 실행하려면 main.py를 사용하세요.")