from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

import edit_guide
from bs4 import BeautifulSoup, NavigableString, Tag


DIST_ROOT = edit_guide.DIST_ROOT
GUIDE_ROOT = DIST_ROOT / "guide"
RENEWED_AT = "2026-06-18"
DOC_VERSION = f"문서 기준: AIMT PRO 1.13 계열<br>최종 편집 일시: {RENEWED_AT}"
ADVANCED_INTRO = "이 문서는 일반 작업 순서에서 벗어나, 값을 직접 확인하거나 세밀하게 조정해야 할 때 참고하는 자료입니다."
SHORT_ARTICLE_FALLBACK = "아직 세부 설명이 충분하지 않은 문서입니다. 먼저 기능의 위치와 실행 결과를 확인하고, 필요한 경우 관련 상위 문서를 함께 확인하세요."

GROUP_PAGES: dict[str, str] = {
    "guide/start/index.html": "시작하기",
    "guide/basic-workflow/index.html": "기본 작업 흐름",
    "guide/engine-guides/index.html": "엔진별 가이드",
    "guide/features/index.html": "기능별 설명",
    "guide/troubleshooting/index.html": "문제 해결",
    "guide/advanced-reference/index.html": "참고 자료",
}

VIRTUAL_GROUP_PAGES: set[str] = set(GROUP_PAGES)

ADVANCED_SUBGROUP_PAGES: dict[str, str] = {}

SETTING_REFERENCE_GROUP_PAGES: dict[str, str] = {}

EXTERNAL_REFERENCE_PAGES: dict[str, str] = {
    "guide/제공자별-참고-링크/index.html": "제공자별 참고 링크",
}

STARTING_PATHS = {
    "guide/프롬프트/index.html",
}

WORKFLOW_PATHS = {
    "guide/새-프로젝트-프로젝트-지정/index.html",
    "guide/추출/index.html",
    "guide/번역/index.html",
    "guide/적용과-즉시적용/index.html",
}

ENGINE_PATHS = {
    "guide/rpg-maker-mvmz-개정1/index.html",
    "guide/rpg-maker-vxvxa-개정1/index.html",
    "guide/wolf-rpg-editor/index.html",
    "guide/tyranobuilder-tyranoscript-개정1/index.html",
    "guide/pixel-game-maker-mv-アクションゲームツクール-mv/index.html",
    "guide/clickteam-fusion-multimedia-fusion-작성예정/index.html",
}

TROUBLESHOOTING_PATHS = {
    "guide/자주-나오는-질문/index.html",
}

EXCLUDE_FROM_NAV_PATHS = VIRTUAL_GROUP_PAGES | {
    "guide/cmd/index.html",
    "guide/advanced-regex-rules/index.html",
    "guide/advanced-mvmz-options/index.html",
    "guide/advanced-file-formats/index.html",
    "guide/advanced-ai-local/index.html",
    "guide/mvmz/index.html",
    "guide/vxvxa/index.html",
    "guide/wolf/index.html",
    "guide/ctf/index.html",
    "guide/tyrano/index.html",
    "guide/kirikiri/index.html",
    "guide/pgmmv/index.html",
    "guide/electron/index.html",
    "guide/features-workspace-tools/index.html",
    "guide/features-engine-tools/index.html",
    "guide/features-external-tools/index.html",
    "guide/features-settings/index.html",
    "guide/winmerge-check/index.html",
}

DELETE_DIST_PATHS = (EXCLUDE_FROM_NAV_PATHS - {"guide/cmd/index.html"}) | VIRTUAL_GROUP_PAGES

ADVANCED_KEYWORDS = (
    "code:",
    "명령코드",
    "정규식",
    "이스케이프",
    "401",
    "402",
    "cmd",
    "raw",
    "json",
    "utf-16le",
    "asar",
    "appdata",
    "llama",
    "flatten",
    "include",
    "merge 101-401",
    "multiline",
    "extract names",
)

TITLE_OVERRIDES = {
    "guide/index.html": "AIMT 사용설명서",
    "guide/도구/index.html": "작업 도구",
    "guide/설정/index.html": "설정 화면",
    "guide/clickteam-fusion-multimedia-fusion-작성예정/index.html": "ClickTeam Fusion 준비 중",
    "guide/rpgmaker-명령코드-정리-작성-예정/index.html": "RPG Maker 명령 코드 참고",
    "guide/advanced-reference/index.html": "참고 자료",
    "guide/asar-47c728f5/index.html": "ASAR (Tyrano 계열)",
    "guide/asar/index.html": "ASAR (Electron)",
    "guide/라인메이커/index.html": "라인메이커 (MVMZ)",
    "guide/라인메이커-2948edda/index.html": "라인메이커 (VXVXA)",
    "guide/타이틀변경/index.html": "타이틀변경 (VXVXA)",
    "guide/타이틀-변경/index.html": "타이틀 변경 (CTF)",
    "guide/타이틀-변경-2ccdb6d4/index.html": "타이틀 변경 (Tyrano)",
    "guide/크립터/index.html": "크립터 (CTF)",
    "guide/크립터-16cf2cb1/index.html": "크립터 (PGMMV)",
}

ADVANCED_REGEX_PATHS = {
}

ADVANCED_MVMZ_PATHS = {
}

ADVANCED_FILE_PATHS = {
}

ADVANCED_AI_PATHS = {
}

ADVANCED_DIRECT_PATHS = {
    "guide/rpgmaker-명령코드-정리-작성-예정/index.html",
    "guide/같이-쓰면-좋은-도구들/index.html",
    "guide/제공자별-참고-링크/index.html",
}

FEATURE_SUBGROUP_PAGES: dict[str, str] = {
    "guide/features-screen/index.html": "화면 영역",
    "guide/features-quickslot/index.html": "퀵슬롯",
    "guide/features-reference/index.html": "기타 참고",
}

MERGED_SCREEN_PAGE_PATHS: set[str] = {
    "guide/상단부/index.html",
    "guide/중단부/index.html",
    "guide/하단부/index.html",
}

SCREEN_AREA_LINK_ONLY_PATHS: set[str] = {
    "guide/view/index.html",
}

FEATURE_SCREEN_PATHS: set[str] = set()

SCREEN_AREA_SECTIONS: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "영역① 상단부",
        "프로젝트 지정, 파일 목록 갱신, 프롬프트, 빠른번역, 설정, 화면 모드 진입처럼 작업을 시작하거나 화면 상태를 바꾸는 영역입니다.",
        "guide/assets/상단부/image.png",
        (
            ("guide/새-프로젝트-프로젝트-지정/index.html", "새 프로젝트 / 프로젝트 지정"),
            ("guide/파일목록-새로고침/index.html", "파일목록 새로고침"),
            ("guide/프롬프트/index.html", "프롬프트"),
            ("guide/빠른번역/index.html", "빠른번역"),
            ("guide/설정/index.html", "설정"),
            ("guide/view/index.html", "VIEW"),
        ),
    ),
    (
        "영역② 중단부",
        "선택한 파일과 작업 대상의 내용을 확인하는 영역입니다. 목록에서 대상을 고르고, 필요한 경우 VIEW 화면으로 세부 내용을 확인합니다.",
        "guide/assets/중단부/image 3.png",
        (
            ("guide/view/index.html", "VIEW"),
        ),
    ),
    (
        "영역③ 하단부",
        "추출, 번역, 적용, 도구, 퀵슬롯처럼 실제 작업을 실행하는 영역입니다. 작업 단계가 바뀔 때 가장 자주 사용하는 버튼들이 모여 있습니다.",
        "guide/assets/하단부/image 1.png",
        (
            ("guide/도구/index.html", "작업 도구"),
            ("guide/추출/index.html", "추출"),
            ("guide/번역/index.html", "번역"),
            ("guide/적용과-즉시적용/index.html", "적용과 즉시적용"),
            ("guide/퀵슬롯/index.html", "퀵슬롯"),
        ),
    ),
)

SETTINGS_PAGE_PATH = "guide/설정/index.html"

SETTINGS_NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "general",
        "일반",
        (
            "guide/테마/index.html",
            "guide/추출정규식/index.html",
            "guide/이스케이프패턴/index.html",
            "guide/언어패턴설정/index.html",
        ),
    ),
    (
        "translation",
        "번역설정",
        (
            "guide/번역-설정/index.html",
            "guide/ai-model/index.html",
            "guide/api-key-설정/index.html",
        ),
    ),
    (
        "mvmz",
        "MVMZ",
        (
            "guide/제외정규식-예외정규식/index.html",
            "guide/치환용어설정/index.html",
            "guide/기본폰트설정/index.html",
            "guide/타이틀텍스트/index.html",
            "guide/multiline-db/index.html",
            "guide/extract-names/index.html",
            "guide/merge-101-401/index.html",
            "guide/apply-exclude-regex-to-401-block/index.html",
            "guide/401-extract-mode/index.html",
            "guide/flatten-mode/index.html",
            "guide/include-text-type/index.html",
            "guide/include-speaker-name/index.html",
            "guide/401-block-unit-for-consistency-duplicate/index.html",
        ),
    ),
    (
        "wolf",
        "WOLF",
        (
            "guide/2차-추출-필터/index.html",
            "guide/cmd-122-2차-추출-중복처리/index.html",
        ),
    ),
    (
        "ctf",
        "CTF",
        (
            "guide/ctf-이미지-고속-추출/index.html",
            "guide/ctf-2차-추출-필터-편집/index.html",
        ),
    ),
    (
        "log-backup",
        "로그/백업",
        (
            "guide/로그-관리/index.html",
            "guide/백업-관리/index.html",
            "guide/캐시-관리/index.html",
        ),
    ),
    (
        "help",
        "도움말",
        (
            "guide/도움말/index.html",
        ),
    ),
    (
        "etc",
        "기타",
        (
            "guide/기타/index.html",
        ),
    ),
)

SETTINGS_PAGE_CHILD_PATHS: tuple[str, ...] = tuple(
    child_path
    for _group_id, _group_title, child_paths in SETTINGS_NAV_GROUPS
    for child_path in child_paths
)

SETTINGS_PAGE_CHILD_ORDER = {path: index for index, path in enumerate(SETTINGS_PAGE_CHILD_PATHS)}
SETTINGS_PAGE_CHILD_PATH_SET = set(SETTINGS_PAGE_CHILD_PATHS)

FEATURE_SETTINGS_PATHS = {
    SETTINGS_PAGE_PATH,
}

FEATURE_WORKSPACE_TOOL_PATHS = {
    "guide/도구/index.html",
    "guide/파일목록-새로고침/index.html",
    "guide/빠른번역/index.html",
    "guide/적용취소/index.html",
    "guide/번역-가져오기/index.html",
    "guide/빈칸채우기/index.html",
    "guide/사용자사전-전후처리/index.html",
    "guide/번역일관성/index.html",
    "guide/추출-중복/index.html",
    "guide/일본어체크/index.html",
    "guide/받침정리/index.html",
    "guide/코드-복원/index.html",
    "guide/세이브-에디터/index.html",
    "guide/ttc-빌드/index.html",
    "guide/vscode/index.html",
    "guide/notepad/index.html",
}

