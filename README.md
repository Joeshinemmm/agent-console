# Agent Console

로컬 ai-agent 작업을 시작하고 구조화된 JSONL 실행 이벤트를 실시간 Terminal UI로 관찰하는 독립 client/controller.

처음 사용한다면 [설치와 사용 안내서 (HTML)](docs/getting-started.html)를 따라 해보세요.
Windows PowerShell과 macOS/Linux의 설치, 샘플 실행, 화면 읽기, 실제 Agent 연결 방법을 설명합니다.
다운로드한 저장소에서 HTML 파일을 브라우저로 열면 안내 화면을 볼 수 있습니다.
GitHub에서는 HTML 소스가 표시되며, 별도의 웹 주소로 배포된 페이지는 아닙니다.

## Why

Agent Console은 관찰 가능한 이벤트를 바탕으로 AI Agent가 무엇을 하는지, 어떤 component가
실행 중인지, 어디서 실패했는지, 전체 run이 성공·실패·취소됐는지를 보여줍니다.
별도 `ai-agent`가 공개한 stdout JSONL stream 또는 versioned event log만 소비하며,
upstream 내부 Python module을 import하거나 모델을 직접 호출하지 않습니다.
prompt 원문이나 hidden chain-of-thought를 보여주는 도구가 아닙니다.

## Current Status

**v0.2.0 — Live Launcher E2E verified.** 로컬 Runtime Profile, New Run 화면,
Workspace Check, 실행 확인 및 기존 Monitor 연결을 제공합니다. 사용자가 일반 non-elevated
PowerShell에서 실제 Workspace Check와 Developer/Codex 문서 생성, Launcher 복귀를 검증했습니다.
v0.1의 replay/직접 subprocess Monitor 기능도 유지합니다.
설정과 사용자 검증 순서는 [Run Launcher 안내](docs/run-launcher.md)를 참고하세요.

| 검증 항목 | 상태 | 근거 |
| --- | --- | --- |
| Fixture replay | Verified | synthetic 성공·실패 fixture 테스트 |
| Subprocess streaming | Verified | 실제 subprocess pipe 테스트 |
| Successful / failed run | Verified | 상태 계산·CLI·TUI 테스트 |
| Real ai-agent JSONL | Verified | 사용자 read-only live 연동 검증 |
| Real Developer monitoring | Verified | v0.1 사용자 실제 파일 생성 및 TUI 관찰 |
| Run Launcher Workspace Check | Verified | 사용자 실제 workspace 검증, exit 0, Issues 0 |
| Run Launcher Developer Live E2E | Verified | 명시적 승인 후 문서 하나 생성, 완료 및 Launcher 복귀 |
| Production deployment | Not claimed | 검증 범위에 포함하지 않음 |

v0.2 Live 검증은 Workspace Check와 단일 문서 생성 시나리오에 한정합니다.
릴리스 변경 사항은 [CHANGELOG](CHANGELOG.md)를 참고하세요.

## Features

- JSONL 파일 replay, stdin 입력, 외부 명령의 실시간 stdout 구독
- schema v1 검증과 호환성 오류 표시, 잘못된 입력 이후 복구
- 지원 schema 안의 unknown event/component를 generic event로 표시
- run별 타임라인, component 상태, 최근 작업, 실행 요약
- sequence 정렬, 중복 제거, 충돌 및 누락 진단
- 실패·취소·불완전 실행 구분, subprocess 종료 코드와 stderr 수신량 표시
- 다중 run 선택, 키보드 탐색, 자동 plain-text 출력
- synthetic fixture 기반 개발 및 테스트
- 로컬 Runtime Profile CLI와 Developer/Codex Run Launcher
- 실행별 모델 override, verify none/pytest/web 선택, max retries 0–3
- 별도 Workspace Check, 기본 OFF인 Allow execution, Start 확인 대화상자
- 실행 취소·Launcher 복귀, 공개 상대 경로를 이용한 작은 파일 변경 요약

## Architecture

```text
Agent Console Launcher
    ↓ RuntimeProfile + LaunchRequest
CommandBuilder (argv)
    ↓
local ai-agent subprocess
    ↓ stdout JSONL             file / stdin replay
    └─────────────┬───────────────────┘
                  ↓
         Parser → Event → Reducer
                  ↓
               RunState
                  ↓
        Textual TUI / plain report

subprocess stderr → byte count (원문 폐기)
subprocess exit   → 독립적인 process 결과
```

제어 흐름은 `사용자 → Launcher → Check Workspace → 사용자 Start 승인 → ai-agent →
Developer/Codex → Target Project`입니다. Check 성공 후에도 별도 Start 승인이 필요하며,
최종 workspace/실행 권한 판단은 ai-agent에 있습니다.

