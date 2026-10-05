# v0.2 Run Launcher 사용 및 Live 검증

**v0.2.0 — Run Launcher implemented / Live Launcher E2E verified.** 사용자가 아래 Step 1과
Step 2를 일반 non-elevated PowerShell에서 직접 수행하고 성공을 확인했다.
Workspace Check, 명시적 승인 후 Developer/Codex 문서 생성, Monitor 완료 및 Launcher 복귀를
검증했다. [사용자 검증 기록](v0.2-launcher-smoke.md)에 결과를 정리했다.
개발 당시 패키지 버전은 0.1.0이었으며, Live E2E 성공 후 0.2.0으로 확정했다.
개발 자동 테스트는 synthetic subprocess만 사용하고 실제 Live 실행은 다시 수행하지 않았다.

## 1. 설치와 Runtime Profile 등록

Agent Console 저장소 root에서 기존 가상환경에 현재 코드를 설치한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\agent-console.exe profile path
.\.venv\Scripts\agent-console.exe profile list
```

아래 두 경로와 모델 이름을 **자신의 별도 ai-agent runtime** 값으로 바꾼다.
Python은 Agent Console의 Python이 아니라 ai-agent 의존성이 설치된 실행 파일이다.
기존 ai-agent/Codex 인증을 사용하며 Agent Console에 비밀번호나 API key를 입력하지 않는다.

```powershell
.\.venv\Scripts\agent-console.exe profile add local `
  --python "C:/path/to/ai-agent/.venv/Scripts/python.exe" `
  --main "C:/path/to/ai-agent/main.py" `
  --provider codex --model "your-supported-model" `
  --verify none --max-retries 0
