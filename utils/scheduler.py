import schedule
import time
import threading
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('menu_scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_daily_menu_workflow(workflow_function, shared_store):
    """
    매일 메뉴 워크플로우를 실행하는 함수
    
    Args:
        workflow_function: 실행할 워크플로우 함수
        shared_store: 공유 저장소
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"🚀 메뉴 워크플로우 시작: {current_time}")
        
        # 워크플로우 실행
        workflow_function(shared_store)
        
        logging.info("✅ 메뉴 워크플로우 완료")
        
    except Exception as e:
        logging.error(f"❌ 메뉴 워크플로우 실행 중 오류: {e}")
        
        # 에러 알림 (옵션)
        try:
            from utils.slack_sender import send_error_notification
            send_error_notification(f"스케줄러 오류: {str(e)}")
        except:
            pass  # 슬랙 알림 실패해도 스케줄러는 계속 동작

def schedule_daily_menu_job(workflow_function, shared_store, time_str="11:00"):
    """
    매일 지정된 시간에 메뉴 워크플로우를 스케줄링합니다.
    
    Args:
        workflow_function: 실행할 워크플로우 함수
        shared_store: 공유 저장소
        time_str (str): 실행 시간 (HH:MM 형식, 기본값: "11:00")
    """
    
    # 매일 지정된 시간에 실행
    schedule.every().day.at(time_str).do(
        run_daily_menu_workflow, 
        workflow_function, 
        shared_store
    )
    
    logging.info(f"📅 매일 {time_str}에 메뉴 워크플로우 스케줄링 완료")
    
def run_scheduler():
    """
    스케줄러를 실행합니다. (무한 루프)
    """
    logging.info("⏰ 스케줄러 시작")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
            
        except KeyboardInterrupt:
            logging.info("⏹️ 스케줄러 중지됨 (KeyboardInterrupt)")
            break
        except Exception as e:
            logging.error(f"❌ 스케줄러 오류: {e}")
            time.sleep(60)  # 오류 발생해도 계속 실행

def run_scheduler_in_background():
    """
    스케줄러를 백그라운드 스레드에서 실행합니다.
    """
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("🔄 백그라운드 스케줄러 시작")
    return scheduler_thread

def run_immediately(workflow_function, shared_store):
    """
    테스트용: 워크플로우를 즉시 실행합니다.
    
    Args:
        workflow_function: 실행할 워크플로우 함수
        shared_store: 공유 저장소
    """
    logging.info("⚡ 즉시 실행 모드")
    run_daily_menu_workflow(workflow_function, shared_store)

def get_next_run_time():
    """
    다음 실행 예정 시간을 반환합니다.
    
    Returns:
        str: 다음 실행 시간
    """
    jobs = schedule.get_jobs()
    if jobs:
        next_run = min(job.next_run for job in jobs)
        return next_run.strftime("%Y-%m-%d %H:%M:%S")
    return "스케줄된 작업 없음"

def list_scheduled_jobs():
    """
    현재 스케줄된 작업들을 출력합니다.
    """
    jobs = schedule.get_jobs()
    if not jobs:
        logging.info("📋 스케줄된 작업이 없습니다.")
        return
    
    logging.info("📋 현재 스케줄된 작업들:")
    for i, job in enumerate(jobs, 1):
        logging.info(f"  {i}. {job} (다음 실행: {job.next_run})")

if __name__ == "__main__":
    # 테스트용 더미 워크플로우
    def dummy_workflow(shared):
        print("🧪 테스트 워크플로우 실행")
        print(f"Shared store: {shared}")
        
    # 테스트용 공유 저장소
    test_shared = {
        "config": {
            "instagram_url": "https://www.instagram.com/sunaedong_buffet/",
            "slack_channel": "#gudo",
            "debug_mode": True
        }
    }
    
    # 즉시 실행 테스트
    print("=== 즉시 실행 테스트 ===")
    run_immediately(dummy_workflow, test_shared)
    
    # 스케줄링 테스트 (실제로는 매일 11시, 테스트에서는 1분 후)
    print("\n=== 스케줄링 테스트 ===")
    from datetime import datetime, timedelta
    test_time = (datetime.now() + timedelta(minutes=1)).strftime("%H:%M")
    print(f"1분 후({test_time})에 실행되도록 스케줄링...")
    
    schedule_daily_menu_job(dummy_workflow, test_shared, test_time)
    list_scheduled_jobs()
    
    print("스케줄러 시작... (Ctrl+C로 중지)")
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n테스트 완료") 