# AIMT Guide Site

이 폴더는 GitHub Pages에 올릴 사용자 가이드와 로컬 편집 도구를 담습니다.

## 현재 상태

- `dist/`가 현재 가이드 배포 원본입니다.
- `ExportBlock/`은 더 이상 배포에 필요하지 않습니다.
- `scripts/rebuild_recovery_dist.py`는 최소 문서 골격을 다시 만드는 복구용 스크립트입니다. 실제 본문을 다시 작성한 뒤에는 무심코 실행하지 마세요.
- `scripts/migrate_exportblock_to_dist.py`는 과거 `ExportBlock/` Notion export가 있을 때만 쓰는 선택용 변환 스크립트입니다.
- `scripts/edit_guide.py`는 dist HTML을 직접 편집하는 로컬 WYSIWYG 에디터입니다.
- `scripts/validate_dist.py`는 배포 전 내부 링크, 이미지, `.md` 링크, Windows 절대경로 누출을 검사합니다.

## 배포 전 검증

```powershell
python scripts\validate_dist.py
```

## 로컬 편집

```powershell
python scripts\edit_guide.py
```

브라우저에서 `http://127.0.0.1:8776/`을 열어 편집합니다.

지원 기능:

- 문서 본문 WYSIWYG 편집 및 HTML 소스 보기
- 실제 이미지 삽입, 이미지 선택 후 정렬/크기 조절
- 새 페이지 생성
- 가이드 목차 트리 접기/펼치기
- 페이지를 다른 페이지에 드래그해 하위 페이지로 이동
- 하위 문서를 가진 묶음은 접힌 상태에서만 묶음째 이동

## 검증

```powershell
python -m py_compile scripts\edit_guide.py scripts\validate_dist.py scripts\rebuild_recovery_dist.py scripts\migrate_exportblock_to_dist.py
python scripts\validate_dist.py
```

## GitHub Pages 배포

`main` 브랜치에 push하면 `.github/workflows/pages.yml`이 `dist/` 폴더를 GitHub Pages artifact로 배포합니다.

배포 전에는 현재 `dist/` 산출물을 검증합니다.

```powershell
python scripts\validate_dist.py
```

`https://aimt-guide.github.io/` 주소를 쓰려면 GitHub 사용자 또는 조직 이름이 `aimt-guide`여야 하며, 저장소 이름은 `aimt-guide.github.io`여야 합니다. 저장소 Settings > Pages의 Build and deployment Source는 `GitHub Actions`로 설정합니다.
