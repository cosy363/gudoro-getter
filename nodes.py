from pocketflow import Node
from utils.call_llm import call_llm
from utils.instagram_scraper import scrape_menu_from_instagram
from utils.slack_sender import send_slack_message, send_error_notification, send_debug_info
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

class FetchMenuNode(Node):
    """인스타그램에서 최신 메뉴 포스트를 수집하는 노드"""
    
    def prep(self, shared):
        """Instagram URL을 shared store에서 가져옵니다"""
        instagram_url = shared["config"]["instagram_url"]
        logging.info(f"📱 인스타그램 URL 준비: {instagram_url}")
        return instagram_url
    
    def exec(self, instagram_url):
        """Instagram에서 메뉴 정보를 스크래핑합니다"""
        logging.info("🕷️ 인스타그램 스크래핑 시작...")
        menu_content = scrape_menu_from_instagram(instagram_url)
        
        if not menu_content:
            raise Exception("인스타그램에서 메뉴 정보를 가져올 수 없습니다")
            
        logging.info(f"✅ 메뉴 정보 수집 완료 (길이: {len(menu_content)})")
        return menu_content
    
    def exec_fallback(self, prep_res, exc):
        """스크래핑 실패 시 fallback 메시지 반환"""
        logging.warning(f"⚠️ 인스타그램 스크래핑 실패: {exc}")
        fallback_message = """
오늘의 메뉴 정보를 자동으로 가져올 수 없습니다.
직접 인스타그램(@sunaedong_buffet)을 확인해주세요.

🔗 https://www.instagram.com/sunaedong_buffet/
        """.strip()
        return fallback_message
    
    def post(self, shared, prep_res, exec_res):
        """수집된 메뉴 정보를 shared store에 저장"""
        shared["menu_data"]["raw_content"] = exec_res
        shared["status"]["fetch_success"] = bool(exec_res and len(exec_res) > 20)
        shared["status"]["last_run"] = datetime.now().isoformat()
        
        if not shared["status"]["fetch_success"]:
            shared["status"]["error_log"].append(f"메뉴 수집 실패: 내용이 너무 짧음 ({len(exec_res)} 글자)")
        
        logging.info(f"💾 메뉴 데이터 저장 완료 (성공: {shared['status']['fetch_success']})")
        return "default"

class SummarizeMenuNode(Node):
    """LLM을 사용하여 메뉴 정보를 요약하는 노드"""
    
    def prep(self, shared):
        """수집된 메뉴 정보를 가져옵니다"""
        raw_content = shared["menu_data"]["raw_content"]
        logging.info(f"📝 요약할 메뉴 정보 준비 (길이: {len(raw_content)})")
        return raw_content
    
    def exec(self, raw_content):
        """LLM을 사용하여 메뉴를 요약합니다"""
        if not raw_content:
            raise Exception("요약할 메뉴 내용이 없습니다")
        
        prompt = f"""
다음은 한식뷔페 인스타그램 포스트에서 가져온 메뉴 정보입니다.
이 내용을 읽기 쉽고 구조화된 형태로 요약해주세요.

원본 내용:
{raw_content}

요약 요구사항:
1. 한국어로 작성
2. 메뉴를 카테고리별로 정리 (주요리, 밑반찬, 국물류, 후식 등)
3. 이모지를 적절히 사용하여 보기 좋게 작성
4. 없는 메뉴는 추가하지 마세요
5. 영업시간이나 기타 정보가 있다면 포함

아래 형식으로 작성해주세요:

🍽️ **오늘의 메뉴**

**🥩 주요리**
- 메뉴1
- 메뉴2

**🥬 밑반찬**
- 반찬1
- 반찬2

**🍲 국물류**
- 국물요리1

**🍰 후식**
- 후식류

**ℹ️ 기타정보**
- 영업시간: (있다면)
- 특이사항: (있다면)
"""
        
        logging.info("🤖 LLM 요약 시작...")
        summary = call_llm(prompt)
        
        if not summary:
            raise Exception("LLM 요약 결과가 비어있습니다")
            
        logging.info("✅ 메뉴 요약 완료")
        return summary
    
    def exec_fallback(self, prep_res, exc):
        """요약 실패 시 원본 텍스트를 간단히 정리하여 반환"""
        logging.warning(f"⚠️ LLM 요약 실패: {exc}")
        
        if prep_res:
            fallback_summary = f"""
🍽️ **오늘의 메뉴** (자동 요약 실패)

📝 원본 정보:
{prep_res[:500]}{'...' if len(prep_res) > 500 else ''}

⚠️ 자동 요약에 실패했습니다. 위 원본 정보를 참고해주세요.
            """.strip()
        else:
            fallback_summary = "메뉴 정보를 가져올 수 없습니다. 직접 인스타그램을 확인해주세요."
            
        return fallback_summary
    
    def post(self, shared, prep_res, exec_res):
        """요약된 메뉴를 shared store에 저장"""
        shared["menu_data"]["summary"] = exec_res
        shared["status"]["summarize_success"] = bool(exec_res and "메뉴" in exec_res)
        
        if not shared["status"]["summarize_success"]:
            shared["status"]["error_log"].append("메뉴 요약 실패: 유효하지 않은 요약 결과")
        
        logging.info(f"💾 메뉴 요약 저장 완료 (성공: {shared['status']['summarize_success']})")
        return "default"