WORKSPACE_TOOL_LINK_ONLY_PATHS: set[str] = {
    "guide/파일목록-새로고침/index.html",
    "guide/빠른번역/index.html",
    "guide/빠른번역-77499184/index.html",
}

FEATURE_ENGINE_TOOL_PATHS = {
    "guide/mvmz/index.html",
    "guide/vxvxa/index.html",
    "guide/wolf/index.html",
    "guide/ctf/index.html",
    "guide/tyrano/index.html",
    "guide/kirikiri/index.html",
    "guide/pgmmv/index.html",
    "guide/electron/index.html",
    "guide/라인메이커/index.html",
    "guide/라인메이커-2948edda/index.html",
    "guide/플러그인추가/index.html",
    "guide/이름-일관성/index.html",
    "guide/통합-일관성/index.html",
    "guide/크립터-이미지-오디오/index.html",
    "guide/data-복호화/index.html",
    "guide/프로젝트-변환/index.html",
    "guide/언팩/index.html",
    "guide/타이틀변경/index.html",
    "guide/전용추출/index.html",
    "guide/imbook패치-bbtext패치-missions패치/index.html",
    "guide/mv변환/index.html",
    "guide/언팩-리팩/index.html",
    "guide/통합-치환/index.html",
    "guide/exe-패치/index.html",
    "guide/메타정보-확인/index.html",
    "guide/타이틀-변경/index.html",
    "guide/타이틀-변경-2ccdb6d4/index.html",
    "guide/언어-변경/index.html",
    "guide/크립터/index.html",
    "guide/크립터-16cf2cb1/index.html",
}

FEATURE_ENGINE_TOOL_PARENT_PATHS: tuple[str, ...] = (
    "guide/mvmz/index.html",
    "guide/vxvxa/index.html",
    "guide/wolf/index.html",
    "guide/ctf/index.html",
    "guide/tyrano/index.html",
    "guide/kirikiri/index.html",
    "guide/pgmmv/index.html",
    "guide/electron/index.html",
)

FEATURE_ENGINE_TOOL_GROUP_TITLES: dict[str, str] = {
    "guide/mvmz/index.html": "MVMZ",
    "guide/vxvxa/index.html": "VXVXA",
    "guide/wolf/index.html": "WOLF",
    "guide/ctf/index.html": "CTF",
    "guide/tyrano/index.html": "Tyrano",
    "guide/kirikiri/index.html": "Kirikiri",
    "guide/pgmmv/index.html": "PGMMV",
    "guide/electron/index.html": "Electron",
}

FEATURE_QUICKSLOT_PATHS = {
    "guide/퀵슬롯/index.html",
    "guide/메모장/index.html",
    "guide/빠른번역-77499184/index.html",
    "guide/용어사전/index.html",
}

FEATURE_QUICKSLOT_PARENT_PATHS: tuple[str, ...] = (
    "guide/퀵슬롯/index.html",
)

FEATURE_NESTED_CHILD_PATHS_BY_PARENT: dict[str, tuple[str, ...]] = {
    "guide/도구/index.html": (
        "guide/빈칸채우기/index.html",
        "guide/사용자사전-전후처리/index.html",
        "guide/적용취소/index.html",
        "guide/번역일관성/index.html",
        "guide/추출-중복/index.html",
        "guide/이스케이프/index.html",
        "guide/일본어체크/index.html",
        "guide/받침정리/index.html",
        "guide/vscode/index.html",
        "guide/notepad/index.html",
        "guide/appdata/index.html",
        "guide/ttc-빌드/index.html",
        "guide/세이브-에디터/index.html",
        "guide/llama-server/index.html",
    ),
    "guide/mvmz/index.html": (
        "guide/라인메이커/index.html",
        "guide/플러그인추가/index.html",
        "guide/401-병합-분할/index.html",
        "guide/402-동기화/index.html",
        "guide/이름-일관성/index.html",
        "guide/통합-일관성/index.html",
        "guide/코드-복원/index.html",
        "guide/번역-가져오기/index.html",
        "guide/이스케이프-data/index.html",
        "guide/크립터-이미지-오디오/index.html",
        "guide/data-복호화/index.html",
        "guide/프로젝트-변환/index.html",
    ),
    "guide/vxvxa/index.html": (
        "guide/언팩/index.html",
        "guide/타이틀변경/index.html",
        "guide/라인메이커-2948edda/index.html",
        "guide/전용추출/index.html",
        "guide/imbook패치-bbtext패치-missions패치/index.html",
        "guide/mv변환/index.html",
    ),
    "guide/wolf/index.html": (
        "guide/언팩-리팩/index.html",
        "guide/통합-치환/index.html",
        "guide/exe-패치/index.html",
        "guide/raw-파일명-치환/index.html",
    ),
    "guide/ctf/index.html": (
        "guide/메타정보-확인/index.html",
        "guide/타이틀-변경/index.html",
        "guide/언어-변경/index.html",
        "guide/크립터/index.html",
    ),
    "guide/tyrano/index.html": (
        "guide/asar-47c728f5/index.html",
        "guide/타이틀-변경-2ccdb6d4/index.html",
    ),
    "guide/kirikiri/index.html": (
        "guide/utf-16le-변환/index.html",
    ),
    "guide/pgmmv/index.html": (
        "guide/크립터-16cf2cb1/index.html",
    ),
    "guide/electron/index.html": (
        "guide/asar/index.html",
    ),
    "guide/퀵슬롯/index.html": (
        "guide/메모장/index.html",
        "guide/빠른번역-77499184/index.html",
        "guide/용어사전/index.html",
    ),
}

WORKSPACE_TOOL_NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "workspace-utilities",
        "유틸리티",
        (
            "guide/빈칸채우기/index.html",
            "guide/사용자사전-전후처리/index.html",
            "guide/적용취소/index.html",
            "guide/번역일관성/index.html",
            "guide/추출-중복/index.html",
            "guide/이스케이프/index.html",
            "guide/일본어체크/index.html",
            "guide/받침정리/index.html",
        ),
    ),
    (
        "workspace-shortcuts",
        "바로가기",
        (
            "guide/vscode/index.html",
            "guide/notepad/index.html",
            "guide/appdata/index.html",
        ),
    ),
    (
        "workspace-engine-tools",
        "엔진별 보조 도구",
        (),
    ),
    (
        "workspace-etc",
        "기타",
        (
            "guide/ttc-빌드/index.html",
            "guide/세이브-에디터/index.html",
            "guide/llama-server/index.html",
        ),
    ),
)

FEATURE_NESTED_PARENT_PATHS = set(FEATURE_NESTED_CHILD_PATHS_BY_PARENT)
FEATURE_NESTED_CHILD_PATHS = {
    child_path
    for child_paths in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.values()
    for child_path in child_paths
}
FEATURE_NESTED_CHILD_ORDER_BY_PARENT = {
    parent_path: {child_path: index for index, child_path in enumerate(child_paths)}
    for parent_path, child_paths in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.items()
}

FEATURE_REFERENCE_PATHS = {
    "guide/추출-파일별-설명/index.html",
    "guide/2차-추출-필터/index.html",
    "guide/ctf-이미지-고속-추출/index.html",
    "guide/ctf-2차-추출-필터-편집/index.html",
}

PHRASE_REPLACEMENTS = {
    "현재 코드 기준으로": "현재 버전에서는",
    "현재 코드 기준": "현재 버전 기준",
    "내부적으로": "프로그램에서는",
    "raw state": "최근 추출 결과",
    "스레드": "동시 처리",
    "하드코딩된 텍스트": "자동 추출되지 않는 텍스트",
    "plugins/js 내부의 .js 파일을 직접 열고 고쳐주시길 바랍니다.": "자동 추출되지 않는 문구는 별도 편집이 필요할 수 있습니다.",
    "본 가이드는": "이 문서는",
    "작성예정": "준비 중",
    "작성 예정": "준비 중",
    "이에 대한 모든 책임은 사용자에게 있으며, 당 프로그램은 그에 대한 책임을 지지 않습니다.": "여러 키를 함께 사용할 때는 제공자의 이용 약관과 할당량 정책을 먼저 확인하세요.",
    "현재 버전에서는는": "현재 버전에서는",
    "메세지": "메시지",
    "유저": "사용자",
    "체크합니다": "확인합니다",
    "체크하세요": "확인하세요",
    "체크해야 합니다": "확인해야 합니다",
    "클릭합니다": "선택합니다",
    "클릭하세요": "선택하세요",
    "할 수 있습니다.": "할 수 있습니다.",
    "문서 기준으로 단정해서 말하긴 어렵지만, ": "",
    "다만 내부 경로에 따라 우선 순서 해석이 조금 다를 수 있어 정확한 대표 키 선택 순서는 <code>확인 필요</code>입니다.": "주로 사용할 키는 알아보기 쉽게 정리해 두는 편이 좋습니다.",
    "코드상 권장값": "권장값",
}

DUPLICATE_TEMPLATE_SECTION_TITLES = {
    # Cleanup-only list. This is not the writing standard itself.
    # The standard is documented in docs/guide-writing-standards.md and
    # implemented by PAGE_TYPE_TEMPLATES / PAGE_METADATA / PAGE_TYPE_BY_PATH.
    "이 설명서에서 할 수 있는 일",
    "처음 시작할 때 정할 것",
    "엔진별 시작 경로",
    "자주 찾는 작업",
    "작업 전 주의사항",
    "이 영역에서 확인할 수 있는 것",
    "처음이라면",
    "무엇을 할 수 있나요?",
    "이 기능은 무엇인가요?",
    "이 단계의 목적",
    "이 단계는 무엇인가요?",
    "이 엔진에서 확인할 것",
    "이 참고 문서의 범위",
    "언제 필요한가요?",
    "언제 사용하나요?",
    "언제 진행하나요?",
    "언제 이 문서를 보나요?",
    "먼저 확인할 것",
    "시작 전에 확인할 것",
    "사용 전 확인할 것",
    "바로 이동",
    "따라 하기",
    "진행 순서",
    "기본 사용 순서",
    "문제 해결 순서",
    "화면과 항목",
    "질문과 답변",
    "참고 내용",
    "명령 코드 참고",
    "완료 후 확인",
    "완료 기준",
    "결과 확인 방법",
    "주의/중요/권장",
    "알아둘 점",
    "자주 헷갈리는 점",
    "그래도 해결되지 않을 때",
}


def _escape(value: str) -> str:
    return html.escape(value, quote=False)


def _p(value: str) -> str:
    return f"<p>{_escape(value)}</p>"


def _ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ul>"


def _ol(items: list[str]) -> str:
    return "<ol>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ol>"


def _doc_version() -> str:
    return f'<p class="doc-version">{DOC_VERSION}</p>'


