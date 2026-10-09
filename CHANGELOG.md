# Changelog

## [0.2.1] - Unreleased

- Launcher의 넓은 화면 2열 배치와 80×24 스크롤 fallback, Prompt 및 고정 action 접근성 개선
- Workspace 상태 배지, Execution OFF/ENABLED 표시 및 선택 값에 맞는 짧은 도움말
- 확인창 설정 정렬, Cancel의 disabled처럼 보이던 focus 반전 스타일 수정 및 안전한 초기 focus 유지
- Launcher/Monitor Tab 탐색 연결 수정, 버튼의 focus·pressed·disabled 시각적 구분
- Monitor의 짧은 run ID, 내용에 맞는 Timeline 높이, 중립 panel 테두리와 focus 강조
- component 상태 강조, terminal 결과 및 수치 summary 표시
- stream/process 종료 후 Cancel 숨김과 Back to Launcher 강조; 종료 전 취소 동작 유지
- viewport와 keyboard/mouse 동작에 대한 synthetic UI 회귀 테스트

### Second pass

- Launcher의 열 수는 너비로 결정하고, 낮은 창은 설정·Runtime control을 compact하게 표시
- 일반 창에서 Prompt와 actions 동시 노출, Workspace 상태를 label 옆에 배치
- Agents 여섯 상태에 필요한 높이를 먼저 확보하고 System 상태는 보조 줄로 분리
- Run result에 종료·파일 변경 정보, Summary에 수치 지표를 배치해 중복 제거
- 단일 run은 한 줄 header와 전체 ID tooltip, 다중 run은 compact selector 사용
- 버튼의 공통 높이·여백·테두리와 밝은 focus 표시 통일, disabled label 가독성 개선
- 실행 중 버튼 위치가 이동하지 않는 고정 action bar 유지
- 80×24, 110×28, 120×30, 120×34, 160×50에서 실제 합성 terminal cell 및 panel clipping 검사

### User feedback pass

- compact 입력의 경계·배경 및 설정 구분선을 추가하고 드롭다운 메뉴 테두리를 유지
- 설정 행의 가로 배치 CSS가 Select 내부에 적용되어 메뉴가 옆으로 열리던 문제 수정
- Allow execution을 기본 OFF인 스위치로 교체하고 명시적 승인·확인 흐름 유지
- 버튼 기본 입체형 hover/pressed 스타일을 제거해 평면 외곽선 유지
- Launcher/Monitor에서 작동하지 않는 기본 명령 메뉴 아이콘 제거
- Prompt 높이 축소·확대·자동 복원 추가; 편집 내용·undo 및 고정 action 유지
- 메뉴 위치·버튼 상태·크기 조절을 실제 합성 terminal cell과 viewport로 검증

### Stabilization and documentation

- Workspace Check·실패·취소·완료 이후 새 Workspace에서 재실행할 때 상태가 섞이지 않는 회귀 테스트 추가
- README와 기존 HTML 안내서를 목적·두 프로젝트의 역할·사용 흐름·구현 및 검증 범위 중심으로 정리
- 직접 child만 취소하는 범위, 자동 실행 시간 제한 부재와 pipe 종료 지연 가능성 명시
- 향후 핵심 기능 안정화 이후 전문 UI/UX 디자이너와 협업할 계획 표시

현재 범위의 UI/UX polish는 마무리했으며 패키지 버전은 0.2.0을 유지한다.
2026-10-09 사용자 피드백으로 기본 기능의 실제 사용 동작을 확인했다.
합성 화면 검사·사용자 기본 동작 확인과 전문 디자인 검증을 구분하며, 전문 디자인 검증은 미실시다.
main 반영과 별개로 0.2.1 공식 태그·릴리스는 아직 생성하지 않았다.

## [0.2.0] - 2026-10-06

### Added

- 사용자 전용 TOML Runtime Profile 및 add/list/show/select/remove/path CLI
- Developer/Codex TUI Run Launcher, 모델 override, verify 선택, 제한된 retries
- shell 없는 argv builder, 기본 OFF인 Allow execution과 명시적 실행 확인
- 별도 read-only Workspace Check 및 공개 JSONL 기반 결과 표시
- 기존 Monitor 재사용, 단일 활성 subprocess, 직접 child 취소와 Launcher 복귀
- Start 후 prompt/undo 기록 제거, allowlist 상대 경로의 파일 변경 요약
- synthetic subprocess와 Textual headless 기반 Launcher 테스트 및 사용자 Live 검증 절차

### Verified

- 사용자 일반 non-elevated PowerShell에서 실제 ai-agent Workspace Check 성공
- 명시적 실행 승인 후 실제 Developer/Codex Launcher Live E2E 성공
- smoke 문서 하나 생성, COMPLETED / exit 0 / Errors 0 / Issues 0 / stream ended 확인
- 의도하지 않은 파일 변경 없음 및 Launcher 복귀 정상 확인

패키지 버전을 0.2.0으로 확정했다. 검증 범위는 Workspace Check와 단일 문서 생성이며,
운영 환경 배포나 모든 workflow의 검증을 주장하지 않는다.
일반화된 사용자 검증 결과는 [v0.2 smoke 기록](docs/v0.2-launcher-smoke.md)을 참고한다.

## 0.1.0

- JSONL schema v1 consumer와 malformed/unknown event 처리
- 파일 replay, stdin, 실시간 subprocess 입력
- Textual TUI의 Timeline, component 상태, Current activity, run 요약
- 다중 run 추적, sequence 정렬, 중복·충돌·누락 진단
- 성공·실패·취소·불완전 실행 구분과 subprocess 종료 코드 표시
- 민감 payload 비보관, stderr byte 요약 및 run/event 보관 한도
- synthetic fixture와 core·CLI·TUI 테스트, HTML 설치·사용 안내서
- 실제 ai-agent JSONL 연동 및 Developer Live E2E 사용자 검증 완료

Live E2E 검증 범위와 결과는 [smoke 기록](docs/live-ai-agent-smoke.md)을 참고한다.
이 릴리스는 로컬 v0.1.0 MVP 검증 기준점이다.