class SendSlackNode(Node):
    """요약된 메뉴를 슬랙으로 전송하는 노드"""
    
    def prep(self, shared):
        """전송할 메뉴 요약과 채널 정보를 가져옵니다"""
        summary = shared["menu_data"]["summary"]
        channel = shared["config"]["slack_channel"]
        
        logging.info(f"📤 슬랙 전송 준비: {channel}")
        return summary, channel
    
    def exec(self, inputs):
        """슬랙으로 메뉴 메시지를 전송합니다"""
        summary, channel = inputs
        
        if not summary:
            raise Exception("전송할 메뉴 요약이 없습니다")
        
        logging.info("📨 슬랙 메시지 전송 시작...")
        success = send_slack_message(summary, channel)
        
        if not success:
            raise Exception("슬랙 메시지 전송에 실패했습니다")
            
        logging.info("✅ 슬랙 메시지 전송 완료")
        return success
    
    def exec_fallback(self, prep_res, exc):
        """슬랙 전송 실패 시 에러 알림 전송 시도"""
        logging.warning(f"⚠️ 슬랙 전송 실패: {exc}")
        
        try:
            summary, channel = prep_res
            error_msg = f"메뉴 알림 전송 실패: {str(exc)}"
            send_error_notification(error_msg, channel)
            return False
        except:
            return False
    
    def post(self, shared, prep_res, exec_res):
        """전송 결과를 shared store에 저장"""
        shared["status"]["send_success"] = bool(exec_res)
        
        if not shared["status"]["send_success"]:
            shared["status"]["error_log"].append("슬랙 메시지 전송 실패")
        
        logging.info(f"💾 전송 상태 저장 완료 (성공: {shared['status']['send_success']})")
        return "default"

class DebugCheckNode(Node):
    """각 단계의 실행 상태를 확인하고 디버그 정보를 제공하는 노드"""
    
    def prep(self, shared):
        """현재 실행 상태 정보를 가져옵니다"""
        status = shared["status"]
        debug_mode = shared["config"].get("debug_mode", False)
        
        logging.info(f"🔍 디버그 체크 시작 (디버그 모드: {debug_mode})")
        return status, debug_mode
    
    def exec(self, inputs):
        """현재 상태를 분석하고 다음 액션을 결정합니다"""
        status, debug_mode = inputs
        
        # 실행 상태 체크
        fetch_ok = status.get("fetch_success", False)
        summarize_ok = status.get("summarize_success", False)
        send_ok = status.get("send_success", False)
        
        # 전체 성공 여부
        all_success = fetch_ok and summarize_ok and send_ok
        
        debug_info = {
            "fetch_success": fetch_ok,
            "summarize_success": summarize_ok,
            "send_success": send_ok,
            "all_success": all_success,
            "error_count": len(status.get("error_log", [])),
            "last_run": status.get("last_run"),
            "details": f"수집: {'✅' if fetch_ok else '❌'}, 요약: {'✅' if summarize_ok else '❌'}, 전송: {'✅' if send_ok else '❌'}",
            "error_log": status.get("error_log", [])
        }
        
        # 디버그 모드일 때 슬랙으로 디버그 정보 전송
        if debug_mode:
            try:
                send_debug_info(debug_info, "#lunch-menu-debug")
            except Exception as e:
                logging.warning(f"디버그 정보 전송 실패: {e}")
        
        # 다음 액션 결정
        if all_success:
            action = "success"
        elif status.get("error_log") and len(status["error_log"]) >= 3:
            action = "fail"  # 너무 많은 에러 발생시 포기
        else:
            action = "retry"  # 재시도 가능
            
        logging.info(f"🎯 디버그 결과: {action} (성공률: {sum([fetch_ok, summarize_ok, send_ok])}/3)")
        
        return {
            "action": action,
            "debug_info": debug_info
        }
    
    def post(self, shared, prep_res, exec_res):
        """디버그 결과에 따라 다음 액션을 반환"""
        action = exec_res["action"]
        debug_info = exec_res["debug_info"]
        
        # 최종 상태 업데이트
        shared["status"]["debug_info"] = debug_info
        shared["status"]["final_success"] = debug_info["all_success"]
        
        logging.info(f"🏁 최종 결과: {action}")
        
        return action