def _section(title: str, body: str) -> str:
    return f"<h2>{_escape(title)}</h2>\n{body}"


def _notice(level: str, message: str) -> str:
    return f"<p><strong>{_escape(level)}:</strong> {_escape(message)}</p>"


def _link(path: str, title: str, from_path: Path | None = None) -> str:
    href = edit_guide.relative_href(from_path or (GUIDE_ROOT / "index.html"), path, DIST_ROOT)
    return f'<a href="{href}">{_escape(title)}</a>'


def _strip_tags(value: str) -> str:
    return re.sub(r"\s+", " ", edit_guide.strip_tags(value)).strip()


def _clean_html(value: str) -> str:
    cleaned = value
    for old, new in PHRASE_REPLACEMENTS.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"(?is)</?article\b[^>]*>", "", cleaned)
    cleaned = _simplify_card_markup(cleaned)
    cleaned = re.sub(r"(?is)<h1\b[^>]*>.*?</h1>", "", cleaned, count=1)
    cleaned = re.sub(r"(?is)<p\b[^>]*class=[\"'][^\"']*doc-version[^\"']*[\"'][^>]*>.*?</p>", "", cleaned, count=1)
    cleaned = re.sub(r"(?is)<p\b[^>]*>\s*(?:문서 기준|사용설명서 리뉴얼 기준):.*?최종 편집 일시:.*?</p>", "", cleaned)
    cleaned = _polish_content_markup(cleaned)
    cleaned = _remove_excluded_links(cleaned)
    cleaned = re.sub(r"(?is)<p>\s*(?:문서 기준|사용설명서 리뉴얼 기준):.*?최종 편집 일시:.*?</p>", "", cleaned)
    cleaned = cleaned.replace(f"<p>{ADVANCED_INTRO}</p>", "")
    cleaned = cleaned.replace(ADVANCED_INTRO, "")
    cleaned = _unwrap_existing_manual(cleaned)
    cleaned = re.sub(r"귀책사유\s*\(ex\..*?\)\s*가 될 수 있습니다\.", "이용 약관 위반 사유로 판단될 수 있습니다.", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = cleaned.replace("귀책사유", "이용 약관 위반 사유")
    cleaned = cleaned.replace("현재 버전에서는는", "현재 버전에서는")
    cleaned = re.sub(r"(?is)<p\b[^>]*>\s*(?:<br\s*/?>)?\s*</p>", "", cleaned)
    cleaned = cleaned.replace("※", "<strong>주의:</strong>")
    return cleaned.strip()


def _simplify_card_markup(value: str) -> str:
    def replace_bookmark(match: re.Match[str]) -> str:
        attrs = match.group(1)
        body = match.group(2)
        href_match = re.search(r"href=[\"']([^\"']+)[\"']", attrs, flags=re.IGNORECASE)
        title_match = re.search(r"(?is)<div\b[^>]*class=[\"'][^\"']*bookmark-title[^\"']*[\"'][^>]*>(.*?)</div>", body)
        title = _strip_tags(title_match.group(1)) if title_match else _strip_tags(body)
        href = href_match.group(1) if href_match else "#"
        label = title or href
        return f'<p><a href="{html.escape(href, quote=True)}">{_escape(label)}</a></p>'

    simplified = re.sub(
        r"(?is)<a\b([^>]*class=[\"'][^\"']*bookmark[^\"']*[\"'][^>]*)>(.*?)</a>",
        replace_bookmark,
        value,
    )
    simplified = re.sub(r"(?is)<img\b[^>]*(?:notion-static-icon|notion\.so/icons|/icons/)[^>]*>", "", simplified)
    simplified = re.sub(r"(?is)<span\b[^>]*class=[\"'][^\"']*notion-static-icon[^\"']*[\"'][^>]*>.*?</span>", "", simplified)
    simplified = re.sub(r"(?is)<div\b[^>]*class=[\"'][^\"']*notion-static-icon[^\"']*[\"'][^>]*>.*?</div>", "", simplified)
    simplified = re.sub(r"(?is)\sclass=[\"'][^\"']*(?:card|callout|panel|bookmark)[^\"']*[\"']", "", simplified)
    return simplified


def _polish_content_markup(value: str) -> str:
    polished = re.sub(r"(?is)<figure\b[^>]*>(.*?)</figure>", r"\1", value)
    polished = re.sub(r"(?is)</?div\b[^>]*>", "", polished)
    polished = re.sub(r"(?is)<summary\b[^>]*>", "<summary>", polished)
    polished = re.sub(r"(?is)<hr\b[^>]*>", "<hr>", polished)
    polished = re.sub(r"\s(?:id|class|style|dir)=[\"'][^\"']*[\"']", "", polished)
    polished = re.sub(r"(?is)<p>\s*</p>", "", polished)
    return polished


def _remove_excluded_links(value: str) -> str:
    markers: list[str] = []
    for path in EXCLUDE_FROM_NAV_PATHS:
        slug = path.removeprefix("guide/").removesuffix("/index.html")
        markers.extend([slug, quote(slug)])
    cleaned = value
    for marker in markers:
        cleaned = re.sub(
            rf"(?is)<a\b[^>]*href=[\"'][^\"']*{re.escape(marker)}(?:/index\.html)?[^\"']*[\"'][^>]*>.*?</a>",
            "",
            cleaned,
        )
    return cleaned


def _drop_duplicate_standard_sections(value: str) -> str:
    matches = list(re.finditer(r"(?is)<h2\b[^>]*>(.*?)</h2>", value))
    if not matches:
        return value

    chunks: list[str] = [value[: matches[0].start()]]
    for index, match in enumerate(matches):
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        title = _strip_tags(match.group(1))
        if title in DUPLICATE_TEMPLATE_SECTION_TITLES:
            continue
        chunks.append(value[match.start() : section_end])
    return "".join(chunks).strip()


def _unwrap_existing_manual(value: str) -> str:
    markers = [r"<h2[^>]*>\s*항목별 설명\s*</h2>", r"<h2[^>]*>\s*고급 사용자 참고\s*</h2>", r"<h2[^>]*>\s*질문과 답변\s*</h2>"]
    starts: list[tuple[int, int]] = []
    for marker in markers:
        starts.extend((match.start(), match.end()) for match in re.finditer(marker, value, flags=re.IGNORECASE))
    if not starts:
        return value
    _start, body_start = sorted(starts)[-1]
    tail = value[body_start:]
    stop = re.search(
        r"(?is)<h2[^>]*>\s*(?:결과 확인 방법|알아둘 점|자주 헷갈리는 점|주의|그래도 해결되지 않을 때)\s*</h2>",
        tail,
    )
    return tail[: stop.start()] if stop else tail


def _replace_article_safe(text: str, article: str) -> str:
    clean = re.sub(r"\s*contenteditable=[\"']true[\"']", "", article, flags=re.IGNORECASE)
    clean = clean.replace(" is-selected-image", "")
    main_re = re.compile(r"(?is)(<main\b[^>]*class=[\"'][^\"']*content-shell[^\"']*[\"'][^>]*>).*?(</main>)")
    return main_re.sub(lambda match: f"{match.group(1)}\n{clean}\n{match.group(2)}", text, count=1)


def _source_text_for(path: str, fallback: str) -> str:
    git_path = f"HEAD:dist/{path}"
    try:
        completed = subprocess.run(
            ["git", "show", git_path],
            cwd=DIST_ROOT.parent,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return completed.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return fallback


PAGE_TYPE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "home": ("manual_scope", "start_decision", "core_workflow", "engine_routes", "frequent_tasks", "safe_use"),
    "hub": ("area_goal", "direct_links", "suggested_path"),
    "feature": ("task_goal", "use_cases", "readiness", "procedure", "details", "verification", "decision_notes", "common_mistakes"),
    "workflow": ("step_goal", "entry_conditions", "readiness", "procedure", "details", "done_definition"),
    "engine": ("engine_scope", "engine_fit", "readiness", "procedure", "details", "verification", "decision_notes"),
    "troubleshooting": ("triage", "diagnosis_steps", "faq_content", "support_packet"),
    "advanced_reference": ("reference_scope", "change_guard", "reference_content"),
    "command_reference": ("command_scope", "change_guard", "command_content"),
}

PAGE_TYPE_BY_PATH: dict[str, str] = {
    "guide/index.html": "home",
    "guide/자주-나오는-질문/index.html": "troubleshooting",
    "guide/rpgmaker-명령코드-정리-작성-예정/index.html": "command_reference",
}

PAGE_METADATA: dict[str, dict[str, Any]] = {
    "guide/index.html": {
        "title": "AIMT 사용설명서",
        "about": "AIMT는 게임 파일에서 번역할 문장을 추출하고, AI 또는 번역 서비스를 이용해 번역한 뒤, 결과를 다시 게임에 적용하도록 돕는 프로그램입니다.",
        "first_steps": [
            "번역할 게임 형식을 확인합니다.",
            "AIMT에서 프로젝트 폴더를 지정합니다.",
            "AI 번역을 사용할 경우 API 키와 사용할 모델을 준비합니다.",
            "추출할 언어와 번역 방향을 확인합니다.",
            "작은 범위로 추출, 번역, 적용을 시험합니다.",
            "게임을 실행해 결과를 확인한 뒤 전체 작업을 진행합니다.",
        ],
        "flow_intro": "AIMT의 일반적인 작업 순서는 <strong>프로젝트 지정 → 추출 → 번역 → 적용 → 게임 실행 확인</strong>입니다.",
        "basic_flow": [
            "프로젝트 지정: 작업 결과를 저장할 AIMT 프로젝트를 선택합니다.",
            "추출: 게임 파일에서 번역 대상 문구를 찾습니다.",
            "번역: 추출된 문구를 선택한 번역 방식으로 번역합니다.",
            "적용: 번역 결과를 게임 프로젝트에 반영합니다.",
            "확인: 게임을 실행해 누락, 깨짐, 오역, 적용 실패를 점검합니다.",
        ],
        "engine_links": [
            ("guide/rpg-maker-mvmz-개정1/index.html", "RPG Maker MV/MZ"),
            ("guide/rpg-maker-vxvxa-개정1/index.html", "RPG Maker VX/VXA"),
            ("guide/wolf-rpg-editor/index.html", "WOLF RPG Editor"),
            ("guide/tyranobuilder-tyranoscript-개정1/index.html", "TyranoBuilder/TyranoScript"),
            ("guide/pixel-game-maker-mv-アクションゲームツクール-mv/index.html", "Pixel Game Maker MV"),
        ],
        "frequent_links": [
            ("guide/api-key-설정/index.html", "API KEY 설정"),
            ("guide/ai-model/index.html", "AI-MODEL"),
            ("guide/번역-설정/index.html", "번역 설정"),
            ("guide/추출/index.html", "추출"),
            ("guide/번역/index.html", "번역"),
            ("guide/적용과-즉시적용/index.html", "적용과 즉시적용"),
            ("guide/자주-나오는-질문/index.html", "자주 나오는 질문"),
        ],
        "notices": [("주의", "게임 형식마다 추출 가능한 텍스트와 적용 방식이 다릅니다. 처음 작업하는 형식은 엔진별 가이드를 먼저 확인하세요.")],
    },
    "guide/도구/index.html": {
        "summary": "작업 도구는 번역 작업 중 텍스트를 정리하거나 결과를 점검할 때 쓰는 보조 기능을 모은 화면입니다.",
        "when": ["번역 결과를 점검하거나 정리할 때", "사용자사전, 일관성, 코드 복원처럼 보조 기능이 필요할 때", "엔진별 보조 도구로 이동해야 할 때"],
        "before": ["작업 중인 프로젝트가 올바르게 지정되어 있는지 확인합니다.", "어떤 파일이나 결과를 수정하려는지 먼저 확인합니다.", "결과를 되돌려야 할 수 있다면 작업 전 파일을 보관합니다."],
        "steps": ["필요한 도구 묶음을 확인합니다.", "사용할 기능 문서로 이동합니다.", "기능별 안내에 따라 실행합니다.", "완료 메시지와 결과 파일을 확인합니다."],
    },
    "guide/api-key-설정/index.html": {
        "summary": "API KEY 설정은 Gemini, OpenAI, Claude, DeepSeek, OpenRouter, DeepL 같은 번역 제공자에 접속하기 위한 인증 정보를 등록하고 관리하는 화면입니다.",
        "when": ["AI 번역 또는 DeepL 번역을 처음 준비할 때", "기존 키를 새 키로 교체할 때", "번역 요청이 인증 오류로 실패할 때", "여러 키의 사용 여부를 켜거나 끌 때"],
        "before": ["API 키는 각 제공자 계정에서 직접 발급해야 합니다.", "어떤 모델을 쓸지는 AI-MODEL 또는 번역 설정에서 따로 선택합니다.", "무료 키를 여러 개 동시에 사용하는 경우 제공자의 이용 약관과 할당량 정책을 먼저 확인하세요."],
        "steps": ["제공자 종류를 선택합니다.", "키 입력 영역에 발급받은 값을 붙여 넣습니다.", "사용할 키의 ON/OFF 상태를 확인합니다.", "저장합니다.", "빠른번역이나 일반 번역으로 정상 동작을 확인합니다."],
        "result": ["저장 후 오류 메시지가 없는지 확인합니다.", "빠른번역에서 짧은 문장을 번역해 키가 정상인지 확인합니다.", "실패하면 키 값, 제공자 선택, 모델 선택, 네트워크 상태를 순서대로 확인합니다."],
        "notices": [("주의", "API 키는 개인 인증 정보입니다. 공개 문서, 스크린샷, 커뮤니티 글에 그대로 노출하지 마세요.")],
        "confusion": [("API 키를 넣었는데 모델이 바뀌지 않습니다", "API KEY 설정은 인증 정보 관리 화면입니다. 사용할 모델은 AI-MODEL 또는 번역 설정에서 따로 확인하세요.")],
    },
    "guide/ai-model/index.html": {
        "summary": "AI-MODEL은 번역에 사용할 제공자와 모델을 선택하는 화면입니다.",
        "when": ["처음 AI 번역 환경을 준비할 때", "번역 품질, 속도, 비용을 바꾸고 싶을 때", "오류가 나는 모델을 다른 모델로 바꿀 때"],
        "before": ["API KEY 설정에 사용할 제공자의 키가 준비되어 있어야 합니다.", "모델마다 지원 기능과 비용이 다를 수 있습니다.", "로컬 모델을 사용할 경우 로컬 서버 상태를 먼저 확인합니다."],
        "steps": ["사용할 제공자를 선택합니다.", "메인 모델을 선택합니다.", "필요하면 예비 모델을 선택합니다.", "저장한 뒤 짧은 문장으로 번역을 시험합니다."],
        "result": ["번역 설정과 빠른번역에서 선택한 모델이 사용되는지 확인합니다.", "오류가 나면 API 키, 모델명, 제공자 상태를 순서대로 확인합니다."],
    },
    "guide/번역-설정/index.html": {
        "summary": "번역 설정은 어떤 번역 방식과 모델을 사용할지, 번역 결과를 어떤 방식으로 처리할지 정하는 핵심 설정입니다.",
        "when": ["처음 번역 환경을 준비할 때", "번역 품질이나 속도를 조정하고 싶을 때", "모델을 바꿨는데 결과가 달라지는 이유를 확인할 때", "프롬프트, 용어사전, 번역 범위를 함께 점검할 때"],
        "before": ["API KEY 설정에 사용할 키가 등록되어 있어야 합니다.", "AI-MODEL에서 사용할 제공자와 모델을 확인해야 합니다.", "게임 형식별 추출 설정이 번역 대상에 영향을 줄 수 있습니다."],
        "steps": ["번역 엔진과 모델을 확인합니다.", "원문 언어와 번역 언어를 확인합니다.", "프롬프트, 용어사전, 후처리 옵션을 필요한 만큼 조정합니다.", "짧은 문장 또는 일부 파일로 먼저 테스트합니다.", "결과가 안정적이면 전체 번역을 진행합니다."],
        "result": ["빠른번역으로 짧은 문장을 시험합니다.", "일부 파일만 번역해 문체와 용어가 유지되는지 봅니다.", "오류가 나면 API 키, 모델 선택, 요청 제한, 네트워크 상태를 확인합니다."],
        "notices": [("중요", "번역 설정은 이후 번역 작업에 영향을 줍니다. 이미 번역된 결과 파일은 설정을 바꿔도 자동으로 다시 번역되지 않습니다.")],
    },
    "guide/추출/index.html": {
        "summary": "추출은 게임 파일에서 번역할 수 있는 텍스트를 찾아 작업용 파일로 준비하는 단계입니다.",
        "when": ["새 프로젝트를 시작할 때", "게임 파일이 바뀐 뒤 번역 대상을 다시 만들 때", "누락된 문장이 있는지 확인할 때"],
        "before": ["프로젝트 폴더가 올바른지 확인합니다.", "게임 형식에 맞는 엔진별 가이드를 확인합니다.", "이전 추출 결과를 덮어쓸 수 있으므로 필요한 파일을 보관합니다."],
        "steps": ["프로젝트와 게임 형식을 확인합니다.", "추출 옵션을 확인합니다.", "추출을 실행합니다.", "완료 메시지와 생성된 파일을 확인합니다."],
        "result": ["추출 결과 목록에 번역 대상이 표시되는지 확인합니다.", "예상보다 항목이 적으면 엔진별 제한과 추출 옵션을 확인합니다."],
    },
    "guide/번역/index.html": {
        "summary": "번역은 추출된 원문을 선택한 번역 방식으로 번역하는 단계입니다.",
        "when": ["추출 결과가 준비되었을 때", "일부 파일만 다시 번역할 때", "번역 설정을 바꾼 뒤 결과를 새로 만들 때"],
        "before": ["API 키, 모델, 번역 설정을 확인합니다.", "원문 언어와 결과 언어를 확인합니다.", "먼저 작은 범위로 테스트할 준비를 합니다."],
        "steps": ["번역할 파일이나 범위를 선택합니다.", "번역 설정을 확인합니다.", "번역을 실행합니다.", "오류 메시지와 생성 결과를 확인합니다."],
        "result": ["번역 결과 파일이 생성되었는지 확인합니다.", "일부 문장을 열어 용어와 문체가 유지되는지 확인합니다.", "오류가 나면 키, 모델, 요청 제한을 확인합니다."],
    },
    "guide/적용과-즉시적용/index.html": {
        "summary": "적용과 즉시적용은 번역 결과를 게임 프로젝트에 반영하는 단계입니다.",
        "when": ["번역 결과를 실제 게임에서 확인하려 할 때", "일부 결과만 빠르게 반영해야 할 때", "적용 후 문제가 생겨 다시 확인해야 할 때"],
        "before": ["번역 결과가 준비되어 있어야 합니다.", "게임을 실행 중이라면 파일 잠금 문제가 없는지 확인합니다.", "되돌릴 수 있도록 적용 전 파일을 보관합니다."],
        "steps": ["적용할 결과와 대상 프로젝트를 확인합니다.", "적용 또는 즉시적용을 선택합니다.", "완료 메시지를 확인합니다.", "게임을 실행해 실제 화면을 확인합니다."],
        "result": ["게임 화면에 번역문이 반영되었는지 확인합니다.", "깨짐, 누락, 적용 실패가 있으면 적용 대상과 엔진별 제한을 확인합니다."],
    },
    "guide/빠른번역/index.html": {
        "summary": "빠른번역은 짧은 문장이나 일부 내용을 빠르게 번역해 설정과 모델 상태를 확인하는 기능입니다.",
        "when": ["API 키와 모델이 정상인지 시험할 때", "짧은 문장을 즉시 번역해야 할 때", "전체 번역 전에 문체와 용어를 확인할 때"],
        "before": ["API 키와 모델이 준비되어 있어야 합니다.", "원문 언어와 결과 언어를 확인합니다.", "프롬프트나 용어사전이 결과에 영향을 줄 수 있습니다."],
        "steps": ["번역할 문장을 입력합니다.", "사용할 번역 방식과 모델을 확인합니다.", "빠른번역을 실행합니다.", "결과와 오류 메시지를 확인합니다."],
        "result": ["짧은 문장이 정상 번역되는지 확인합니다.", "실패하면 API 키, 모델, 네트워크 상태를 확인합니다."],
    },
    "guide/자주-나오는-질문/index.html": {
        "before": ["프로젝트 폴더가 올바른지 확인합니다.", "추출, 번역, 적용 중 어느 단계에서 문제가 생겼는지 구분합니다.", "오류 메시지가 있다면 문구를 그대로 확인합니다.", "API 관련 문제는 키, 모델, 사용량, 네트워크를 순서대로 확인합니다."],
        "steps": ["최근에 바꾼 설정을 확인합니다.", "작은 범위로 다시 실행해 같은 문제가 반복되는지 확인합니다.", "화면에 표시된 오류 메시지와 작업 단계를 함께 확인합니다.", "엔진별 가이드에서 해당 형식의 제한 사항을 확인합니다."],
        "followup": "문의할 때는 사용한 AIMT 버전, 게임 형식, 어느 단계에서 실패했는지, 표시된 오류 메시지, 재현 순서를 함께 정리하면 원인을 더 빠르게 찾을 수 있습니다.",
    },
}


def _infer_page_type(path: str, title: str) -> str:
    if path in PAGE_TYPE_BY_PATH:
        return PAGE_TYPE_BY_PATH[path]
    if path in GROUP_PAGES or path in ADVANCED_SUBGROUP_PAGES or path in SETTING_REFERENCE_GROUP_PAGES or path in FEATURE_SUBGROUP_PAGES:
        return "hub"
    if path in WORKFLOW_PATHS:
        return "workflow"
    if path in ENGINE_PATHS:
        return "engine"
    if title.lower().startswith("code:"):
        return "command_reference"
    if path in ADVANCED_DIRECT_PATHS or _is_advanced(path, title):
        return "advanced_reference"
    return "feature"


def _default_summary(page_type: str, title: str) -> str:
    title_lower = title.lower()
    if page_type == "advanced_reference":
        return f"{title}은 일반 작업 흐름보다 세밀한 설정이나 파일 내용을 확인할 때 참고하는 문서입니다."
    if page_type == "command_reference":
        return f"{title}은 RPG Maker 이벤트 명령을 확인하거나 번역 결과의 명령 구조를 점검할 때 참고하는 문서입니다."
    if page_type == "engine" or any(word in title_lower for word in ("mvmz", "vxvxa", "wolf", "tyrano", "pgmmv", "ctf", "kirikiri", "electron")):
        return f"{title}은 해당 형식의 게임에서 추출, 번역, 적용을 진행할 때 필요한 준비와 주의사항을 안내합니다."
    if "설정" in title:
        return f"{title}은 AIMT의 동작 방식과 번역 결과에 영향을 주는 값을 확인하고 조정하는 화면입니다."
    if "번역" in title:
        return f"{title}은 추출된 원문을 원하는 언어로 바꾸거나 번역 결과를 확인할 때 사용하는 기능입니다."
    if "추출" in title:
        return f"{title}은 게임 파일에서 번역할 수 있는 텍스트를 찾아 작업용 파일로 준비하는 기능입니다."
    if "적용" in title:
        return f"{title}은 번역 결과를 게임 프로젝트에 반영하거나 반영 전 상태를 확인할 때 사용하는 기능입니다."
    return f"{title}은 AIMT 사용 중 필요한 작업을 더 정확하게 진행하기 위한 기능입니다."


def _default_metadata(page_type: str, title: str) -> dict[str, Any]:
    if page_type == "workflow":
        return {
            "summary": _default_summary(page_type, title),
            "when": ["새 프로젝트를 시작할 때", "이전 단계의 결과가 준비되었을 때", "번역 결과를 실제 게임에서 확인하기 전후에 필요한 상태를 점검할 때"],
            "before": ["작업 대상 게임과 AIMT 프로젝트가 올바르게 지정되어 있어야 합니다.", "이전 단계에서 오류가 없었는지 확인합니다.", "필요하면 작업 전 파일을 보관합니다."],
            "steps": ["대상 프로젝트를 확인합니다.", "필요한 파일이나 옵션을 선택합니다.", "기능을 실행합니다.", "완료 메시지와 생성 결과를 확인합니다.", "문제가 있으면 설정을 조정한 뒤 같은 단계를 다시 실행합니다."],
            "result": ["목록에 새 파일이나 결과가 표시되는지 확인합니다.", "오류 메시지가 있으면 메시지 내용과 대상 파일을 함께 확인합니다.", "적용 단계 이후에는 게임을 실행해 실제 화면에서 번역 결과를 확인합니다."],
        }
    if page_type == "engine":
        return {
            "summary": _default_summary(page_type, title),
            "when": ["해당 형식의 게임을 처음 작업할 때", "추출 또는 적용 방식이 다른 형식과 다를 때", "엔진별 제한 때문에 결과가 예상과 다를 때"],
            "before": ["게임 형식이 이 문서와 맞는지 확인합니다.", "원본 게임 파일을 보관합니다.", "먼저 작은 범위로 추출, 번역, 적용을 시험합니다."],
            "steps": ["게임 형식과 프로젝트 위치를 확인합니다.", "엔진별 추출 옵션을 확인합니다.", "추출, 번역, 적용 순서로 진행합니다.", "게임 실행 화면에서 결과를 확인합니다."],
            "result": ["해당 엔진의 실제 게임 화면에서 번역문을 확인합니다.", "누락되거나 깨진 문장이 있으면 엔진별 제한과 고급 옵션을 확인합니다."],
            "notices": [("주의", "엔진별 파일 구조와 적용 방식이 다르므로 다른 엔진 문서의 절차를 그대로 적용하지 마세요.")],
        }
    return {
        "summary": _default_summary(page_type, title),
        "when": ["작업 중 이 기능의 역할을 확인해야 할 때", "어떤 항목을 선택해야 하는지 판단해야 할 때", "실행 후 결과가 맞는지 확인할 기준이 필요할 때"],
        "before": ["작업 중인 프로젝트가 올바르게 지정되어 있는지 확인합니다.", "이 기능이 현재 작업 흐름에서 필요한 단계인지 확인합니다.", "결과를 되돌려야 할 수 있다면 작업 전 파일을 보관합니다."],
        "steps": ["현재 작업 중인 프로젝트와 대상 게임 형식을 확인합니다.", "필요한 설정값이나 선택 항목을 확인합니다.", "기능을 실행합니다.", "화면에 표시되는 완료 메시지, 오류 메시지, 생성 파일을 확인합니다.", "결과가 예상과 다르면 관련 설정을 조정한 뒤 다시 실행합니다."],
        "result": ["화면에 표시되는 완료 메시지와 오류 메시지를 확인합니다.", "생성되거나 수정된 파일이 예상 위치에 있는지 확인합니다.", "번역 결과가 게임 실행 또는 미리보기에서 자연스럽게 보이는지 확인합니다."],
        "notes": ["이 문서는 사용자가 직접 조작하거나 판단해야 하는 항목을 중심으로 설명합니다.", "정규식, 명령 코드, 파일 구조처럼 세밀한 내용은 설정 화면이나 관련 기능 문서에서 확인합니다.", "작업 결과가 달라졌다면 최근에 바꾼 설정과 대상 파일을 먼저 확인하세요."],
        "confusion": [
            ("설정을 바꿨는데 결과가 바로 바뀌지 않습니다", "일부 설정은 다음 추출, 다음 번역, 다음 적용 단계부터 반영됩니다. 이미 만들어진 결과 파일은 필요한 경우 다시 생성해야 합니다."),
            ("어떤 문서를 먼저 읽어야 하나요?", "처음 사용하는 기능이라면 기본 사용 순서를 먼저 확인하고, 세부 값이 필요한 경우 화면/항목 설명을 이어서 확인하세요."),
        ],
    }


def _metadata_for(path: str, title: str, page_type: str) -> dict[str, Any]:
    metadata = _default_metadata(page_type, title)
    metadata.update(PAGE_METADATA.get(path, {}))
    return metadata


def _external_link(url: str, label: str, description: str) -> str:
    return f'<li><a href="{html.escape(url, quote=True)}">{_escape(label)}</a> - {_escape(description)}</li>'


def _external_reference_content() -> str:
    links = [
        ("https://aistudio.google.com/app/apikey", "Gemini API 키", "Google AI Studio에서 Gemini API 키를 만들거나 확인합니다."),
        ("https://ai.google.dev/gemini-api/docs/api-key", "Gemini API 키 문서", "Gemini API 키 사용 방법과 인증 방식을 확인합니다."),
        ("https://platform.openai.com/api-keys", "OpenAI API Keys", "OpenAI API 키를 만들고 관리합니다."),
        ("https://developers.openai.com/api/docs/quickstart", "OpenAI API Quickstart", "OpenAI API 키 준비와 첫 요청 흐름을 확인합니다."),
        ("https://platform.claude.com/", "Claude Console", "Claude API 사용을 위한 콘솔에 접속합니다."),
        ("https://openrouter.ai/settings/keys", "OpenRouter API Keys", "OpenRouter API 키를 만들고 사용량 제한을 관리합니다."),
        ("https://openrouter.ai/docs/api/reference/authentication", "OpenRouter 인증 문서", "OpenRouter API 키와 Bearer 인증 방식을 확인합니다."),
        ("https://platform.deepseek.com/api_keys", "DeepSeek API Keys", "DeepSeek API 키를 만들고 관리합니다."),
        ("https://api-docs.deepseek.com/api/deepseek-api", "DeepSeek 인증 문서", "DeepSeek API 인증과 호출 방식을 확인합니다."),
        ("https://developers.deepl.com/docs/getting-started/auth", "DeepL 인증 문서", "DeepL API 인증 키 확인 위치와 보안 주의사항을 확인합니다."),
        ("https://developers.deepl.com/docs/getting-started/managing-api-keys", "DeepL API 키 관리", "DeepL API 키 생성, 사용량, 제한 설정을 확인합니다."),
        ("https://docs.litellm.ai/docs/providers", "LiteLLM Providers", "제공자별 모델 연결 방식과 표기 방식을 확인합니다."),
        ("https://litellm.vercel.app/docs/providers/openai", "LiteLLM OpenAI 제공자 문서", "OpenAI 제공자 관련 이미지나 설명의 출처로 참고합니다."),
    ]
    return "<ul>" + "".join(_external_link(url, label, description) for url, label, description in links) + "</ul>"


def _render_links(links: list[tuple[str, str]], from_path: Path | None = None) -> str:
    return "<ul>" + "".join(f"<li>{_link(link_path, text, from_path)}</li>" for link_path, text in links) + "</ul>"


def _title_for_path(path: str) -> str:
    if path in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[path]
    html_path = DIST_ROOT / path
    try:
        return edit_guide.parse_title(edit_guide.read_text(html_path), html_path.parent.name)
    except FileNotFoundError:
        return Path(path).parent.name


def _settings_group_links(child_paths: tuple[str, ...], from_path: Path) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for child_path in child_paths:
        if (DIST_ROOT / child_path).exists():
            links.append((child_path, _title_for_path(child_path)))
    return links


def _first_link_list_before_next_heading(heading: Tag) -> Tag | None:
    current = heading.next_sibling
    while current is not None:
        if _is_blank_text_node(current):
            current = current.next_sibling
            continue
        if isinstance(current, Tag) and current.name in {"h2", "h3"}:
            return None
        if isinstance(current, Tag) and current.name == "ul":
            return current
        current = current.next_sibling
    return None


def _section_link_targets(heading: Tag, from_path: Path) -> set[str]:
    targets: set[str] = set()
    current = heading.next_sibling
    while current is not None:
        if isinstance(current, Tag) and current.name in {"h2", "h3"}:
            break
        if isinstance(current, Tag):
            for link in current.find_all("a", href=True):
                target = edit_guide.get_href_target(DIST_ROOT, from_path, str(link["href"]))
                if target:
                    targets.add(target)
        current = current.next_sibling
    return targets


def _insert_settings_link_list(heading: Tag, soup: BeautifulSoup, links_html: str) -> None:
    insert_after: Any = heading
    current = heading.next_sibling
    while current is not None:
        if _is_blank_text_node(current):
            insert_after = current
            current = current.next_sibling
            continue
        if isinstance(current, Tag) and current.name == "a" and current.find("img"):
            insert_after = current
            current = current.next_sibling
            continue
        break
    fragment = BeautifulSoup(links_html, "html.parser")
    for node in reversed(list(fragment.contents)):
        insert_after.insert_after(node)


def _append_missing_settings_links(link_list: Tag, soup: BeautifulSoup, links_html: str) -> None:
    fragment = BeautifulSoup(links_html, "html.parser")
    source_list = fragment.find("ul")
    if source_list is None:
        return
    for list_item in source_list.find_all("li", recursive=False):
        link_list.append(list_item)


def _ensure_settings_group_link_lists(content: str, from_path: Path) -> str:
    soup = BeautifulSoup(f"<section>{content}</section>", "html.parser")
    root = soup.section
    if root is None:
        return content
    headings = {
        heading.get_text(" ", strip=True): heading
        for heading in root.find_all("h3")
    }
    for _group_id, group_title, child_paths in SETTINGS_NAV_GROUPS:
        heading = headings.get(group_title)
        if heading is None:
            continue
        existing_targets = _section_link_targets(heading, from_path)
        missing_links = [
            (child_path, title)
            for child_path, title in _settings_group_links(child_paths, from_path)
            if child_path not in existing_targets
        ]
        if not missing_links:
            continue
        link_list = _first_link_list_before_next_heading(heading)
        if link_list is None:
            _insert_settings_link_list(heading, soup, _render_links(missing_links, from_path))
        else:
            _append_missing_settings_links(link_list, soup, _render_links(missing_links, from_path))
    return root.decode_contents(formatter="html")


def _normalize_settings_page_content(content: str) -> str:
    token_re = re.compile(r"(?is)(<h1\b[^>]*>.*?</h1>|<a\b[^>]*>.*?</a>)")
    parts: list[str] = []
    link_buffer: list[str] = []

    def flush_links() -> None:
        if not link_buffer:
            return
        parts.append("<ul>" + "".join(f"<li>{link}</li>" for link in link_buffer) + "</ul>")
        link_buffer.clear()

    for token in token_re.split(content):
        if not token:
            continue
        if re.match(r"(?is)<h1\b", token):
            flush_links()
            heading = _strip_tags(token)
            if heading:
                parts.append(f"<h3>{_escape(heading)}</h3>")
            continue
        if re.match(r"(?is)<a\b", token):
            if re.search(r"(?is)<img\b", token):
                flush_links()
                parts.append(token)
            else:
                link_buffer.append(token)
            continue
        if token.strip():
            flush_links()
            parts.append(token)
        else:
            parts.append(token)
    flush_links()
    return _ensure_settings_group_link_lists("".join(parts), DIST_ROOT / SETTINGS_PAGE_PATH)


def _is_internal_list_link_node(node: Any) -> bool:
    if not isinstance(node, Tag) or node.name != "a":
        return False
    href = str(node.get("href", ""))
    if not href or href.startswith(("#", "http://", "https://", "mailto:")):
        return False
    if "assets/" in href or node.find("img"):
        return False
    return bool(node.get_text(" ", strip=True))


def _is_blank_text_node(node: Any) -> bool:
    return isinstance(node, NavigableString) and not str(node).strip()


def _wrap_direct_link_runs(container: Tag, soup: BeautifulSoup) -> None:
    while True:
        first_link = next((node for node in list(container.contents) if _is_internal_list_link_node(node)), None)
        if first_link is None:
            return

        link_list = soup.new_tag("ul")
        first_link.insert_before(link_list)
        current = first_link
        while current and (_is_internal_list_link_node(current) or _is_blank_text_node(current)):
            next_node = current.next_sibling
            if _is_internal_list_link_node(current):
                list_item = soup.new_tag("li")
                current.extract()
                list_item.append(current)
                link_list.append(list_item)
            else:
                current.extract()
            current = next_node


def _normalize_parent_page_link_lists(content: str) -> str:
    soup = BeautifulSoup(f"<section>{content}</section>", "html.parser")
    root = soup.section
    if root is None:
        return content
    _wrap_direct_link_runs(root, soup)
    for details in root.find_all("details"):
        _wrap_direct_link_runs(details, soup)
    return root.decode_contents(formatter="html")


def _render_notices(notices: list[tuple[str, str]]) -> str:
    return "\n".join(_notice(level, message) for level, message in notices)


def _render_confusion(items: list[tuple[str, str]]) -> str:
    return "".join(f"<h3>{_escape(question)}</h3>{_p(answer)}" for question, answer in items)


def _render_guidance(metadata: dict[str, Any]) -> str:
    guidance: list[tuple[str, str]] = []
    guidance.extend(list(metadata.get("notices", [])))
    guidance.extend(("권장", str(note)) for note in metadata.get("notes", []))
    return _render_notices(guidance)


def _render_template_section(
    section_id: str,
    path: str,
    title: str,
    page_type: str,
    metadata: dict[str, Any],
    content: str,
) -> str:
    from_path = DIST_ROOT / path
    match section_id:
        case "manual_scope":
            return _section("이 설명서에서 할 수 있는 일", _p(str(metadata["about"])))
        case "start_decision":
            return _section("처음 시작할 때 정할 것", _ol(list(metadata["first_steps"])))
        case "core_workflow":
            return _section("기본 번역 흐름", f"<p>{metadata['flow_intro']}</p>" + _ul(list(metadata["basic_flow"])))
        case "engine_routes":
            return _section("엔진별 시작 경로", _render_links(list(metadata["engine_links"]), from_path))
        case "frequent_tasks":
            return _section("자주 찾는 작업", _render_links(list(metadata["frequent_links"]), from_path))
        case "safe_use":
            notices = _render_guidance(metadata)
            return _section("작업 전 주의사항", notices) if notices else ""
        case "area_goal":
            return _section("이 영역에서 확인할 수 있는 것", _p(str(metadata["summary"])))
        case "direct_links":
            return _section("바로 이동", _render_links(list(metadata["links"]), from_path))
        case "suggested_path":
            return _section("처음이라면", _p(str(metadata.get("reading_order", "위에서 아래 순서로 읽으면 됩니다. 이미 작업 중이라면 필요한 문서를 검색하거나 목차에서 바로 선택하세요."))))
        case "task_goal":
            return _section("무엇을 할 수 있나요?", _p(str(metadata["summary"])))
        case "step_goal":
            return _section("이 단계의 목적", _p(str(metadata["summary"])))
        case "engine_scope":
            return _section("이 엔진에서 확인할 것", _p(str(metadata["summary"])))
        case "use_cases":
            return _section("언제 필요한가요?", _ul(list(metadata["when"])))
        case "entry_conditions":
            return _section("언제 진행하나요?", _ul(list(metadata["when"])))
        case "engine_fit":
            return _section("언제 이 문서를 보나요?", _ul(list(metadata["when"])))
        case "readiness":
            return _section("시작 전에 확인할 것", _ul(list(metadata["before"])))
        case "procedure":
            heading = "진행 순서" if page_type in {"workflow", "engine"} else "따라 하기"
            return _section(heading, _ol(list(metadata["steps"])))
        case "details":
            return _section("화면과 항목", content)
        case "verification":
            return _section("완료 후 확인", _ul(list(metadata["result"])))
        case "done_definition":
            return _section("완료 기준", _ul(list(metadata["result"])))
        case "decision_notes":
            notices = _render_guidance(metadata)
            return _section("주의/중요/권장", notices) if notices else ""
        case "common_mistakes":
            confusion = list(metadata.get("confusion", []))
            return _section("자주 헷갈리는 점", _render_confusion(confusion)) if confusion else ""
        case "triage":
            return _section("먼저 확인할 것", _ul(list(metadata["before"])))
        case "diagnosis_steps":
            return _section("문제 해결 순서", _ol(list(metadata["steps"])))
        case "faq_content":
            return _section("질문과 답변", content)
        case "support_packet":
            return _section("그래도 해결되지 않을 때", _p(str(metadata["followup"])))
        case "reference_scope":
            return _section("이 참고 문서의 범위", _p(str(metadata.get("summary", ADVANCED_INTRO))))
        case "command_scope":
            return _section("명령 코드 참고 범위", _p(str(metadata.get("summary", ADVANCED_INTRO))))
        case "change_guard":
            message = str(metadata.get("advanced_notice", "값을 바꾸기 전에는 기존 설정, 원문 파일, 적용 전 결과를 먼저 확인하세요."))
            return _section("변경 전 확인할 중요 사항", _notice("중요", message))
        case "reference_content":
            return _section("참고 내용", content)
        case "command_content":
            return _section("명령 코드 참고", content)
        case _:
            return ""


def _prepare_content(page_type: str, original_article: str) -> str:
    cleaned = _clean_html(original_article)
    if page_type not in {"advanced_reference", "command_reference", "troubleshooting"}:
        cleaned = _drop_duplicate_standard_sections(cleaned)
    if len(_strip_tags(cleaned)) < 80:
        cleaned += "\n" + _p(SHORT_ARTICLE_FALLBACK)
    return cleaned


def _render_article_body(path: str, title: str, page_type: str, metadata: dict[str, Any], content: str) -> str:
    title = str(metadata.get("title", title))
    parts = [f'<article class="guide-content"><h1>{_escape(title)}</h1>', _doc_version()]
    for section_id in PAGE_TYPE_TEMPLATES[page_type]:
        section = _render_template_section(section_id, path, title, page_type, metadata, content)
        if section:
            parts.append(section)
    parts.append("</article>")
    return "\n".join(parts)


def _render_article(path: str, title: str, original_article: str) -> str:
    page_type = _infer_page_type(path, title)
    metadata = _metadata_for(path, title, page_type)
    content = _prepare_content(page_type, original_article) if page_type != "home" else ""
    if path == "guide/설정/index.html":
        content = _normalize_settings_page_content(content)
    if path in FEATURE_NESTED_PARENT_PATHS or page_type == "command_reference":
        content = _normalize_parent_page_link_lists(content)
    return _render_article_body(path, title, page_type, metadata, content)


def _hub_article(path: str, title: str, summary: str, links: list[tuple[str, str]]) -> str:
    metadata = _metadata_for(path, title, "hub")
    metadata.update({"summary": summary, "links": links})
    return _render_article_body(path, title, "hub", metadata, "")


def _image_block(from_path: Path, asset_path: str, alt: str) -> str:
    href = edit_guide.relative_href(from_path, asset_path, DIST_ROOT)
    escaped_alt = _escape(alt)
    return f'<p><a href="{href}"><img src="{href}" alt="{escaped_alt}"></a></p>'


def _screen_area_article() -> str:
    path = "guide/features-screen/index.html"
    from_path = DIST_ROOT / path
    parts = [
        '<article class="guide-content"><h1>화면 영역</h1>',
        _doc_version(),
        _image_block(from_path, "guide/assets/하단부/image.png", "AIMT 화면 전체"),
        "<h2>전체 화면</h2>",
        _p("AIMT 화면은 크게 영역① 상단부, 영역② 중단부, 영역③ 하단부로 나누어 볼 수 있습니다. 먼저 전체 화면의 위치 관계를 확인한 뒤, 필요한 영역의 설명과 관련 문서로 이동하세요."),
    ]
    for title, description, asset_path, links in SCREEN_AREA_SECTIONS:
        parts.extend([
            f"<h2>{_escape(title)}</h2>",
            _p(description),
            _image_block(from_path, asset_path, title),
            "<h3>관련 문서</h3>",
            _render_links(list(links), from_path),
        ])
    parts.append("</article>")
    return "\n".join(parts)


def _links_from_paths(paths: set[str]) -> list[tuple[str, str]]:
    labels = {**TITLE_OVERRIDES}
    for path, title in ADVANCED_SUBGROUP_PAGES.items():
        labels[path] = title
    for path, title in SETTING_REFERENCE_GROUP_PAGES.items():
        labels[path] = title
    for path, title in EXTERNAL_REFERENCE_PAGES.items():
        labels[path] = title
    for path, title in FEATURE_SUBGROUP_PAGES.items():
        labels[path] = title
    items: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for item in edit_guide.get_nav_entries(DIST_ROOT):
        path = str(item["path"])
        if path in paths and path not in seen_paths:
            items.append((path, labels.get(path, str(item["title"]))))
            seen_paths.add(path)
    missing = sorted(paths - {path for path, _title in items})
    items.extend((path, labels.get(path, Path(path).parent.name)) for path in missing)
    return items


def _links_from_ordered_paths(paths: tuple[str, ...]) -> list[tuple[str, str]]:
    labels = {**TITLE_OVERRIDES}
    for item in edit_guide.get_nav_entries(DIST_ROOT):
        labels.setdefault(str(item["path"]), str(item["title"]))
    return [(path, labels.get(path, Path(path).parent.name)) for path in paths]


def _is_advanced(path: str, title: str) -> bool:
    haystack = f"{path} {title}".lower()
    return any(keyword.lower() in haystack for keyword in ADVANCED_KEYWORDS)


def _ensure_group_pages() -> None:
    entries = edit_guide.get_nav_entries(DIST_ROOT)
    for path, title in {**GROUP_PAGES, **ADVANCED_SUBGROUP_PAGES, **SETTING_REFERENCE_GROUP_PAGES, **FEATURE_SUBGROUP_PAGES, **EXTERNAL_REFERENCE_PAGES}.items():
        if path in VIRTUAL_GROUP_PAGES:
            continue
        html_path = DIST_ROOT / path
        if not html_path.exists():
            edit_guide.write_text(html_path, edit_guide.render_new_page(title, path, entries, DIST_ROOT))
    for path in SETTINGS_PAGE_CHILD_PATHS:
        html_path = DIST_ROOT / path
        if html_path.exists():
            continue
        source_text = _source_text_for(path, "")
        title = TITLE_OVERRIDES.get(path)
        if not title and source_text:
            title = edit_guide.parse_title(source_text, html_path.parent.name)
        if not title:
            title = html_path.parent.name.replace("-", " ")
        edit_guide.write_text(html_path, edit_guide.render_new_page(title, path, entries, DIST_ROOT))


def _remove_deleted_pages() -> None:
    for path in DELETE_DIST_PATHS:
        html_path = DIST_ROOT / path
        try:
            html_path.unlink()
        except FileNotFoundError:
            continue
        parent = html_path.parent
        while parent != GUIDE_ROOT and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def _build_group_articles() -> dict[str, str]:
    return {
        "guide/start/index.html": _hub_article(
            "guide/start/index.html",
            "시작하기",
            "AIMT를 처음 사용할 때 필요한 준비 과정을 모은 영역입니다.",
            [
                ("guide/프롬프트/index.html", "프롬프트"),
            ],
        ),
        "guide/basic-workflow/index.html": _hub_article(
            "guide/basic-workflow/index.html",
            "기본 작업 흐름",
            "프로젝트를 지정한 뒤 추출, 번역, 적용, 확인까지 이어지는 일반적인 작업 순서입니다.",
            [
                ("guide/새-프로젝트-프로젝트-지정/index.html", "새 프로젝트 / 프로젝트 지정"),
                ("guide/추출/index.html", "추출"),
                ("guide/번역/index.html", "번역"),
                ("guide/적용과-즉시적용/index.html", "적용과 즉시적용"),
            ],
        ),
        "guide/engine-guides/index.html": _hub_article(
            "guide/engine-guides/index.html",
            "엔진별 가이드",
            "게임 제작 도구나 엔진별로 다른 준비사항과 작업 흐름을 확인하는 영역입니다.",
            [
                ("guide/rpg-maker-mvmz-개정1/index.html", "RPG Maker MV/MZ"),
                ("guide/rpg-maker-vxvxa-개정1/index.html", "RPG Maker VX/VXA"),
                ("guide/wolf-rpg-editor/index.html", "WOLF RPG Editor"),
                ("guide/tyranobuilder-tyranoscript-개정1/index.html", "TyranoBuilder/TyranoScript"),
            ],
        ),
        "guide/features/index.html": _hub_article(
            "guide/features/index.html",
            "기능별 설명",
            "AIMT 화면의 각 영역과 도구별 기능을 찾아보는 영역입니다.",
            [
                ("guide/features-screen/index.html", "화면 영역"),
                ("guide/설정/index.html", "설정 화면"),
                ("guide/도구/index.html", "작업 도구"),
                ("guide/features-quickslot/index.html", "퀵슬롯"),
                ("guide/features-reference/index.html", "기타 참고"),
            ],
        ),
        "guide/features-screen/index.html": _screen_area_article(),
        "guide/features-quickslot/index.html": _hub_article(
            "guide/features-quickslot/index.html",
            "퀵슬롯",
            "퀵슬롯과 퀵슬롯에서 바로 여는 보조 기능 문서 묶음입니다.",
            _links_from_ordered_paths(FEATURE_QUICKSLOT_PARENT_PATHS),
        ),
        "guide/features-reference/index.html": _hub_article(
            "guide/features-reference/index.html",
            "기타 참고",
            "기능별 설명에 속하지만 특정 화면 영역으로 묶기 어려운 참고 문서입니다.",
            _links_from_paths(FEATURE_REFERENCE_PATHS),
        ),
        "guide/troubleshooting/index.html": _hub_article(
            "guide/troubleshooting/index.html",
            "문제 해결",
            "오류, 적용 실패, 결과 이상, 사용량 문제처럼 작업 중 막히는 상황을 확인하는 영역입니다.",
            [
                ("guide/자주-나오는-질문/index.html", "자주 나오는 질문"),
            ],
        ),
        "guide/advanced-reference/index.html": _hub_article(
            "guide/advanced-reference/index.html",
            "참고 자료",
            "AIMT에서 함께 참고하기 좋은 외부 사이트, API 제공자 문서, 출처 링크를 모은 영역입니다.",
            [
                ("guide/rpgmaker-명령코드-정리-작성-예정/index.html", "RPG Maker 명령 코드 참고"),
                ("guide/같이-쓰면-좋은-도구들/index.html", "외부 유틸리티"),
                ("guide/제공자별-참고-링크/index.html", "제공자별 참고 링크"),
            ],
        ),
        "guide/제공자별-참고-링크/index.html": _render_article_body(
            "guide/제공자별-참고-링크/index.html",
            "제공자별 참고 링크",
            "advanced_reference",
            {
                "summary": "API 키 발급, 제공자별 문서, 이미지 출처처럼 AIMT 설정 과정에서 함께 확인하기 좋은 외부 자료를 모은 문서입니다.",
                "advanced_notice": "외부 사이트의 화면과 정책은 바뀔 수 있습니다. API 키를 만들거나 결제 정보를 확인할 때는 각 제공자의 최신 안내를 함께 확인하세요.",
            },
            _external_reference_content(),
        ),
    }


def _sort_key(entry: dict[str, Any]) -> tuple[int, str]:
    return int(entry.get("order", 999999)), str(entry["title"])


def _append_feature_parent_with_children(
    nav: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    parent_entry: dict[str, Any],
    parent_path: str,
    parent_depth: int,
) -> None:
    nav_entry = dict(parent_entry)
    nav_entry["depth"] = parent_depth
    nav.append(nav_entry)

    child_order = FEATURE_NESTED_CHILD_ORDER_BY_PARENT.get(parent_path, {})
    child_entries: list[dict[str, Any]] = []
    for child_path in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.get(parent_path, ()):
        if child_path in EXCLUDE_FROM_NAV_PATHS or child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
            continue
        try:
            child_entry = dict(by_path[child_path])
        except KeyError:
            continue
        child_entry["depth"] = parent_depth + 1
        child_entries.append(child_entry)
    nav.extend(sorted(child_entries, key=lambda item: (child_order.get(str(item["path"]), 999999), _sort_key(item))))


def _append_feature_children(
    nav: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    parent_path: str,
    parent_depth: int,
) -> None:
    child_order = FEATURE_NESTED_CHILD_ORDER_BY_PARENT.get(parent_path, {})
    child_entries: list[dict[str, Any]] = []
    for child_path in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.get(parent_path, ()):
        if child_path in EXCLUDE_FROM_NAV_PATHS or child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
            continue
        try:
            child_entry = dict(by_path[child_path])
        except KeyError:
            continue
        child_entry["depth"] = parent_depth + 1
        child_entries.append(child_entry)
    nav.extend(sorted(child_entries, key=lambda item: (child_order.get(str(item["path"]), 999999), _sort_key(item))))


def _append_virtual_parent_with_children(
    nav: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    parent_path: str,
    parent_title: str,
    parent_depth: int,
) -> None:
    nav.append(_virtual_nav_group(parent_path.replace("/", "-"), parent_title, parent_depth))
    child_order = FEATURE_NESTED_CHILD_ORDER_BY_PARENT.get(parent_path, {})
    child_entries: list[dict[str, Any]] = []
    for child_path in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.get(parent_path, ()):
        if child_path in EXCLUDE_FROM_NAV_PATHS or child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
            continue
        try:
            child_entry = dict(by_path[child_path])
        except KeyError:
            continue
        child_entry["depth"] = parent_depth + 1
        child_entries.append(child_entry)
    nav.extend(sorted(child_entries, key=lambda item: (child_order.get(str(item["path"]), 999999), _sort_key(item))))


def _virtual_nav_group(group_id: str, title: str, depth: int) -> dict[str, Any]:
    return {
        "path": f"__nav_group__/{group_id}",
        "title": title,
        "depth": depth,
        "order": -1,
        "virtual": True,
    }


def _append_workspace_tool_groups(
    nav: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    engine_tool_entries: list[dict[str, Any]],
    parent_depth: int,
) -> None:
    group_depth = parent_depth + 1
    child_depth = group_depth + 1

    for group_id, title, child_paths in WORKSPACE_TOOL_NAV_GROUPS:
        nav.append(_virtual_nav_group(group_id, title, group_depth))
        if group_id == "workspace-engine-tools":
            for parent_path in FEATURE_ENGINE_TOOL_PARENT_PATHS:
                _append_virtual_parent_with_children(
                    nav,
                    by_path,
                    parent_path,
                    FEATURE_ENGINE_TOOL_GROUP_TITLES[parent_path],
                    child_depth,
                )
            continue
        for child_path in child_paths:
            if child_path in EXCLUDE_FROM_NAV_PATHS or child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
                continue
            try:
                child_entry = dict(by_path[child_path])
            except KeyError:
                continue
            child_entry["depth"] = child_depth
            nav.append(child_entry)


def _ensure_path_entry(by_path: dict[str, dict[str, Any]], path: str) -> None:
    if path in by_path:
        return
    html_path = DIST_ROOT / path
    if not html_path.exists():
        return
    by_path[path] = {
        "path": path,
        "title": _title_for_path(path),
        "depth": 1,
        "order": 999999,
        "hasChildren": False,
    }


def _append_settings_groups(
    nav: list[dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
    parent_depth: int,
) -> None:
    group_depth = parent_depth + 1
    child_depth = group_depth + 1
    for group_id, title, child_paths in SETTINGS_NAV_GROUPS:
        children: list[dict[str, Any]] = []
        for child_path in child_paths:
            if child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
                continue
            _ensure_path_entry(by_path, child_path)
            try:
                child_entry = dict(by_path[child_path])
            except KeyError:
                continue
            child_entry["depth"] = child_depth
            children.append(child_entry)
        if not children:
            continue
        nav.append(_virtual_nav_group(f"settings-{group_id}", title, group_depth))
        nav.extend(children)


def _make_nav(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path = {str(entry["path"]): dict(entry) for entry in entries}
    for path, title in {**GROUP_PAGES, **ADVANCED_SUBGROUP_PAGES, **SETTING_REFERENCE_GROUP_PAGES, **FEATURE_SUBGROUP_PAGES, **EXTERNAL_REFERENCE_PAGES}.items():
        by_path[path] = {"path": path, "title": title, "depth": 1, "order": -1, "hasChildren": True, "virtual": path in VIRTUAL_GROUP_PAGES}
    for path in SETTINGS_PAGE_CHILD_PATHS:
        _ensure_path_entry(by_path, path)
    for path, title in TITLE_OVERRIDES.items():
        if path in by_path:
            by_path[path]["title"] = title

    root = by_path.pop("guide/index.html")
    root["depth"] = 0
    root["title"] = TITLE_OVERRIDES["guide/index.html"]

    buckets: dict[str, list[dict[str, Any]]] = {
        "guide/start/index.html": [],
        "guide/basic-workflow/index.html": [],
        "guide/engine-guides/index.html": [],
        "guide/features/index.html": [],
        "guide/troubleshooting/index.html": [],
        "guide/advanced-reference/index.html": [],
    }
    advanced_buckets: dict[str, list[dict[str, Any]]] = {"guide/advanced-reference/index.html": []}
    settings_reference_parent_paths: set[str] = set()
    settings_buckets: dict[str, list[dict[str, Any]]] = {path: [] for path in settings_reference_parent_paths}
    settings_page_children: list[dict[str, Any]] = []
    feature_buckets: dict[str, list[dict[str, Any]]] = {
        "guide/features-screen/index.html": [],
        "guide/도구/index.html": [],
        "guide/features-engine-tools/index.html": [],
        "guide/features-quickslot/index.html": [],
        "guide/features-reference/index.html": [],
        "guide/features/index.html": [],
    }
    for path, entry in list(by_path.items()):
        if path in EXCLUDE_FROM_NAV_PATHS:
            continue
        if path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
            continue
        if path in MERGED_SCREEN_PAGE_PATHS or path in SCREEN_AREA_LINK_ONLY_PATHS:
            continue
        if path == SETTINGS_PAGE_PATH:
            continue
        if path in GROUP_PAGES or path in ADVANCED_SUBGROUP_PAGES or path in FEATURE_SUBGROUP_PAGES or path in settings_reference_parent_paths:
            continue
        title = str(entry["title"])
        settings_parent = ""
        if title.lower().startswith("code:"):
            continue
        if path in SETTINGS_PAGE_CHILD_ORDER:
            group = "guide/features/index.html"
        elif path in STARTING_PATHS:
            group = "guide/start/index.html"
        elif path in WORKFLOW_PATHS:
            group = "guide/basic-workflow/index.html"
        elif path in ENGINE_PATHS:
            group = "guide/engine-guides/index.html"
        elif path in TROUBLESHOOTING_PATHS:
            group = "guide/troubleshooting/index.html"
        elif settings_parent:
            group = "guide/features/index.html"
        elif path in ADVANCED_DIRECT_PATHS:
            group = "guide/advanced-reference/index.html"
        elif _is_advanced(path, title):
            group = "guide/features/index.html"
        else:
            group = "guide/features/index.html"
        entry["depth"] = 2
        if group == "guide/advanced-reference/index.html":
            advanced_buckets["guide/advanced-reference/index.html"].append(entry)
        else:
            if group == "guide/features/index.html":
                if path in SETTINGS_PAGE_CHILD_ORDER:
                    entry["depth"] = 3
                    settings_page_children.append(entry)
                elif settings_parent:
                    entry["depth"] = 4
                    settings_buckets[settings_parent].append(entry)
                elif path in FEATURE_NESTED_CHILD_PATHS and path not in FEATURE_NESTED_PARENT_PATHS:
                    continue
                elif path in FEATURE_SCREEN_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-screen/index.html"].append(entry)
                elif path in FEATURE_WORKSPACE_TOOL_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/도구/index.html"].append(entry)
                elif path in FEATURE_ENGINE_TOOL_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-engine-tools/index.html"].append(entry)
                elif path in FEATURE_QUICKSLOT_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-quickslot/index.html"].append(entry)
                elif path in FEATURE_REFERENCE_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-reference/index.html"].append(entry)
                else:
                    feature_buckets["guide/features/index.html"].append(entry)
            else:
                buckets[group].append(entry)

    nav = [root]
    for group_path in GROUP_PAGES:
        group_entry = dict(by_path[group_path])
        group_entry["depth"] = 1
        nav.append(group_entry)
        children = sorted(buckets[group_path], key=_sort_key)
        if group_path == "guide/features/index.html":
            for subgroup_path in [
                "guide/features-screen/index.html",
                SETTINGS_PAGE_PATH,
                "guide/도구/index.html",
                "guide/features-quickslot/index.html",
                "guide/features-reference/index.html",
            ]:
                subgroup_entry = dict(by_path[subgroup_path])
                subgroup_entry["depth"] = 2
                nav.append(subgroup_entry)
                if subgroup_path == SETTINGS_PAGE_PATH:
                    _append_settings_groups(nav, by_path, 2)
                    continue
                if subgroup_path == "guide/도구/index.html":
                    _append_workspace_tool_groups(
                        nav,
                        by_path,
                        feature_buckets["guide/features-engine-tools/index.html"],
                        2,
                    )
                    continue
                for feature_entry in sorted(feature_buckets[subgroup_path], key=_sort_key):
                    feature_path = str(feature_entry["path"])
                    if feature_path in FEATURE_NESTED_PARENT_PATHS:
                        _append_feature_parent_with_children(nav, by_path, feature_entry, feature_path, 3)
                    else:
                        nav.append(feature_entry)
            for child in sorted(feature_buckets["guide/features/index.html"], key=_sort_key):
                child["depth"] = 2
                nav.append(child)
        elif group_path == "guide/advanced-reference/index.html":
            for child in sorted(advanced_buckets["guide/advanced-reference/index.html"], key=_sort_key):
                child["depth"] = 2
                nav.append(child)
        else:
            nav.extend(children)
    deduped_nav: list[dict[str, Any]] = []
    seen_nav_paths: set[str] = set()
    for entry in nav:
        path = str(entry["path"])
        if path in seen_nav_paths:
            continue
        deduped_nav.append(entry)
        seen_nav_paths.add(path)
    nav = deduped_nav

    for index, entry in enumerate(nav):
        entry["order"] = index
        entry["hasChildren"] = index + 1 < len(nav) and int(nav[index + 1]["depth"]) > int(entry["depth"])
    return nav


def _flatten_nested_card_styles() -> None:
    css_path = GUIDE_ROOT / "static" / "styles.css"
    if not css_path.exists():
        return
    text = edit_guide.read_text(css_path)
    replacements = {
        "blockquote{margin:20px 0;padding:12px 18px;border-left:4px solid var(--accent);background:var(--soft);border-radius:12px}": "blockquote{margin:20px 0;padding:0 0 0 14px;border-left:3px solid var(--accent);background:transparent;border-radius:0}",
        ".callout{border-radius:12px;padding:1rem;background:var(--soft)}": ".callout{border-radius:0;padding:0;background:transparent}",
        ".bookmark{display:flex;width:100%;align-items:stretch;border:1px solid var(--line);border-radius:12px;overflow:hidden;text-decoration:none}": ".bookmark{display:flex;width:100%;align-items:stretch;border:0;border-radius:0;overflow:visible;text-decoration:none}",
        ".bookmark-info{padding:12px 14px}": ".bookmark-info{padding:0}",
        ".selected-value{display:inline-block;padding:0 .5em;background:var(--soft);border-radius:3px;margin:.3em .5em .3em 0}": ".selected-value{display:inline;font-weight:700;background:transparent;border-radius:0;margin:0 .25em 0 0}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    edit_guide.write_text(css_path, text)


def main() -> int:
    _ensure_group_pages()
    _remove_deleted_pages()
    entries = edit_guide.get_nav_entries(DIST_ROOT)
    group_articles = _build_group_articles()
    all_paths = {entry["path"] for entry in edit_guide.list_files(DIST_ROOT, include_unlisted=True)}

    for path in sorted(all_paths):
        html_path = DIST_ROOT / path
        if not html_path.exists():
            continue
        text = edit_guide.read_text(html_path)
        source_text = _source_text_for(path, text)
        try:
            original_article = edit_guide.extract_article(source_text)
        except ValueError:
            continue
        title = TITLE_OVERRIDES.get(path, edit_guide.parse_title(source_text, html_path.parent.name))
        article = group_articles.get(path) or _render_article(path, title, original_article)
        updated = _replace_article_safe(text, article)
        updated = re.sub(r"(?is)<title>.*?</title>", f"<title>{_escape(title)} · AIMT Guide</title>", updated, count=1)
        edit_guide.write_text(html_path, updated)

    new_entries = _make_nav(edit_guide.get_nav_entries(DIST_ROOT))
    changed = edit_guide.rewrite_navs(DIST_ROOT, new_entries)
    _flatten_nested_card_styles()
    edit_guide.rebuild_search_index(DIST_ROOT)
    print(f"Renewed guide articles and navigation. nav_rewritten={changed}, pages={len(edit_guide.list_files(DIST_ROOT))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
