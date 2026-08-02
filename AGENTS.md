# Core Settings
- Response language: Korean (always)
- Primary languages: Python, JavaScript, TypeScript, React, Kotlin, Flutter(Dart)
- 세션을 처음 시작했다면 `.codex\research.md`, `.codex\knowledge\index.md` 순으로 확인하고, 전역 구조가 더 필요할 때만 `areas\project\overview.md`, `areas\codex\overview.md`를 추가로 연다.
- 작업이 완전히 끝날 때까지 계속 진행한다.
- 별도의 지시없이 `.develop`을 탐색하지 않는다. 단, 빌드 시엔 허용한다.
- 작업 로그는 최신순으로 정렬하여 작성한다.

# 4 Core Principles
1. 변경 용이성: 나중에 쉽게 바꿀 수 있는가?
2. 수정 비용: 적은 비용으로 수정/폐기 가능한가?
3. 가독성: 처음 보는 사람이 구조를 쉽게 파악하는가?
4. 간결성: 주석은 필수적인 것만 간단하게.

# Work Rules
- 모든 작업 변경 사항은 `.codex\progress-log.md`에 반영한다.
- 모든 작업은 `.codex\plan.md`를 기준으로 진행한다.
- 작업 시작 시 파일 읽기는 `read-once`를 기본으로 한다. 처음 읽을 때 필요한 범위를 최대한 좁히고, 같은 파일 재열람은 `확인 필요`, 변경 충돌, 검증 목적처럼 근거가 있을 때만 수행한다.
- 전역 파일 탐색은 기본값이 아니다. 먼저 `.codex\knowledge\index.md`, `areas\project\overview.md`, `areas\codex\overview.md`로 범위를 좁히고, 자동 필터링이 필요할 때만 `.codex\file-index.json`을 본다.
- `.codex\knowledge`는 선택적 읽기용 내부 위키다. 세션 시작 시 전체를 읽지 말고 `.codex\knowledge\index.md`에서 현재 작업에 필요한 문서 1~2개만 골라 읽는다.
- 파일 추가/이동/삭제, 폴더 책임 변경, `.codex` 구조 문서 변경 후에는 `python .codex\generate_project_index.py`를 실행해 인덱스를 갱신한다.
- `.codex\*-backup`, `.codex\.tmp_*.js`, `rco\core\extractor\wolf\native\build`는 기본 탐색 대상이 아니다.
- 선택사항/옵션이 발생하면 사용자에게 먼저 질문한다(기본값 강행 금지).
- 모호한 포인트는 결과를 단정하지 않고 "확인 필요"를 표기한다.
- 필요 시, 파일을 직접 생성 후 처리한 뒤 보고한다.

# Code Guidelines
- Function-based decomposition with sufficient comments
- Mark uncertainties: "추측", "확인 필요"
- Request concrete methods - don't assume/imagine APIs
- Prioritize clarity over cleverness

# Type Hints
- Python: Always use type hints (PEP 484)
- TypeScript: Prefer explicit types over 'any'
- Document complex types in docstring

# Pythonic Patterns (Python-specific)
- EAFP over LBYL: try-except > if 체크 (when exceptions expected)
- Use all()/any() for multiple conditions
- Extract validators for complex validation logic
- Decorators for repeated checks
- Match-case for multiple branches (Python 3.10+)
- Early return: only for simple guard clauses (1-2 checks)

# Error Handling
- Explicit error cases in docstring
- Prefer specific exceptions over generic
- Document expected failures

# Naming Conventions
- Functions/methods: verb_noun (snake_case in Python, camelCase in JS/TS)
- Variables: descriptive nouns
- Constants: UPPER_SNAKE_CASE
- Private: _leading_underscore

# Code Quality Checks
Before suggesting code, verify:
1. Single Responsibility: 각 함수가 한 가지만 하는가?
2. Dependencies: 외부 의존성 최소화되었는가?
3. Testability: 테스트하기 쉬운 구조인가?
4. Coupling: 결합도가 낮은가?

# Code Review (When reviewing user's code)
Priority order:
1. Correctness: 버그, 로직 오류, 에지 케이스
2. 3 Core Principles: 변경 용이성, 수정 비용, 가독성
3. Pythonic/Idiomatic patterns
4. Performance: 명백한 비효율만
5. Security: injection, XSS, 민감정보 노출

Feedback format:
- Specify line/block: "Line 15-20의..."
- Before/After code (concise)
- Explain WHY: 문제 이유, 개선 이유
- Priority tags: [Critical], [Important], [Minor], [Suggestion]

Checklist:
- Docstring/type hints 누락?
- Magic numbers/strings?
- 함수 > 15 lines?
- Error handling 누락?
- 중복 로직 3회+?
- 테스트 불가능한 구조?

Avoid:
- 완벽주의: minor 이슈로 과도한 리팩토링 제안 금지
- 스타일 논쟁: 린터 통과하면 OK
- 과도한 추상화: YAGNI

# Performance Notes
- Document time/space complexity for non-trivial algorithms
- Note performance trade-offs in docstring
- Mark optimization opportunities: "TODO: optimize if needed"

# Refactoring Priority
When suggesting improvements, order by:
1. Correctness (bugs first)
2. Readability (understand > clever)
3. Maintainability (change cost)
4. Performance (measure first)

# Avoid
- Magic numbers: use named constants
- Deep nesting: prefer patterns above
- Functions > 15 lines: consider splitting
- Boolean params without context: use named args or enums
