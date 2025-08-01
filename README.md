# 🍽️ 구도 한식뷔페 메뉴 알림 시스템

매일 오전 11시에 인스타그램(@sunaedong_buffet)에서 오늘의 메뉴를 자동으로 가져와서 LLM으로 요약한 후 슬랙으로 전송하는 자동화 시스템입니다.

## ✨ 주요 기능

- 🕐 **자동 스케줄링**: 매일 오전 11시에 자동 실행
- 📱 **인스타그램 크롤링**: Selenium을 이용한 동적 컨텐츠 수집
- 🤖 **AI 메뉴 요약**: OpenAI GPT를 활용한 메뉴 정리 및 카테고리 분류
- 💬 **슬랙 알림**: 요약된 메뉴를 슬랙 채널로 자동 전송
- 🔍 **디버그 시스템**: 각 단계별 상태 확인 및 재시도 메커니즘
- ⚡ **즉시 실행**: 테스트 및 수동 실행 모드 지원

## 🏗️ 시스템 아키텍처

이 프로젝트는 [PocketFlow](https://github.com/The-Pocket/PocketFlow) 프레임워크를 기반으로 구축되었습니다.

```mermaid
flowchart TD
    start[시작: 오전 11시 스케줄] --> fetch[FetchMenuNode<br/>인스타그램 메뉴 수집]
    fetch --> debug1{DebugCheckNode<br/>수집 성공?}
    debug1 -->|성공| summarize[SummarizeMenuNode<br/>LLM 메뉴 요약]
    debug1 -->|실패| retry1[재시도 또는 알림]
    retry1 --> fetch
    
    summarize --> debug2{DebugCheckNode<br/>요약 성공?}
    debug2 -->|성공| send[SendSlackNode<br/>슬랙 메시지 전송]
    debug2 -->|실패| retry2[재시도 또는 알림]
    retry2 --> summarize
    
    send --> debug3{DebugCheckNode<br/>전송 성공?}
    debug3 -->|성공| complete[완료]
    debug3 -->|실패| retry3[재시도 또는 에러 알림]
    retry3 --> send
```

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 환경변수를 설정하세요:

```bash
# OpenAI API 키 (LLM 메뉴 요약용)
# https://platform.openai.com/api-keys 에서 발급
OPENAI_API_KEY=sk-your-openai-api-key-here

# 슬랙 봇 토큰 (메시지 전송용)  
# https://api.slack.com/apps 에서 봇 생성 후 발급
# Bot Token Scopes: chat:write, chat:write.public
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
```

### 3. Chrome 드라이버 설정

인스타그램 크롤링을 위해 Chrome과 ChromeDriver가 필요합니다:

- **Chrome 브라우저** 설치
- **ChromeDriver** 자동 설치 (첫 실행 시 자동으로 설치됩니다)

### 4. 슬랙 봇 설정

1. [Slack API 웹사이트](https://api.slack.com/apps)에서 새 앱 생성
2. **Bot Token Scopes**에 다음 권한 추가:
   - `chat:write` (메시지 전송)
   - `chat:write.public` (공개 채널 전송)
3. 봇을 원하는 채널에 초대: `/invite @your-bot-name`

## 💻 사용 방법

### 환경변수 확인
```bash
python main.py --check
```

### 테스트 모드 (더미 데이터)
```bash
python main.py --test
```

### 즉시 실행 (지금 당장 메뉴 가져오기)
```bash
python main.py --now
```

### 스케줄러 모드 (매일 11시 자동 실행)
```bash
python main.py
```

## 📁 프로젝트 구조

```
├── main.py                 # 메인 애플리케이션
├── flow.py                 # 워크플로우 정의
├── nodes.py                # 각 단계별 노드 구현
├── requirements.txt        # 의존성 패키지
├── docs/
│   └── design.md          # 시스템 설계 문서
└── utils/                 # 유틸리티 함수들
    ├── call_llm.py        # OpenAI API 호출
    ├── instagram_scraper.py # 인스타그램 크롤링
    ├── slack_sender.py    # 슬랙 메시지 전송
    └── scheduler.py       # 스케줄링 관리
```

## 🔧 커스터마이징

### 메뉴 요약 프롬프트 수정
`nodes.py`의 `SummarizeMenuNode` 클래스에서 프롬프트를 수정할 수 있습니다.

### 실행 시간 변경
`main.py`의 `scheduler_mode()` 함수에서 실행 시간을 변경할 수 있습니다:
```python
schedule_daily_menu_job(run_menu_workflow, shared, "09:00")  # 오전 9시로 변경
```

### 슬랙 채널 변경
`flow.py`의 `get_default_shared_store()` 함수에서 채널을 변경할 수 있습니다:
```python
"slack_channel": "#gudo",
```

## 🐛 문제 해결

### Chrome 드라이버 문제
```bash
# Chrome 브라우저 버전 확인
google-chrome --version

# ChromeDriver 수동 설치
# https://chromedriver.chromium.org/downloads
```

### 인스타그램 접근 문제
- Instagram이 구조를 변경할 수 있어 스크래핑이 실패할 수 있습니다
- 이 경우 fallback 메시지가 전송됩니다

### 슬랙 권한 문제
- 봇이 채널에 초대되어 있는지 확인
- 필요한 권한(`chat:write`, `chat:write.public`)이 있는지 확인

## 📝 로그 확인

시스템 실행 로그는 다음 파일들에서 확인할 수 있습니다:
- `menu_notification.log` - 애플리케이션 로그
- `menu_scheduler.log` - 스케줄러 로그

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 라이선스

이 프로젝트는 [PocketFlow](https://github.com/The-Pocket/PocketFlow) 프레임워크를 기반으로 합니다.

## 🙏 감사의 말

- [PocketFlow](https://github.com/The-Pocket/PocketFlow) - 100줄의 미니멀한 LLM 프레임워크
- OpenAI - GPT API 제공
- Slack - 메시지 플랫폼 제공
