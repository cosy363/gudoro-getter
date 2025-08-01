from pocketflow import Flow
from nodes import (
    FetchMenuNode, 
    SpecialSituationDetectorNode,
    HolidayNoticeNode,
    SpecialMenuNode,
    SummarizeMenuNode, 
    SendSlackNode, 
    DebugCheckNode
)
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

def create_menu_notification_flow():
    """
    구도 한식뷔페 메뉴 알림 워크플로우를 생성합니다.
    
    향상된 플로우 구조:
    1. FetchMenuNode: 인스타그램에서 메뉴 수집
    2. SpecialSituationDetectorNode: 특수 상황 감지 (휴무일, 특별 메뉴 등)
    3. 상황별 분기:
       - normal: 일반 메뉴 요약 및 전송
       - holiday: 휴무일 알림 전송
       - special_menu: 특별 메뉴 알림 전송
    4. DebugCheckNode: 각 단계별 상태 확인
    """
    
    # 1. 노드 생성 (재시도 옵션 포함)
    fetch_node = FetchMenuNode(max_retries=3, wait=5)
    situation_detector = SpecialSituationDetectorNode(max_retries=2, wait=3)
    
    # 특수 상황 처리 노드들
    holiday_notice = HolidayNoticeNode(max_retries=2, wait=2)
    special_menu = SpecialMenuNode(max_retries=2, wait=2)
    
    # 일반 메뉴 처리 노드들
    summarize_node = SummarizeMenuNode(max_retries=2, wait=3)
    send_node = SendSlackNode(max_retries=2, wait=2)
    
    # 디버그 체크 노드들
    debug_fetch = DebugCheckNode()
    debug_situation = DebugCheckNode()
    debug_summarize = DebugCheckNode()
    debug_send = DebugCheckNode()
    
    # 2. 플로우 연결
    # 메뉴 수집 -> 디버그 체크
    fetch_node >> debug_fetch
    
    # 수집 디버그 결과에 따른 분기
    debug_fetch - "success" >> situation_detector  # 성공시 상황 감지
    debug_fetch - "retry" >> fetch_node            # 재시도시 다시 수집
    debug_fetch - "fail" >> send_node              # 실패시 에러 메시지 전송
    
    # 상황 감지 -> 디버그 체크
    situation_detector >> debug_situation
    
    # 상황 감지 결과에 따른 분기
    debug_situation - "normal" >> summarize_node     # 일반 메뉴: 요약 진행
    debug_situation - "holiday_notice" >> holiday_notice  # 휴무일: 휴무일 알림
    debug_situation - "special_notice" >> special_menu    # 특별 메뉴: 특별 메뉴 알림
    debug_situation - "error_notice" >> send_node         # 오류: 에러 메시지 전송
    debug_situation - "retry" >> situation_detector       # 재시도
    debug_situation - "fail" >> send_node                 # 실패: 에러 메시지 전송
    
    # 휴무일 알림 -> 완료
    holiday_notice >> None
    
    # 특별 메뉴 알림 -> 완료
    special_menu >> None
    
    # 일반 메뉴: 요약 -> 디버그 체크
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
    debug_send - "fail" >> None     # 실패시 종료
    
    # 3. 플로우 생성 (fetch_node부터 시작)
    flow = Flow(start=fetch_node)
    
    logging.info("📋 향상된 메뉴 알림 워크플로우 생성 완료")
    logging.info("🔗 플로우 구조: fetch -> situation_detector -> [holiday/special/normal] -> send")
    
    return flow

def create_simple_menu_flow():
    """
    디버그 없는 간단한 메뉴 워크플로우 (테스트용)
    """
    fetch_node = FetchMenuNode(max_retries=2)
    situation_detector = SpecialSituationDetectorNode(max_retries=2)
    holiday_notice = HolidayNoticeNode(max_retries=2)
    special_menu = SpecialMenuNode(max_retries=2)
    summarize_node = SummarizeMenuNode(max_retries=2)
    send_node = SendSlackNode(max_retries=2)
    
    # 상황 감지 결과에 따른 분기
    fetch_node >> situation_detector
    
    # 상황별 분기
    situation_detector - "normal" >> summarize_node >> send_node
    situation_detector - "holiday_notice" >> holiday_notice
    situation_detector - "special_notice" >> special_menu
    situation_detector - "error_notice" >> send_node
    
    return Flow(start=fetch_node)

def create_holiday_test_flow():
    """
    휴무일 상황 테스트용 플로우
    """
    fetch_node = FetchMenuNode(max_retries=1)
    situation_detector = SpecialSituationDetectorNode(max_retries=1)
    holiday_notice = HolidayNoticeNode(max_retries=1)
    
    fetch_node >> situation_detector
    situation_detector - "holiday_notice" >> holiday_notice
    situation_detector - "normal" >> holiday_notice  # 테스트용으로 모두 휴무일로 처리
    
    return Flow(start=fetch_node)

def create_special_menu_test_flow():
    """
    특별 메뉴 상황 테스트용 플로우
    """
    fetch_node = FetchMenuNode(max_retries=1)
    situation_detector = SpecialSituationDetectorNode(max_retries=1)
    special_menu = SpecialMenuNode(max_retries=1)
    
    fetch_node >> situation_detector
    situation_detector - "special_notice" >> special_menu
    situation_detector - "normal" >> special_menu  # 테스트용으로 모두 특별 메뉴로 처리
    
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
            "summary": "",
            "situation_analysis": {}
        },
        "status": {
            "fetch_success": False,
            "summarize_success": False,
            "send_success": False,
            "situation_detected": False,
            "holiday_notice_sent": False,
            "special_menu_sent": False,
            "last_run": None,
            "error_log": []
        }
    }

# 기본 워크플로우 생성
menu_flow = create_menu_notification_flow()
simple_flow = create_simple_menu_flow()
holiday_test_flow = create_holiday_test_flow()
special_test_flow = create_special_menu_test_flow()

if __name__ == "__main__":
    # 테스트 실행
    print("=== 향상된 메뉴 알림 워크플로우 테스트 ===")
    
    # 테스트용 shared store
    shared = get_default_shared_store()
    
    # 간단한 플로우로 테스트
    print("간단한 플로우로 테스트 실행...")
    try:
        simple_flow.run(shared)
        print(f"✅ 테스트 완료")
        print(f"📊 최종 상태: {shared['status']}")
        
        # 상황 분석 결과 출력
        if shared['menu_data'].get('situation_analysis'):
            analysis = shared['menu_data']['situation_analysis']
            print(f"🔍 상황 분석: {analysis.get('situation_type', 'unknown')}")
            print(f"📝 상황 요약: {analysis.get('summary', 'N/A')}")
        
        if shared['menu_data'].get('summary'):
            print(f"📝 요약 결과: {shared['menu_data']['summary'][:100]}...")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        
    print("\n" + "="*50)
    print("실제 워크플로우를 실행하려면 main.py를 사용하세요.")
    print("특수 상황 테스트:")
    print("  - 휴무일 테스트: python main.py --holiday-test")
    print("  - 특별 메뉴 테스트: python main.py --special-test")