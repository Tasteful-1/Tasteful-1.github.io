# AIMT Guide CLI

`scripts/guide_cli.py`는 가이드 관리 중 자주 반복되는 작업을 한곳에 묶은 보조 CLI입니다.

## 안전한 반복 작업

아래 명령은 기존 HTML 본문을 전면 재작성하지 않습니다.

- `python scripts\\guide_cli.py status`
- `python scripts\\guide_cli.py search`
- `python scripts\\guide_cli.py nav`
- `python scripts\\guide_cli.py sync`
- `python scripts\\guide_cli.py validate --compile --leaks`
- `python scripts\\guide_cli.py serve`
- `python scripts\\guide_cli.py editor`

`status`는 현재 guide 페이지 수, 목차 항목 수, 검색 인덱스 수를 요약합니다.
`search`는 현재 `dist/guide/**/index.html`의 본문을 기준으로 `search-index.json`만 다시 만듭니다.
`nav`는 현재 목차 구조를 모든 guide HTML에 다시 씁니다. 기본적으로 검색 인덱스도 갱신합니다.
`sync`는 목차와 검색 인덱스를 갱신한 뒤 정적 검증을 실행합니다.
`validate`는 `dist` 필수 파일, 내부 링크, 로컬 경로 노출을 검사합니다.
`serve`는 `dist`를 로컬 서버로 엽니다.
`editor`는 가이드 에디터 서버를 엽니다.

## 목차 생성 기준 선택

- `python scripts\\guide_cli.py nav --canonical`
- `python scripts\\guide_cli.py sync --canonical`
- `python scripts\\guide_cli.py compare-nav`

기본 `nav`는 현재 `dist`에 들어 있는 목차 순서를 기준으로 다른 페이지의 목차를 맞춥니다.
`--canonical`은 `scripts/renew_user_manual.py`의 목차 규칙을 적용합니다.
`compare-nav`는 현재 목차와 생성 스크립트 기준 목차가 같은지 비교만 합니다.

## 본문 재작성 작업

- `python scripts\\guide_cli.py renew --yes`

`renew`는 가이드 article 본문까지 공식 템플릿 기준으로 다시 씁니다. 사용자가 에디터에서 직접 고친 `dist` 본문이 있는 경우 실행 전 변경 범위를 반드시 확인하세요. 실수 방지를 위해 `--yes` 없이는 실행되지 않습니다.
