# Agent Console

**AI 에이전트의 작업을 시작하고, 진행 과정과 결과를 터미널에서 확인하는 프로그램입니다.**

개발 작업을 맡겼을 때 “아직 준비 중인지, 파일을 만드는 중인지, 어디서 실패했는지” 알기 어려울 수 있습니다.
Agent Console은 공개된 실행 기록을 시간순으로 정리하고 작업별 상태와 종료 결과를 보여줍니다.

처음 접한다면 [프로젝트 소개 · 설치와 사용 안내 (HTML)](docs/getting-started.html)를 보세요.
다운로드한 저장소에서 이 파일을 브라우저로 열면 됩니다. GitHub에서는 HTML 소스가 표시되며,
별도 웹사이트로 배포된 문서는 아닙니다. 실제 에이전트 없이 샘플부터 실행할 수 있습니다.

## 두 프로젝트의 역할

| 프로젝트 | 하는 일 | 포함 범위 |
| --- | --- | --- |
| **AI Agent Platform (`ai-agent`)** | 실제 작업을 수행하는 별도 실행 엔진 | Main의 작업 분배, Developer, Browser, Desktop, Training |
| **Agent Console (`agent-console`, 이 저장소)** | 실행 엔진에 요청을 전달하고 공개 진행 기록을 표시 | 실행 환경 등록, 폴더 검사, 작업 시작, Timeline, 상태·결과 표시 |

두 프로젝트는 **별도 저장소**입니다. Agent Console은 ai-agent 내부 모듈을 가져오거나 모델을 직접 호출하지 않습니다.
현재 Launcher에서 시작할 수 있는 작업은 **로컬 Developer / Codex**입니다. Browser·Desktop·Training 상태를
표시할 수 있다는 사실이 이 작업들을 Launcher에서 시작할 수 있다는 뜻은 아닙니다.

```text
사용자: 작업할 프로젝트 폴더와 요청 입력 → 실행 승인
    ↓
Agent Console: 별도 ai-agent 실행
    ↓
AI Agent Platform: Main이 Developer로 작업 분배
    ↓
Developer → Codex → 선택한 프로젝트의 파일 작업
    ↓
ai-agent가 공개 진행 이벤트를 출력
    ↓
Agent Console: 진행 단계 · 오류 · 종료 결과 확인
```

Main은 흐름을 관리하는 Python 규칙 기반 구성요소입니다. Developer는 Codex를 사용하는 AI 개발 기능이고,
Browser는 Playwright 웹 자동화, Desktop은 Windows UI Automation, Training은 학습 파이프라인입니다.
모든 구성요소가 각각 독립적인 언어 모델을 호출하는 것은 아닙니다.

## 무엇을 할 수 있나요?

- **샘플 재생:** 저장된 공개 이벤트 파일로 화면을 익힙니다 (`replay`).
- **실시간 관찰:** 외부 프로그램의 공개 이벤트를 받습니다 (`run --`).
- **작업 시작:** Runtime Profile에 실행 환경을 등록하고 Launcher에서 폴더 검사와 작업을 시작합니다 (`profile`, `launch`).
- **진행과 결과 확인:** Timeline, 여섯 Agent 상태, System 상태, 실행 결과와 수치 요약을 봅니다.
- **문제 구분:** 작업 실패·취소·종료 이벤트 누락·프로세스 실패를 구분합니다.

예를 들어 문서 하나를 만드는 작업은 **폴더 선택 → Check Workspace → 요청 입력 → Allow execution 선택 →
Start Run 확인 → 진행 확인 → 결과와 실제 파일 확인** 순서입니다. Check 성공은 실행 승인이 아닙니다.
실제 파일 변경과 도구 실행의 최종 권한 판단은 ai-agent가 담당합니다.

## 현재 구현과 검증 상태

패키지 버전은 **0.2.0**입니다. UI/UX polish 작업은 현재 범위에서 마무리했으며,
2026-10-09 사용자 피드백으로 기본 기능의 실제 사용 동작을 확인했습니다.
전문적인 디자인 검증이나 모든 환경의 안정성을 보증하지는 않습니다.
후속 변경은 [CHANGELOG의 0.2.1 Unreleased](CHANGELOG.md)에 기록하며 공식 릴리스는 별도입니다.

