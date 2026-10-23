# Provider 중립 명령 smoke 기록

결과 반영일: 2026-10-24. 사용자가 사용량 발생을 승인한 뒤 provider별로 한 번씩 수행했다.
아래는 실행 결과를 일반화한 기록이다.

## 방법

- Launcher와 같은 CommandBuilder(`build_command`)로 Runtime Profile과 LaunchRequest에서 argv를 만들고,
  그 argv를 `agent-console run --plain -- <argv>`로 실행했다. 실행 명령, parser, reducer,
  plain report 경로는 Launcher와 같다.
- Launcher TUI 조작(입력, 확인창, 버튼)은 이 smoke에 포함하지 않았다. 그 부분은 synthetic Textual
  테스트로만 확인했다.
- 대상은 별도 smoke용 Git 저장소(외부 workspace)다. verify `none`, max retries `0`이며,
  문서 생성 실행에만 Allow execution을 사용했다.
- provider마다 Workspace Check 1회와 문서 생성 1회를 실행했다. 모델은 각 provider에서 사용할 수 있는
  모델을 실행할 때 지정했다. 모델 이름은 계정 플랜에 따라 달라지므로 기록이나 기본값으로 두지 않는다.
- 요청 내용: 새 smoke 문서 하나만 생성. 기존 파일 수정, 소스·의존성 변경, Git commit/push와
  remote 변경은 금지.

## 결과

| provider | Workspace Check | 문서 생성 |
| --- | --- | --- |
| `claude` | `COMPLETED`, 이벤트 5개, `Process exit 0`, `Issues 0` | `COMPLETED`, 이벤트 12개, `Errors 0`, `Issues 0`, stderr 0 bytes, `Process exit 0` |
| `codex` | `COMPLETED`, 이벤트 5개, `Process exit 0`, `Issues 0` | `COMPLETED`, 이벤트 12개, `Errors 0`, `Issues 0`, stderr 0 bytes, `Process exit 0` |

- 문서 생성 실행의 이벤트 순서는 두 provider 모두 `llm.session.started` → `llm.turn.started` →
  `llm.turn.completed` → `file.created` → `run.completed`였다.
- Timeline에는 `LLM session started (Claude)`, `LLM turn completed (Codex)`처럼 provider가 함께 표시되고,
  plain report에는 `llm=Completed`와 `LLM provider: claude|codex`가 표시됐다.
- 실행 argv에는 `--provider <claude|codex> --model <이름>`이 들어가고 `--codex-model`은 없었다.
- plain report에 `thread_id`, `auth_type` 같은 세션 식별 값은 표시되지 않았다.
- 대상 저장소에는 provider별 새 문서가 하나씩만 생겼다(커밋되지 않은 새 파일). 기존 파일, commit, remote는
  바뀌지 않았다. 생성된 문서에는 개인 경로, 사용자명, thread ID가 없었다.

## 범위

이 기록은 Workspace Check와 단일 문서 생성 흐름의 검증 결과다. 실제 Launcher TUI 조작, 다른 작업,
운영 환경이나 모든 ai-agent workflow를 검증했다는 의미는 아니다.
개인 경로, 인증 정보, 실제 run/thread ID, 전체 prompt, 원본 JSONL은 이 기록에 포함하지 않는다.
