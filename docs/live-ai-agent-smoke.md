# Agent Console Live E2E Smoke

이 smoke test는 실제 ai-agent Developer Agent가 문서를 생성하는 동안 Agent Console의 실시간 TUI가 공개 JSONL stdout을 올바르게 표시하는지 확인한다.

Developer Agent를 실행해 문서 생성을 요청하고, 그 stdout 스트림을 Agent Console에 연결해 진행 상태와 이벤트를 실시간으로 관찰한다.

## 검증 결과

사용자가 일반 non-elevated PowerShell에서 실제 실행을 수행하고, 실행 종료 후 파일 변경과
TUI 관찰 결과를 확인하여 Live Developer E2E 성공을 판정했다. 이 문서는 실제 Developer가
생성한 smoke 문서에 해당 사용자 검증 결과를 반영한 기록이다. 릴리스 정리 과정에서는
실제 ai-agent / Codex 실행을 반복하지 않았다.

```text
Agent Console → ai-agent subprocess → External Workspace validation
→ Main / Developer Agent → Codex → target workspace 문서 생성
→ JSONL stdout → Agent Console TUI
```

- 실제 Codex thread 시작 및 turn 완료를 확인했다.
- 요청한 `docs/live-ai-agent-smoke.md` 하나만 생성됐으며 다른 프로젝트 파일 변경은 없었다.
- `file.created`, Developer 완료, cleanup 완료, `run.completed`를 확인했다.
- TUI에서 `RUNNING → COMPLETED`, `Errors 0`, `Issues 0`, `Process exit 0`, `stream ended`를 확인했다.
- Live Agent 작업에서는 commit, push, remote 변경이 발생하지 않았다.

```text
real_ai_agent_live_integration_verified=true
self_hosting_e2e_verified=true
```

## 범위

검증 범위는 외부 ai-agent runtime이 Agent Console 저장소를 target workspace로 사용해
문서 하나를 생성하고, Agent Console이 공개 JSONL 이벤트를 관찰한 로컬 MVP 시나리오다.
운영 환경 배포나 모든 Agent 작업의 안정성을 검증했다는 의미는 아니다.

개인 경로, 사용자명, 실제 thread ID, credential, 원본 JSONL, 전체 prompt 및 hidden reasoning은
이 기록에 포함하지 않는다. 성공 판정은 사용자 관찰에 근거하며 원본 실행 로그를 첨부하지 않는다.