**Verified**는 아래 명시한 시나리오만 검증했다는 뜻입니다. **Partially Verified**는 구현됐으나 검증 범위가 제한적입니다.

### Agent Console

| 항목 | 상태 | 확인 범위 |
| --- | --- | --- |
| JSONL Replay / Live Subprocess Monitoring | Verified | synthetic 파일·stdin·실제 child pipe 테스트, 사용자 live 연동 |
| Timeline / Component Status / Run Summary | Verified | 순서·중복·다중 run·실패 처리, headless 및 viewport 테스트 |
| Runtime Profile / Workspace Check / Run Launcher | Verified | 합성 테스트와 사용자 실제 폴더 검사·실행 승인·복귀 |
| 실제 Developer Launcher E2E | Verified | 단일 문서 생성과 종료·파일 확인; 아래 검증 기록 참고 |
| UI/UX polish | Implemented / Partially Verified | 개선 구현·합성 화면 검사·사용자 기본 동작 확인; 전문 디자인 평가는 미실시 |
| Filter / Search / Run History | Planned | 미구현 |
| Web UI / Database / Remote Monitoring / 다른 Task Launcher | Not Supported | 현재 제공하지 않음 |

### 별도 AI Agent Platform

아래는 별도 ai-agent README 및 기존 검증 기록을 읽어 정리한 상태입니다. 이번 점검에서 플랫폼을 수정하거나
실제 개발·브라우저·Desktop·GPU 작업을 다시 실행하지 않았습니다.

| 항목 | 상태 | 검증 범위와 제한 |
| --- | --- | --- |
| Main Orchestrator | Implemented / Partially Verified | 규칙 기반 작업 분배; 검증된 흐름에 한정 |
| Developer Agent | Verified | 제한된 개발·파일 생성 E2E |
| Browser Agent | Partially Verified | 관리된 localhost의 HTTP·렌더링·클릭·cleanup |
| Desktop Agent | Partially Verified | 새 빈 Notepad 하나의 제한된 동작 |
| Training Agent | Partially Verified | 작은 LoRA smoke, checkpoint 저장·resume·reload; 특화 모델 성능 검증 아님 |
| External Workspace / JSONL Event Stream | Verified | 외부 폴더 검사·schema v1 출력·외부 README 한 개 생성 |
| 실제 외부 Developer E2E | Verified | 플랫폼의 외부 README 생성 기록과 Console의 문서 생성 검증 |

Console의 검증 근거: [직접 Monitor Live E2E](docs/live-ai-agent-smoke.md),
[Launcher Live E2E](docs/v0.2-launcher-smoke.md).
사용자 캡처의 README 생성도 단일 파일 시나리오입니다. 임의 웹앱 생성이나 모든 workflow를 검증한 사례로 확대하지 않습니다.

## 설치

Python 3.11 이상이 필요합니다. 이번 검증 환경은 Python 3.13.15 / Textual 8.2.8입니다.
저장소 root에서 실행합니다. Windows PowerShell에서는 activate 없이 실행할 수 있습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\agent-console.exe --help
```

macOS / Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/agent-console --help
```

일반 사용자 설치에는 `pip install .`로 개발 의존성을 생략할 수 있습니다.

## 사용하기

