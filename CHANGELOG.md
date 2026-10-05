# Changelog

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