`models`, `protocol`, `state`, `sources`, `launcher` core는 Textual을 import하지 않습니다.
UI는 상태를 표시하며 business state를 생성하지 않습니다. 이벤트 종류에 따른 설명은
`presentation.py`, lifecycle 상태 규칙은 `state/reducer.py`에 모았습니다.

Textual은 Python 기반 terminal widget, 비동기 입력, 키보드 탐색, headless UI 테스트를
지원하므로 선택했습니다. Python 3.13.15 / Textual 8.2.8 환경에서 동작을 검증했습니다.
설치 지원 범위는 Python 3.11 이상, Textual 8.2 이상 9 미만입니다.
라이브러리 참고: [Textual](https://textual.textualize.io/),
[testing guide](https://textual.textualize.io/guide/testing/).

## Live Integration

v0.2에서는 사용자가 Runtime Profile을 통해 Launcher에서 실제 Workspace Check와 Developer run을
시작했습니다. 명시적 Allow execution 및 Start confirmation 이후 `file.created`, `run.completed`,
`COMPLETED`, `Process exit 0`, `Errors 0`, `Issues 0`, `[stream ended]`를 확인했습니다.
`docs/v0.2-launcher-smoke.md` 하나만 생성됐고 의도하지 않은 파일 변경은 없었으며 Launcher 복귀도
정상 확인했습니다. [v0.2 검증 기록](docs/v0.2-launcher-smoke.md)에 사용자 보고 범위를 정리했습니다.
Production Ready나 모든 ai-agent workflow의 검증을 의미하지 않습니다.

다음은 v0.1에서 먼저 완료한 직접 subprocess Monitor 검증 기록입니다.

별도 ai-agent runtime과의 read-only JSONL 연동에 이어, 일반 non-elevated PowerShell에서
실제 Developer Agent와 Codex를 사용하는 Live E2E를 사용자가 실행하고 성공을 확인했습니다.

```text
Agent Console
    ↓ subprocess
ai-agent → Main → External Workspace validation
    ↓ Developer → Codex
target workspace: smoke 문서 생성
    ↓ JSONL stdout (진행 및 완료 이벤트)
Agent Console TUI
```

검증 범위는 external workspace validation, 실제 Developer Agent 및 Codex thread 시작,
target 파일 생성, `file.created`, Developer·cleanup 완료, `run.completed`,
TUI 실시간 표시, subprocess exit `0`입니다. TUI에서 `RUNNING → COMPLETED`,
`Errors 0`, `Issues 0`, `[stream ended]`도 확인했습니다.

Live Agent가 생성한 파일은 `docs/live-ai-agent-smoke.md` 하나이며, 다른 프로젝트 파일 변경이나
commit/push/remote 변경은 없었습니다. 이 결과는 해당 문서 생성 시나리오에서 이 저장소 자체를
target으로 사용한 self-hosting E2E 검증입니다. 범용 자율 작업이나 운영 환경 배포를 보증하지 않습니다.

검증 근거는 [Live E2E smoke 기록](docs/live-ai-agent-smoke.md)에 일반화해 정리했습니다.
실제 thread ID, 개인 경로, 원본 이벤트 로그는 공개 문서에 포함하지 않습니다.

## Screenshot

아래는 화면 구성을 설명하는 ASCII preview이며 실제 캡처가 아닙니다.

```text
AGENT CONSOLE
Run [synthetic-developer-run                  v]
Run synthetic-developer-run   COMPLETED   [stream ended]
┌ Timeline · sequence order ──────────────────────────┐
│ Seq   Elapsed   Component   Event / activity        │
│   1    0.006s   Main        Run started             │
│ ...                                                │
│  12    4.315s   Main        Run completed           │
└────────────────────────────────────────────────────┘
┌ Components ─────────────┐ ┌ Current activity ───────┐
│ Main        Completed  │ │ Cleanup                 │
│ Developer   Completed  │ │ Cleanup completed       │
│ Codex       Completed  │ │                         │
│ Test        Idle       │ │                         │
└────────────────────────┘ └─────────────────────────┘
Elapsed 4.315s   Events 12   Errors 0   COMPLETED
Q Quit   Ctrl+C Stop   Tab Panel
```

## Installation

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

## Usage

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
  terminal event가 와도 producer가 종료되지 않으면 계속 구독합니다.
- stdin replay는 plain mode이며, subprocess의 대화형 stdin은 지원하지 않습니다.
- Web UI, network/WebSocket server, database, remote monitoring, persistent run history,
  browser screenshot preview, training graph, GitHub 연동은 없습니다.

## Roadmap

아래는 다음 버전의 검토 후보이며 v0.2.0 구현 범위에 포함되지 않습니다.

- 파일 변경 요약의 경로 문자 지원 확대
- run/component 필터와 replay playback 제어
- 장시간·대량 stream의 중복 검사 인덱스 및 timeline 갱신 최적화
