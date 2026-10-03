# Agent Console

Versioned AI agent JSONL 이벤트를 실행 타임라인과 component 상태로 보여주는 독립 Terminal UI.

처음 사용한다면 [설치와 사용 안내서 (HTML)](docs/getting-started.html)를 따라 해보세요.
Windows PowerShell과 macOS/Linux의 설치, 샘플 실행, 화면 읽기, 실제 Agent 연결 방법을 설명합니다.
다운로드한 저장소에서 HTML 파일을 브라우저로 열면 안내 화면을 볼 수 있습니다.
GitHub에서는 HTML 소스가 표시되며, 별도의 웹 주소로 배포된 페이지는 아닙니다.

## Why

AI agent의 작업 흐름을 파악하려면 관찰 가능한 실행 기록이 필요합니다. Agent Console은
`ai-agent`가 공개한 stdout JSONL stream 또는 event log만 읽는 외부 client입니다.
내부 Python module, 모델 호출, 숨겨진 추론에 접근하지 않습니다.

## Features

- JSONL 파일 replay, stdin 입력, 외부 명령의 실시간 stdout 구독
- schema v1 검증과 호환성 오류 표시, 잘못된 입력 이후 복구
- run별 타임라인, component 상태, 최근 작업, 실행 요약
- sequence 정렬, 중복 제거, 충돌 및 누락 진단
- 실패·취소·불완전 실행 구분, subprocess 종료 코드와 stderr 수신량 표시
- 다중 run 선택, 키보드 탐색, 자동 plain-text 출력
- synthetic fixture 기반 개발 및 테스트

## Architecture

```text
ai-agent (external process / existing event log)
    │ stdout JSONL / file
    ▼
sources → JSONL parser → Event → pure reducer → RunState
                                                │
                                      Session → Textual TUI / plain report
stderr → byte count (content discarded)          │
exit code → independent process result ──────────┘
```

`models`, `protocol`, `state`, `sources`는 Textual을 import하지 않습니다.
UI는 상태를 표시하며 business state를 생성하지 않습니다. 이벤트 종류에 따른 설명은
`presentation.py`, lifecycle 상태 규칙은 `state/reducer.py`에 모았습니다.