.\.venv\Scripts\agent-console.exe profile show local
.\.venv\Scripts\agent-console.exe profile select local
.\.venv\Scripts\agent-console.exe launch --profile local
```

새 설치는 `No runtime configured`로 시작하며 등록 전 실행 버튼은 비활성화된다.
최초 등록한 profile이 기본값이다. 다른 이름으로 추가하고 `select`로 바꾸거나,
`profile remove <name>`으로 삭제할 수 있다. 기존 이름의 암묵적 덮어쓰기는 하지 않는다.
`show`는 로컬 경로를 출력하므로 출력 내용을 공개 저장소에 복사하지 않는다.

저장 위치:

- Windows: `%APPDATA%/agent-console/config.toml` (없으면 사용자 Roaming 디렉터리)
- macOS/Linux: `$XDG_CONFIG_HOME/agent-console/config.toml`, 기본 `~/.config/agent-console/config.toml`
- 별도 설정: `profile --config ./agent-console.local.toml add ...`,
  `launch --config ./agent-console.local.toml`. 이 파일명만 override로 허용하며 Git에서 제외한다.

필드는 name, python_executable, ai_agent_main, provider, model, default_verify,
default_max_retries다. Workspace와 prompt는 저장하지 않는다. 알 수 없는 필드, credential 필드,
잘못된 타입/범위/버전은 거부한다. 최대 20개 profile, config 최대 64 KiB다.
[예시 config](../config.example.toml)는 placeholder만 포함한다.

등록/사용 시 Python 및 main 경로가 존재하는 파일인지 검사한다. 등록 자체는 runtime을 실행하지
않으며 `--help`도 자동 실행하지 않는다. 신뢰하는 runtime을 등록해야 한다. 실제 CLI 호환성은
다음 Workspace Check에서 확인한다. 모델 지원 목록은 ai-agent/Codex가 최종 판단한다.

## 2. Live Verification Step 1 — Check Workspace

일반 PowerShell에서 위 `launch`를 실행하고 다음과 같이 입력한다.

| 항목 | 입력 |
| --- | --- |
| Runtime profile | 등록한 local |
| Workspace | 현재 Agent Console 저장소의 절대 경로 |
| Task / Provider | Developer / Codex |
| Model | profile 기본값, 필요하면 이번 실행만 변경 |
| Verify / Max retries | none / 0 |
| Allow execution | OFF 유지 |
| Prompt | 이 단계에서는 비워도 됨 |

1. **Check Workspace**를 누른다. prompt와 실행 옵션은 전달되지 않는다.
2. Monitor에서 `workspace.validated`, `run.completed`, `COMPLETED`, `[stream ended]`,
   `Process exit 0`, `Issues 0`을 확인한다.
3. **Back to Launcher**를 누르면 `Valid`, Git repository/dirty 여부가 표시된다.
4. Git 상태를 확인해 이 check로 프로젝트 파일이 바뀌지 않았는지 확인한다.

현재 public JSONL의 Git 정보는 `git_repository`와 `dirty` boolean뿐이다.
브랜치·read/write/commit/push 권한은 **not reported**로 표시한다. 알려지지 않은 정보를
허용으로 추정하지 않는다. 실패·빈 스트림·잘못된 protocol·취소·비정상 exit는 성공으로 표시하지 않는다.
실패 시 Monitor의 event/diagnostic을 확인하고 경로·runtime 호환성을 수정한 뒤 다시 check한다.

Check 성공은 작업 승인이나 미래 실행의 권한 보장이 아니다. 자동 Developer 실행은 없으며
별도 Start Run이 필요하다. Workspace/profile을 바꾸면 이전 check 결과를 무효화한다.

## 3. Live Verification Step 2 — 문서 하나 생성

아래는 완료한 검증의 재현 절차다. 릴리스에는 검증 당시 생성된 smoke 문서가 포함되어 있으므로
같은 저장소에서 그대로 재실행하면 기존 파일 확인 단계에서 중단해야 한다. 기록을 덮어쓰지 않는다.

Step 1 성공 후 사용자가 실제 실행을 승인할 때 수행한다. 기존 작업을 먼저 확인하고
`docs/v0.2-launcher-smoke.md`가 이미 있으면 덮어쓰지 말고 중단한다.

```powershell
git status --short
Test-Path docs/v0.2-launcher-smoke.md
```

Launcher에서 Workspace는 이 저장소, Developer/Codex, 확인한 모델, verify `none`, retries `0`으로
설정한다. **Allow execution을 직접 ON**으로 바꾸고 아래 synthetic smoke 요청을 입력한다.

```text
현재 workspace에서 docs/v0.2-launcher-smoke.md 파일 하나만 새로 생성하세요.
파일이 이미 있으면 수정하지 말고 중단하세요.
내용은 "Agent Console v0.2 Launcher smoke test" 제목과,
Launcher에서 시작한 Developer 실행의 문서 생성 확인용이라는 짧은 설명만 작성하세요.
검증되지 않은 성공 선언, 개인 경로, 사용자명, thread ID, 원본 이벤트 로그는 넣지 마세요.
다른 파일 변경, 소스 코드 변경, 의존성 변경, Git commit/push 및 remote 변경은 금지합니다.
```

**Start Run** → 확인 창의 Workspace/모델/verify/retries/Execution을 확인 → **Start**를 누른다.
확인 창의 Cancel/Escape는 subprocess를 시작하지 않는다. 실행 중 prompt 입력과 undo 기록은
비워지고 Allow execution은 OFF로 돌아간다. 별도의 prompt/config/history/log 저장은 없다.

Monitor에서 Main → Developer → Codex 진행, `file.created`, `run.completed`, `COMPLETED`,
`Process exit 0`, `Errors 0`, `Issues 0`, `[stream ended]`를 확인한다.
file event에 지원하는 상대 경로가 있으면 Summary에 `+ docs/v0.2-launcher-smoke.md`가 표시된다.
실행 후 **Back to Launcher**로 돌아가 새 요청을 준비할 수 있다.

마지막으로 직접 파일과 Git 상태를 확인한다.

```powershell
Get-Content docs/v0.2-launcher-smoke.md
git status --short
git diff --stat
```

`git diff --stat`에는 untracked 새 파일이 나오지 않으므로 `git status --short`와 파일 확인을 함께
사용한다. 기대 변경은 새 문서 하나뿐이다. 이 절차에서 자동 commit/push/tag/release는 하지 않는다.
이 절차의 성공은 사용자가 확인했으며, 그 결과를 이번 v0.2.0 릴리스에 반영했다.

## 실행 계약과 제한

CommandBuilder는 순수 로직으로 아래 **argument list**를 만든다. shell 문자열로 연결하지 않는다.

```text
Check:
[python, -u, main.py, --workspace, workspace, --check-workspace, --output, jsonl]

