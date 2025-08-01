from pocketflow import Node
from utils.call_llm import call_llm
from utils.instagram_scraper import scrape_menu_from_instagram
from utils.slack_sender import send_slack_message, send_error_notification, send_debug_info
from datetime import datetime
import logging
import re

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

class SpecialSituationDetectorNode(Node):
    """특수 상황(휴무일, 영업 중단 등)을 감지하는 노드"""
    
    def prep(self, shared):
        """수집된 메뉴 정보를 가져옵니다"""
        raw_content = shared["menu_data"]["raw_content"]
        logging.info(f"🔍 특수 상황 감지 시작 (내용 길이: {len(raw_content)})")
        return raw_content
    
    def exec(self, raw_content):
        """LLM을 사용하여 특수 상황을 감지합니다"""
        if not raw_content:
            raise Exception("분석할 내용이 없습니다")
        
        prompt = f"""
다음은 한식뷔페 인스타그램 포스트에서 가져온 내용입니다.
이 내용을 분석하여 특수 상황(휴무일, 영업 중단, 특별 메뉴 등)이 있는지 판단해주세요.

원본 내용:
{raw_content}

분석 요구사항:
1. 휴무일 관련 키워드: "휴무", "휴점", "쉬는날", "영업안함", "문닫음", "오늘휴무"
2. 영업 중단 관련: "영업중단", "임시휴무", "특별휴무", "정기휴무"
3. 특별 메뉴 관련: "특별메뉴", "이벤트", "한정메뉴", "시즌메뉴"
4. 영업시간 변경: "영업시간변경", "시간조정", "오늘만"

분석 결과를 다음 JSON 형식으로 반환해주세요:
```json
{{
    "situation_type": "normal|holiday|special_menu|business_hours_change|error",
    "confidence": 0.0-1.0,
    "detected_keywords": ["키워드1", "키워드2"],
    "summary": "상황 요약",
    "action_required": "normal|holiday_notice|special_notice|error_notice"
}}
```

situation_type 설명:
- normal: 정상 영업, 일반 메뉴
- holiday: 휴무일 또는 영업 중단
- special_menu: 특별 메뉴 또는 이벤트
- business_hours_change: 영업시간 변경
- error: 분석 불가능한 상황

action_required 설명:
- normal: 일반 메뉴 요약 진행
- holiday_notice: 휴무일 알림 전송
- special_notice: 특별 메뉴 알림 전송
- error_notice: 오류 상황 알림 전송
"""
        
        logging.info("🤖 특수 상황 분석 시작...")
        analysis_result = call_llm(prompt)
        
        # JSON 파싱 시도
        try:
            import json
            # JSON 부분만 추출
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', analysis_result, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # JSON 블록이 없으면 전체를 파싱 시도
                result = json.loads(analysis_result)
        except:
            # 파싱 실패 시 기본값
            result = {
                "situation_type": "normal",
                "confidence": 0.5,
                "detected_keywords": [],
                "summary": "분석 실패로 인해 정상 영업으로 간주",
                "action_required": "normal"
            }
        
        logging.info(f"✅ 특수 상황 분석 완료: {result['situation_type']} (신뢰도: {result['confidence']})")
        return result
    
    def exec_fallback(self, prep_res, exc):
        """분석 실패 시 기본값 반환"""
        logging.warning(f"⚠️ 특수 상황 분석 실패: {exc}")
        
        fallback_result = {
            "situation_type": "normal",
            "confidence": 0.3,
            "detected_keywords": [],
            "summary": "분석 실패로 인해 정상 영업으로 간주",
            "action_required": "normal"
        }
        
        return fallback_result
    
    def post(self, shared, prep_res, exec_res):
        """분석 결과를 shared store에 저장"""
        shared["menu_data"]["situation_analysis"] = exec_res
        shared["status"]["situation_detected"] = exec_res["situation_type"] != "normal"
        
        logging.info(f"💾 특수 상황 분석 저장: {exec_res['situation_type']} -> {exec_res['action_required']}")
        return exec_res["action_required"]

