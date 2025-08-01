#!/usr/bin/env python3
"""
구도 한식뷔페 메뉴 알림 시스템

매일 오전 11시에 인스타그램에서 메뉴를 가져와서 슬랙으로 전송하는 자동화 시스템입니다.

사용법:
    python main.py                    # 스케줄러 모드 (매일 11시 실행)
    python main.py --now              # 즉시 실행 모드  
    python main.py --test             # 테스트 모드 (더미 데이터)
    python main.py --check            # 환경변수 체크
    python main.py --holiday-test     # 휴무일 상황 테스트
    python main.py --special-test     # 특별 메뉴 상황 테스트
"""

import argparse
import os
import sys
from datetime import datetime
import logging

# dotenv가 있으면 로드 (선택사항)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flow import (
    create_menu_notification_flow, 
    create_simple_menu_flow, 
    create_holiday_test_flow,
    create_special_menu_test_flow,
    get_default_shared_store
)
from utils.scheduler import schedule_daily_menu_job, run_scheduler, run_immediately, get_next_run_time
from utils.slack_sender import send_slack_message

# 로깅 설정
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('menu_notification.log'),
            logging.StreamHandler()
        ]
    )

def check_environment():
    """
    필요한 환경변수들이 설정되어 있는지 확인합니다.
    """
    print("🔍 환경변수 체크 중...")
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API 키 (LLM 요약용)',
        'SLACK_BOT_TOKEN': '슬랙 봇 토큰 (메시지 전송용)'
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * 20}...{value[-4:] if len(value) > 4 else '****'}")
        else:
            print(f"❌ {var}: 설정되지 않음 - {description}")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️ 누락된 환경변수: {', '.join(missing_vars)}")
        print("\n설정 방법:")
        print("1. .env 파일 생성:")
        for var in missing_vars:
            print(f"   {var}=your_api_key_here")
        print("\n2. 또는 환경변수로 직접 설정:")
        for var in missing_vars:
            print(f"   export {var}=your_api_key_here")
        return False
    
    print("\n✅ 모든 환경변수가 올바르게 설정되었습니다!")
    return True

def run_menu_workflow(shared_store):
    """
    메뉴 워크플로우를 실행하는 함수
    """
    try:
        flow = create_menu_notification_flow()
        flow.run(shared_store)
        
        # 결과 로깅
        status = shared_store.get("status", {})
        if status.get("final_success"):
            logging.info("🎉 메뉴 알림 워크플로우 성공적으로 완료!")
        else:
            logging.warning("⚠️ 메뉴 알림 워크플로우 완료되었지만 일부 단계에서 문제가 발생했습니다.")
            
    except Exception as e:
        logging.error(f"❌ 메뉴 워크플로우 실행 중 오류: {e}")
        
        # 에러 발생시 슬랙으로 알림
        try:
            error_message = f"메뉴 알림 시스템 오류: {str(e)}"
            send_slack_message(error_message, shared_store["config"]["slack_channel"])
        except:
            pass  # 슬랙 알림도 실패하면 로그만 남김

def test_mode():
    """
    테스트 모드: 더미 데이터로 플로우 테스트
    """
    print("🧪 테스트 모드 실행 중...")
    
    # 더미 shared store
    shared = get_default_shared_store()
    shared["config"]["debug_mode"] = True
    shared["config"]["slack_channel"] = "#gudo"  # gudo 채널 사용
    
    # 더미 메뉴 데이터 주입
    shared["menu_data"]["raw_content"] = """
🍽️ 구도 한식뷔페 오늘의 메뉴

🥩 주요리
- 갈비찜
- 불고기
- 생선구이

🥬 밑반찬
- 김치
- 콩나물무침
- 시금치나물

🍲 국물류  
- 된장찌개
- 김치찌개

🍰 후식
- 과일
- 식혜
    """.strip()
    
    try:
        # 간단한 플로우로 테스트 (스크래핑 건너뛰고 요약부터)
        flow = create_simple_menu_flow()
        
        # FetchMenuNode 건너뛰기 위해 상태 미리 설정
        shared["status"]["fetch_success"] = True
        
        flow.run(shared)
        
        print("✅ 테스트 완료!")
        print(f"📊 최종 상태: {shared['status']}")
        print(f"📝 요약 결과:")
        print(shared['menu_data']['summary'])
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

def holiday_test_mode():
    """
    휴무일 상황 테스트 모드
    """
    print("🏖️ 휴무일 상황 테스트 모드 실행 중...")
    
    # 더미 shared store
    shared = get_default_shared_store()
    shared["config"]["debug_mode"] = True
    shared["config"]["slack_channel"] = "#gudo"
    
    # 휴무일 상황을 시뮬레이션하는 더미 데이터
    shared["menu_data"]["raw_content"] = """
오늘은 정기 휴무일입니다.
매주 월요일은 휴무입니다.

다음 영업일은 화요일입니다.
맛있는 한식으로 다시 찾아뵙겠습니다.

감사합니다! 🍽️
    """.strip()
    
    try:
        # 휴무일 테스트 플로우 실행
        flow = create_holiday_test_flow()
        
        # FetchMenuNode 건너뛰기 위해 상태 미리 설정
        shared["status"]["fetch_success"] = True
        
        flow.run(shared)
        
        print("✅ 휴무일 테스트 완료!")
        print(f"📊 최종 상태: {shared['status']}")
        
        # 상황 분석 결과 출력
        if shared['menu_data'].get('situation_analysis'):
            analysis = shared['menu_data']['situation_analysis']
            print(f"🔍 감지된 상황: {analysis.get('situation_type', 'unknown')}")
            print(f"📝 상황 요약: {analysis.get('summary', 'N/A')}")
            print(f"🎯 요구된 액션: {analysis.get('action_required', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 휴무일 테스트 실패: {e}")