Run:
[python, -u, main.py, --workspace, workspace,
 --task, developer, --provider, codex, --codex-model, model,
 --max-retries, 0..3, --verify, none|pytest|web, --output, jsonl,
 (--allow-execution only when checked), --, prompt]
```

`asyncio.create_subprocess_exec`는 shell 없이 실행한다. Workspace와 prompt는 각각 하나의 인자이며,
prompt 앞 `--`로 옵션 주입을 막는다. prompt는 최대 12,000자다. 이는 보안 권한을 부여하는 기능이
아니며 실제 파일 쓰기·도구·sandbox·Git 정책은 ai-agent가 최종 판단한다.

verify `none`은 별도 host verification 없음, `pytest`는 pytest 검증,
`web`은 pytest 및 local web 검증을 뜻한다. Desktop/Training/다른 provider는 이번 Launcher에 없다.

한 instance당 check/run subprocess 하나만 허용한다. 실행 중 **Cancel Run** 또는 `q`/`Ctrl+C`는
직접 실행한 child만 terminate하고 필요시 kill한다. descendant 전체 종료는 보장하지 않는다.
local cancel은 upstream terminal event를 위조하지 않고 `cancelled locally`와 Console exit 130을
표시한다. child exit, terminal event, stream 종료는 독립적으로 표시한다.

Monitor는 기존 parser → Event → reducer → RunState 흐름을 재사용한다. Event에는 원문 message와
metadata를 보관하지 않으며 workspace/Git boolean과 제한된 상대 파일 경로만 projection한다.
Summary는 최근 3개 변경 event를 표시하고 source/diff는 읽지 않는다. 절대 경로·상위 경로 이동·제어문자·
민감 파일명 패턴·비 ASCII 경로는 표시에서 제외된다. 임의 secret을 모두 탐지하는 필터는 아니다.

Profile은 credential manager가 아니다. subprocess는 기존 사용자 환경과 인증을 사용하며,
prompt argv는 실행 중 OS 프로세스 조회에 노출될 수 있다. 민감정보를 prompt에 입력하지 않는다.
실제 입력 stream은 기본 저장하지 않는다. 테스트 config/workspace는 모두 임시 디렉터리에만 생성된다.

TUI 최소 권장 크기는 80×24이며 form은 스크롤/Tab으로 이동한다. Summary도 길면 스크롤한다.
Launcher는 interactive terminal이 필요하다. 기존 `replay` 및 `run -- ...`의 plain/TUI 사용은 유지된다.

## 성공 및 릴리스 기준

- Launcher Check 성공, 공개 정보만 표시, check가 실제 작업을 시작하지 않음
- 사용자 Start 승인 후 실제 Developer/Codex 이벤트와 새 문서 하나의 생성 확인
- terminal completed, child exit 0, stream ended, Errors/Issues 0 확인
- 다른 파일·의존성·Git history/remote 변경 없음
- 종료 후 Launcher 복귀, prompt/undo 비우기, Allow execution OFF 확인

현재 상태: `v0_2_implementation_complete=true`, `v0_2_live_e2e_verified=true`.
v0.2.0은 위 Workspace Check 및 문서 생성 시나리오를 검증한 로컬 Launcher 릴리스다.
Production Ready, 완전 자율 실행, 모든 ai-agent workflow의 검증을 의미하지 않는다.