class HolidayNoticeNode(Node):
    """휴무일 알림을 전송하는 노드"""
    
    def prep(self, shared):
        """휴무일 정보와 채널 정보를 가져옵니다"""
        analysis = shared["menu_data"]["situation_analysis"]
        channel = shared["config"]["slack_channel"]
        
        logging.info(f"🏖️ 휴무일 알림 준비: {analysis['situation_type']}")
        return analysis, channel
    
    def exec(self, inputs):
        """휴무일 알림 메시지를 생성합니다"""
        analysis, channel = inputs
        
        # LLM을 사용하여 휴무일 알림 메시지 생성
        prompt = f"""
다음은 한식뷔페의 휴무일 관련 정보입니다:

상황 분석: {analysis['summary']}
감지된 키워드: {', '.join(analysis['detected_keywords'])}

이 정보를 바탕으로 팀원들에게 전달할 휴무일 알림 메시지를 작성해주세요.

요구사항:
1. 친근하고 명확한 톤으로 작성
2. 휴무일 정보를 명확히 전달
3. 다음 영업일 정보가 있다면 포함
4. 이모지를 적절히 사용
5. 200자 이내로 작성

형식:
🏖️ **오늘은 휴무일입니다**

📅 휴무 정보: [상세 내용]
📅 다음 영업일: [정보가 있다면]
ℹ️ 참고사항: [기타 정보]

감사합니다! 🍽️
"""
        
        logging.info("📝 휴무일 알림 메시지 생성...")
        holiday_message = call_llm(prompt)
        
        if not holiday_message:
            # LLM 실패 시 기본 메시지
            holiday_message = f"""
🏖️ **오늘은 휴무일입니다**

📅 휴무 정보: {analysis['summary']}
ℹ️ 자세한 내용은 인스타그램을 확인해주세요.

감사합니다! 🍽️
            """.strip()
        
        # 슬랙으로 전송
        success = send_slack_message(holiday_message, channel)
        
        if not success:
            raise Exception("휴무일 알림 전송에 실패했습니다")
        
        logging.info("✅ 휴무일 알림 전송 완료")
        return holiday_message
    
    def exec_fallback(self, prep_res, exc):
        """휴무일 알림 실패 시 기본 메시지 전송"""
        logging.warning(f"⚠️ 휴무일 알림 실패: {exc}")
        
        try:
            analysis, channel = prep_res
            fallback_message = f"""
🏖️ **오늘은 휴무일입니다**

📅 휴무 정보: {analysis['summary']}
ℹ️ 자세한 내용은 인스타그램을 확인해주세요.

감사합니다! 🍽️
            """.strip()
            
            send_slack_message(fallback_message, channel)
            return fallback_message
        except:
            return "휴무일 알림 전송에 실패했습니다."
    
    def post(self, shared, prep_res, exec_res):
        """휴무일 알림 결과를 저장"""
        shared["status"]["holiday_notice_sent"] = True
        shared["status"]["final_success"] = True
        
        logging.info("💾 휴무일 알림 완료")
        return "success"

class SpecialMenuNode(Node):
    """특별 메뉴 알림을 전송하는 노드"""
    
    def prep(self, shared):
        """특별 메뉴 정보와 채널 정보를 가져옵니다"""
        analysis = shared["menu_data"]["situation_analysis"]
        raw_content = shared["menu_data"]["raw_content"]
        channel = shared["config"]["slack_channel"]
        
        logging.info(f"🎉 특별 메뉴 알림 준비: {analysis['situation_type']}")
        return analysis, raw_content, channel
    
    def exec(self, inputs):
        """특별 메뉴 알림 메시지를 생성합니다"""
        analysis, raw_content, channel = inputs
        
        # LLM을 사용하여 특별 메뉴 요약
        prompt = f"""
다음은 한식뷔페의 특별 메뉴 정보입니다:

상황 분석: {analysis['summary']}
원본 내용: {raw_content}

이 정보를 바탕으로 특별 메뉴 알림을 작성해주세요.

요구사항:
1. 특별 메뉴의 특징을 강조
2. 메뉴 내용을 구조화하여 정리
3. 이모지를 적절히 사용
4. 특별한 이유나 이벤트 정보가 있다면 포함
5. 300자 이내로 작성

형식:
🎉 **오늘의 특별 메뉴** 🎉

📋 특별 메뉴 정보: [상세 내용]
🍽️ 메뉴 구성: [구조화된 메뉴]
🎊 특별 이벤트: [있다면]
ℹ️ 참고사항: [기타 정보]

맛있게 드세요! 😋
"""
        
        logging.info("📝 특별 메뉴 알림 메시지 생성...")
        special_message = call_llm(prompt)
        
        if not special_message:
            # LLM 실패 시 기본 메시지
            special_message = f"""
🎉 **오늘의 특별 메뉴** 🎉

📋 특별 메뉴 정보: {analysis['summary']}
🍽️ 메뉴 구성: {raw_content[:200]}{'...' if len(raw_content) > 200 else ''}

맛있게 드세요! 😋
            """.strip()
        
        # 슬랙으로 전송
        success = send_slack_message(special_message, channel)
        
        if not success:
            raise Exception("특별 메뉴 알림 전송에 실패했습니다")
        
        logging.info("✅ 특별 메뉴 알림 전송 완료")
        return special_message
    
    def exec_fallback(self, prep_res, exc):
        """특별 메뉴 알림 실패 시 기본 메시지 전송"""
        logging.warning(f"⚠️ 특별 메뉴 알림 실패: {exc}")
        
        try:
            analysis, raw_content, channel = prep_res
            fallback_message = f"""
🎉 **오늘의 특별 메뉴** 🎉

📋 특별 메뉴 정보: {analysis['summary']}
🍽️ 메뉴 구성: {raw_content[:200]}{'...' if len(raw_content) > 200 else ''}

맛있게 드세요! 😋
            """.strip()
            
            send_slack_message(fallback_message, channel)
            return fallback_message
        except:
            return "특별 메뉴 알림 전송에 실패했습니다."
    
    def post(self, shared, prep_res, exec_res):
        """특별 메뉴 알림 결과를 저장"""
        shared["status"]["special_menu_sent"] = True
        shared["status"]["final_success"] = True
        
        logging.info("💾 특별 메뉴 알림 완료")
        return "success"

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