def special_menu_test_mode():
    """
    특별 메뉴 상황 테스트 모드
    """
    print("🎉 특별 메뉴 상황 테스트 모드 실행 중...")
    
    # 더미 shared store
    shared = get_default_shared_store()
    shared["config"]["debug_mode"] = True
    shared["config"]["slack_channel"] = "#gudo"
    
    # 특별 메뉴 상황을 시뮬레이션하는 더미 데이터
    shared["menu_data"]["raw_content"] = """
🎊 오늘의 특별 이벤트 메뉴 🎊

한정 특별 메뉴: 갈비찜 + 불고기 콤보
이벤트 기간: 오늘 하루만
특별 가격: 15,000원 (기존 18,000원)

🥩 특별 메뉴 구성:
- 프리미엄 갈비찜
- 불고기
- 각종 밑반찬
- 된장찌개
- 후식 (과일 + 식혜)

🎁 추가 혜택:
- 음료 무료 제공
- 디저트 추가 서비스

많이 찾아주세요! 😋
    """.strip()
    
    try:
        # 특별 메뉴 테스트 플로우 실행
        flow = create_special_menu_test_flow()
        
        # FetchMenuNode 건너뛰기 위해 상태 미리 설정
        shared["status"]["fetch_success"] = True
        
        flow.run(shared)
        
        print("✅ 특별 메뉴 테스트 완료!")
        print(f"📊 최종 상태: {shared['status']}")
        
        # 상황 분석 결과 출력
        if shared['menu_data'].get('situation_analysis'):
            analysis = shared['menu_data']['situation_analysis']
            print(f"🔍 감지된 상황: {analysis.get('situation_type', 'unknown')}")
            print(f"📝 상황 요약: {analysis.get('summary', 'N/A')}")
            print(f"🎯 요구된 액션: {analysis.get('action_required', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 특별 메뉴 테스트 실패: {e}")

def immediate_mode():
    """
    즉시 실행 모드: 지금 당장 메뉴 워크플로우 실행
    """
    print("⚡ 즉시 실행 모드")
    
    # 환경변수 체크
    if not check_environment():
        return
    
    # shared store 준비
    shared = get_default_shared_store()
    
    print("🚀 메뉴 워크플로우 시작...")
    run_menu_workflow(shared)
    
    print("📊 실행 결과:")
    print(f"- 수집 성공: {shared['status'].get('fetch_success', False)}")
    print(f"- 상황 감지: {shared['status'].get('situation_detected', False)}")
    print(f"- 요약 성공: {shared['status'].get('summarize_success', False)}")
    print(f"- 전송 성공: {shared['status'].get('send_success', False)}")
    print(f"- 휴무일 알림: {shared['status'].get('holiday_notice_sent', False)}")
    print(f"- 특별 메뉴 알림: {shared['status'].get('special_menu_sent', False)}")
    print(f"- 전체 성공: {shared['status'].get('final_success', False)}")
    
    # 상황 분석 결과 출력
    if shared['menu_data'].get('situation_analysis'):
        analysis = shared['menu_data']['situation_analysis']
        print(f"\n🔍 상황 분석 결과:")
        print(f"  - 상황 타입: {analysis.get('situation_type', 'unknown')}")
        print(f"  - 신뢰도: {analysis.get('confidence', 0.0)}")
        print(f"  - 감지된 키워드: {', '.join(analysis.get('detected_keywords', []))}")
        print(f"  - 상황 요약: {analysis.get('summary', 'N/A')}")

def scheduler_mode():
    """
    스케줄러 모드: 매일 11시에 자동 실행
    """
    print("⏰ 스케줄러 모드")
    
    # 환경변수 체크
    if not check_environment():
        return
    
    # shared store 준비
    shared = get_default_shared_store()
    
    # 스케줄링 설정
    schedule_daily_menu_job(run_menu_workflow, shared, "11:00")
    
    print(f"📅 매일 오전 11시에 메뉴 알림 실행하도록 설정했습니다.")
    print(f"⏳ 다음 실행 예정: {get_next_run_time()}")
    print("💡 Ctrl+C로 중지할 수 있습니다.")
    
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n⏹️ 스케줄러가 중지되었습니다.")

def main():
    """메인 함수"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="구도 한식뷔페 메뉴 알림 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python main.py                    # 스케줄러 모드 (매일 11시 실행)
  python main.py --now              # 즉시 실행 모드  
  python main.py --test             # 테스트 모드 (더미 데이터)
  python main.py --check            # 환경변수 체크
  python main.py --holiday-test     # 휴무일 상황 테스트
  python main.py --special-test     # 특별 메뉴 상황 테스트
        """
    )
    
    parser.add_argument(
        '--now', 
        action='store_true', 
        help='즉시 실행 모드 (지금 당장 메뉴 가져오기)'
    )
    
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='테스트 모드 (더미 데이터로 플로우 테스트)'
    )
    
    parser.add_argument(
        '--check', 
        action='store_true', 
        help='환경변수 설정 확인'
    )
    
    parser.add_argument(
        '--holiday-test', 
        action='store_true', 
        help='휴무일 상황 테스트 모드'
    )
    
    parser.add_argument(
        '--special-test', 
        action='store_true', 
        help='특별 메뉴 상황 테스트 모드'
    )
    
    args = parser.parse_args()
    
    print("🍽️ 구도 한식뷔페 메뉴 알림 시스템")
    print("=" * 50)
    
    if args.check:
        check_environment()
    elif args.test:
        test_mode()
    elif args.holiday_test:
        holiday_test_mode()
    elif args.special_test:
        special_menu_test_mode()
    elif args.now:
        immediate_mode()
    else:
        scheduler_mode()

if __name__ == "__main__":
    main()