Launcher의 기본 사용 순서는 다음과 같습니다. 실제 등록 명령은
[Runtime Profile 등록 안내](docs/run-launcher.md#1-설치와-runtime-profile-등록)를 참고하세요.

1. 로컬 Runtime Profile을 등록합니다.
2. `agent-console launch --profile <name>`을 실행합니다.
3. 작업할 Workspace의 절대 경로를 입력합니다.
4. **Check Workspace** 결과를 확인하고 Launcher로 돌아옵니다.
5. Prompt를 입력합니다.
6. 파일 쓰기·도구 실행이 필요하면 **Allow execution**을 직접 ON으로 바꿉니다.
7. **Start Run**을 누릅니다.
8. 확인 창에서 설정을 검토하고 **Start**를 누릅니다.
9. 기존 Monitor에서 진행과 종료 결과를 관찰합니다.
10. 완료 후 **Back to Launcher**로 돌아옵니다.

Launcher는 110열 이상이면 높이가 낮아도 Run settings를 2열로 유지한다.
36행 미만에서는 Runtime과 설정을 compact하게 표시하고 일부 도움말은 tooltip으로 제공한다.
compact 입력은 양쪽 경계와 배경색, 설정 행은 구분선으로 식별하며 드롭다운은 테두리 있는 메뉴로 아래에 열린다.
Allow execution은 기본 OFF인 스위치이며 클릭 또는 Space로 전환한다.
Prompt 옆 `[-]` / `[+]`로 높이를 3행씩 조절하고 `Auto`로 기본 높이를 복원한다.
편집 영역은 최소 3행이며, 확대 시 필요한 경우 폼을 스크롤한다. 입력·undo와 하단 실행 버튼 위치는 유지된다.
일반 창을 근사한 110×28 / 120×30 / 120×34에서 Prompt와 action의 동시 노출을 검사한다.
캡처의 정확한 문자 셀 크기를 알 수 없어 여러 중간 크기를 검사한다. 사용자 실제 사용 확인과 자동 viewport 검사는 별도 근거다.
80×24에서는 1열 스크롤을 사용하며 action은 하단에 유지된다. Tab / Shift+Tab으로 이동한다.
Workspace 옆의 Unchecked / Checking / Valid / Invalid와 Execution의 OFF / ENABLED를 확인한다.
Workspace 검증 성공은 실행 승인이 아니다. 확인창은 Cancel에 먼저 focus되며,
Enter는 focus된 버튼을 실행하고 Esc는 확인창을 취소한다.

가상환경의 `Scripts` 또는 `bin`이 PATH에 있는 경우:

```sh
agent-console replay tests/fixtures/successful_developer_run.jsonl
agent-console replay tests/fixtures/failed_run.jsonl
agent-console replay tests/fixtures/successful_developer_run.jsonl --delay 0.2
agent-console replay tests/fixtures/successful_developer_run.jsonl --plain
agent-console replay - < events.jsonl
agent-console run -- <executable> <arguments>
agent-console profile list
agent-console launch
```

`<executable> <arguments>`는 실제 producer 명령으로 바꿉니다. 기존 `run --`은 외부
producer의 argv를 그대로 전달합니다. 새 `launch`는 [문서화한 ai-agent CLI 계약](docs/run-launcher.md)을
사용합니다. 두 방식 모두 shell 없이 argument vector로 실행합니다.
`--plain` / `--tui`는 `run`의 `--` 앞에 둡니다. 외부 명령의 stdin은 닫혀 있으므로
대화형 입력을 요구하는 producer는 지원하지 않습니다. producer는 각 JSONL 줄을 즉시
flush해야 하며 Python producer는 `-u` 또는 자체 flush를 사용합니다.

실제 ai-agent 없이 live mode를 검증하는 Windows 명령:

```powershell
.\.venv\Scripts\agent-console.exe run -- .\.venv\Scripts\python.exe -u examples/emit_fixture.py tests/fixtures/successful_developer_run.jsonl
```

PowerShell stdin 예:

```powershell
Get-Content tests/fixtures/successful_developer_run.jsonl | .\.venv\Scripts\agent-console.exe replay -
```

TUI에서 `Tab`으로 panel을 이동하고 화살표 키로 timeline/component 목록을 탐색합니다.
위 selector로 run을 선택합니다. 새 run이 나타나면 해당 run으로 전환합니다.
입력 종료 후 결과 화면은 유지되며 `q` 또는 `Ctrl+C`로 종료합니다. 실행 중 종료하면
직접 실행한 subprocess를 terminate하고 필요시 kill합니다.
권장 최소 terminal 크기는 80×24입니다. 더 작은 창은 `--plain`을 사용합니다.
stdout이 terminal이 아니면 최종 plain report를 출력합니다. stdin replay는 항상 plain mode입니다.
`launch`는 대화형 stdin/stdout terminal이 필요하며 plain 모드를 제공하지 않습니다.

CLI exit code:

| Code | 의미 |
| --- | --- |
| 0 | 모든 run이 completed, 입력 오류 없음 |
| 1 | failed/cancelled run 또는 범위 밖 subprocess 실패 코드 |
| 2 | 입력·호환성 오류, sequence 누락, terminal event 없음, 빈 stream |
| 1–125 | subprocess nonzero 종료 코드를 우선 전달 |
| 130 | 실행 중 사용자 중단 |

재시도 중 component 실패가 있어도 최종 `run.completed`면 성공할 수 있습니다.
subprocess exit가 nonzero면 protocol의 Completed 표시를 바꾸지 않고 별도 오류를 표시합니다.
plain mode는 stream이 끝난 뒤 보고서를 출력합니다.

## 개발자를 위한 구조

`launcher`는 Runtime Profile과 LaunchRequest를 검증하고, shell 없는 argv를 만들어
`sources`의 subprocess 실행에 전달합니다. `protocol`은 공개 JSONL을 검증하고,
`models`는 허용된 이벤트 정보만 보관합니다. `state`의 Reducer는 실행별 상태를 계산하며
`ui`와 `presentation`은 그 결과를 TUI 또는 plain 보고서로 표시합니다.

Parser와 Reducer는 Textual에 의존하지 않습니다. Launcher의 각 실행은 새 Session을 사용하고,
단일 활성 subprocess 제어와 확인창을 통해 실행 중복 및 의도하지 않은 시작을 막습니다.

## Event Protocol

UTF-8 newline-delimited JSON, 한 줄에 한 event이며 `schema_version = 1`만 지원합니다.
아래는 consumer가 사용하는 필드 요약입니다. 전체 upstream 이벤트 목록을 복제하지 않습니다.

| 필드 | 용도 |
| --- | --- |
| `schema_version` | 지원 schema 확인 |
| `event_id`, `run_id`, `sequence` | 중복 식별, run 분리, 실행 순서 |
| `timestamp_utc`, `elapsed_ms`, `duration_ms` | UTC 시각, 경과 시간, 선택적 duration 값 |
| `component`, `event_type`, `status`, `level` | 작업 설명, lifecycle, 오류 판정 |
| `message`, `metadata` | 타입 검증 후 원문 폐기. 아래 allowlist만 typed details로 보관 |

`workspace.validated.metadata.external`, `git.status.metadata.git_repository/dirty`는 실제 boolean만,
`file.created/modified/deleted.metadata.path`는 제한된 안전한 상대 경로만 보관합니다.
브랜치, read/write/commit/push 권한은 현재 계약에 없으므로 추정하지 않습니다.

위 필드는 모두 필요하며 `duration_ms`의 값은 `null`일 수 있습니다. producer는 public event
정책에 맞는 safe metadata만 보내야 합니다. 형태 예시는
[synthetic fixture](tests/fixtures/successful_developer_run.jsonl), 정확한 검증 규칙은
[Event model](src/agent_console/models/event.py)을 참고하세요.

- sequence는 run별 1부터 시작하는 양의 64-bit 정수입니다. 늦게 도착한 이벤트는 sequence로
  정렬하여 상태를 계산합니다. 중복은 무시하고 충돌은 첫 값을 유지하며, 종료 시 누락을 진단합니다.
  message/폐기된 metadata만 다른 중복은 구별하지 않습니다. allowlist details의 차이는 충돌로 감지합니다.
- component는 마지막 lifecycle 상태를 유지합니다. 전체 결과는 `run.completed`, `run.failed`,
  `run.cancelled`를 따르며 terminal event 없이 입력이 끝나면 `Incomplete`입니다.
- error/critical/fatal level 또는 failed/denied lifecycle을 오류로 집계합니다.
  Current activity는 가장 높은 sequence의 non-run 이벤트입니다.
- 빈 줄은 무시하며 malformed JSON, UTF-8 오류, 필드 오류, oversized line은 진단 후 건너뜁니다.
  지원하지 않는 schema는 compatibility error, unknown event/component는 generic event로 처리합니다.
  마지막 줄에 newline이 없어도 읽습니다.

## Security / Privacy

- Monitor는 prompt 원문을 표시하지 않으며 hidden reasoning을 표시하지 않습니다. 공개 저장소에는
  일반화된 문서와 synthetic fixture만 포함합니다.
- API key, token, password, cookie, Authorization, prompt, source payload를 저장하는 기능이 없습니다.
- free-form message/metadata는 표시하거나 상태에 보관하지 않습니다. 위 allowlist만 사용하며
  파일 내용·diff를 읽지 않습니다. stderr는 동시에 drain하고 byte 수만 표시합니다.
- Launcher prompt는 실행 시 argv로만 전달하며 config/history/log/Event State에 저장하지 않습니다.
  Start 후 입력과 undo 기록을 비웁니다. 실행 중 OS 프로세스 조회 도구에는 argv가 보일 수 있습니다.
- Runtime Profile에는 실행 파일 경로와 기본 옵션만 저장합니다. credential 필드나 prompt history는
  허용하지 않습니다. 기본 위치는 Windows `%APPDATA%/agent-console/config.toml`입니다.
- Allow execution은 기본 OFF이며 실행마다 명시적으로 선택합니다. Check 성공은 실행 승인이 아니며,
  workspace와 실행 권한의 최종 판단은 ai-agent가 담당합니다.
- parser 오류는 원본 줄이나 예외의 입력 값을 출력하지 않습니다. terminal escape/markup을
  identifier 검증 및 literal Text 렌더링으로 차단합니다.
- protocol identifier 자체는 표시됩니다. producer가 ID나 event_type에 secret을 넣는 경우까지
  임의 secret을 탐지·보호하는 도구는 아닙니다. producer의 public event 정책을 유지해야 합니다.
- credential 파일을 읽거나 관리하지 않습니다. subprocess는 사용자 환경을 상속하며, 외부
  producer가 자신의 credential을 사용하는 책임은 producer에 있습니다.
- 자동 event log, database, telemetry, network server가 없습니다. stdout report를 사용자가 직접
  redirect하거나 terminal scrollback을 저장하는 것은 별도 동작입니다.
- `.env*`, 가상환경, cache, 로그, 실제 `*.jsonl`은 Git에서 제외합니다. synthetic test fixture만
  예외입니다. 실제 log를 fixture 폴더에 넣지 마세요.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
```

core parser/reducer, sequence·terminal 처리, 실제 subprocess pipe, stdin/file replay, CLI,
Textual `run_test()` startup/선택/종료를 테스트합니다. 외부 ai-agent나 credential이 필요 없습니다.
pytest 임시 파일은 저장소 내 `.pytest_tmp/`에 생성합니다.

## Limitations

- Terminal UI와 plain report만 제공하며 schema v1 consumer입니다.
- 한 줄은 LF 구분자를 제외하고 최대 64 KiB, session당 최대 20 run, run당 최대 10,000 event를
  보관합니다. 한도를 넘긴 이벤트는 오류로 보고하고 버리며 CLI 성공으로 처리하지 않습니다.
- TUI는 최근 1,000 event, plain report는 최근 200 event, 진단 이력은 최근 100개로 제한합니다.
- component별 마지막 lifecycle을 표시하며 nested task별 상태 집계는 하지 않습니다.
- 메시지 원문·임의 metadata·절대 파일 경로·thread ID·stderr 원문은 표시하지 않습니다.
  파일 변경 요약은 보관된 이벤트 중 최근 3개이며 ASCII 상대 경로만 표시합니다.
- Launcher는 로컬 Developer/Codex 하나만 동시에 실행합니다. Profile의 모델 지원 여부는
  runtime이 판단하며 모델 목록을 직접 조회하지 않습니다.
- 직접 실행한 subprocess만 종료하며 descendant process tree 전체를 관리하지 않습니다.
  terminal event가 와도 producer가 종료되지 않으면 계속 구독합니다. 자동 실행 시간 제한은 없습니다.
  하위 프로세스가 pipe를 열어 두면 EOF도 지연될 수 있습니다. Cancel은 직접 child를 대상으로 합니다.
- stdin replay는 plain mode이며, subprocess의 대화형 stdin은 지원하지 않습니다.
- Web UI, network/WebSocket server, database, remote monitoring, persistent run history,
  browser screenshot preview, training graph, GitHub 연동은 없습니다.

## 다음 개발 후보

아래 항목은 Planned이며 아직 구현하지 않았습니다. 이번 정리에서는 새 기능을 추가하지 않습니다.

- 파일 변경 요약의 경로 문자 지원 확대
- run/component 필터와 replay playback 제어
- 장시간·대량 stream의 중복 검사 인덱스 및 timeline 갱신 최적화

향후 핵심 기능 안정화 이후 전문 UI/UX 디자이너와 협업하여 인터페이스와 사용 경험을 고도화할 계획입니다.
현재 협업 중이거나 전문 디자인 검증이 완료됐다는 의미는 아닙니다.