Textual은 Python 기반 terminal widget, 비동기 입력, 키보드 탐색, headless UI 테스트를
지원하므로 선택했습니다. Python 3.13.15 / Textual 8.2.8 환경에서 동작을 검증했습니다.
설치 지원 범위는 Python 3.11 이상, Textual 8.2 이상 9 미만입니다.
라이브러리 참고: [Textual](https://textual.textualize.io/),
[testing guide](https://textual.textualize.io/guide/testing/).

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

가상환경의 `Scripts` 또는 `bin`이 PATH에 있는 경우:

```sh
agent-console replay tests/fixtures/successful_developer_run.jsonl
agent-console replay tests/fixtures/failed_run.jsonl
agent-console replay tests/fixtures/successful_developer_run.jsonl --delay 0.2
agent-console replay tests/fixtures/successful_developer_run.jsonl --plain
agent-console replay - < events.jsonl
agent-console run -- <executable> <arguments>
```

`<executable> <arguments>`는 실제 producer 명령으로 바꿉니다. 이 프로젝트는 외부
ai-agent의 CLI 옵션을 가정하지 않습니다. 명령은 shell 없이 argument vector로 실행합니다.
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

UTF-8 newline-delimited JSON, 한 줄에 한 event. v0.1 consumer는 `schema_version: 1`만
지원합니다. 지원하지 않는 버전은 compatibility diagnostic을 표시하고 해당 줄을 건너뜁니다.

필수 필드:

```json
{
  "schema_version": 1,
  "event_id": "synthetic-event-1",
  "run_id": "synthetic-run",
  "sequence": 1,
  "timestamp_utc": "2026-01-01T00:00:00Z",
  "elapsed_ms": 6.1,
  "component": "main",
  "event_type": "run.started",
  "status": "started",
  "level": "info",
  "message": "run.started",
  "duration_ms": null,
  "metadata": {}
}
```

- sequence는 run별 1부터 시작하는 양의 64-bit 정수입니다. sequence가 canonical order이며
  timestamp나 수신 순서가 달라도 timeline과 component 상태는 sequence 순서로 계산합니다.
- elapsed/duration은 음수가 아닌 유한 숫자, timestamp는 UTC offset을 포함한 ISO 8601입니다.
- ID/component/type/status/level은 최대 128자의 영문·숫자·`_ . : -` identifier입니다.
  identifier는 영문 또는 숫자로 시작해야 합니다. free-form message는 문자열,
  metadata는 object여야 하며 검증 후 둘 다 consumer model에서 버립니다.
- 같은 run의 동일 event_id는 무시합니다. 내용이 충돌하는 ID 또는 sequence는 첫 값을 유지하고
  입력 오류를 보고합니다. message/metadata만 다른 중복은 payload를 저장하지 않으므로 구별하지 않습니다.
- 늦게 도착한 event는 정렬 후 상태를 다시 계산합니다. 종료 시 sequence gap을 검사합니다.
- unknown event/component와 추가 필드는 허용합니다. 알려지지 않은 종류는 generic label로 표시합니다.
- component lifecycle은 type의 마지막 단어, 다음으로 status를 사용합니다.
  started/running/resumed/retry/ready → Running, completed/stopped → Completed,
  failed/denied → Failed, cancelled → Cancelled입니다. 그 외 이벤트는 이전 상태를 유지합니다.
  nested lifecycle도 해당 component의 마지막 상태로 표시하며 task별 집계는 하지 않습니다.
- 전체 run 결과는 `run.completed`, `run.failed`, `run.cancelled`로 결정합니다.
  EOF에 terminal event가 없으면 Incomplete이며 성공으로 추정하지 않습니다.
- error/critical/fatal level 또는 failed/denied lifecycle은 error count에 포함됩니다.
  Current activity는 가장 높은 sequence의 non-run event입니다.

빈 줄은 무시합니다. malformed JSON, UTF-8 오류, 필드 오류, oversized line은 안전한 진단과
함께 건너뛰며 다음 줄을 계속 읽습니다. EOF 직전 newline 없는 마지막 event도 읽습니다.
한 줄은 LF 구분자를 제외하고 최대 64 KiB, session은 최대 20 run, run은 최대 10,000 event를 보관합니다.
한도 이후 event는 명시적 오류로 보고하고 버립니다. TUI는 최근 1,000 event, plain report는
최근 200 event, 진단은 최근 100개를 표시합니다. 제한에 도달한 실행 결과는 입력 오류로
취급하므로 관측한 terminal event만으로 CLI 성공을 반환하지 않습니다.

## Security / Privacy

- API key, token, password, cookie, Authorization, prompt, source payload를 저장하는 기능이 없습니다.
- free-form message/metadata는 표시하거나 상태에 보관하지 않습니다. 파일 이름 등 상세 정보도
  숨겨지며 activity는 event 종류로 설명합니다. stderr는 동시에 drain하고 byte 수만 표시합니다.
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

## Roadmap

- 실제 ai-agent public JSONL producer와 end-to-end 호환성 확인
- 장시간·대량 stream의 중복 검사 인덱스 및 timeline 갱신 최적화
- protocol contract 확정 후 상세 presentation mapping 보강
- run/component 필터와 replay playback 제어

v0.1에는 web dashboard, cloud, socket/WebSocket, 계정, DB, GitHub 연동, 모델 호출,
browser screenshot, training graph가 없습니다. subprocess descendant process tree 전체를
관리하지 않으며 직접 실행한 process만 종료합니다. 실시간 terminal event가 오더라도
producer가 종료되지 않으면 계속 구독합니다.
