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
RENEWED_AT = "2026-08-02"
DOC_VERSION = f"문서 기준: AIMT PRO 1.17.0.0<br>최종 편집 일시: {RENEWED_AT}"
ADVANCED_INTRO = "이 문서는 일반 작업 순서에서 벗어나, 값을 직접 확인하거나 세밀하게 조정해야 할 때 참고하는 자료입니다."
SHORT_ARTICLE_FALLBACK = "아직 세부 설명이 충분하지 않은 문서입니다. 먼저 기능의 위치와 실행 결과를 확인하고, 필요한 경우 관련 상위 문서를 함께 확인하세요."

GROUP_PAGES: dict[str, str] = {
    "guide/basic-workflow/index.html": "기본 작업 흐름",
    "guide/engine-guides/index.html": "엔진별 가이드",
    "guide/features/index.html": "기능별 설명",
    "guide/troubleshooting/index.html": "문제 해결",
    "guide/advanced-reference/index.html": "참고 자료",
}

VIRTUAL_GROUP_PAGES: set[str] = set(GROUP_PAGES) - {"guide/basic-workflow/index.html"}

ADVANCED_SUBGROUP_PAGES: dict[str, str] = {}

SETTING_REFERENCE_GROUP_PAGES: dict[str, str] = {}

EXTERNAL_REFERENCE_PAGES: dict[str, str] = {
    "guide/external-utilities/index.html": "외부 유틸리티",
    "guide/provider-reference-links/index.html": "제공자별 참고 링크",
}

NAV_ONLY_EXCLUDE_PATHS: set[str] = {
    "guide/extract-python-data-strings/index.html",
}

WORKFLOW_PATHS = {
    "guide/project-selection/index.html",
    "guide/extraction/index.html",
    "guide/translation/index.html",
    "guide/apply-and-instant-apply/index.html",
}

ENGINE_NAV_PATHS: tuple[str, ...] = (
    "guide/rpg-maker-mvmz/index.html",
    "guide/rpg-maker-vxvxa/index.html",
    "guide/wolf-rpg-editor/index.html",
    "guide/clickteam-fusion-coming-soon/index.html",
    "guide/tyranobuilder-tyranoscript/index.html",
    "guide/pixel-game-maker-mv/index.html",
    "guide/srpg-studio/index.html",
    "guide/livemaker/index.html",
    "guide/bakin/index.html",
    "guide/renpy/index.html",
    "guide/csv-tsv/index.html",
    "guide/multi-regex-engines/index.html",
)

ENGINE_PATHS = set(ENGINE_NAV_PATHS)
ENGINE_NAV_ORDER = {path: index for index, path in enumerate(ENGINE_NAV_PATHS)}

TROUBLESHOOTING_PATHS = {
    "guide/faq/index.html",
}

EXCLUDE_FROM_NAV_PATHS = VIRTUAL_GROUP_PAGES | {
    "guide/start/index.html",
    "guide/features-quickslot/index.html",
    "guide/용어사전/index.html",
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
    "guide/editor-word-wrap/index.html",
    "guide/escape-diff-viewer/index.html",
}

DELETE_DIST_PATHS = EXCLUDE_FROM_NAV_PATHS | VIRTUAL_GROUP_PAGES

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
    "guide/workspace-tools/index.html": "작업 도구",
    "guide/settings-screen/index.html": "설정 화면",
    "guide/project-selection/index.html": "Project Hub",
    "guide/clickteam-fusion-coming-soon/index.html": "Clickteam Fusion 번역 가이드",
    "guide/ctf-fast-image-extraction/index.html": "CTF 이미지 추출과 적용",
    "guide/renpy/index.html": "Ren'Py 번역 가이드",
    "guide/livemaker/index.html": "LiveMaker 번역 가이드",
    "guide/srpg-studio/index.html": "SRPG Studio 번역 가이드",
    "guide/bakin/index.html": "Bakin 번역 가이드",
    "guide/rpg-maker-command-code-reference/index.html": "RPG Maker 명령 코드 참고",
    "guide/advanced-reference/index.html": "참고 자료",
    "guide/external-utilities/index.html": "외부 유틸리티",
    "guide/view-switching/index.html": "화면전환",
    "guide/wolf-secondary-exclusion-filter/index.html": "WOLF 2차 추출 제외 필터",
    "guide/vxvxa-message-block-unit/index.html": "Message Block Unit",
    "guide/extract-troop-names/index.html": "Extract Troop Names",
    "guide/dbdic-include-extract-names/index.html": "DBdic include Extract Names",
    "guide/srpg-secondary-extraction-filter/index.html": "SRPG 2차 추출 필터",
    "guide/livemaker-font-settings/index.html": "LiveMaker 폰트 설정",
    "guide/asar-tyrano/index.html": "ASAR (Tyrano 계열)",
    "guide/asar/index.html": "ASAR (Electron)",
    "guide/line-maker-mvmz/index.html": "라인메이커 (MVMZ)",
    "guide/line-maker-vxvxa/index.html": "라인메이커 (VXVXA)",
    "guide/title-change-vxvxa/index.html": "타이틀변경 (VXVXA)",
    "guide/title-change-ctf/index.html": "타이틀 변경 (CTF)",
    "guide/title-change-tyrano/index.html": "타이틀 변경 (Tyrano)",
    "guide/ctf-crypter/index.html": "크립터 (CTF)",
    "guide/pgmmv-crypter/index.html": "크립터 (PGMMV)",
    "guide/renpy-crypter/index.html": "크립터 (Ren'Py)",
    "guide/renpy-tag-check/index.html": "태그 검사",
    "guide/renpy-font-replacement/index.html": "폰트 교체",
    "guide/srpg-studio-unpack/index.html": "언팩",
    "guide/srpg-studio-manual-build/index.html": "수동 빌드",
    "guide/srk-crypter/index.html": "SRK 크립터",
    "guide/include-tl-translations/index.html": "Ren'Py TL 준비와 기존 번역 사용",
    "guide/save-editor/index.html": "Save Editor",
    "guide/csv-tsv/index.html": "CSV/TSV 번역 가이드",
    "guide/multi-regex-engines/index.html": "범용 정규식 엔진 가이드",
}

RENAMED_PAGE_PATHS = {
    "guide/2차-추출-필터/index.html": "guide/wolf-secondary-exclusion-filter/index.html",
    "guide/2차-추출-제외-필터/index.html": "guide/wolf-secondary-exclusion-filter/index.html",
    "guide/ctf-2차-추출-필터-편집/index.html": "guide/ctf-secondary-exclusion-filter/index.html",
    "guide/bakin-2차-추출-필터-편집/index.html": "guide/bakin-secondary-exclusion-filter/index.html",
    "guide/ctf-2차-추출-제외-필터-편집/index.html": "guide/ctf-secondary-exclusion-filter/index.html",
    "guide/bakin-2차-추출-제외-필터-편집/index.html": "guide/bakin-secondary-exclusion-filter/index.html",
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
    "guide/rpg-maker-command-code-reference/index.html",
    "guide/extraction-files-reference/index.html",
    "guide/external-utilities/index.html",
    "guide/provider-reference-links/index.html",
}

FEATURE_SUBGROUP_PAGES: dict[str, str] = {
    "guide/features-screen/index.html": "화면 영역",
}

MERGED_SCREEN_PAGE_PATHS: set[str] = {
    "guide/top-area/index.html",
    "guide/middle-area/index.html",
    "guide/bottom-area/index.html",
}

SCREEN_AREA_LINK_ONLY_PATHS: set[str] = {
    "guide/viewer/index.html",
}

FEATURE_SCREEN_PATHS: set[str] = {
    "guide/view-switching/index.html",
}

SCREEN_AREA_SECTIONS: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "영역1 사이드바",
        "프로젝트 지정, 파일 목록 갱신, 프롬프트, 빠른번역, 설정, 화면 전환처럼 작업을 시작하거나 화면 상태를 바꾸는 영역입니다.",
        "guide/assets/top-area/image.png",
        (
            ("guide/project-selection/index.html", "Project Hub"),
            ("guide/refresh-file-list/index.html", "파일목록 새로고침"),
            ("guide/view-switching/index.html", "화면전환"),
            ("guide/prompt/index.html", "프롬프트"),
            ("guide/quick-translation/index.html", "빠른번역"),
            ("guide/settings-screen/index.html", "설정 화면"),
        ),
    ),
    (
        "영역2 메인뷰",
        "선택한 파일과 작업 대상의 내용을 확인하는 영역입니다. 목록에서 대상을 고르고, 필요한 경우 Viewer 화면으로 세부 내용을 확인합니다.",
        "guide/assets/middle-area/image 3.png",
        (
            ("guide/viewer/index.html", "Viewer"),
            ("guide/console/index.html", "Console"),
        ),
    ),
    (
        "영역3 커맨드바",
        "추출, 번역, 적용, 도구, 퀵슬롯처럼 실제 작업을 실행하는 영역입니다. 작업 단계가 바뀔 때 가장 자주 사용하는 버튼들이 모여 있습니다.",
        "guide/assets/bottom-area/image 1.png",
        (
            ("guide/extraction/index.html", "추출"),
            ("guide/translation/index.html", "번역"),
            ("guide/apply-and-instant-apply/index.html", "적용과 즉시적용"),
            ("guide/workspace-tools/index.html", "작업 도구"),
            ("guide/quickslot/index.html", "퀵슬롯"),
        ),
    ),
)

SCREEN_AREA_NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "sidebar",
        "영역1 사이드바",
        (
            "guide/project-selection/index.html",
            "guide/refresh-file-list/index.html",
            "guide/view-switching/index.html",
            "guide/prompt/index.html",
            "guide/quick-translation/index.html",
        ),
    ),
    (
        "mainview",
        "영역2 메인뷰",
        (
            "guide/viewer/index.html",
            "guide/console/index.html",
        ),
    ),
    (
        "commandbar",
        "영역3 커맨드바",
        (
            "guide/extraction/index.html",
            "guide/translation/index.html",
            "guide/apply-and-instant-apply/index.html",
        ),
    ),
)

SCREEN_AREA_NAV_CHILD_PATHS: set[str] = {
    child_path
    for _group_id, _group_title, child_paths in SCREEN_AREA_NAV_GROUPS
    for child_path in child_paths
}

SETTINGS_PAGE_PATH = "guide/settings-screen/index.html"

ELEVATED_SETTINGS_PAGE_CHILD_PATHS: tuple[str, ...] = (
    "guide/translation-settings/index.html",
)

SETTINGS_NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "general",
        "일반",
        (
            "guide/theme/index.html",
            "guide/extraction-regex/index.html",
            "guide/escape-patterns/index.html",
            "guide/language-pattern-settings/index.html",
        ),
    ),
    (
        "translation",
        "번역설정",
        (
            "guide/ai-model/index.html",
            "guide/api-key-settings/index.html",
        ),
    ),
    (
        "mvmz",
        "MVMZ",
        (
            "guide/exclude-exception-regex/index.html",
            "guide/replacement-terms/index.html",
            "guide/default-font-settings/index.html",
            "guide/title-text/index.html",
            "guide/multiline-db/index.html",
            "guide/extract-troop-names/index.html",
            "guide/extract-names/index.html",
            "guide/dbdic-include-extract-names/index.html",
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
        "vxvxa",
        "VXVXA",
        (
            "guide/vxvxa-message-block-unit/index.html",
        ),
    ),
    (
        "wolf",
        "WOLF",
        (
            "guide/wolf-secondary-exclusion-filter/index.html",
            "guide/cmd-122-secondary-duplicate-handling/index.html",
        ),
    ),
    (
        "ctf",
        "CTF",
        (
            "guide/ctf-fast-image-extraction/index.html",
            "guide/ctf-secondary-exclusion-filter/index.html",
        ),
    ),
    (
        "srpgstudio",
        "SRPG Studio",
        (
            "guide/srpg-secondary-extraction-filter/index.html",
        ),
    ),
    (
        "livemaker",
        "LiveMaker",
        (
            "guide/livemaker-font-settings/index.html",
        ),
    ),
    (
        "bakin",
        "Bakin",
        (
            "guide/bakin-secondary-exclusion-filter/index.html",
        ),
    ),
    (
        "renpy",
        "Ren'Py",
        (
            "guide/include-tl-translations/index.html",
        ),
    ),
    (
        "log-backup",
        "로그/백업",
        (
            "guide/log-management/index.html",
            "guide/backup-management/index.html",
            "guide/cache-management/index.html",
        ),
    ),
    (
        "help",
        "도움말",
        (
            "guide/help-settings/index.html",
        ),
    ),
    (
        "etc",
        "기타",
        (
            "guide/misc-settings/index.html",
        ),
    ),
)

SETTINGS_PAGE_CHILD_PATHS: tuple[str, ...] = ELEVATED_SETTINGS_PAGE_CHILD_PATHS + tuple(
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
    "guide/workspace-tools/index.html",
    "guide/refresh-file-list/index.html",
    "guide/quick-translation/index.html",
    "guide/undo-apply/index.html",
    "guide/import-translation/index.html",
    "guide/fill-blanks/index.html",
    "guide/user-dictionary-prepost/index.html",
    "guide/translation-consistency/index.html",
    "guide/extraction-duplicates/index.html",
    "guide/japanese-check/index.html",
    "guide/final-consonant-cleanup/index.html",
    "guide/code-restore/index.html",
    "guide/save-editor/index.html",
    "guide/ttc-build/index.html",
    "guide/vscode/index.html",
    "guide/notepad/index.html",
}

WORKSPACE_TOOL_LINK_ONLY_PATHS: set[str] = {
    "guide/quickslot-quick-translation/index.html",
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
    "guide/renpy-tools/index.html",
    "guide/srpg-studio-tools/index.html",
    "guide/line-maker-mvmz/index.html",
    "guide/line-maker-vxvxa/index.html",
    "guide/add-plugin/index.html",
    "guide/name-consistency/index.html",
    "guide/integrated-consistency/index.html",
    "guide/mvmz-media-crypter/index.html",
    "guide/data-decryption/index.html",
    "guide/project-conversion/index.html",
    "guide/enigma-unpack/index.html",
    "guide/vxvxa-unpack/index.html",
    "guide/title-change-vxvxa/index.html",
    "guide/dedicated-extraction/index.html",
    "guide/imbook-bbtext-missions-patch/index.html",
    "guide/mv-conversion/index.html",
    "guide/wolf-unpack-repack/index.html",
    "guide/integrated-replacement/index.html",
    "guide/exe-patch/index.html",
    "guide/metadata-check/index.html",
    "guide/title-change-ctf/index.html",
    "guide/title-change-tyrano/index.html",
    "guide/language-change/index.html",
    "guide/ctf-crypter/index.html",
    "guide/pgmmv-crypter/index.html",
    "guide/renpy-crypter/index.html",
    "guide/renpy-tag-check/index.html",
    "guide/renpy-font-replacement/index.html",
    "guide/srpg-studio-unpack/index.html",
    "guide/srpg-studio-manual-build/index.html",
    "guide/srk-crypter/index.html",
}

FEATURE_ENGINE_TOOL_PARENT_PATHS: tuple[str, ...] = (
    "guide/mvmz/index.html",
    "guide/vxvxa/index.html",
    "guide/wolf/index.html",
    "guide/ctf/index.html",
    "guide/tyrano/index.html",
    "guide/kirikiri/index.html",
    "guide/pgmmv/index.html",
    "guide/srpg-studio-tools/index.html",
    "guide/renpy-tools/index.html",
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
    "guide/srpg-studio-tools/index.html": "SRPG Studio",
    "guide/renpy-tools/index.html": "Ren'Py",
    "guide/electron/index.html": "Electron",
}

FEATURE_QUICKSLOT_PATHS = {
    "guide/quickslot/index.html",
    "guide/memo/index.html",
    "guide/quickslot-quick-translation/index.html",
}

FEATURE_QUICKSLOT_PARENT_PATHS: tuple[str, ...] = (
    "guide/quickslot/index.html",
)

FEATURE_NESTED_CHILD_PATHS_BY_PARENT: dict[str, tuple[str, ...]] = {
    "guide/workspace-tools/index.html": (
        "guide/fill-blanks/index.html",
        "guide/user-dictionary-prepost/index.html",
        "guide/undo-apply/index.html",
        "guide/translation-consistency/index.html",
        "guide/extraction-duplicates/index.html",
        "guide/escape-check/index.html",
        "guide/final-consonant-cleanup/index.html",
        "guide/vscode/index.html",
        "guide/notepad/index.html",
        "guide/appdata/index.html",
        "guide/ttc-build/index.html",
        "guide/save-editor/index.html",
        "guide/llama-server/index.html",
    ),
    "guide/mvmz/index.html": (
        "guide/line-maker-mvmz/index.html",
        "guide/add-plugin/index.html",
        "guide/401-merge-split/index.html",
        "guide/402-sync/index.html",
        "guide/name-consistency/index.html",
        "guide/integrated-consistency/index.html",
        "guide/japanese-check/index.html",
        "guide/code-restore/index.html",
        "guide/import-translation/index.html",
        "guide/escape-data/index.html",
        "guide/mvmz-media-crypter/index.html",
        "guide/data-decryption/index.html",
        "guide/project-conversion/index.html",
        "guide/enigma-unpack/index.html",
    ),
    "guide/vxvxa/index.html": (
        "guide/vxvxa-unpack/index.html",
        "guide/title-change-vxvxa/index.html",
        "guide/line-maker-vxvxa/index.html",
        "guide/dedicated-extraction/index.html",
        "guide/imbook-bbtext-missions-patch/index.html",
        "guide/mv-conversion/index.html",
    ),
    "guide/wolf/index.html": (
        "guide/wolf-unpack-repack/index.html",
        "guide/integrated-replacement/index.html",
        "guide/exe-patch/index.html",
        "guide/raw-filename-replacement/index.html",
    ),
    "guide/ctf/index.html": (
        "guide/metadata-check/index.html",
        "guide/title-change-ctf/index.html",
        "guide/language-change/index.html",
        "guide/ctf-crypter/index.html",
    ),
    "guide/tyrano/index.html": (
        "guide/asar-tyrano/index.html",
        "guide/title-change-tyrano/index.html",
    ),
    "guide/kirikiri/index.html": (
        "guide/utf-16le-conversion/index.html",
    ),
    "guide/pgmmv/index.html": (
        "guide/pgmmv-crypter/index.html",
    ),
    "guide/electron/index.html": (
        "guide/asar/index.html",
    ),
    "guide/renpy-tools/index.html": (
        "guide/renpy-crypter/index.html",
        "guide/renpy-tag-check/index.html",
        "guide/renpy-font-replacement/index.html",
    ),
    "guide/srpg-studio-tools/index.html": (
        "guide/srpg-studio-unpack/index.html",
        "guide/srpg-studio-manual-build/index.html",
        "guide/srk-crypter/index.html",
    ),
    "guide/quickslot/index.html": (
        "guide/memo/index.html",
        "guide/quickslot-quick-translation/index.html",
    ),
}

WORKSPACE_TOOL_NAV_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "workspace-utilities",
        "유틸리티",
        (
            "guide/fill-blanks/index.html",
            "guide/user-dictionary-prepost/index.html",
            "guide/undo-apply/index.html",
            "guide/translation-consistency/index.html",
            "guide/extraction-duplicates/index.html",
            "guide/escape-check/index.html",
            "guide/final-consonant-cleanup/index.html",
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
            "guide/ttc-build/index.html",
            "guide/save-editor/index.html",
            "guide/llama-server/index.html",
        ),
    ),
)

WORKSPACE_ENGINE_TOOL_PAGE_PATHS: tuple[str, ...] = tuple(
    child_path
    for parent_path in FEATURE_ENGINE_TOOL_GROUP_TITLES
    for child_path in FEATURE_NESTED_CHILD_PATHS_BY_PARENT.get(parent_path, ())
)

WORKSPACE_TOOL_PAGE_PATHS: tuple[str, ...] = (
    "guide/workspace-tools/index.html",
    *(child_path for _group_id, _title, child_paths in WORKSPACE_TOOL_NAV_GROUPS for child_path in child_paths),
    *WORKSPACE_ENGINE_TOOL_PAGE_PATHS,
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
    "무엇을 조정하는 설정인가요?",
    "이 단계의 목적",
    "이 단계는 무엇인가요?",
    "이 엔진에서 확인할 것",
    "이 참고 문서의 범위",
    "언제 필요한가요?",
    "언제 사용하나요?",
    "언제 진행하나요?",
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


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{_escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


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
    markers = [
        r"<h2[^>]*>\s*항목별 설명\s*</h2>",
        r"<h2[^>]*>\s*고급 사용자 참고\s*</h2>",
        r"<h2[^>]*>\s*질문과 답변\s*</h2>",
        r"<h2[^>]*>\s*화면과 항목\s*</h2>",
        r"<h2[^>]*>\s*화면/항목 설명\s*</h2>",
        r"<h2[^>]*>\s*참고 내용\s*</h2>",
        r"<h2[^>]*>\s*명령 코드 참고\s*</h2>",
    ]
    starts: list[tuple[int, int]] = []
    for marker in markers:
        starts.extend((match.start(), match.end()) for match in re.finditer(marker, value, flags=re.IGNORECASE))
    if not starts:
        return value
    _start, body_start = sorted(starts)[-1]
    tail = value[body_start:]
    stop = re.search(
        r"(?is)<h2[^>]*>\s*(?:변경 전 확인할 중요 사항|완료 후 확인|완료 기준|결과 확인 방법|주의/중요/권장|알아둘 점|자주 헷갈리는 점|주의|그래도 해결되지 않을 때)\s*</h2>",
        tail,
    )
    return tail[: stop.start()] if stop else tail


def _replace_article_safe(text: str, article: str) -> str:
    clean = re.sub(r"\s*contenteditable=[\"']true[\"']", "", article, flags=re.IGNORECASE)
    clean = clean.replace(" is-selected-image", "")
    main_re = re.compile(r"(?is)(<main\b[^>]*class=[\"'][^\"']*content-shell[^\"']*[\"'][^>]*>).*?(</main>)")
    return main_re.sub(lambda match: f"{match.group(1)}\n{clean}\n{match.group(2)}", text, count=1)


def _git_source_text_for(path: str) -> str:
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
        return ""


def _article_from_current_or_git(path: str, current_text: str) -> tuple[str, str, bool]:
    """Return article source and title source, preferring the current file.

    Expected failures:
        ValueError is raised when neither the current file nor the committed
        fallback has an article.guide-content block.
    """

    try:
        current_article = edit_guide.extract_article(current_text)
        return current_article, current_text, True
    except ValueError:
        git_text = _git_source_text_for(path)
        if not git_text:
            raise
        return edit_guide.extract_article(git_text), git_text, False


PAGE_TYPE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "home": ("manual_scope", "start_decision", "core_workflow", "engine_routes", "frequent_tasks", "safe_use"),
    "hub": ("area_goal", "direct_links", "suggested_path"),
    "feature": ("task_goal", "use_cases", "readiness", "procedure", "details", "verification", "decision_notes", "common_mistakes"),
    "workflow": ("step_goal", "entry_conditions", "readiness", "procedure", "details", "done_definition"),
    "engine": ("engine_scope", "readiness", "procedure", "details", "verification", "decision_notes"),
    "troubleshooting": ("triage", "diagnosis_steps", "faq_content", "support_packet"),
    "advanced_reference": ("reference_scope", "change_guard", "reference_content"),
    "command_reference": ("command_scope", "change_guard", "command_content"),
}

PAGE_TYPE_BY_PATH: dict[str, str] = {
    "guide/index.html": "home",
    "guide/basic-workflow/index.html": "workflow",
    "guide/faq/index.html": "troubleshooting",
    "guide/rpg-maker-command-code-reference/index.html": "command_reference",
    "guide/exclude-exception-regex/index.html": "feature",
    "guide/replacement-terms/index.html": "feature",
    "guide/default-font-settings/index.html": "feature",
    "guide/title-text/index.html": "feature",
    "guide/multiline-db/index.html": "feature",
    "guide/extract-troop-names/index.html": "feature",
    "guide/extract-names/index.html": "feature",
    "guide/dbdic-include-extract-names/index.html": "feature",
    "guide/merge-101-401/index.html": "feature",
    "guide/apply-exclude-regex-to-401-block/index.html": "feature",
    "guide/401-extract-mode/index.html": "feature",
    "guide/flatten-mode/index.html": "feature",
    "guide/include-text-type/index.html": "feature",
    "guide/include-speaker-name/index.html": "feature",
    "guide/include-tl-translations/index.html": "feature",
    "guide/401-block-unit-for-consistency-duplicate/index.html": "feature",
}

PAGE_TYPE_BY_PATH.update(
    {path: "feature" for path in WORKSPACE_TOOL_PAGE_PATHS if path != "guide/workspace-tools/index.html"}
)
PAGE_TYPE_BY_PATH["guide/workspace-tools/index.html"] = "hub"

PAGE_METADATA: dict[str, dict[str, Any]] = {
    "guide/index.html": {
        "title": "AIMT 사용설명서",
        "about": "AIMT는 게임 파일에서 번역할 문장을 추출하고, AI 또는 번역 서비스를 이용해 번역한 뒤, 결과를 다시 게임에 적용하도록 돕는 프로그램입니다.",
        "first_steps": [
            "번역할 게임 형식을 확인합니다.",
            "AIMT에서 프로젝트 폴더를 지정합니다.",
            "AI 번역을 사용할 경우 API 키와 사용할 모델을 준비합니다.",
            "추출할 언어와 번역 방향을 확인합니다.",
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
            ("guide/rpg-maker-mvmz/index.html", "RPG Maker MV/MZ"),
            ("guide/rpg-maker-vxvxa/index.html", "RPG Maker VX/VXA"),
            ("guide/wolf-rpg-editor/index.html", "WOLF RPG Editor"),
            ("guide/clickteam-fusion-coming-soon/index.html", "ClickTeam Fusion"),
            ("guide/tyranobuilder-tyranoscript/index.html", "TyranoBuilder/TyranoScript"),
            ("guide/pixel-game-maker-mv/index.html", "Pixel Game Maker MV"),
            ("guide/srpg-studio/index.html", "SRPG Studio"),
            ("guide/livemaker/index.html", "LiveMaker"),
            ("guide/bakin/index.html", "Bakin"),
            ("guide/renpy/index.html", "Ren'Py"),
            ("guide/csv-tsv/index.html", "CSV/TSV"),
            ("guide/multi-regex-engines/index.html", "HTML·범용 정규식 엔진"),
        ],
        "frequent_links": [
            ("guide/basic-workflow/index.html", "기본 작업 흐름"),
            ("guide/api-key-settings/index.html", "API KEY 설정"),
            ("guide/ai-model/index.html", "AI-MODEL"),
            ("guide/translation-settings/index.html", "번역 설정"),
            ("guide/extraction/index.html", "추출"),
            ("guide/translation/index.html", "번역"),
            ("guide/apply-and-instant-apply/index.html", "적용과 즉시적용"),
            ("guide/faq/index.html", "자주 나오는 질문"),
        ],
        "notices": [("주의", "게임 형식마다 추출 가능한 텍스트와 적용 방식이 다릅니다. 처음 작업하는 형식은 엔진별 가이드를 먼저 확인하세요.")],
    },
    "guide/basic-workflow/index.html": {
        "summary": "AIMT로 처음 번역할 때 필요한 전체 순서입니다. 프로젝트를 고른 뒤 추출, 번역, 적용을 거쳐 게임에서 결과를 확인합니다.",
        "when": [
            "AIMT로 새 번역 작업을 시작할 때",
            "현재 작업이 어느 단계인지 헷갈릴 때",
            "엔진별 가이드를 읽기 전에 전체 순서를 먼저 익히고 싶을 때",
        ],
        "before": [
            "번역할 게임의 엔진을 확인합니다.",
            "원본 게임 폴더를 복사해 작업본을 준비합니다.",
            "AI 번역을 쓰려면 API 키와 모델을 설정합니다.",
            "해당 엔진의 가이드에서 필요한 준비 사항을 확인합니다.",
        ],
        "steps": [
            "Project Hub에서 새 프로젝트를 만들거나 기존 프로젝트를 엽니다.",
            "게임 엔진과 프로젝트 경로가 맞는지 확인합니다.",
            "추출을 실행하고 번역할 파일과 문장이 제대로 들어왔는지 확인합니다.",
            "필요한 파일만 선택해 번역합니다.",
            "번역 결과를 살펴본 뒤 게임에 적용합니다.",
            "게임을 실행해 대사, 메뉴, 선택지, 글자 표시와 줄바꿈을 확인합니다.",
        ],
        "result": [
            "AIMT 프로젝트에 추출 결과와 번역 결과가 생성됩니다.",
            "게임 화면에 번역문이 반영됩니다.",
            "대사, 메뉴, 선택지에 빠진 문장이 없고 글자가 깨지지 않습니다.",
        ],
        "details_title": "단계별 안내",
        "links": [
            ("guide/project-selection/index.html", "Project Hub"),
            ("guide/extraction/index.html", "추출"),
            ("guide/translation/index.html", "번역"),
            ("guide/apply-and-instant-apply/index.html", "적용과 즉시적용"),
            ("guide/faq/index.html", "자주 나오는 질문"),
        ],
    },
    "guide/workspace-tools/index.html": {
        "summary": "작업 도구는 번역 작업 중 텍스트를 정리하거나 결과를 점검할 때 쓰는 보조 기능을 모은 화면입니다.",
        "when": ["번역 결과를 점검하거나 정리할 때", "사용자사전, 일관성, 코드 복원처럼 보조 기능이 필요할 때", "엔진별 보조 도구로 이동해야 할 때"],
        "before": ["작업 중인 프로젝트가 올바르게 지정되어 있는지 확인합니다.", "어떤 파일이나 결과를 수정하려는지 먼저 확인합니다.", "결과를 되돌려야 할 수 있다면 작업 전 파일을 보관합니다."],
        "steps": ["필요한 도구 묶음을 확인합니다.", "사용할 기능 문서로 이동합니다.", "기능별 안내에 따라 실행합니다.", "완료 메시지와 결과 파일을 확인합니다."],
    },
    "guide/livemaker/index.html": {
        "summary": "LiveMaker 번역 가이드는 LiveMaker 게임을 AIMT에서 추출, 번역, 적용할 때 확인해야 할 흐름을 정리한 문서입니다.",
        "when": ["LiveMaker 게임을 처음 번역할 때", "적용 후 한글 폰트나 표시 문제가 있는지 확인해야 할 때", "LiveMaker 전용 설정과 기본 작업 흐름을 함께 봐야 할 때"],
        "before": ["작업할 게임이 LiveMaker 계열인지 확인합니다.", "원본 파일과 작업본을 분리해 보관합니다.", "한글 표시를 확인할 수 있도록 게임을 실행할 준비를 합니다."],
        "steps": ["AIMT에서 프로젝트를 지정합니다.", "LiveMaker 형식으로 추출을 진행합니다.", "추출 결과를 열어 대사, 선택지, UI 문구가 들어왔는지 확인합니다.", "필요한 번역 설정을 확인하고 번역합니다.", "적용 후 게임을 실행해 글자 표시와 줄바꿈을 확인합니다."],
        "result": ["대사와 메뉴가 게임 화면에서 정상적으로 표시되는지 확인합니다.", "한글이 깨지거나 네모로 보이면 LiveMaker 폰트 설정을 확인합니다.", "누락 문장이 있으면 추출 범위와 원본 파일 상태를 다시 확인합니다."],
    },
    "guide/srpg-studio/index.html": {
        "summary": "SRPG Studio 번역 가이드는 SRPG Studio 게임의 추출 범위, 2차 추출 필터, 적용 후 확인 흐름을 정리한 문서입니다.",
        "when": ["SRPG Studio 게임을 처음 번역할 때", "이벤트, 이름/설명, String Table, JS Plugin 문구의 추출 범위를 조정해야 할 때", "2차 추출 결과가 너무 넓거나 좁을 때"],
        "before": ["작업할 게임이 SRPG Studio 계열인지 확인합니다.", "원본과 작업본을 분리해 보관합니다.", "2차 추출 필터는 제외 필터가 아니라 추출할 대상을 지정하는 설정임을 확인합니다."],
        "steps": ["AIMT에서 프로젝트를 지정합니다.", "SRPG Studio 형식으로 1차 추출을 진행합니다.", "필요하면 SRPG 2차 추출 필터에서 추출할 대상을 조정합니다.", "2차 추출 결과에서 실제 번역 대상이 들어왔는지 확인합니다.", "번역과 적용을 진행한 뒤 게임에서 이벤트와 메뉴를 확인합니다."],
        "result": ["필요한 이벤트 문장과 이름/설명이 추출되었는지 확인합니다.", "불필요한 항목이 많으면 2차 추출 필터 조건을 좁힙니다.", "필요한 문장이 빠지면 포함 조건을 넓히고 다시 추출합니다."],
        "notices": [("중요", "SRPG 2차 추출 필터는 기본적으로 포함할 대상을 지정합니다. 다른 엔진의 제외 필터처럼 이해하지 않도록 주의하세요.")],
    },
    "guide/bakin/index.html": {
        "summary": "Bakin 번역 가이드는 RBR 직접 번역과 dic.txt 사전 방식을 나누어 추출, 번역, 적용 순서를 설명합니다.",
        "when": ["Bakin 게임을 처음 번역할 때", "RBR 직접 번역과 사전 방식 중 작업 경로를 정할 때", "2차 추출 결과에 불필요한 후보가 많이 섞일 때"],
        "before": ["작업할 게임이 Bakin 계열인지 확인합니다.", "원본과 작업본을 분리해 보관합니다.", "RBR 직접 번역과 dic.txt 사전 방식 중 사용할 방식을 정합니다.", "2차 추출 제외 필터는 조건과 일치하는 후보를 제외하는 설정임을 확인합니다."],
        "steps": ["Project Hub에서 Bakin 프로젝트를 엽니다.", "Extract1과 Extract2를 실행하고 필요한 문장을 확인합니다.", "필요한 JSON을 번역하고 검수합니다.", "RBR 직접 번역에서 필요하면 Apply1 전에 폰트를 교체합니다.", "선택한 방식에 맞춰 Apply1과 Apply2를 실행합니다.", "게임을 실행해 번역과 폰트 표시를 확인합니다."],
        "result": ["필요한 문장이 번역되었는지 확인합니다.", "RBR 직접 번역에서는 data.rbpack과 폰트 표시를 확인합니다.", "사전 방식에서는 dic.txt와 player override 적용을 확인합니다."],
        "notices": [("중요", "dic.txt는 사전 방식에서만 사용합니다."), ("주의", "Bakin 2차 추출 제외 필터는 조건과 일치하는 항목을 빼는 방식입니다. 추출 결과에서 필요한 문장이 함께 제외되지 않았는지 확인하세요.")],
    },
    "guide/csv-tsv/index.html": {
        "summary": "CSV/TSV 번역 가이드는 프로젝트 아래의 표 형식 파일에서 지정한 열을 추출하고 번역 결과를 원하는 열에 적용하는 흐름을 설명합니다.",
        "when": ["CSV 또는 TSV 파일을 직접 번역할 때", "원문 열과 번역문 열을 나누어 적용할 때", "Project Viewer의 직접 편집이 아니라 추출, 번역, 적용 흐름이 필요할 때"],
        "before": ["Project Hub에서 CSV/TSV 엔진과 프로젝트 루트를 선택합니다.", "원본 파일을 별도로 보관합니다.", "헤더 미리보기에서 열 번호와 인코딩을 확인합니다."],
        "steps": ["추출을 눌러 감지된 파일을 확인합니다.", "추출할 열, 헤더 제외, 구분자, 인코딩과 언어 필터를 정합니다.", "CSV_로 시작하는 추출 JSON을 확인하고 번역합니다.", "적용할 열과 저장 인코딩을 확인한 뒤 적용합니다.", "결과 파일을 열거나 사용하는 프로그램에서 결과를 확인합니다."],
        "result": ["선택한 열의 문장만 추출되었는지 확인합니다.", "번역문이 지정한 적용 열에 들어갔는지 확인합니다.", "구분자, 글자 인코딩과 따옴표 형식이 대상 프로그램에서 정상인지 확인합니다."],
        "notices": [("중요", "TSV는 화면의 구분자 선택과 관계없이 탭을 사용합니다. CSV는 선택한 구분자를 사용합니다."), ("주의", "적용은 원본 표 파일을 수정합니다. AIMT가 적용 전에 백업하고 실패 시 복구하지만, 원본 사본도 따로 보관하세요.")],
    },
    "guide/multi-regex-engines/index.html": {
        "summary": "범용 정규식 엔진 가이드는 Custom, LIGHTVN, GameMaker, Electron, HTML 파일에서 저장한 추출정규식으로 문장을 찾아 번역하고 적용하는 흐름을 설명합니다.",
        "when": ["전용 엔진 대신 JSON, JS, TXT 또는 HTML 파일을 정규식으로 처리할 때", "기본 패턴으로 필요한 문장이 잡히지 않을 때", "코드와 식별자의 과다 추출을 줄여야 할 때"],
        "before": ["대상 파일 종류와 검색 위치가 선택한 엔진에 맞는지 확인합니다.", "설정의 추출정규식에서 사용할 패턴을 확인합니다.", "원본 프로젝트를 별도로 보관합니다."],
        "steps": ["Project Hub에서 대상 엔진과 프로젝트를 선택합니다.", "필요하면 추출정규식의 엔진별 패턴을 수정하고 저장합니다.", "추출을 실행하고 패턴별 JSON과 매핑을 확인합니다.", "필요한 JSON만 번역합니다.", "적용한 뒤 프로젝트를 실행하거나 파일을 열어 결과를 확인합니다."],
        "result": ["필요한 문장 전체가 추출되었는지 확인합니다.", "코드, 경로와 식별자가 번역 대상에 섞이지 않았는지 확인합니다.", "적용 후 파일 인코딩과 실행 결과가 정상인지 확인합니다."],
        "notices": [("중요", "저장한 정규식은 다음 추출부터 적용됩니다. 기존 추출 결과는 자동으로 바뀌지 않습니다.")],
    },
    "guide/srpg-studio-unpack/index.html": {
        "summary": "언팩은 SRPG Studio 프로젝트의 패키지 파일을 작업 가능한 형태로 풀어 번역 준비를 돕는 보조 도구입니다.",
        "when": ["SRPG Studio 게임 파일을 바로 추출하기 어렵거나 패키지 상태로 묶여 있을 때", "번역 전에 내부 데이터와 리소스 구성을 확인해야 할 때", "수동 빌드나 SRK 크립터 작업 전에 원본 구성을 풀어야 할 때"],
        "before": ["현재 대상이 SRPG Studio 계열인지 확인합니다.", "언팩 전 원본 파일을 따로 보관합니다.", "출력 폴더에 기존 작업 결과가 있다면 덮어쓰기나 혼선을 피하도록 정리합니다."],
        "steps": ["작업 도구의 SRPG Studio 영역에서 언팩을 선택합니다.", "언팩할 원본 파일 또는 폴더를 확인합니다.", "출력 위치와 완료 메시지를 확인합니다.", "생성된 파일 구성을 열어 추출 대상이 준비되었는지 확인합니다."],
        "result": ["출력 폴더에 필요한 데이터와 리소스가 풀렸는지 확인합니다.", "AIMT에서 추출할 수 있는 상태인지 확인합니다.", "실패하면 원본 파일 형식과 파일 잠금 상태를 확인합니다."],
        "notices": [("중요", "언팩은 원본 구조를 작업용으로 푸는 단계입니다. 원본을 직접 덮어쓰지 않도록 작업본을 분리하세요.")],
    },
    "guide/srpg-studio-manual-build/index.html": {
        "summary": "수동 빌드는 SRPG Studio 작업 결과를 사용자가 확인한 파일 구성으로 다시 묶거나 실행 가능한 작업본으로 정리할 때 사용하는 보조 도구입니다.",
        "when": ["자동 적용 후 직접 파일 구성을 확인하며 빌드해야 할 때", "언팩한 결과를 수정한 뒤 다시 실행 가능한 형태로 정리해야 할 때", "적용 결과를 단계별로 비교하며 마무리해야 할 때"],
        "before": ["번역 적용 결과가 준비되어 있어야 합니다.", "빌드 대상 폴더와 출력 위치를 구분합니다.", "빌드 전 현재 작업본을 보관하고, 원본 파일과 섞이지 않도록 확인합니다."],
        "steps": ["작업 도구의 SRPG Studio 영역에서 수동 빌드를 선택합니다.", "빌드에 사용할 작업 폴더를 확인합니다.", "출력 위치와 빌드 옵션을 확인합니다.", "빌드를 실행하고 완료 메시지를 확인합니다.", "생성된 결과를 실행해 번역문과 리소스 로딩 상태를 확인합니다."],
        "result": ["빌드 결과물이 지정한 위치에 생성되었는지 확인합니다.", "게임을 실행해 시작 화면, 이벤트, 메뉴 표시를 확인합니다.", "누락 파일이나 로딩 오류가 있으면 빌드 대상 폴더 구성을 다시 확인합니다."],
    },
    "guide/srk-crypter/index.html": {
        "summary": "SRK 크립터는 SRPG Studio 계열 작업에서 SRK 파일을 암호화하거나 복호화해야 할 때 사용하는 보조 도구입니다.",
        "when": ["SRK 파일 내용을 확인하거나 수정해야 할 때", "언팩 또는 빌드 과정에서 SRK 파일 처리가 필요할 때", "적용 후 SRK 관련 리소스가 정상적으로 읽히는지 확인해야 할 때"],
        "before": ["처리할 파일이 SRK 형식인지 확인합니다.", "복호화 또는 암호화 전 원본 파일을 보관합니다.", "잘못된 방향으로 처리하면 게임에서 파일을 읽지 못할 수 있으므로 작업 방향을 먼저 정합니다."],
        "steps": ["작업 도구의 SRPG Studio 영역에서 SRK 크립터를 선택합니다.", "처리할 SRK 파일 또는 폴더를 확인합니다.", "복호화 또는 암호화 작업 방향을 선택합니다.", "실행 후 완료 메시지와 출력 파일을 확인합니다.", "필요하면 게임 실행으로 리소스 로딩 상태를 확인합니다."],
        "result": ["출력 파일이 생성되었는지 확인합니다.", "복호화 결과는 열람 또는 후속 작업이 가능한지 확인합니다.", "암호화 결과는 게임에서 정상적으로 읽히는지 확인합니다."],
        "notices": [("주의", "SRK 파일은 작업 방향이 중요합니다. 원본 보관 없이 덮어쓰지 말고, 처리 후 실행 확인까지 진행하세요.")],
    },
    "guide/title-change-tyrano/index.html": {
        "summary": "타이틀 변경 (Tyrano)은 Tyrano 계열 프로젝트의 Config.tjs에서 ;System.title= 값을 찾아 새 타이틀로 바꾸는 도구입니다.",
        "when": ["번역본의 게임 제목을 원문 제목에서 번역 제목으로 바꾸고 싶을 때", "Tyrano 프로젝트의 Config.tjs에 남아 있는 제목만 빠르게 수정하고 싶을 때", "적용 후 실행 창 제목이 의도한 이름으로 표시되는지 확인하고 싶을 때"],
        "before": ["현재 프로젝트가 Tyrano 계열 작업본인지 확인합니다.", "프로젝트 안에 Config.tjs가 있어야 합니다.", "Config.tjs는 UTF-8로 읽을 수 있어야 합니다.", "Config.tjs 안에 ;System.title= 항목이 있어야 합니다.", "이 도구는 대상 파일을 직접 저장하므로 실행 전 현재 작업본을 보관해 두세요."],
        "steps": ["작업 도구에서 타이틀 변경 (Tyrano)을 엽니다.", "입력창에 표시되는 현재 타이틀을 확인합니다.", "새 Tyrano 타이틀을 입력합니다.", "빈 값이 아닌지 확인한 뒤 실행합니다.", "CMD 화면과 알림에서 완료 메시지를 확인합니다.", "게임을 실행해 창 제목이나 표시 제목이 의도대로 바뀌었는지 확인합니다."],
        "result": ["완료 메시지에 입력한 제목이 표시되는지 확인합니다.", "Config.tjs의 ;System.title= 값이 새 제목으로 바뀌었는지 확인합니다.", "게임을 실행해 창 제목이나 게임 내 표시 제목이 의도한 이름으로 보이는지 확인합니다.", "변경되지 않았다면 다른 설정 파일이나 실행 파일 쪽에서 별도 제목을 쓰는 프로젝트인지 확인합니다."],
        "notices": [("중요", "이 도구는 Config.tjs를 직접 수정합니다. 실행 전 작업본을 보관하고, 변경 후 실제 실행 화면을 확인하세요."), ("주의", "Config.tjs가 UTF-8이 아니거나 ;System.title= 항목이 없으면 변경할 수 없습니다. 이 경우 파일 구조를 먼저 확인해야 합니다."), ("권장", "제목만 바꾸는 기능입니다. 창 아이콘, 실행 파일 이름, 패키지 메타데이터까지 바꾸려면 별도로 확인하세요.")],
        "confusion": [("게임 안의 모든 제목 이미지도 바뀌나요?", "아닙니다. 이 도구는 Config.tjs의 텍스트 타이틀 값을 바꿉니다. 타이틀 화면 이미지나 로고 이미지가 따로 있으면 별도로 수정해야 합니다."), ("현재 타이틀이 알 수 없음으로 표시됩니다", "Config.tjs를 찾지 못했거나, 파일을 UTF-8로 읽지 못했거나, ;System.title= 항목이 없을 수 있습니다."), ("변경 후에도 실행 화면 제목이 그대로입니다", "게임이 다른 파일에서 제목을 다시 지정하거나 패키징된 결과물을 보고 있을 수 있습니다. 현재 작업본의 Config.tjs가 실제 실행 대상인지 확인하세요.")],
    },
    "guide/utf-16le-conversion/index.html": {
        "summary": "UTF-16LE 변환은 선택한 폴더 아래의 Kirikiri 계열 스크립트 파일을 찾아 UTF-16LE 형식으로 저장하는 도구입니다.",
        "when": ["Kirikiri 스크립트 파일을 UTF-16LE 인코딩으로 맞춰야 할 때", "번역 또는 편집 후 스크립트 파일의 글자가 깨져 보일 때", ".ks, .tjs, .ma, .asd 파일을 한 폴더 단위로 정리하고 싶을 때"],
        "before": ["변환할 폴더가 Kirikiri 스크립트 파일을 포함하고 있는지 확인합니다.", "이 도구는 선택한 폴더 아래를 재귀적으로 검사합니다. 하위 폴더의 대상 확장자 파일도 함께 처리될 수 있습니다.", "변환 대상 파일은 같은 위치에 다시 저장됩니다. 실행 전 원본을 보관해 두세요.", "이미 UTF-16LE로 판정된 파일은 스킵됩니다.", "대상 확장자 파일이 하나도 없으면 변환할 파일이 없다는 오류가 표시됩니다."],
        "steps": ["작업 도구에서 UTF-16LE 변환을 실행합니다.", "폴더 선택 안내가 표시되면 내용을 확인하고 계속합니다.", "변환할 폴더를 선택합니다.", "AIMT가 선택한 폴더 아래의 .ks, .tjs, .ma, .asd 파일을 검사합니다.", "CMD 화면에서 파일별 변환, 스킵, 실패 메시지를 확인합니다.", "완료 메시지에서 전체 파일 수, 변환 수, 스킵 수, 실패 수를 확인합니다.", "변환한 파일을 열어 한글, 일본어, 제어문자가 정상적으로 보이는지 확인합니다."],
        "result": ["완료 메시지의 전체 파일 수와 변환 수를 확인합니다.", "스킵 수가 많다면 이미 UTF-16LE인 파일이 많다는 뜻입니다.", "실패 수가 0보다 크면 CMD 화면의 파일별 실패 메시지를 확인합니다.", "변환된 스크립트를 텍스트 편집기로 열어 문자가 깨지지 않는지 확인합니다.", "게임을 실행해 대사, 메뉴, 스크립트 동작이 정상인지 확인합니다."],
        "notices": [("중요", "이 도구는 대상 파일을 같은 위치에 다시 저장합니다. 변환 전 폴더를 보관하고, 변환된 파일을 직접 열어 확인하세요."), ("주의", "줄바꿈은 변환 과정에서 정리될 수 있습니다. 줄바꿈 차이가 중요한 스크립트는 변환 전후를 비교하세요.")],
        "confusion": [("모든 파일을 UTF-16LE로 바꾸나요?", "아닙니다. .ks, .tjs, .ma, .asd 파일만 대상입니다."), ("이미 UTF-16LE인 파일도 다시 저장되나요?", "아닙니다. 이미 UTF-16LE로 판정된 파일은 스킵됩니다."), ("폴더를 잘못 선택하면 어떻게 되나요?", "선택한 폴더 아래에서 대상 확장자를 찾습니다. 대상 파일이 없으면 변환할 파일이 없다고 표시되고, 대상 파일이 있으면 해당 파일이 처리됩니다."), ("실패 항목이 있으면 전체 변환이 실패한 건가요?", "아닙니다. 파일별로 변환 결과가 나뉩니다. 실패한 파일은 따로 인코딩과 파일 잠금 상태를 확인하세요.")],
    },
    "guide/line-maker-mvmz/index.html": {
        "summary": "라인메이커 (MVMZ)는 RPG Maker MV/MZ 프로젝트의 data JSON 파일과 plugins.js를 AIMT가 다루기 쉬운 줄 구성으로 다시 정리하는 도구입니다.",
        "when": ["MVMZ 적용이나 수동 편집 후 JSON이 한 줄로 길게 붙어 있어 확인하기 어려울 때", "Map, CommonEvents, Troops, Scenario 같은 이벤트 명령 목록을 줄 단위로 보기 좋게 정리하고 싶을 때", "plugins.js의 플러그인 목록과 parameters 구조를 다시 정리해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "프로젝트 안에 data 폴더가 있어야 합니다.", "전체 실행 시 대상 JSON과 plugins.js가 같은 위치에 다시 저장됩니다. 실행 전 작업본을 보관하세요.", "라인메이커는 내용 번역이나 코드 의미 변경을 목적으로 하는 도구가 아닙니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 Line Maker를 실행합니다.", "AIMT가 현재 프로젝트의 data 폴더를 검사합니다.", "MVMZ 주요 데이터 파일, Scenario, Map 파일을 대상으로 처리합니다.", "전체 실행에서는 js/plugins.js가 있으면 함께 정리합니다.", "완료 메시지와 CMD 로그에서 처리 파일 수와 실패 파일을 확인합니다."],
        "result": ["완료 메시지에서 전체 처리 파일 수, 성공 수, 실패 수를 확인합니다.", "실패 파일이 있으면 CMD 로그의 파일명을 먼저 확인합니다.", "정리된 JSON을 열어 이벤트 명령이 줄 단위로 나뉘어 보이는지 확인합니다.", "게임을 실행해 정리 후에도 데이터 로딩 오류가 없는지 확인합니다."],
        "notices": [("중요", "라인메이커는 대상 파일을 같은 위치에 다시 저장합니다. 실행 전 현재 작업본을 보관하세요."), ("주의", "라인메이커는 게임 화면의 대사 줄 길이를 자동으로 맞추는 도구가 아닙니다. 실제 표시 줄바꿈은 게임 실행 화면에서 별도로 확인해야 합니다."), ("권장", "적용 결과를 비교하거나 수동 검수하기 전에 실행하면 변경 위치를 읽기 쉬워집니다.")],
        "confusion": [("대사 줄바꿈을 화면 폭에 맞춰 주나요?", "아닙니다. 파일 구조를 보기 좋게 정리하는 도구입니다. 대사 표시 폭과 줄바꿈은 게임에서 직접 확인해야 합니다."), ("모든 JSON 파일을 처리하나요?", "아닙니다. MVMZ에서 사용하는 주요 데이터 파일과 Map, Scenario 파일을 중심으로 처리합니다."), ("plugins.js도 항상 처리되나요?", "전체 실행에서는 plugins.js가 있으면 함께 처리합니다. 특정 파일만 대상으로 실행되는 흐름에서는 플러그인 파일 처리가 제외될 수 있습니다.")],
    },
    "guide/add-plugin/index.html": {
        "summary": "플러그인추가는 AIMT가 제공하거나 사용자가 가져온 MVMZ용 플러그인 파일을 현재 프로젝트에 추가하는 도구입니다.",
        "when": ["MVMZ 프로젝트에 번역 보조용 플러그인을 추가해야 할 때", "현재 프로젝트의 plugins.js에 플러그인 등록이 필요할 때", "이미 등록된 플러그인을 교체할지 확인해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "프로젝트 안에 js 폴더와 plugins.js를 쓸 수 있어야 합니다.", "기존 플러그인과 이름이 같거나 이미 등록되어 있으면 덮어쓰기 확인이 표시될 수 있습니다.", "플러그인 충돌 가능성이 있으므로 실행 전 프로젝트를 보관하세요."],
        "steps": ["작업 도구의 MVMZ 영역에서 Add Plugin을 엽니다.", "표시되는 플러그인 목록에서 추가할 .js 파일을 선택합니다.", "필요하면 플러그인 설명이나 도움말 내용을 확인합니다.", "추가를 실행합니다.", "이미 같은 파일이나 등록 정보가 있으면 덮어쓰기 여부를 선택합니다.", "프로젝트의 js/plugins와 plugins.js에서 반영 여부를 확인합니다."],
        "result": ["완료 메시지가 표시되는지 확인합니다.", "프로젝트의 js/plugins 폴더에 선택한 플러그인 파일이 있는지 확인합니다.", "plugins.js에 플러그인 이름이 등록되었는지 확인합니다.", "게임을 실행해 플러그인 로딩 오류나 기존 플러그인과의 충돌이 없는지 확인합니다."],
        "notices": [("중요", "플러그인추가는 파일 복사와 plugins.js 수정을 함께 수행할 수 있습니다. 실행 전 프로젝트를 보관하세요."), ("주의", "같은 이름의 플러그인을 덮어쓰면 기존 플러그인 내용이 바뀔 수 있습니다. 덮어쓰기 전 대상이 맞는지 확인하세요."), ("권장", "플러그인을 추가한 직후에는 게임을 한 번 실행해 콘솔 오류와 플러그인 충돌 여부를 확인하세요.")],
        "confusion": [("파일만 복사하나요?", "아닙니다. 새 플러그인을 추가할 때는 파일 복사와 함께 plugins.js 등록도 시도합니다."), ("이미 등록된 플러그인은 어떻게 되나요?", "이미 등록되어 있거나 파일이 존재하면 덮어쓰기 확인이 표시될 수 있습니다. 취소하면 변경하지 않습니다."), ("플러그인을 추가하면 바로 게임에 적용되나요?", "프로젝트 파일에는 반영되지만, 실제 동작 여부는 게임 실행으로 확인해야 합니다.")],
    },
    "guide/401-merge-split/index.html": {
        "summary": "401 병합 & 분할은 MVMZ 이벤트 명령의 401 대사 줄을 합치거나 다시 나누는 도구입니다.",
        "when": ["여러 줄로 나뉜 401 대사를 한 번에 번역하거나 검수하기 쉬운 단위로 합치고 싶을 때", "병합된 401 텍스트를 게임 적용 전 원래처럼 여러 401 줄로 다시 나눠야 할 때", "CommonEvents, Troops, Scenario, Map 파일의 401 대사 구조를 정리해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "대상 파일은 CommonEvents, Troops, Scenario, Map 계열 JSON입니다.", "병합과 분할은 프로젝트 JSON을 직접 수정합니다. 실행 전 작업본을 보관하세요.", "분할은 기본적으로 텍스트 안의 줄바꿈을 기준으로 나눕니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 Merge 401 또는 Split 401을 선택합니다.", "Merge 401을 선택했다면 병합 방식을 고릅니다.", "병합 방식은 줄바꿈, Half-space, None 중 선택합니다.", "AIMT가 CommonEvents, Troops, Scenario, Map 파일을 검사합니다.", "Merge 401은 같은 들여쓰기의 연속된 401을 첫 번째 401에 합치고 나머지 401을 제거합니다.", "Split 401은 줄바꿈이 들어간 401을 여러 401 명령으로 나눕니다."],
        "result": ["완료 메시지에서 병합 그룹 수, 제거된 401 수, 분할 그룹 수, 추가된 401 수를 확인합니다.", "수정된 Map 또는 이벤트 파일을 열어 대사 명령 순서가 유지되는지 확인합니다.", "게임을 실행해 대사창 표시와 선택지 흐름이 정상인지 확인합니다."],
        "notices": [("중요", "401 병합과 분할은 이벤트 명령 목록을 직접 수정합니다. 실행 전 작업본을 보관하고, 처리 후 실제 대사 장면을 확인하세요."), ("주의", "None 방식은 줄 사이 구분자가 사라집니다. 문장이 붙어도 괜찮은 경우에만 사용하세요."), ("권장", "번역 품질을 위해 병합했다면 적용 전에는 Split 401으로 구조를 되돌린 뒤 게임 화면을 확인하는 흐름이 안전합니다.")],
        "confusion": [("101 대사 표시 명령도 같이 바뀌나요?", "이 도구는 401 대사 줄을 대상으로 합니다. 101과 401을 함께 다루는 설정은 별도의 merge 101-401 설정을 확인하세요."), ("분할하면 항상 원본과 같은 줄 수가 되나요?", "기본 분할은 줄바꿈 기준입니다. 원본 기준 보충이 필요한 경우에는 원본 데이터와 비교해 부족한 401을 전각공백으로 보충할 수 있습니다."), ("모든 401이 하나로 합쳐지나요?", "아닙니다. 같은 들여쓰기에서 연속된 401 그룹만 병합됩니다.")],
    },
    "guide/402-sync/index.html": {
        "summary": "402 동기화는 MVMZ 선택지 명령의 102 항목과 그 결과 분기인 402 항목의 표시 텍스트를 맞추는 도구입니다.",
        "when": ["선택지 번역 후 402 분기 이름이 원문이나 이전 값으로 남아 있을 때", "선택지 표시문과 분기 조건 텍스트가 서로 다르게 보일 때", "Map, CommonEvents, Troops, Scenario 파일의 선택지 구조를 적용 전에 정리하고 싶을 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "선택지 명령 102와 분기 명령 402가 포함된 JSON 파일이 있어야 합니다.", "이 도구는 402의 표시 텍스트를 102 선택지 기준으로 직접 수정합니다.", "선택지 순서나 인덱스가 이미 손상된 경우 일부 402는 범위 밖 항목으로 처리될 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 Sync 402를 실행합니다.", "AIMT가 CommonEvents, Troops, Scenario, Map 파일을 검사합니다.", "각 명령 목록에서 같은 들여쓰기의 최신 102 선택지 목록을 기준으로 기억합니다.", "402 명령을 만나면 분기 인덱스에 해당하는 102 선택지 텍스트와 비교합니다.", "다르면 402의 표시 텍스트를 102 선택지 텍스트로 수정합니다.", "완료 메시지에서 검사한 402 수와 수정 수를 확인합니다."],
        "result": ["완료 메시지에서 수정된 402 수를 확인합니다.", "102 누락 또는 범위 밖 402 수가 있으면 해당 선택지 이벤트를 직접 확인합니다.", "게임을 실행해 선택지 문구와 선택 후 분기 흐름이 정상인지 확인합니다."],
        "notices": [("중요", "402 동기화는 선택지 분기 텍스트를 직접 수정합니다. 실행 전 작업본을 보관하고, 처리 후 실제 선택 장면을 확인하세요."), ("주의", "이 도구는 선택지 순서를 새로 판단하지 않습니다. 402 인덱스가 이미 잘못되어 있으면 범위 밖 항목으로 남을 수 있습니다."), ("권장", "선택지 번역을 수정한 뒤 적용 전에 Sync 402를 실행하면 선택지와 분기 표시가 어긋나는 문제를 줄일 수 있습니다.")],
        "confusion": [("선택지 순서도 자동으로 고치나요?", "아닙니다. 402가 가진 선택지 번호를 기준으로 텍스트만 맞춥니다."), ("102가 없는 402도 고쳐지나요?", "아닙니다. 기준이 될 102 선택지 목록을 찾지 못하면 누락 항목으로 집계되고 건너뜁니다."), ("선택지 번역 자체를 새로 번역하나요?", "아닙니다. 이미 저장된 102 선택지 텍스트를 기준으로 402 텍스트를 맞추는 도구입니다.")],
    },
    "guide/name-consistency/index.html": {
        "summary": "이름 일관성은 RPG Maker MV/MZ 이벤트 대사의 \\N<이름>, \\n<이름> 형식 이름 태그가 번역 후 여러 표기로 갈라졌는지 확인하고, 필요한 경우 한 표기로 맞추는 도구입니다.",
        "when": ["같은 이름 태그가 장면마다 서로 다른 번역으로 표시될 때", "번역 적용 전에 대사창 이름 표기를 한 번에 점검하고 싶을 때", "자동 번역 후 인물 이름 표기가 흔들렸는지 확인해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "원문 기준으로 비교하려면 번역 전 원본 data 폴더를 선택할 수 있어야 합니다.", "통일 적용은 현재 프로젝트 파일을 수정할 수 있으므로 실행 전 작업본을 보관합니다.", "이 도구는 일반 문장 속 고유명사가 아니라 대사 이름 태그를 중심으로 검사합니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 이름 일관성을 엽니다.", "원문 폴더 선택 안내가 나오면 원문 data 폴더를 선택합니다. 원문 기준이 필요 없다면 현재 프로젝트 기준으로 검사합니다.", "검사 결과에서 원문 이름 태그별 번역 후보와 사용 위치를 확인합니다.", "같은 이름으로 맞출 후보를 고릅니다.", "필요한 항목만 적용하거나, 자동 통일을 사용할 경우 결과를 확인한 뒤 반영합니다.", "게임을 실행해 해당 인물의 이름창 표시가 의도대로 보이는지 확인합니다."],
        "result": ["검사 결과에서 불일치 이름 태그 수와 후보 목록을 확인합니다.", "적용 후 같은 인물의 이름창이 여러 장면에서 같은 표기로 표시되는지 확인합니다.", "동명이인이나 의도적으로 다른 표기를 쓴 장면이 있다면 통일 대상에서 제외합니다."],
        "notices": [("중요", "같은 원문 이름 태그라도 장면에 따라 별칭, 가명, 호칭을 다르게 써야 할 수 있습니다. 적용 전 위치 목록을 확인하세요."), ("권장", "전체 통일을 한 번에 실행하기보다 불일치가 많은 이름부터 순서대로 확인하면 의도하지 않은 변경을 줄일 수 있습니다.")],
        "confusion": [("문장 속 인물 이름도 찾아 주나요?", "아닙니다. 이 도구는 대사 이름창에 쓰이는 이름 태그를 중심으로 검사합니다."), ("원문 폴더를 꼭 선택해야 하나요?", "원문 태그 기준으로 정확히 비교하려면 선택하는 편이 좋습니다. 원문 폴더가 없으면 현재 프로젝트에서 발견되는 태그를 기준으로 확인합니다."), ("자동 통일을 쓰면 항상 안전한가요?", "자동 통일은 사용 빈도와 표기 형태를 기준으로 후보를 고릅니다. 캐릭터 설정상 다른 표기가 필요한 경우에는 수동으로 확인하세요.")],
    },
    "guide/integrated-consistency/index.html": {
        "summary": "통합 일관성은 RPG Maker MV/MZ 이벤트 명령의 주요 텍스트 파라미터를 한꺼번에 검사해, 같은 원문이 여러 번역 표기로 갈라진 항목을 찾아 주는 도구입니다.",
        "when": ["대사, 선택지, 주석, 스크립트, 플러그인 명령 등 여러 영역의 번역 표기를 함께 점검할 때", "대규모 번역 후 같은 원문이 다른 번역으로 저장된 항목을 찾고 싶을 때", "적용 전에 반복 표현과 명령 파라미터 번역을 넓게 검수해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "원문 기준 비교가 필요하면 번역 전 원본 data 폴더를 준비합니다.", "이 도구는 여러 명령 코드를 대상으로 하므로, 적용 전 수정 범위를 반드시 확인합니다.", "같은 원문이라도 문맥에 따라 다른 번역이 필요한 항목은 통일 대상에서 제외합니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 통합 일관성을 엽니다.", "원문 폴더를 선택해 원문과 현재 번역 결과를 비교합니다.", "검사 결과를 명령 그룹별로 확인합니다.", "불일치 항목의 번역 후보와 사용 위치를 검토합니다.", "필요한 항목만 선택해 같은 번역으로 통일합니다.", "자동 통일을 사용할 경우 적용 전후 결과를 비교하고, 게임에서 해당 장면을 확인합니다."],
        "result": ["그룹별 불일치 수와 후보 목록을 확인합니다.", "적용한 항목이 의도한 명령 그룹에만 반영되었는지 확인합니다.", "대사, 선택지, 플러그인 명령처럼 게임 동작에 영향을 줄 수 있는 항목은 실제 장면에서 다시 확인합니다."],
        "notices": [("중요", "통합 일관성은 넓은 범위를 다룹니다. 같은 원문이라도 명령 종류나 장면에 따라 다른 번역이 필요한지 먼저 확인하세요."), ("권장", "먼저 검사 결과를 그룹별로 좁혀 보고, 대사나 선택지처럼 눈에 보이는 항목부터 통일하는 흐름이 안전합니다.")],
        "confusion": [("모든 텍스트를 검사하나요?", "아닙니다. MVMZ 이벤트 명령에서 AIMT가 지원하는 주요 텍스트 파라미터를 검사합니다."), ("이름 일관성과 무엇이 다른가요?", "이름 일관성은 대사 이름 태그에 집중합니다. 통합 일관성은 대사, 선택지, 주석, 스크립트, 플러그인 명령 등 여러 명령 그룹을 함께 봅니다."), ("자동 통일 후 바로 적용해도 되나요?", "자동 통일은 후보를 빠르게 고르는 보조 기능입니다. 실제 문맥이 맞는지는 결과 목록과 게임 화면에서 확인해야 합니다.")],
    },
    "guide/code-restore/index.html": {
        "summary": "코드 복원은 원본 data 폴더의 특정 RPG Maker MV/MZ 명령 코드 라인을 현재 프로젝트의 같은 위치로 가져와 덮어쓰는 도구입니다.",
        "when": ["번역 또는 수동 편집 중 특정 명령 코드 라인이 손상되어 원본으로 되돌려야 할 때", "선택지, 변수, 조건, 플러그인 명령 같은 기능 명령을 원본 구조로 복구해야 할 때", "적용 전 특정 코드 계열을 원본과 같은 명령 라인으로 맞추고 싶을 때"],
        "before": ["현재 프로젝트와 원본 data 폴더가 같은 게임 버전, 같은 파일 구성인지 확인합니다.", "복원할 코드가 들어 있는 원본 폴더를 선택할 수 있어야 합니다.", "복원 대상 명령 코드를 정확히 선택합니다. 선택한 코드 라인은 현재 프로젝트에서 원본 내용으로 덮어써질 수 있습니다.", "파일의 줄 수나 선택 코드 개수가 맞지 않는 파일은 건너뛸 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 코드 복원을 엽니다.", "복원 코드 선택 팝업에서 필요한 프리셋을 고르거나 직접 코드 번호를 입력합니다.", "원본 data 폴더를 선택합니다.", "AIMT가 원본 폴더와 현재 프로젝트의 같은 상대 경로 JSON 파일을 비교합니다.", "선택한 코드 번호의 명령 라인이 같은 개수로 발견되는 파일만 처리합니다.", "완료 후 처리 파일 수와 복원 라인 수를 확인합니다."],
        "result": ["완료 메시지에서 처리된 파일 수와 복원된 라인 수를 확인합니다.", "건너뛴 파일이 있으면 파일 구조나 줄 수가 원본과 달라졌는지 확인합니다.", "복원한 코드가 포함된 장면을 게임에서 실행해 이벤트 흐름이 정상인지 확인합니다."],
        "notices": [("중요", "코드 복원은 선택한 명령 코드 라인 전체를 원본으로 덮어쓸 수 있습니다. 해당 라인에 번역문이 들어 있다면 번역도 함께 사라질 수 있습니다."), ("권장", "처음에는 필요한 코드 번호만 좁게 선택하고, 처리 후 변경 파일을 비교해 의도한 라인만 바뀌었는지 확인하세요.")],
        "confusion": [("제어문자만 골라서 복원하나요?", "아닙니다. 선택한 명령 코드에 해당하는 JSON 라인을 원본 라인으로 교체하는 방식입니다."), ("원본과 현재 파일의 줄 수가 다르면 어떻게 되나요?", "안전하게 맞출 수 없는 파일은 건너뜁니다. 먼저 Line Maker나 구조 정리 도구로 파일 구조를 맞춘 뒤 다시 확인하세요."), ("복원 후 왜 대사가 원문으로 돌아갔나요?", "대사 코드인 401이나 405를 선택하면 해당 라인 전체가 원본으로 돌아갈 수 있습니다. 번역을 유지해야 한다면 대사 코드는 신중하게 선택하세요.")],
    },
    "guide/import-translation/index.html": {
        "summary": "번역 가져오기는 이전 작업의 원본 폴더와 번역된 폴더를 비교해 번역 대응표를 만들고, 현재 MVMZ 프로젝트에서 같은 원문을 찾으면 기존 번역을 가져오는 도구입니다.",
        "when": ["같은 게임의 새 작업본에 이전 번역을 최대한 재사용하고 싶을 때", "업데이트판이나 재추출 프로젝트에 기존 번역을 옮기고 싶을 때", "대사, 선택지, DB, 시스템, 노트 등 필요한 영역만 골라 가져오고 싶을 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "이전 작업의 원본 data 폴더와 이전 작업의 번역 완료 data 폴더를 모두 준비합니다.", "Font Settings를 가져오려면 이전 프로젝트의 폰트 설정과 파일도 확인합니다.", "가져올 대상 프리셋을 필요한 범위로만 선택합니다.", "게임 버전이 크게 다르면 일치하지 않는 항목이 늘어날 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 번역 가져오기를 엽니다.", "가져올 대상 프리셋을 선택합니다. 필요하면 코드나 카테고리를 직접 입력합니다.", "이전 작업의 원본 data 폴더를 선택합니다.", "이전 작업의 번역 완료 data 폴더를 선택합니다.", "Font Settings를 선택했다면 이전 프로젝트 폰트를 가져올 대상인지 확인합니다.", "AIMT가 이전 원문과 이전 번역을 비교해 현재 프로젝트에 일치하는 항목을 반영합니다.", "완료 메시지에서 일치, 미일치, 처리 파일 수를 확인합니다."],
        "result": ["완료 메시지의 matched, unmatched, processed files 값을 확인합니다.", "미일치가 많은 경우 이전 원본과 현재 프로젝트의 버전 차이 또는 추출 범위를 확인합니다.", "가져온 번역이 적용된 장면, DB 이름, 시스템 용어, 노트 기반 표시를 실제 게임에서 확인합니다.", "Font Settings를 선택했다면 이전 프로젝트의 폰트 설정과 파일이 반영됐는지 확인합니다."],
        "notices": [("중요", "번역 가져오기는 같은 원문을 기준으로 이전 번역을 재사용합니다. 현재 프로젝트에서 문맥이 달라진 항목은 가져온 뒤 반드시 검수하세요.")],
        "confusion": [("이전 번역 파일 하나만 있으면 되나요?", "아닙니다. 이전 원본과 이전 번역본이 모두 있어야 어떤 원문이 어떤 번역으로 바뀌었는지 비교할 수 있습니다."), ("Font Settings는 현재 프리셋을 적용하나요?", "아닙니다. 이전 번역 프로젝트의 폰트 설정과 파일을 가져오는 것이 기준 동작입니다. AIMT 1.17.0.0 구현은 현재 프리셋을 적용할 수 있어 결과 확인이 필요합니다."), ("빈 번역이나 코드만 있는 줄도 가져오나요?", "빈 번역은 가져오지 않습니다. 이벤트 대사 쪽에서는 제어코드만 있는 줄도 불필요한 치환을 피하기 위해 건너뛸 수 있습니다."), ("맵 표시 이름이 왜 안 바뀌나요?", "현재 프로젝트의 맵 표시 이름이 이전 원본과 다르면 같은 항목으로 보기 어려워 건너뛸 수 있습니다. 현재 원문과 이전 원문이 같은지 확인하세요.")],
    },
    "guide/escape-data/index.html": {
        "summary": "이스케이프 (data)는 원본 data 폴더와 현재 프로젝트 data 폴더의 주요 명령 파라미터를 비교해, 이스케이프 코드나 특수 표기가 번역 과정에서 깨졌는지 검사하고 수정 후보를 만드는 도구입니다.",
        "when": ["번역 후 대사, 선택지, 변수, 주석, 플러그인 명령 등의 제어 표기가 깨진 것처럼 보일 때", "원본에는 있던 이스케이프 코드가 번역 결과에서 빠졌는지 확인하고 싶을 때", "적용 전 원본 data 기준으로 위험 항목을 따로 뽑아 비교하고 싶을 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "번역 전 원본 data 폴더를 선택할 수 있어야 합니다.", "검사 결과는 check 영역의 data 복사본에 만들어지며, 현재 프로젝트 data를 바로 고치는 기능이 아닙니다.", "이전 검사 결과가 남아 있으면 새 검사 전에 정리될 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 이스케이프 (data)를 실행합니다.", "안내가 나오면 원본 data 폴더를 선택합니다.", "AIMT가 원본 data와 현재 프로젝트 data에서 비교 가능한 파라미터를 추출합니다.", "이스케이프 불일치, 전각공백 누락, 후행 공백, 문장부호 위치 문제를 검사합니다.", "수정이 필요한 항목이 있으면 check 영역에 수정본을 만듭니다.", "비교 화면이나 생성된 결과를 확인한 뒤 실제 반영 여부를 판단합니다."],
        "result": ["완료 메시지에서 비교한 파라미터 수와 수정 후보 수를 확인합니다.", "수정 파일이 생성되었다면 현재 프로젝트 data와 check 쪽 수정본을 비교합니다.", "이스케이프 불일치로 원문 전체가 후보에 들어간 항목은 번역문이 사라질 수 있으므로 반드시 직접 확인합니다."],
        "notices": [("중요", "이스케이프 불일치가 큰 항목은 원본 텍스트 전체를 수정 후보로 사용할 수 있습니다. 번역을 유지해야 하는 문장은 비교 후 수동으로 조정하세요."), ("권장", "검사 결과를 바로 믿기보다 원본, 현재 번역, 수정 후보를 나란히 확인한 뒤 필요한 항목만 반영하는 흐름이 안전합니다.")],
        "confusion": [("현재 프로젝트 data를 바로 수정하나요?", "아닙니다. 수정 후보는 check 영역의 data 복사본에 만들어집니다. 실제 반영은 비교 후 사용자가 판단해야 합니다."), ("일반 이스케이프 검사와 무엇이 다른가요?", "이스케이프 (data)는 번역 전 원본 data 폴더와 현재 프로젝트 data를 비교 기준으로 사용합니다."), ("수정 후보가 원문으로 돌아간 것처럼 보여요", "이스케이프 구조가 맞지 않으면 안전하게 원본 텍스트를 후보로 둘 수 있습니다. 해당 항목은 번역문과 제어코드를 함께 보며 수동으로 정리하세요.")],
    },
    "guide/mvmz-media-crypter/index.html": {
        "summary": "크립터 (이미지 / 오디오)는 RPG Maker MV/MZ의 암호화된 이미지와 오디오 리소스를 복호화하거나, 복호화된 리소스를 다시 암호화하는 도구입니다.",
        "when": ["암호화된 이미지 파일을 PNG로 확인하거나 편집해야 할 때", "암호화된 오디오 파일을 OGG 또는 M4A로 확인해야 할 때", "수정한 이미지나 오디오를 게임에서 사용할 수 있도록 다시 암호화해야 할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "복호화할 파일은 암호화 작업 폴더에, 다시 암호화할 파일은 복호화 작업 폴더에 있어야 합니다.", "복호화에는 이미지 또는 오디오 파일에서 찾을 수 있는 암호화 키가 필요합니다.", "암호화 작업은 프로젝트의 System.json에서 암호화 키를 읽을 수 있어야 합니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 크립터 (이미지 / 오디오)를 엽니다.", "이미지 또는 오디오를 선택합니다.", "Decrypt 또는 Encrypt를 선택합니다.", "Decrypt는 암호화된 파일을 복호화 작업 폴더로 변환합니다.", "Encrypt는 복호화된 파일을 암호화 작업 폴더로 변환합니다.", "완료 메시지에서 처리된 파일 수를 확인합니다."],
        "result": ["완료 메시지의 처리 파일 수를 확인합니다.", "복호화 후 이미지나 오디오가 정상적으로 열리는지 확인합니다.", "암호화 후 게임을 실행해 리소스 로딩 오류가 없는지 확인합니다."],
        "notices": [("중요", "작업 대상 폴더의 기존 결과 파일은 새 작업 전에 정리될 수 있습니다. 필요한 파일은 실행 전에 따로 보관하세요.")],
        "confusion": [("게임 폴더의 모든 리소스를 자동으로 찾아 처리하나요?", "아닙니다. 크립터 작업 폴더에 있는 지원 확장자 파일을 대상으로 처리합니다."), ("키를 직접 입력해야 하나요?", "일반적으로 복호화는 System.json이나 암호화된 파일에서 키를 찾고, 암호화는 현재 프로젝트의 System.json 키를 사용합니다. 키를 찾지 못하면 작업이 실패합니다."), ("이미지와 오디오는 함께 처리되나요?", "아닙니다. 이미지와 오디오는 선택한 파일 유형별로 따로 처리합니다.")],
    },
    "guide/data-decryption/index.html": {
        "summary": "Data 복호화는 현재 RPG Maker MV/MZ 프로젝트의 data JSON 파일이 특수 암호화 방식으로 저장되어 있을 때, 읽을 수 있는 JSON으로 복호화해 같은 위치에 덮어쓰는 도구입니다.",
        "when": ["data 폴더의 JSON 파일이 일반 텍스트 JSON처럼 열리지 않을 때", "MVMZ 추출 전에 data 파일을 먼저 읽을 수 있는 형태로 바꿔야 할 때", "게임이 별도 로더로 암호화된 data를 읽는 구조라 AIMT 추출이 실패할 때"],
        "before": ["현재 프로젝트가 RPG Maker MV/MZ 계열인지 확인합니다.", "프로젝트 안에 data 폴더와 System.json이 있어야 합니다.", "이 도구는 data JSON을 같은 위치에 덮어씁니다. 실행 전 프로젝트를 보관하세요.", "복호화 방식에 따라 js 폴더의 로더 파일도 평문 data를 읽도록 함께 수정될 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 Data 복호화를 실행합니다.", "확인 메시지에서 현재 프로젝트 data를 덮어써도 되는지 다시 확인합니다.", "AIMT가 현재 프로젝트의 data 폴더를 검사합니다.", "감지된 방식에 맞춰 data JSON을 복호화합니다.", "필요한 경우 게임의 data 로더 스크립트도 평문 JSON을 읽는 형태로 조정합니다.", "완료 메시지에서 처리된 파일 수와 대상 경로를 확인합니다."],
        "result": ["완료 메시지에서 처리된 파일 수를 확인합니다.", "data JSON을 열어 일반 JSON으로 읽히는지 확인합니다.", "게임을 실행해 데이터 로딩 오류가 없는지 확인한 뒤 추출을 진행합니다."],
        "notices": [("중요", "Data 복호화는 현재 프로젝트의 data JSON을 같은 위치에 덮어씁니다. 실행 전 반드시 프로젝트를 보관하세요."), ("주의", "복호화와 함께 로더 JS가 수정될 수 있습니다. 복호화 후 게임 실행 확인을 먼저 하고 다음 작업으로 넘어가세요.")],
        "confusion": [("이미지나 오디오도 복호화하나요?", "아닙니다. Data 복호화는 data JSON 중심입니다. 이미지와 오디오는 크립터 (이미지 / 오디오)를 사용합니다."), ("복호화 결과가 별도 폴더에 만들어지나요?", "아닙니다. 최종 결과는 현재 프로젝트 data 폴더에 같은 이름으로 반영됩니다."), ("실패하면 일부 파일만 바뀔 수 있나요?", "작업 중 오류가 발생하면 원래 파일로 되돌리도록 처리됩니다. 그래도 작업 전 프로젝트 보관은 필수입니다.")],
    },
    "guide/project-conversion/index.html": {
        "summary": "프로젝트 변환은 RPG Maker MV/MZ 배포본이나 data/www 구조의 게임 폴더를 AIMT에서 작업하기 쉬운 프로젝트 폴더로 복사하고, 암호화된 이미지와 오디오가 있으면 함께 복호화하는 도구입니다.",
        "when": ["배포된 MV/MZ 게임을 작업용 프로젝트 형태로 따로 만들고 싶을 때", "입력 경로가 게임 루트, www 폴더, data 폴더 중 어느 쪽인지 헷갈릴 때", "암호화된 이미지나 오디오를 함께 풀어 작업 가능한 복사본을 만들고 싶을 때"],
        "before": ["변환 소스 폴더에는 data/System.json을 찾을 수 있어야 합니다.", "출력 기준 폴더는 이미 존재하는 폴더여야 합니다.", "출력 기준 폴더를 입력 프로젝트 내부로 지정하면 안 됩니다.", "변환 결과는 원본을 직접 바꾸지 않고 새 Project 계열 폴더로 만들어집니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 프로젝트 변환을 엽니다.", "변환 소스 폴더에 MV/MZ 게임 폴더, www 폴더, data 폴더 중 하나를 지정합니다.", "출력 기준 폴더에 변환 결과를 만들 상위 폴더를 지정합니다.", "확인을 누르면 AIMT가 새 Project 계열 폴더를 생성합니다.", "소스 파일을 복사하고, 필요한 경우 이미지와 오디오 암호화를 해제합니다.", "완료 메시지에서 출력 폴더, 복사 파일 수, 복호화 파일 수를 확인합니다."],
        "result": ["완료 메시지의 출력 폴더를 엽니다.", "data, js, img, audio 등 필요한 폴더가 복사되었는지 확인합니다.", "복호화 파일 수가 표시되면 이미지나 오디오가 열리는지 확인합니다.", "변환된 폴더를 AIMT 프로젝트로 지정해 추출이 가능한지 확인합니다."],
        "notices": [("중요", "출력 기준 폴더는 원본 게임 폴더 밖으로 지정하세요. 원본 안에 결과를 만들면 변환이 실패하거나 파일 구분이 어려워집니다."), ("권장", "변환 후에는 새로 만들어진 Project 폴더를 작업 대상으로 사용하고, 원본 배포본은 그대로 보관하세요.")],
        "confusion": [("원본 프로젝트를 직접 바꾸나요?", "아닙니다. 소스 폴더를 복사해 출력 기준 폴더 아래에 새 Project 계열 폴더를 만듭니다."), ("data 폴더만 선택해도 되나요?", "data/System.json을 찾을 수 있으면 data 폴더, www 폴더, 게임 루트 중 하나를 선택할 수 있습니다."), ("텍스트 번역까지 자동으로 되나요?", "아닙니다. 프로젝트 변환은 작업 가능한 복사본을 만드는 단계입니다. 변환 후 프로젝트 지정, 추출, 번역, 적용 흐름을 진행해야 합니다.")],
    },
    "guide/enigma-unpack/index.html": {
        "summary": "에니그마 언팩은 Enigma Virtual Box로 패키징된 RPG Maker MV/MZ 실행 파일에서 포함된 VFS 파일을 선택한 출력 폴더로 풀어내는 도구입니다.",
        "when": ["게임 파일이 EXE 하나에 묶여 있어 data, js, img, audio 폴더를 바로 확인할 수 없을 때", "MVMZ 추출이나 프로젝트 변환을 진행하기 전에 패키징된 실행 파일의 내부 파일을 꺼내야 할 때", "Enigma Virtual Box 계열 패키징으로 보이는 실행 파일을 별도 출력 폴더에 풀어 확인하고 싶을 때"],
        "before": ["패키징된 EXE 파일을 선택할 수 있어야 합니다.", "출력 폴더는 이미 존재하는 폴더여야 합니다.", "출력 폴더 안에 같은 이름의 파일이 있으면 언팩 결과가 덮어쓸 수 있으므로, 빈 폴더나 새로 준비한 폴더를 사용하는 것이 좋습니다.", "이 도구는 Enigma Virtual Box VFS 형식을 대상으로 합니다. 다른 패키징 방식의 실행 파일은 실패할 수 있습니다."],
        "steps": ["작업 도구의 MVMZ 영역에서 에니그마 언팩을 엽니다.", "패키징된 EXE 항목에서 Enigma Virtual Box로 묶인 실행 파일을 선택합니다.", "출력 폴더 항목에서 언팩 결과를 저장할 기존 폴더를 선택합니다.", "확인을 누르면 AIMT가 CMD 화면으로 전환하고 언팩을 시작합니다.", "완료 메시지에서 출력 폴더, 추출된 파일 수, 감지된 포맷을 확인합니다.", "출력 폴더를 열어 data, js, img, audio 등 작업에 필요한 파일이 풀렸는지 확인합니다."],
        "result": ["완료 알림과 CMD 로그에 출력 폴더, 파일 수, 포맷이 표시되는지 확인합니다.", "출력 폴더에 게임 실행에 필요한 폴더와 파일이 생성되었는지 확인합니다.", "언팩된 폴더를 기준으로 AIMT 프로젝트 지정이나 프로젝트 변환을 이어서 진행할 수 있는지 확인합니다.", "실패했다면 선택한 EXE가 Enigma Virtual Box 패키징인지, 출력 폴더가 존재하고 쓸 수 있는지 먼저 확인합니다."],
        "notices": [("중요", "출력 폴더는 기존 폴더를 선택해야 하며, 같은 이름의 파일이 있으면 결과 파일이 덮어써질 수 있습니다. 새 작업용 폴더를 준비한 뒤 실행하세요."), ("주의", "지원하지 않는 패키징 방식이거나 VFS 정보를 찾을 수 없는 실행 파일은 언팩에 실패할 수 있습니다."), ("권장", "언팩이 끝난 뒤 바로 원본 EXE를 지우지 말고, 언팩 결과로 추출과 실행 확인이 가능한지 먼저 확인하세요.")],
        "confusion": [("에니그마 언팩이 번역까지 해주나요?", "아닙니다. 실행 파일 안의 파일을 꺼내는 준비 단계입니다. 언팩 후 프로젝트 지정, 추출, 번역, 적용 흐름을 진행해야 합니다."), ("출력 폴더를 새로 만들어 주나요?", "아닙니다. 사용자가 기존 폴더를 선택해야 합니다. 빈 작업용 폴더를 먼저 만들어 두면 결과를 구분하기 쉽습니다."), ("모든 EXE 파일을 풀 수 있나요?", "아닙니다. Enigma Virtual Box VFS 형식으로 패키징된 실행 파일을 대상으로 합니다. 다른 보호 도구나 다른 패키징 방식은 지원되지 않을 수 있습니다.")],
    },
    "guide/metadata-check/index.html": {
        "summary": "메타정보 확인은 CTF 소스의 게임 이름, Fusion 버전, 패키징 형태, 언어, 코드페이지, EXE 전용 여부와 청크 정보를 읽어 보여 주는 확인 도구입니다.",
        "when": ["CTF 작업 대상이 어떤 언어와 코드페이지로 구성되어 있는지 확인할 때", "타이틀 변경이나 언어 변경을 실행하기 전에 현재 메타데이터 값을 확인할 때", "DAT, CCN, EXE 중 실제로 어떤 소스를 기준으로 작업해야 할지 판단할 때", "CTF 적용 결과가 의도한 파일에 반영되었는지 CMD 로그와 함께 점검할 때"],
        "before": ["확인할 CTF 소스인 DAT, CCN, EXE 파일을 선택할 수 있어야 합니다.", "이 도구는 읽기 전용 확인 기능입니다. 파일 내용을 직접 바꾸지 않습니다.", "EXE를 선택한 경우 구조에 따라 연결된 DAT 또는 해석된 소스 기준으로 정보가 표시될 수 있습니다.", "메타정보가 비어 있거나 형식을 읽지 못하면 일부 항목이 알 수 없음으로 표시될 수 있습니다."],
        "steps": ["작업 도구의 CTF 영역에서 메타정보 확인을 실행합니다.", "CTF 소스 선택 화면에서 확인할 DAT, CCN, EXE를 선택합니다.", "CMD 화면에 표시되는 game_name, fusion, packaging, exe_only, locale, codepage 값을 확인합니다.", "필요하면 출력된 청크 정보를 함께 확인해 소스 구조를 파악합니다.", "타이틀 변경이나 언어 변경을 진행할 경우 현재 값을 기록해 둡니다.", "변경 작업 후 다시 메타정보 확인을 실행해 값이 의도대로 바뀌었는지 비교합니다."],
        "result": ["CMD 로그에 게임 이름, Fusion 버전, 패키징 형태, 언어/LCID, 코드페이지가 표시되는지 확인합니다.", "패치 전후 비교가 필요하면 변경 전 값을 기록해 둡니다.", "EXE를 선택했다면 실제로 어떤 출력 대상이 확인되었는지 로그를 함께 확인합니다.", "값이 비어 있거나 읽히지 않으면 대상 파일이 CTF 계열인지, 다른 프로그램에서 사용 중인지 확인합니다."],
        "notices": [("중요", "메타정보 확인은 파일을 수정하지 않습니다. 실제 변경은 타이틀 변경이나 언어 변경에서 진행합니다."), ("주의", "EXE 구조에 따라 표시되는 정보가 동반 DAT 또는 해석된 소스 기준일 수 있습니다. 작업 전후 CMD 로그의 대상 정보를 같이 확인하세요."), ("권장", "타이틀 변경, 언어 변경 전후로 이 도구를 한 번씩 실행하면 변경된 값을 비교하기 쉽습니다.")],
        "confusion": [("메타정보 확인만으로 언어가 바뀌나요?", "아닙니다. 이 도구는 현재 값을 읽어 보여 줍니다. 언어 값 변경은 언어 변경 도구에서 진행합니다."), ("codepage와 LCID는 같은 값인가요?", "아닙니다. codepage는 문자 해석 기준이고 LCID는 앱 언어 식별값입니다. 언어 변경 도구는 두 값을 언어 프리셋에 맞춰 함께 설정합니다."), ("게임 이름이 비어 있으면 오류인가요?", "항상 오류는 아닙니다. 일부 CTF 소스는 게임 이름 메타데이터가 비어 있을 수 있습니다. 필요하면 타이틀 변경으로 값을 지정하세요.")],
    },
    "guide/title-change-ctf/index.html": {
        "summary": "타이틀 변경 (CTF)은 CTF 소스의 메타데이터에 저장된 game_name 값을 사용자가 입력한 제목으로 패치하는 도구입니다.",
        "when": ["번역본의 게임 이름 메타데이터를 새 제목으로 바꾸고 싶을 때", "메타정보 확인에서 game_name이 비어 있거나 원문 제목으로 남아 있을 때", "CTF 작업본의 표시 제목을 번역본 기준으로 정리할 때", "언어 변경과 함께 CTF 메타데이터를 배포용 값으로 맞추고 싶을 때"],
        "before": ["타이틀을 바꿀 DAT, CCN, EXE 소스를 선택할 수 있어야 합니다.", "입력할 제목은 비워 둘 수 없으며 260자를 넘기지 않아야 합니다.", "이 도구는 CTF 메타데이터를 직접 패치합니다. 실행 전 대상 파일을 보관하세요.", "게임 로고 이미지나 타이틀 화면 이미지는 이 기능으로 바뀌지 않습니다.", "다른 프로그램이 대상 DAT 또는 EXE를 사용 중이면 패치에 실패할 수 있습니다."],
        "steps": ["작업 도구의 CTF 영역에서 타이틀 변경을 실행합니다.", "CTF 소스 선택 화면에서 DAT, CCN, EXE 중 패치할 대상을 선택합니다.", "입력창에 표시되는 현재 제목을 확인합니다.", "새 CTF 타이틀을 입력합니다.", "빈 값이 아닌지 확인한 뒤 실행합니다.", "CMD 로그에서 패치 완료 메시지와 백업, 출력 위치를 확인합니다.", "메타정보 확인을 다시 실행해 game_name 값이 새 제목으로 바뀌었는지 확인합니다."],
        "result": ["완료 메시지에 입력한 제목이 표시되는지 확인합니다.", "CMD 로그에서 백업과 출력 위치가 생성되었는지 확인합니다.", "메타정보 확인을 다시 실행해 game_name이 새 제목으로 표시되는지 확인합니다.", "게임을 실행해 실제 표시 제목이 의도대로 보이는지 확인합니다.", "제목 이미지가 따로 있는 게임은 이미지 리소스도 별도로 확인합니다."],
        "notices": [("중요", "타이틀 변경은 CTF 메타데이터를 직접 패치합니다. 대상 파일을 닫고 원본을 보관한 뒤 실행하세요."), ("주의", "이 기능은 game_name 값을 바꿉니다. 타이틀 화면 이미지, 로고, 실행 파일 이름은 자동으로 바뀌지 않습니다."), ("권장", "변경 전후로 메타정보 확인을 실행해 game_name 값이 의도대로 바뀌었는지 비교하세요.")],
        "confusion": [("게임 안의 타이틀 이미지도 바뀌나요?", "아닙니다. 이 도구는 CTF 메타데이터의 게임 이름 값을 바꿉니다. 이미지 리소스는 별도로 수정해야 합니다."), ("빈 제목으로 지울 수 있나요?", "아닙니다. 제목 입력값은 비워 둘 수 없습니다."), ("EXE를 선택해도 되나요?", "가능합니다. 다만 EXE 구조에 따라 동반 DAT 또는 재패킹 결과가 실제 적용 대상이 될 수 있으므로 CMD 로그의 출력 정보를 확인하세요.")],
    },
    "guide/language-change/index.html": {
        "summary": "언어 변경은 CTF 소스의 메타데이터에 저장된 코드페이지와 언어 LCID를 선택한 언어 프리셋으로 패치하는 도구입니다.",
        "when": ["CTF 작업본의 코드페이지와 LCID가 번역 언어와 맞지 않을 때", "한글 번역본인데 메타정보가 일본어 또는 다른 언어로 남아 있을 때", "문자열 표시나 리소스 해석이 언어 설정의 영향을 받는 프로젝트를 정리할 때", "타이틀 변경과 함께 CTF 메타데이터를 번역본 기준으로 맞추고 싶을 때"],
        "before": ["현재 작업 대상이 CTF 계열인지 확인합니다.", "언어 값을 바꿀 DAT, CCN, EXE 소스를 선택할 수 있어야 합니다.", "이 도구는 코드페이지와 LCID를 실제로 패치합니다. 실행 전 대상 파일을 보관하세요.", "언어 변경은 번역문 자체를 바꾸지 않습니다. 이미 저장된 텍스트 내용은 별도로 확인해야 합니다.", "다른 프로그램이 대상 DAT 또는 EXE를 사용 중이면 패치에 실패할 수 있습니다."],
        "steps": ["작업 도구의 CTF 영역에서 언어 변경을 실행합니다.", "CTF 소스 선택 화면에서 DAT, CCN, EXE 중 패치할 대상을 선택합니다.", "언어 선택 모달에서 적용할 언어를 선택합니다.", "AIMT가 선택한 언어에 맞는 코드페이지와 LCID를 CTF 메타데이터에 반영합니다.", "CMD 로그에서 패치 완료 메시지와 적용된 locale, lcid, codepage 값을 확인합니다.", "메타정보 확인을 다시 실행해 값이 의도대로 바뀌었는지 확인합니다.", "게임을 실행해 글자 깨짐이나 리소스 로딩 문제가 없는지 확인합니다."],
        "items": [("일본어", "codepage 932, LCID 1041로 설정합니다."), ("한국어", "codepage 949, LCID 1042로 설정합니다."), ("영어", "codepage 1252, LCID 1033으로 설정합니다."), ("중국어 간체", "codepage 936, LCID 2052로 설정합니다."), ("중국어 번체", "codepage 950, LCID 1028로 설정합니다."), ("패치 결과", "성공 시 백업과 출력 위치, 변경된 locale, lcid, codepage가 CMD 로그에 표시됩니다.")],
        "result": ["패치 완료 알림을 확인합니다.", "CMD 로그에서 locale, lcid, codepage 값을 확인합니다.", "메타정보 확인을 다시 실행해 선택한 언어 프리셋 값으로 표시되는지 확인합니다.", "게임을 실행해 목표 언어의 글자가 깨지지 않는지 확인합니다."],
        "notices": [("중요", "언어 변경은 CTF 메타데이터를 직접 패치합니다. 실행 전 대상 파일을 닫고 원본을 보관하세요."), ("주의", "코드페이지와 LCID를 바꿔도 이미 잘못 저장된 텍스트가 자동으로 다시 번역되거나 복구되지는 않습니다."), ("권장", "언어 변경 전후로 메타정보 확인을 실행해 codepage와 lcid가 의도대로 바뀌었는지 비교하세요.")],
        "confusion": [("언어 변경을 하면 번역문도 바뀌나요?", "아닙니다. 이 도구는 CTF 메타데이터의 코드페이지와 LCID를 바꿉니다. 번역문 내용은 바꾸지 않습니다."), ("한국어를 고르면 어떤 값이 들어가나요?", "한국어 프리셋은 codepage 949, LCID 1042를 적용합니다."), ("EXE를 선택해도 되나요?", "가능합니다. 다만 EXE 구조에 따라 동반 DAT 또는 재패킹 결과가 실제 적용 대상이 될 수 있으므로 CMD 로그의 출력 정보를 확인하세요.")],
    },
    "guide/ctf-crypter/index.html": {
        "summary": "크립터 (CTF)는 CTF 소스에서 이미지, 폰트, 사운드, 셰이더, 바이너리 리소스를 추출하거나 수정한 리소스를 다시 적용하는 CTF 리소스 작업 도구입니다.",
        "when": ["CTF 게임의 이미지, 사운드, 폰트 같은 리소스를 꺼내 확인하거나 수정할 때", "수정한 리소스를 원래 CTF 소스에 다시 반영해야 할 때", "번역 작업 중 폰트, 이미지, 바이너리 리소스를 별도로 점검해야 할 때", "CTF 리소스 적용 후 누락된 파일이나 적용 실패 항목을 CMD 로그로 확인하고 싶을 때"],
        "before": ["CTF 소스인 DAT, CCN, EXE 중 작업할 대상을 선택할 수 있어야 합니다.", "Extract 결과는 프로젝트의 _Extract 아래 리소스별 폴더에 저장됩니다.", "Apply는 선택한 리소스를 CTF 소스에 반영합니다. 실행 전 원본을 보관하세요.", "셰이더 Apply는 현재 사용할 수 없습니다. 셰이더는 추출 용도로 확인하세요.", "바이너리 Apply는 먼저 바이너리 Extract를 실행해 _Extract/binary 결과가 있어야 합니다."],
        "steps": ["작업 도구의 CTF 영역에서 크립터를 확인합니다.", "이미지, 폰트, 사운드, 셰이더, 바이너리 중 작업할 리소스 종류를 선택합니다.", "열리는 선택 화면에서 Extract 또는 Apply를 고릅니다.", "CTF 소스 선택 화면에서 DAT, CCN, EXE 중 대상 파일을 선택합니다.", "Extract를 선택했다면 완료 후 리소스별 추출 폴더를 확인합니다.", "Apply를 선택했다면 적용할 파일이나 폴더를 선택하고 완료 메시지를 확인합니다.", "CMD 로그에서 적용 개수, 건너뛴 항목, 백업과 출력 위치를 확인합니다.", "게임을 실행해 리소스가 의도대로 표시되거나 재생되는지 확인합니다."],
        "items": [("이미지", "이미지 리소스를 추출하거나 PNG 파일을 다시 적용합니다."), ("폰트", "폰트 리소스를 추출하거나 폰트 적용용 JSON 정보를 기준으로 반영합니다."), ("사운드", "WAV, OGG, MP3, AIFF, BIN 등 사운드 리소스를 추출하거나 적용합니다."), ("셰이더", "셰이더 리소스를 추출합니다. Apply는 현재 비활성화되어 있습니다."), ("바이너리", "바이너리 리소스를 추출하거나, 먼저 추출해 둔 _Extract/binary 결과를 적용합니다."), ("Extract", "선택한 CTF 소스에서 리소스를 꺼내 리소스별 추출 폴더에 저장합니다."), ("Apply", "수정한 리소스를 선택한 CTF 소스에 반영하고 백업과 출력 결과를 남깁니다.")],
        "result": ["Extract 후 리소스별 추출 폴더에 파일이 생성되었는지 확인합니다.", "Apply 후 CMD 로그에서 applied_count와 건너뛴 항목 수를 확인합니다.", "백업과 출력 위치가 표시되면 필요한 파일을 보관합니다.", "게임을 실행해 이미지, 폰트, 사운드 등이 정상적으로 표시되거나 재생되는지 확인합니다."],
        "notices": [("중요", "Apply는 CTF 소스에 리소스를 다시 반영하는 작업입니다. 대상 파일을 닫고 원본을 보관한 뒤 실행하세요."), ("주의", "셰이더는 현재 Apply를 사용할 수 없습니다. 셰이더 버튼은 추출과 확인 용도로 사용하세요.")],
        "confusion": [("크립터가 CTF 파일 전체를 암호화하거나 복호화하는 기능인가요?", "아닙니다. 이 페이지의 크립터는 CTF 리소스의 추출과 적용을 다루는 작업 도구입니다."), ("바이너리 Apply가 실패해요", "바이너리 Apply는 먼저 바이너리 Extract 결과가 있어야 합니다. _Extract/binary 폴더가 준비되어 있는지 확인하세요."), ("셰이더 파일도 다시 넣을 수 있나요?", "현재 셰이더 Apply는 사용할 수 없습니다. 셰이더는 Extract로 내용을 확인하는 용도로 사용하세요.")],
    },
    "guide/pgmmv-crypter/index.html": {
        "summary": "크립터 (PGMMV)는 Pixel Game Maker MV 프로젝트의 Resources 파일을 복호화하거나, 작업 후 다시 암호화하는 보조 도구입니다.",
        "when": ["PGMMV 프로젝트의 Resources가 암호화되어 있어 먼저 복호화해야 할 때", "번역 적용이나 리소스 수정 후 원래 암호화 대상 파일을 다시 암호화해야 할 때", "PGMMV 작업 흐름에서 복호화, 추출, 번역, 적용, 암호화 순서를 정리해야 할 때"],
        "before": ["현재 프로젝트가 PGMMV 계열인지 확인합니다.", "프로젝트 안에 Resources와 Resources/data/info.json이 있어야 합니다.", "Decrypt는 원본 Resources를 백업한 뒤 현재 프로젝트의 파일을 제자리에서 복호화합니다.", "Encrypt는 복호화 때 보관된 원본 백업을 기준으로, 원래 암호화되어 있던 파일만 다시 암호화합니다.", "암호화 시 key type 선택이 필요하면 타입1 또는 타입2를 선택하는 창이 표시될 수 있습니다."],
        "steps": ["작업 도구에서 크립터 (PGMMV)를 엽니다.", "처리 모달에서 Decrypt 또는 Encrypt를 선택합니다.", "Decrypt를 선택했다면 PGMMV 복호화가 시작되고, Resources 파일을 검사합니다.", "복호화 중 원본 파일은 백업 영역에 보관되고, 암호화된 파일은 현재 프로젝트 안에서 복호화됩니다.", "번역 추출, 번역, 적용 등 필요한 작업을 진행합니다.", "작업이 끝난 뒤 Encrypt를 선택해 원래 암호화되어 있던 파일을 다시 암호화합니다.", "key type 선택 창이 표시되면 프로젝트에 맞는 타입1 또는 타입2를 선택합니다.", "완료 메시지에서 처리된 파일 수를 확인합니다."],
        "result": ["Decrypt 완료 메시지에서 복호화된 파일 수와 평문 유지 파일 수를 확인합니다.", "복호화 후 Resources/data/project.json 등 필요한 데이터 파일을 읽을 수 있는지 확인합니다.", "Encrypt 완료 메시지에서 다시 암호화한 파일 수를 확인합니다.", "암호화 후 게임을 실행해 리소스 로딩 오류가 없는지 확인합니다.", "Encrypt에서 암호화할 파일이 없다고 나오면 이미 암호화된 상태이거나, 복호화 백업 기준으로 다시 암호화할 대상이 없다는 뜻입니다."],
        "notices": [("중요", "Decrypt는 현재 프로젝트의 Resources를 제자리에서 복호화합니다. 실행 전 원본 보관 상태를 확인하고, 중간 작업본과 배포용 작업본을 구분하세요."), ("주의", "Encrypt는 원본 백업을 기준으로 원래 암호화되어 있던 파일만 다시 암호화합니다. 복호화 백업이 없거나 현재 프로젝트 파일이 누락되어 있으면 실패할 수 있습니다."), ("권장", "Decrypt 후 바로 추출과 적용을 진행하고, 최종 확인 직전에 Encrypt를 실행하는 흐름으로 관리하면 중간 상태를 파악하기 쉽습니다.")],
        "confusion": [("Decrypt는 파일을 새 폴더로 복사하나요?", "아닙니다. 원본을 백업한 뒤 현재 프로젝트의 Resources 파일을 제자리에서 복호화합니다."), ("Encrypt는 모든 파일을 암호화하나요?", "아닙니다. 복호화 때 보관된 원본 백업을 기준으로 원래 암호화되어 있던 파일만 다시 암호화합니다. 이미 암호화된 파일이나 원래 평문이었던 파일은 건너뛸 수 있습니다."), ("타입1과 타입2는 언제 선택하나요?", "PGMMV 키 정보를 자동으로 확정하기 어려울 때 선택 창이 표시됩니다. 프로젝트에 맞는 key type을 선택해야 이후 암호화 결과가 정상적으로 열립니다."), ("암호화할 파일이 없다고 나오면 실패인가요?", "항상 실패는 아닙니다. 다시 암호화할 대상이 없거나 이미 암호화된 상태일 수 있습니다. 작업 순서와 백업 상태를 확인하세요.")],
    },
    "guide/translation-consistency/index.html": {
        "summary": "번역일관성은 같은 원문이 여러 위치에서 서로 다른 번역으로 저장된 항목을 찾아 보여 주고, 선택한 번역 후보로 해당 원문의 번역을 통일하는 검수 도구입니다.",
        "when": ["같은 원문이 파일이나 위치마다 다르게 번역된 것 같을 때", "반복 대사, 시스템 문구, 메뉴 문구의 표현을 하나로 맞추고 싶을 때", "전체 적용 전에 번역 결과 JSON의 표현 흔들림을 검수할 때", "MVMZ 401 대사 블록 단위 설정을 켠 뒤 대사 블록의 번역 일관성을 확인할 때"],
        "before": ["추출 결과와 번역 결과가 모두 준비되어 있어야 합니다.", "일반 작업에서는 System, Event, data 계열의 원문/번역 결과를 검사합니다.", "시나리오 계열 작업에서는 Scenario 결과를 중심으로 검사하며, 일부 엔진은 System 결과도 함께 검사할 수 있습니다.", "같은 원문에 서로 다른 번역 후보가 2개 이상 있을 때만 목록에 표시됩니다.", "선택 적용과 Auto Select는 번역 결과 파일을 실제로 수정합니다. 넓은 범위에 실행하기 전 현재 번역 결과를 보관해 두세요."],
        "steps": ["작업 도구에서 번역일관성을 실행합니다.", "검사가 완료되면 일관성이 맞지 않는 원문 목록이 모달에 표시됩니다.", "상단의 원문을 확인하고 아래의 번역 후보 목록을 비교합니다.", "각 후보의 사용 횟수와 파일별 위치를 확인합니다.", "Preview로 앞뒤 문맥을 확인하거나 필요한 경우 Edit로 후보 문장을 먼저 수정합니다.", "통일해도 되는 후보를 선택해 현재 원문의 모든 위치에 같은 번역을 반영합니다.", "Auto Next가 켜져 있으면 적용 후 다음 항목으로 자동 이동합니다.", "전체 후보를 기준에 따라 일괄 정리하려면 Auto Select를 사용합니다.", "현재 항목의 적용을 되돌려야 하면 Revert Application을 사용합니다."],
        "result": ["목록이 표시되지 않으면 현재 검사 범위에서 같은 원문에 여러 번역이 저장된 항목이 없다는 뜻입니다.", "후보를 선택한 뒤 완료 알림에서 수정된 파일이나 위치 수를 확인합니다.", "번역 결과 파일을 열어 선택한 번역이 의도한 위치에 반영되었는지 확인합니다.", "적용 후에는 게임을 실행해 같은 원문이라도 문맥상 다르게 번역해야 하는 장면이 없었는지 확인합니다.", "검사 결과 파일이 필요할 때는 translation_inconsistencies.json을 기준으로 어떤 원문이 여러 번역으로 나뉘었는지 확인할 수 있습니다."],
        "notices": [("중요", "후보 선택과 Auto Select는 단순 표시 변경이 아니라 번역 결과 JSON을 수정하는 작업입니다. 실행 전 현재 번역 결과를 보관해 두세요."), ("주의", "같은 원문이라도 화자, 장면, 선택지 위치에 따라 일부러 다른 번역이 필요할 수 있습니다. 대사와 선택지는 Preview로 문맥을 확인한 뒤 통일하세요."), ("권장", "Auto Select는 예외 문자가 적은 후보, 더 자주 사용된 후보, 목록에서 앞에 있는 후보를 우선합니다. 자동 기준이 문맥 판단을 대신하지는 않으므로 적용 결과를 확인하세요.")],
        "confusion": [("용어사전처럼 앞으로의 번역 규칙을 만드는 기능인가요?", "아닙니다. 번역일관성은 이미 만들어진 번역 결과를 검사해 같은 원문에 저장된 여러 번역 후보를 정리하는 도구입니다. 앞으로의 번역 규칙을 관리하려면 사용자사전이나 번역 설정을 함께 확인하세요."), ("Edit로 후보를 고치면 바로 파일이 바뀌나요?", "아닙니다. Edit는 모달 안의 후보 문장을 먼저 고치는 동작입니다. 수정한 후보를 선택해야 해당 원문의 위치들에 실제로 반영됩니다."), ("Revert Application은 전체 자동 선택을 모두 되돌리나요?", "아닙니다. 현재 표시 중인 항목을 기존 후보별 위치 기준으로 되돌리는 용도입니다. 여러 항목을 한꺼번에 자동 처리했다면 별도로 보관해 둔 번역 결과와 비교해 확인하는 편이 안전합니다."), ("검사 결과가 없으면 번역 검수가 끝난 건가요?", "아닙니다. 같은 원문에 여러 번역이 섞인 항목이 없다는 뜻입니다. 오역, 누락, 줄 길이, 화면 넘침, 제어코드 손상은 별도로 확인해야 합니다.")],
    },
    "guide/extraction-duplicates/index.html": {
        "summary": "추출 중복은 추출 결과 안에서 같은 원문이 여러 위치에 반복되는 항목을 찾아 보여 주고, 필요하면 중복 위치에 같은 수정값이나 번역값을 반영하는 도구입니다.",
        "when": ["같은 안내문, 시스템 문구, 메뉴 문구가 여러 파일에 반복될 때", "전체 번역 전에 반복 원문만 먼저 정리해 번역량을 줄이고 싶을 때", "중복 문구의 등장 위치와 파일별 개수를 확인하고 싶을 때", "같은 원문을 같은 번역으로 통일해도 되는지 검수할 때"],
        "before": ["추출 결과가 먼저 준비되어 있어야 합니다.", "일반 모드에서는 System, Event, data 계열 추출 결과를 검사합니다.", "시나리오 계열에서는 Scenario 추출 결과를 중심으로 검사하며, 일부 엔진은 System 결과도 함께 검사할 수 있습니다.", "최소 중복 횟수는 기본값 5입니다. 너무 낮게 잡으면 검토해야 할 항목이 크게 늘어날 수 있습니다.", "선택 파일을 지정하지 않으면 현재 모드의 전체 대상에서 중복을 찾습니다.", "MVMZ 401 대사를 블록 단위로 다루는 설정을 켠 경우, 일부 대사는 줄 단위가 아니라 블록 단위로 중복 판정될 수 있습니다."],
        "steps": ["작업 도구에서 추출 중복을 선택합니다.", "Check 또는 Translate 중 원하는 작업을 선택합니다.", "검사할 파일을 선택합니다. 전체를 검사하려면 별도로 고르지 않고 진행합니다.", "Min. Times에 최소 중복 횟수를 입력합니다.", "검사 모드라면 Check Start를 눌러 중복 목록을 확인합니다.", "번역 모드라면 번역 설정을 확인한 뒤 중복 원문 번역을 시작합니다.", "결과 목록에서 원문, 중복 횟수, 파일별 등장 횟수를 확인합니다.", "검사 결과에서 문구를 수정했다면 저장 후 되돌리기/다시실행 가능 여부를 확인합니다."],
        "result": ["결과 목록이 비어 있으면 설정한 최소 횟수 이상 반복된 원문이 없다는 뜻입니다.", "중복 횟수와 파일별 등장 횟수를 보고 실제로 같은 번역을 써도 되는 문구인지 확인합니다.", "수정 또는 번역 후에는 대상 추출 결과에서 해당 문구가 의도대로 바뀌었는지 확인합니다.", "번역까지 진행했다면 이후 일반 번역/적용 흐름에서 결과가 어긋나지 않는지 확인합니다.", "수동 저장 후 결과가 마음에 들지 않으면 가능한 경우 되돌리기를 사용합니다."],
        "notices": [("중요", "같은 원문이라도 장면, 말투, 변수 위치에 따라 다른 번역이 필요할 수 있습니다. 대사나 선택지는 자동 일괄 반영 전에 문맥을 확인하세요."), ("권장", "반복되는 UI 문구, 시스템 문구, 고정 안내문처럼 문맥 차이가 적은 항목부터 처리하면 검수 부담을 줄이기 쉽습니다.")],
        "confusion": [("파일이 중복되어 있는지 찾는 기능인가요?", "아닙니다. 파일 자체의 중복을 찾는 기능이 아니라, 추출 결과 안에서 같은 원문 텍스트가 여러 위치에 반복되는지 찾는 기능입니다."), ("검사 결과에서 문구를 고치면 모든 비슷한 문장이 바뀌나요?", "아닙니다. 결과 항목에 묶인 같은 원문 위치를 기준으로 반영합니다. 현재 값이 이미 달라진 위치는 건너뛸 수 있습니다."), ("중복 번역은 일반 번역을 대체하나요?", "대체하지 않습니다. 반복 원문을 먼저 처리하는 보조 흐름으로 이해하세요. 남은 일반 문장은 기존 번역 흐름으로 처리해야 합니다.")],
    },
    "guide/escape-check/index.html": {
        "summary": "이스케이프는 원문 추출 결과와 번역 결과를 비교해 제어문자, 태그, 이스케이프 패턴이 번역 중 손상되었는지 검사하는 도구입니다.",
        "when": ["적용 전에 제어코드나 태그가 원문과 같은 구조로 남아 있는지 확인할 때", "게임 화면에 _CTRL 같은 임시 표식이나 <c0/> 형태의 태그가 그대로 보일 때", "번역 후 앞쪽 전각공백, 후행 공백, 닫는 문장부호 위치가 의심될 때", "이스케이프패턴 설정을 바꾼 뒤 검사 결과를 다시 확인할 때"],
        "before": ["추출 결과와 번역 결과가 모두 준비되어 있어야 합니다.", "일반 엔진에서는 System, Event, data 계열의 원문/번역 파일 쌍을 검사합니다.", "시나리오 계열에서는 Scenario 계열을 중심으로 검사하며, 일부 엔진은 System 계열도 함께 검사할 수 있습니다.", "검사 시작 시 이전 Check 결과는 새 결과와 섞이지 않도록 정리됩니다.", "원문과 번역문의 구조나 항목 수가 크게 다르면 해당 파일은 검사에서 제외될 수 있습니다.", "이스케이프 (data)는 원본 게임 data 폴더를 선택해 비교하는 별도 도구입니다."],
        "steps": ["작업 도구에서 이스케이프를 실행합니다.", "AIMT가 현재 엔진에 맞는 일반/시나리오 검사 범위를 선택합니다.", "CMD 화면의 진행 메시지를 확인합니다.", "완료 메시지에서 처리 파일 수, 수정 파일 수, 전체 라인 수, 수정 라인 수를 확인합니다.", "수정 라인이 있으면 비교 바로가기가 열리는지 확인합니다.", "비교 화면에서 번역 결과와 Check 결과의 차이를 확인합니다.", "필요한 항목만 번역 결과에 반영한 뒤 적용하고 게임에서 확인합니다."],
        "result": ["수정 라인 수가 0이면 검사 범위에서 자동 보정하거나 Check로 분리할 항목이 없었다는 뜻입니다.", "수정 라인 수가 0보다 크면 Check 결과와 번역 결과를 비교해 어떤 항목이 달라졌는지 확인합니다.", "전각공백, 후행 공백, 문장부호 보정은 번역 결과에 직접 저장될 수 있습니다.", "이스케이프 불일치 항목은 확인용 결과에 원문 기준 복원안으로 저장됩니다. 필요한 내용만 실제 번역 결과에 반영하세요.", "마지막에는 게임을 실행해 제어문자, 변수, 색상 태그, 줄바꿈이 실제 화면에서 깨지지 않는지 확인합니다."],
        "notices": [("중요", "Check 결과는 그대로 전부 덮어쓰라는 뜻이 아닙니다. 이스케이프가 깨진 항목을 안전하게 비교하기 위한 확인용 결과로 보고, 필요한 항목만 반영하세요."), ("주의", "전각공백과 일부 문장부호 보정은 번역 결과 파일에 직접 저장될 수 있습니다. 실행 전후 차이를 확인할 수 있도록 작업 범위를 관리하세요."), ("권장", "이스케이프 오류는 적용 실패보다 게임 실행 중 표시 깨짐으로 드러나는 경우가 많습니다. 적용 전 검사하고, 적용 후 실제 화면도 함께 확인하세요.")],
        "confusion": [("이스케이프 (data)와 같은 기능인가요?", "아닙니다. 이 페이지의 이스케이프는 AIMT의 추출 결과와 번역 결과를 비교합니다. 이스케이프 (data)는 사용자가 선택한 원본 data 폴더와 현재 프로젝트 data를 비교하는 별도 도구입니다."), ("Check 결과가 생기면 자동으로 적용된 건가요?", "아닙니다. Check 결과는 비교와 검수용입니다. 필요한 차이를 확인한 뒤 실제 번역 결과나 적용 결과에 반영해야 합니다."), ("수정 라인이 0이면 검수가 끝난 건가요?", "아닙니다. 이스케이프 기준으로 발견된 문제가 없다는 뜻입니다. 오역, 누락, 줄 길이, 화면 넘침은 별도로 확인해야 합니다.")],
    },
    "guide/final-consonant-cleanup/index.html": {
        "summary": "받침정리는 번역 결과 JSON 안의 한글 문자열을 NFC 기준으로 정규화하고, 잘못 분리되어 남은 단독 종성 문자를 정리하는 도구입니다.",
        "when": ["번역 결과에 한글 자모가 분리되어 보이는 글자가 있을 때", "외부 편집기나 AI 번역 결과 때문에 한글 유니코드 조합이 깨진 것처럼 보일 때", "적용 전에 Translated 쪽 JSON 텍스트를 한 번 정리하고 싶을 때"],
        "before": ["번역 결과가 준비되어 있어야 합니다.", "System, Event, Data, Scenario 계열의 Translated JSON을 검사합니다.", "수정이 필요한 파일은 원래 번역 결과 파일에도 다시 저장됩니다."],
        "steps": ["작업 도구에서 받침정리를 실행합니다.", "CMD 화면에 한글 자모 수정 작업 시작 메시지가 표시되는지 확인합니다.", "작업 완료 후 처리 파일 수, 수정 파일 수, 교체 항목 수, 단독 종성 수를 확인합니다.", "수정된 파일이 있으면 표본 문장을 열어 글자 상태를 확인합니다."],
        "result": ["수정할 한글 자모가 없다는 메시지가 나오면 현재 검사 범위에서는 바꿀 항목이 없다는 뜻입니다.", "수정 파일 수가 0보다 크면 해당 파일의 번역문이 실제로 변경된 것입니다.", "적용 후 게임 화면에서 해당 문장이 깨지지 않는지 확인합니다."],
        "notices": [("중요", "받침정리는 한국어 조사 교정 도구가 아닙니다. 은/는, 이/가, 을/를을 문맥에 맞게 고르는 기능이 아니라 잘못 분리된 한글 자모와 단독 종성을 정리하는 기능입니다."), ("주의", "단독 종성 문자는 정규화 후에도 남아 있으면 제거됩니다. 특수한 목적으로 해당 문자를 일부러 넣은 경우라면 실행 전 대상 파일을 보관하세요.")],
        "confusion": [("받침에 맞춰 은/는, 이/가를 고쳐 주나요?", "아닙니다. 이 도구는 조사 선택 기능이 아니라 한글 자모 정규화 도구입니다."), ("수정할 한글 자모가 없다고 나오면 실패인가요?", "아닙니다. 검사 범위에서 정규화할 항목이나 단독 종성이 발견되지 않았다는 뜻입니다.")],
    },
    "guide/japanese-check/index.html": {
        "summary": "일본어체크는 현재 프로젝트의 데이터베이스 JSON과 Map 이벤트 JSON을 읽어 일본어로 판정되는 텍스트의 수와 비율을 보여 주는 검사 도구입니다.",
        "when": ["현재 프로젝트 데이터에 일본어 텍스트가 어느 정도 남아 있는지 빠르게 확인하고 싶을 때", "RPG Maker 계열처럼 data 폴더에 JSON 데이터베이스와 Map 파일이 있는 프로젝트를 점검할 때", "데이터베이스 쪽과 이벤트 쪽 중 어느 묶음에 일본어가 더 많이 남았는지 비교할 때"],
        "before": ["검사 대상은 현재 프로젝트의 data 계열 JSON입니다.", "데이터베이스 파일과 Map*.json 이벤트 파일이 있어야 의미 있는 결과가 나옵니다.", "번역 결과 파일 자체를 고치지 않으며 검사 후 파일을 수정하지 않습니다.", "한자도 일본어 판정 범위에 포함되므로 고유명사나 중국어/한자 표기가 함께 잡힐 수 있습니다."],
        "steps": ["작업할 프로젝트가 올바르게 지정되어 있는지 확인합니다.", "작업 도구에서 일본어체크를 실행합니다.", "CMD 화면에서 일본어 텍스트 검사 시작 메시지를 확인합니다.", "검사 완료 후 데이터베이스와 이벤트 항목의 총 텍스트 수, 일본어 텍스트 수, 비율을 확인합니다."],
        "result": ["데이터베이스 비율이 높으면 이름, 설명, 시스템 용어 같은 DB 항목에 원문이 남아 있을 가능성이 큽니다.", "이벤트 비율이 높으면 Map 이벤트 대사, 선택지, 스크롤 텍스트 쪽에 원문이 남아 있을 가능성이 큽니다.", "일본어 수가 0이어도 오역, 누락, 코드 손상까지 검수된 것은 아닙니다."],
        "notices": [("중요", "일본어체크는 검사 도구입니다. 번역문을 수정하거나 미번역 문장을 자동으로 교체하지 않습니다."), ("주의", "일본어 판정에는 한자 범위가 포함됩니다. 따라서 한자 고유명사, 중국어 문장, 일부 한자어도 일본어 텍스트로 계산될 수 있습니다.")],
        "confusion": [("번역 결과 파일을 검사하나요?", "이 도구는 현재 프로젝트의 data 계열 JSON을 기준으로 검사합니다. 일반적인 번역 결과 JSON 전체를 대상으로 직접 수정하는 도구로 이해하면 안 됩니다."), ("비율이 0이면 검수가 끝난 건가요?", "아닙니다. 일본어 문자 기준으로 남은 항목이 없다는 뜻일 뿐입니다. 오역, 누락, 코드 손상은 별도로 확인해야 합니다.")],
    },
    "guide/api-key-settings/index.html": {
        "summary": "API KEY 설정은 Gemini, Vertex, OpenAI, Claude, xAI, DeepSeek, OpenRouter, DeepL 같은 번역 제공자의 인증 정보를 관리하는 화면입니다.",
        "when": ["AI 번역 또는 DeepL 번역을 처음 준비할 때", "기존 키를 새 키로 교체할 때", "번역 요청이 인증 오류로 실패할 때", "여러 키의 사용 여부를 켜거나 끌 때"],
        "before": ["API 키는 각 제공자 계정에서 직접 발급해야 합니다.", "어떤 모델을 쓸지는 AI-MODEL 또는 번역 설정에서 따로 선택합니다."],
        "steps": ["제공자 종류를 선택합니다.", "키 입력 영역에 발급받은 값을 붙여 넣습니다.", "사용할 키의 ON/OFF 상태를 확인합니다.", "저장합니다.", "빠른번역이나 일반 번역으로 정상 동작을 확인합니다."],
        "result": ["저장 후 오류 메시지가 없는지 확인합니다.", "빠른번역에서 짧은 문장을 번역해 키가 정상인지 확인합니다.", "실패하면 키 값, 제공자 선택, 모델 선택, 네트워크 상태를 순서대로 확인합니다."],
        "notices": [("주의", "API 키는 개인 인증 정보입니다. 공개 문서, 스크린샷, 커뮤니티 글에 그대로 노출하지 마세요.")],
        "confusion": [("API 키를 넣었는데 모델이 바뀌지 않습니다", "API KEY 설정은 인증 정보 관리 화면입니다. 사용할 모델은 AI-MODEL 또는 번역 설정에서 따로 확인하세요.")],
    },
    "guide/ai-model/index.html": {
        "summary": "AI-MODEL은 번역에 사용할 제공자와 모델을 선택하는 화면입니다.",
        "when": ["처음 AI 번역 환경을 준비할 때", "번역 품질, 속도, 비용을 바꾸고 싶을 때", "오류가 나는 모델을 다른 모델로 바꿀 때"],
        "before": ["API KEY 설정에 사용할 제공자의 키가 준비되어 있어야 합니다.", "모델마다 지원 기능과 비용이 다를 수 있습니다.", "로컬 모델을 사용할 경우 로컬 서버 상태를 먼저 확인합니다."],
        "steps": ["사용할 제공자를 선택합니다.", "메인 모델을 선택합니다.", "필요하면 예비 모델을 선택합니다.", "설정을 저장합니다."],
        "result": ["번역 설정과 빠른번역에서 선택한 모델이 사용되는지 확인합니다.", "오류가 나면 API 키, 모델명, 제공자 상태를 순서대로 확인합니다."],
    },
    "guide/translation-settings/index.html": {
        "summary": "번역 설정은 AIMT가 어떤 번역 엔진과 모델을 사용하고, 요청 크기·속도·출력 형식·추론 옵션을 어떻게 적용할지 정하는 화면입니다.",
        "when": ["처음 번역 환경을 준비할 때", "모델별로 화면에 표시된 설정의 의미를 확인할 때", "번역 결과가 잘리거나 요청 제한 오류가 날 때", "문맥 해석, 비용, 처리 속도를 조정하고 싶을 때"],
        "before": ["API KEY 설정에 사용할 키가 등록되어 있어야 합니다.", "선택한 엔진과 모델에 따라 화면에 표시되는 항목이 달라질 수 있습니다."],
        "steps": ["번역 엔진과 모델을 확인합니다.", "권장값을 적용하고 API 키 상태를 확인합니다.", "요청 크기, 출력 길이, 요청 속도를 필요한 만큼 조절합니다.", "화면에 표시되는 추론·캐시·출력 형식 옵션만 상황에 맞게 조정합니다."],
        "result": ["번역 결과가 잘리지 않는지 확인합니다.", "요청 제한이나 연속 오류가 발생하지 않는지 봅니다.", "문체와 용어가 유지되는지 확인합니다.", "문제가 있으면 요청 크기, 출력 길이, 속도 제한, 추론 강도 순서로 하나씩 점검합니다."],
        "notices": [("중요", "AIMT는 선택한 엔진과 모델에서 사용할 수 있는 설정을 중심으로 표시합니다. 보이지 않는 항목은 현재 모델에서 직접 조절할 필요가 없는 항목으로 이해하면 됩니다.")],
    },
    "guide/cache-management/index.html": {
        "summary": "캐시 관리는 AIMT 작업 중 쌓인 임시 데이터, 로그, 백업, 엔진별 작업 상태를 선택해서 정리하는 실행형 도구입니다.",
        "when": ["오래된 임시 결과나 로그를 정리할 때", "이전 작업 상태를 비우고 다시 점검할 때", "엔진별 보조 데이터나 검사 결과를 정리할 때", "문제 재현을 위해 중간 데이터를 비우고 새로 실행할 때"],
        "before": ["추출, 번역, 적용 같은 작업이 진행 중이면 먼저 끝내거나 취소합니다.", "나중에 확인해야 할 로그나 백업이 있으면 바로 비우지 않습니다.", "번역 결과나 매핑 정보를 비우면 재추출, 재번역, 재검사가 필요할 수 있습니다."],
        "steps": ["캐시 관리 화면을 엽니다.", "정리할 항목을 선택합니다.", "선택 항목이 현재 작업에 필요한 데이터인지 확인합니다.", "선택 항목 비우기를 누릅니다.", "확인창을 읽고 실행합니다.", "완료 메시지에서 삭제 수와 건너뜀 수를 확인합니다."],
        "result": ["선택한 항목의 내부 내용이 정리되었는지 확인합니다.", "일부 항목이 건너뛰어졌다면 사용 중인 파일이나 권한 문제를 확인합니다.", "필요한 결과가 사라졌다면 관련 작업을 다시 실행합니다."],
        "notices": [("주의", "백업, 매핑, 엔진별 상태는 이후 복구나 재작업에 영향을 줄 수 있습니다. 필요한 항목만 좁게 선택하세요.")],
    },
    "guide/exclude-exception-regex/index.html": {
        "summary": "제외정규식 / 예외정규식은 MVMZ와 VXVXA 추출 과정에서 번역하지 않을 텍스트를 제외하고, 그중 반드시 남겨야 할 텍스트를 예외로 되살리는 설정입니다.",
        "when": ["추출 결과에 시스템값, 제어문, 번역하면 안 되는 문자열이 많이 섞일 때", "넓은 제외 규칙을 쓰되 특정 문구만 번역 대상으로 남기고 싶을 때", "MVMZ 플러그인 파라미터, 이벤트 명령, 데이터베이스 메모처럼 위치별로 제외 범위를 조정할 때"],
        "before": ["정규식은 적용 범위가 넓으므로 변경 후 추출 결과를 확인합니다.", "어느 카테고리에서 문제가 생겼는지 추출 결과의 파일명이나 항목명을 먼저 확인합니다.", "기존 추출 결과가 자동으로 바뀌지 않으므로 저장 후 다시 추출할 계획을 세웁니다."],
        "steps": ["설정 화면에서 MVMZ 또는 VXVXA 영역의 제외정규식 버튼을 엽니다.", "왼쪽 목록에서 조정할 카테고리를 선택합니다.", "제외할 조건은 일반 패턴 영역에 추가합니다.", "제외 규칙에 걸리더라도 꼭 추출해야 하는 조건은 예외 패턴 영역에 추가합니다.", "필요한 줄만 ON으로 두고 저장합니다.", "추출을 다시 실행한 뒤 결과를 확인합니다."],
        "result": ["다시 추출한 결과에서 제외하려던 문장이 빠졌는지 확인합니다.", "예외로 남겨야 하는 문장이 여전히 추출되는지 확인합니다.", "필요한 문장까지 빠졌다면 제외 규칙을 좁히거나 예외 패턴을 추가합니다."],
        "notices": [("주의", "한 카테고리에 너무 넓은 정규식을 넣으면 필요한 대사까지 추출에서 빠질 수 있습니다. 처음에는 한 파일이나 한 구간만 확인하세요."), ("중요", "저장한 규칙은 보통 다음 추출부터 의미가 있습니다. 이미 만들어진 번역 결과를 즉시 고치는 기능은 아닙니다.")],
        "confusion": [("추출정규식과 같은 기능인가요?", "아닙니다. 추출정규식은 주로 추출할 패턴 자체를 정하는 설정이고, 제외정규식은 이미 후보가 된 텍스트 중 빼거나 되살릴 대상을 정하는 설정입니다."), ("예외 패턴만 넣으면 모든 곳에서 살아나나요?", "예외 패턴도 선택한 카테고리 안에서 동작합니다. 다른 위치의 텍스트는 해당 위치의 카테고리를 따로 확인해야 합니다.")],
    },
    "guide/replacement-terms/index.html": {
        "summary": "치환용어설정은 MVMZ 추출 과정에서 특정 문자열을 미리 다른 문자열로 바꿔 저장하도록 하는 간단한 치환 규칙입니다.",
        "when": ["전각 영문, 기호, 자주 반복되는 표기를 추출 단계에서 정리하고 싶을 때", "원문에 같은 표기가 반복되어 번역 전에 통일해 두는 편이 좋을 때", "번역 모델에 넘기기 전에 특정 용어 표기를 사용자 기준으로 맞추고 싶을 때"],
        "before": ["이 기능은 정규식이 아니라 일반 문자열 치환입니다.", "단어 전체 일치가 아니라 문장 안에 포함된 같은 문자열도 바뀔 수 있습니다.", "빈 값으로 지우는 용도보다는 다른 값으로 바꾸는 용도로 사용합니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 치환용어설정을 엽니다.", "원본 칸에 바꾸고 싶은 문자열을 입력합니다.", "치환 칸에 바뀐 뒤의 문자열을 입력합니다.", "필요 없는 줄은 삭제하고, 사용할 규칙만 남깁니다.", "저장한 뒤 추출을 다시 실행합니다.", "추출 결과에서 치환이 의도대로 적용되었는지 확인합니다."],
        "result": ["다시 추출한 결과에서 원본 표기가 치환값으로 바뀌었는지 확인합니다.", "의도하지 않은 단어가 바뀌지 않았는지 변경 결과를 확인합니다.", "치환이 너무 넓게 적용되면 원본 문자열을 더 구체적으로 적습니다."],
        "notices": [("주의", "짧은 문자열은 예상보다 많은 문장에 포함될 수 있습니다. 한 글자나 흔한 기호를 치환할 때는 특히 조심하세요."), ("중요", "저장 후 기존 추출 파일이나 번역 파일이 자동으로 다시 작성되지는 않습니다. 변경 후에는 필요한 범위를 다시 추출하세요.")],
        "confusion": [("정규식을 쓸 수 있나요?", "아닙니다. 치환용어설정은 일반 문자열 기준으로 동작합니다. 패턴 조건이 필요하면 제외정규식이나 관련 정규식 설정을 확인하세요."), ("치환 칸을 비워서 글자를 삭제할 수 있나요?", "빈 치환값은 저장 대상에서 제외될 수 있습니다. 삭제 목적보다는 명확한 대체 문자열을 넣는 방식으로 사용하는 편이 안전합니다.")],
    },
    "guide/default-font-settings/index.html": {
        "summary": "기본폰트설정은 MVMZ 적용 시 사용할 메인 폰트, 숫자 폰트, 폰트 크기를 프리셋으로 관리하는 설정입니다.",
        "when": ["MVMZ 적용 후 한글이 깨지거나 네모로 보일 때", "게임 분위기에 맞는 한글 폰트를 지정하고 싶을 때", "숫자만 다른 폰트로 표시하거나 폰트 크기를 조정해야 할 때"],
        "before": ["한글 글리프가 포함된 폰트를 준비합니다.", "상업적 배포나 공유가 필요한 작업이라면 폰트 라이선스를 먼저 확인합니다.", "폰트 변경은 번역문 내용이 아니라 게임 화면의 글자 표시 방식에 영향을 줍니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 기본폰트설정을 엽니다.", "기존 프리셋을 선택하거나 새 프리셋을 만듭니다.", "메인 폰트와 숫자 폰트를 시스템 폰트 또는 파일 선택으로 지정합니다.", "폰트 크기를 확인하고 저장합니다.", "MVMZ 적용을 다시 실행합니다.", "게임을 실행해 실제 대사창, 메뉴, 숫자 표시를 확인합니다."],
        "result": ["게임 실행 후 한글이 정상 표시되는지 확인합니다.", "대사창, 메뉴, 전투 화면처럼 글자 위치가 다른 화면을 함께 확인합니다.", "숫자 폭이나 줄바꿈이 어색하면 숫자 폰트와 폰트 크기를 다시 조정합니다."],
        "notices": [("주의", "폰트가 바뀌면 글자 폭과 줄바꿈도 달라질 수 있습니다. 적용 후 실제 게임 화면에서 반드시 확인하세요.")],
        "confusion": [("기본 창에서 바로 값을 고치는 건가요?", "기본 창은 현재 프리셋 확인과 선택에 가깝습니다. 실제 값 편집은 새 프리셋 또는 수정 창에서 진행합니다."), ("폰트만 바꾸면 번역문도 바뀌나요?", "아닙니다. 폰트 설정은 표시 방식에 영향을 주며, 번역문 내용 자체를 바꾸지는 않습니다.")],
    },
    "guide/title-text/index.html": {
        "summary": "타이틀텍스트는 MVMZ 적용 시 게임 제목 뒤에 붙일 짧은 문구를 관리하는 설정입니다.",
        "when": ["게임 제목에 한국어판, 한글 패치, 체험판 같은 표시를 붙이고 싶을 때", "배포 상태에 따라 제목 뒤 문구를 빠르게 바꿔야 할 때", "여러 후보 문구를 저장해 두고 하나만 선택해 사용하고 싶을 때"],
        "before": ["제목 뒤에 붙일 문구만 짧게 입력합니다.", "한 번에 여러 문구를 켜는 구조가 아니라는 점을 확인합니다.", "저장 후 실제 반영은 MVMZ 적용 단계에서 확인합니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 타이틀텍스트를 엽니다.", "사용할 문구를 한 줄로 추가합니다.", "현재 적용할 문구만 ON으로 둡니다.", "필요 없는 후보는 삭제하거나 OFF로 둡니다.", "저장한 뒤 MVMZ 적용을 실행합니다.", "게임 제목 화면에서 문구가 붙었는지 확인합니다."],
        "result": ["MVMZ 적용 후 게임 제목 뒤에 선택한 문구가 붙었는지 확인합니다.", "이미 같은 문구가 붙어 있는 제목에 중복으로 붙지 않았는지 확인합니다.", "문구가 필요 없으면 모든 후보를 OFF로 둔 뒤 다시 적용합니다."],
        "notices": [("중요", "타이틀텍스트는 저장 즉시 게임 제목을 바꾸는 기능이 아니라, 다음 MVMZ 적용 때 사용할 문구를 정하는 기능입니다."), ("권장", "문구는 짧게 유지하세요. 긴 설명을 붙이면 제목 화면이나 창 제목에서 잘릴 수 있습니다.")],
        "confusion": [("여러 문구를 동시에 붙일 수 있나요?", "이 설정은 후보를 여러 개 저장해 두고 현재 사용할 하나를 고르는 방식으로 이해하는 편이 안전합니다."), ("원본 제목을 직접 바꾸는 기능인가요?", "아닙니다. 적용 단계에서 제목 뒤에 선택 문구를 덧붙이는 용도입니다.")],
    },
    "guide/multiline-db/index.html": {
        "summary": "Multiline-DB는 MVMZ 데이터베이스의 설명문이나 프로필처럼 줄바꿈이 들어갈 수 있는 항목을 줄 단위로 나눠 추출할지 정하는 설정입니다.",
        "when": ["아이템 설명, 스킬 설명, 배우 프로필처럼 여러 줄 설명이 많은 게임을 작업할 때", "줄마다 따로 번역·검수하는 편이 편할 때", "반대로 설명 전체를 한 문맥으로 번역하고 싶어 설정을 비교해야 할 때"],
        "before": ["기본값은 켜짐입니다.", "설정을 바꾸면 추출 결과의 항목 단위가 달라질 수 있으므로 다시 추출해야 합니다.", "이 설정은 이벤트 대사 401 처리와는 별개의 데이터베이스 설정입니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Multiline-DB를 확인합니다.", "줄 단위로 다루고 싶으면 켭니다.", "설명 전체를 한 항목으로 보고 싶으면 끕니다.", "MVMZ 추출을 다시 실행합니다.", "데이터베이스 설명이나 프로필 추출 결과를 비교합니다.", "선택한 방식으로 번역과 적용을 진행합니다."],
        "result": ["추출 결과에서 설명문이 줄 단위로 나뉘었는지 또는 한 항목으로 유지되는지 확인합니다.", "게임 적용 후 설명창의 줄바꿈이 원래 의도와 맞는지 확인합니다.", "문맥이 끊겨 번역 품질이 떨어지면 끈 상태도 비교합니다."],
        "notices": [("중요", "이 설정은 추출 단위를 바꿉니다. 이미 번역한 뒤 바꾸면 기존 결과와 맞지 않을 수 있으므로 작업 초반에 정하는 편이 좋습니다."), ("권장", "설명이 짧고 줄마다 의미가 분명하면 켜짐, 긴 문단 흐름이 중요하면 꺼짐을 비교해 보세요.")],
        "confusion": [("대사 401도 이 설정의 영향을 받나요?", "아닙니다. 이벤트 대사는 401-Extract Mode, Flatten Mode, merge 101-401 같은 설정에서 다룹니다."), ("켜면 줄바꿈이 사라지나요?", "아닙니다. 줄바꿈을 어떻게 추출 단위로 볼지 정하는 설정이며, 적용 후 화면 줄바꿈은 별도로 확인해야 합니다.")],
    },
    "guide/extract-troop-names/index.html": {
        "summary": "Extract Troop Names는 MVMZ 데이터베이스의 Troops.name, 즉 전투 그룹 이름을 추출과 적용 대상에 포함할지 정하는 설정입니다.",
        "when": ["전투 그룹 이름까지 번역 결과에 포함해야 할 때", "Troops 이벤트 본문은 처리하되 전투 그룹 이름은 따로 관리하고 싶을 때", "이전 번역 파일에 전투 그룹 이름 항목이 있어 적용 여부를 명확히 정해야 할 때"],
        "before": ["기본값은 꺼짐입니다.", "꺼져 있어도 Troops 이벤트 본문 처리는 계속 진행될 수 있습니다.", "이 설정은 추출뿐 아니라 적용 시 전투 그룹 이름을 게임 데이터에 반영할지에도 영향을 줍니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Extract Troop Names를 확인합니다.", "전투 그룹 이름을 번역 대상으로 포함하려면 켭니다.", "전투 그룹 이름을 원문 그대로 두려면 끕니다.", "MVMZ 추출을 다시 실행합니다.", "Database 계열 추출 결과에서 전투 그룹 이름 항목이 포함되었는지 확인합니다.", "번역 후 적용하고 전투 또는 관련 화면에서 이름 반영 여부를 확인합니다."],
        "result": ["켜짐 상태에서는 전투 그룹 이름이 추출 결과에 포함되는지 확인합니다.", "꺼짐 상태에서는 이전 번역 파일에 전투 그룹 이름 항목이 있어도 적용 결과에 반영되지 않는지 확인합니다.", "전투 화면, 데이터베이스 표시, 관련 이벤트에서 이름 표기가 의도대로 유지되는지 확인합니다."],
        "notices": [("중요", "Extract Troop Names가 꺼져 있으면 기존 번역 결과에 전투 그룹 이름 항목이 남아 있어도 적용 단계에서 게임 데이터에 쓰지 않습니다."), ("권장", "전투 그룹 이름이 플레이어에게 직접 보이는 작품인지 먼저 확인한 뒤 켜는 편이 좋습니다.")],
        "confusion": [("Troops 이벤트 대사도 빠지나요?", "아닙니다. 이 설정은 전투 그룹의 DB 이름 항목을 다룹니다. Troops 이벤트 본문은 별도 흐름으로 처리됩니다."), ("Extract Names와 같은 기능인가요?", "아닙니다. Extract Troop Names는 전투 그룹 이름을 실제 추출·적용 대상에 포함하는 설정이고, Extract Names는 이름 검토용 목록을 만드는 보조 설정입니다.")],
    },
    "guide/extract-names/index.html": {
        "summary": "Extract Names는 MVMZ 추출 시 이름이나 호칭으로 참고할 수 있는 텍스트를 별도로 모아 두는 보조 설정입니다.",
        "when": ["캐릭터명, 적 이름, 호칭을 번역 전에 검토하고 싶을 때", "용어사전이나 인명 표기 기준을 만들기 위한 참고 목록이 필요할 때", "번역 대상 본문과 별도로 이름 계열 텍스트를 빠르게 확인하고 싶을 때"],
        "before": ["기본값은 꺼짐입니다.", "이 설정으로 만들어지는 목록은 참고용 성격이 강합니다.", "파일 목록에 일반 번역 대상처럼 표시되지 않을 수 있습니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Extract Names를 켭니다.", "MVMZ 추출을 다시 실행합니다.", "이름 참고 목록이 생성되었는지 확인합니다.", "필요한 표기를 용어사전이나 번역 기준에 반영합니다.", "번역 작업을 진행하면서 이름 표기가 유지되는지 확인합니다."],
        "result": ["추출 후 이름 참고 목록에 검토할 이름이 모였는지 확인합니다.", "실제 번역 파일의 이름 표기와 참고 목록을 비교합니다.", "필요한 이름이 누락되면 일반 추출 결과와 엔진별 이름 위치를 함께 확인합니다."],
        "notices": [("중요", "Extract Names는 번역 결과를 직접 바꾸는 기능이 아닙니다. 이름 표기를 정리하기 위한 참고 자료로 사용하세요."), ("권장", "대량 번역 전에 이 목록으로 주요 인명과 고유명사의 표기 기준을 먼저 정하면 후반 검수 비용이 줄어듭니다.")],
        "confusion": [("켜면 이름이 자동으로 잘 번역되나요?", "아닙니다. 이름을 검토하기 쉬운 자료를 만드는 기능입니다. 실제 번역 기준은 용어사전, 프롬프트, 수동 검수로 맞춰야 합니다."), ("파일 목록에서 안 보이면 실패인가요?", "그렇지 않을 수 있습니다. 이 기능의 결과는 일반 번역 대상 목록과 다르게 참고용으로 생성될 수 있습니다.")],
    },
    "guide/dbdic-include-extract-names/index.html": {
        "summary": "DBdic include Extract Names는 MVMZ DB사전을 자동 구성하거나 가져올 때 Extract Names로 만든 캐릭터명 목록을 함께 포함할지 정하는 설정입니다.",
        "when": ["DB사전에도 캐릭터명 목록을 포함해 이름 표기 기준을 함께 관리하고 싶을 때", "Extract Names로 만든 이름 목록을 번역 프롬프트의 DB사전 정보와 함께 활용하고 싶을 때", "DB사전 가져오기 후 이름 항목이 빠지는지 확인해야 할 때"],
        "before": ["기본값은 꺼짐입니다.", "먼저 Extract Names를 켜고 MVMZ 추출을 실행해 캐릭터명 목록을 만들어야 합니다.", "포함된 이름 항목은 DB사전에서 이름 계열 태그로 분류됩니다."],
        "steps": ["Extract Names를 켜고 MVMZ 추출을 실행합니다.", "이름 참고 목록이 만들어졌는지 확인합니다.", "설정 화면에서 MVMZ 영역의 DBdic include Extract Names를 켭니다.", "DB사전 자동 구성 또는 가져오기를 실행합니다.", "DB사전 목록에서 이름 항목이 포함되었는지 확인합니다.", "번역 결과에서 이름 표기 힌트가 의도대로 쓰이는지 확인합니다."],
        "result": ["DB사전에 캐릭터명 항목이 추가되었는지 확인합니다.", "이름 항목이 중복되거나 불필요하게 섞이면 Extract Names 목록과 DB사전 항목을 정리합니다.", "번역 결과에서 이름 표기가 더 안정적인지 확인합니다."],
        "notices": [("중요", "이 설정은 Extract Names 결과가 준비되어 있을 때 의미가 있습니다. 이름 목록이 없으면 포함할 항목도 없습니다."), ("권장", "DB사전을 번역 프롬프트에 함께 사용하는 작업에서는 이름 항목을 넣기 전에 표기 기준을 한 번 정리하세요.")],
        "confusion": [("이 설정만 켜면 이름 목록이 만들어지나요?", "아닙니다. 이름 목록 생성은 Extract Names와 추출 단계에서 진행됩니다. 이 설정은 만들어진 이름 목록을 DB사전에 포함할지 정합니다."), ("DB사전의 모든 항목이 자동 번역되나요?", "아닙니다. DB사전은 번역 판단을 돕는 참고 정보입니다. 결과는 모델, 프롬프트, 용어 기준에 따라 달라질 수 있습니다.")],
    },
    "guide/merge-101-401/index.html": {
        "summary": "merge 101-401은 MVMZ 이벤트 대사에서 101 계열 정보와 401 대사 줄을 같은 대화 흐름으로 묶어 다룰지 정하는 설정입니다.",
        "when": ["화자명과 대사를 같은 흐름에서 보고 번역하고 싶을 때", "대화 문맥을 유지한 상태로 401 대사를 추출하고 싶을 때", "Include speaker name이나 401-Extract Mode와 함께 대사 구조를 정리하고 싶을 때"],
        "before": ["기본값은 꺼짐입니다.", "설정을 바꾸면 추출 결과 구조가 달라질 수 있으므로 다시 추출해야 합니다.", "기존 번역 결과가 있다면 같은 구조로 만들어진 결과인지 확인합니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 merge 101-401을 확인합니다.", "화자 정보와 대사를 같은 흐름으로 다루려면 켭니다.", "화자 정보와 대사를 분리해서 관리하려면 끕니다.", "필요하면 401-Extract Mode를 함께 확인합니다.", "MVMZ 추출을 다시 실행합니다.", "대사 추출 결과가 원하는 구조로 만들어졌는지 확인합니다."],
        "result": ["추출 결과에서 화자명과 대사가 의도한 파일/묶음으로 정리되었는지 확인합니다.", "번역 후 적용했을 때 화자명과 대사 줄 순서가 어긋나지 않는지 확인합니다.", "기존 번역 결과와 구조가 다르면 필요한 범위를 다시 번역합니다."],
        "notices": [("중요", "이 설정은 대사 추출 구조에 영향을 줍니다. 번역을 많이 진행한 뒤 바꾸면 결과를 다시 맞춰야 할 수 있습니다.")],
        "confusion": [("101과 401이 무엇인가요?", "사용자는 숫자를 외울 필요는 없습니다. 101은 대사 표시와 관련된 정보, 401은 실제 대사 줄이라고 이해하면 충분합니다."), ("켜면 모든 문장이 한 줄로 합쳐지나요?", "아닙니다. 묶는 방식은 401-Extract Mode와 함께 결정됩니다. 켜짐은 화자 정보와 대사 흐름을 함께 관리하기 쉽게 만드는 설정에 가깝습니다.")],
    },
    "guide/apply-exclude-regex-to-401-block/index.html": {
        "summary": "Apply exclude regex to 401 block은 401 대사 한 줄에 걸린 제외/예외 규칙을 같은 대사 블록 전체로 확장할지 정하는 설정입니다.",
        "when": ["한 줄만 보고 제외하면 같은 대화 블록의 나머지 줄이 어색하게 남을 때", "이름표, 제어용 줄, 특정 마커가 포함된 대사 블록 전체를 제외하고 싶을 때", "예외 규칙도 줄 하나가 아니라 같은 블록 전체에 적용하고 싶을 때"],
        "before": ["기본값은 꺼짐입니다.", "제외정규식 / 예외정규식의 401 관련 규칙을 먼저 확인합니다.", "이 설정을 켜면 한 줄 조건이 대사 블록 전체에 영향을 줄 수 있습니다."],
        "steps": ["제외정규식 / 예외정규식에서 401 관련 규칙을 준비합니다.", "설정 화면에서 MVMZ 영역의 Apply exclude regex to 401 block을 켭니다.", "MVMZ 추출을 다시 실행합니다.", "조건에 걸린 줄이 포함된 대사 블록 전체가 제외 또는 예외 처리되는지 확인합니다.", "필요한 대사까지 빠지면 규칙을 좁히거나 설정을 끕니다."],
        "result": ["다시 추출한 결과에서 블록 전체가 의도대로 제외되었는지 확인합니다.", "예외 규칙을 쓴 경우 같은 블록 전체가 필요한 만큼 살아났는지 확인합니다.", "대사 누락이 생기면 제외정규식 조건을 좁히고 다시 추출합니다."],
        "notices": [("주의", "한 줄 조건이 전체 대사 블록으로 확장되므로, 넓은 정규식과 함께 쓰면 필요한 대사가 통째로 빠질 수 있습니다."), ("중요", "이 설정은 추출 판단에 영향을 주므로 저장 후 다시 추출해야 결과를 확인할 수 있습니다.")],
        "confusion": [("예외정규식에도 적용되나요?", "네. 제외뿐 아니라 예외로 반드시 추출하게 하는 판단에도 같은 블록 확장 개념이 적용될 수 있습니다."), ("이미 번역한 결과가 바로 바뀌나요?", "아닙니다. 추출 결과를 새로 만들고 필요한 범위를 다시 번역해야 합니다.")],
    },
    "guide/401-extract-mode/index.html": {
        "summary": "401-Extract Mode는 MVMZ 이벤트 대사의 401 줄을 개별 항목 중심으로 추출할지, 이어지는 흐름을 묶음 중심으로 추출할지 정하는 설정입니다.",
        "when": ["대사를 한 줄씩 세밀하게 수정하고 싶을 때", "여러 줄 대사를 문맥 단위로 보고 번역하고 싶을 때", "merge 101-401과 함께 대사 추출 구조를 처음 정할 때"],
        "before": ["기본값은 list입니다.", "설정을 바꾸면 추출 결과 구조가 달라지므로 다시 추출해야 합니다.", "기존 번역 파일과 구조가 달라질 수 있으므로 작업 초반에 결정하는 편이 좋습니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 401-Extract Mode를 확인합니다.", "줄 단위 관리가 필요하면 list를 선택합니다.", "문맥 단위 관리가 필요하면 group을 선택합니다.", "필요하면 merge 101-401 설정도 함께 확인합니다.", "MVMZ 추출을 다시 실행합니다.", "대사 결과가 원하는 단위로 보이는지 확인합니다."],
        "result": ["추출 결과에서 대사 줄이 개별 항목인지 묶음 항목인지 확인합니다.", "번역 후 적용했을 때 줄 순서와 대사 흐름이 유지되는지 확인합니다.", "번역 품질이 문맥 부족으로 흔들리면 group을 비교하고, 검수 편의가 떨어지면 list를 비교합니다."],
        "notices": [("중요", "401-Extract Mode는 추출 구조를 바꾸는 설정입니다. 이미 번역을 많이 진행했다면 변경 전에 필요한 파일을 보관하세요."), ("권장", "대사량이 많고 문맥이 중요한 작품은 group을 시험하고, 짧은 반복 대사가 많은 작품은 list를 먼저 확인해 보세요.")],
        "confusion": [("Flatten Mode와 같은 설정인가요?", "아닙니다. 401-Extract Mode는 추출 결과의 단위를 정하고, Flatten Mode는 번역 단계에서 AI에 넘기는 입력 단위를 조정합니다."), ("group을 선택하면 적용이 더 위험한가요?", "위험하다기보다 구조가 달라집니다. 번역 결과의 줄 수와 대사 흐름이 맞는지 확인하는 과정이 더 중요해집니다.")],
    },
    "guide/flatten-mode/index.html": {
        "summary": "Flatten Mode는 MVMZ 401 대사를 번역할 때 추출된 대사 구조를 AI에 어떤 입력 단위로 전달할지 정하는 설정입니다.",
        "when": ["대사 문맥을 더 길게 묶어 AI에 전달하고 싶을 때", "줄 단위 번역이 어색해 같은 블록을 한 번에 번역해 보고 싶을 때", "401-Extract Mode 결과에 맞춰 번역 입력 방식을 조정할 때"],
        "before": ["기본값은 full입니다.", "화면에서 선택 가능한 항목만 현재 조합에서 사용할 수 있는 선택지로 보면 됩니다.", "이 설정은 추출 파일을 새로 만드는 기능이 아니라 번역 입력 방식을 조정하는 기능입니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Flatten Mode를 확인합니다.", "기본 동작을 유지하려면 full을 선택합니다.", "대화 흐름을 묶어 번역하고 싶으면 group을 선택합니다.", "줄바꿈으로 이어진 401 블록을 한 번에 번역하고 싶으면 block을 선택합니다.", "번역을 실행합니다."],
        "result": ["번역 결과에서 대사 문맥이 자연스러운지 확인합니다.", "번역 결과의 줄 수가 원문 구조와 크게 어긋나지 않는지 확인합니다.", "적용 후 실제 게임에서 대사창 줄바꿈과 순서를 확인합니다."],
        "notices": [("주의", "묶어서 번역하면 문맥은 좋아질 수 있지만, 결과 줄 수가 달라져 적용이나 검수에서 확인할 항목이 늘어날 수 있습니다."), ("중요", "Flatten Mode 변경 후에는 기존 번역 결과를 그대로 믿지 말고 필요한 범위를 다시 번역해 비교하세요.")],
        "confusion": [("추출 결과 파일 모양도 바뀌나요?", "아닙니다. 이 설정은 주로 번역 단계에서 AI에 전달하는 입력 단위를 조정합니다. 추출 구조는 401-Extract Mode에서 결정합니다."), ("항목이 비활성화되어 있으면 오류인가요?", "아닙니다. 현재 401-Extract Mode 조합에서 의미가 없는 선택지는 화면에서 제한될 수 있습니다.")],
    },
    "guide/include-text-type/index.html": {
        "summary": "Include text type은 MVMZ 이벤트 대사를 AI에 보낼 때 해당 항목이 이름 계열인지 대사 계열인지 구분 힌트를 함께 전달하는 설정입니다.",
        "when": ["이름과 대사가 섞인 번역에서 모델이 역할을 헷갈릴 때", "이름은 음역 또는 고유명사처럼, 대사는 자연스러운 문장처럼 다루게 하고 싶을 때", "프롬프트와 함께 텍스트 역할 정보를 더 분명히 주고 싶을 때"],
        "before": ["기본값은 꺼짐입니다.", "이 설정은 원문 파일이나 게임 데이터를 바꾸지 않습니다.", "역할 힌트가 번역 결과에 미치는 영향을 확인합니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Include text type을 켭니다.", "필요하면 401-Extract Mode와 Flatten Mode도 확인합니다.", "번역을 실행합니다.", "이름과 대사의 번역 방식이 더 안정적인지 확인합니다."],
        "result": ["번역 결과에서 이름 표기와 대사 자연스러움을 확인합니다.", "번역문에 역할 표시가 그대로 섞여 나오지 않는지 확인합니다.", "효과가 작거나 결과가 어색하면 끈 상태로 되돌립니다."],
        "notices": [("중요", "Include text type은 번역 입력 힌트입니다. 이미 만들어진 추출 결과나 게임 데이터 구조를 바꾸는 설정은 아닙니다.")],
        "confusion": [("켜면 이름 번역이 자동으로 고정되나요?", "아닙니다. 이름/대사 구분을 돕는 힌트일 뿐입니다. 고정 표기는 용어사전이나 프롬프트와 함께 관리하세요."), ("모든 엔진에 적용되나요?", "이 문서는 MVMZ 이벤트 대사 번역 흐름을 기준으로 설명합니다.")],
    },
    "guide/include-speaker-name/index.html": {
        "summary": "Include speaker name은 MVMZ 이벤트 대사를 AI에 보낼 때 해당 문장을 말하는 화자명을 함께 전달하는 설정입니다.",
        "when": ["화자에 따라 존댓말, 반말, 말투가 달라지는 작품을 번역할 때", "같은 문장도 누가 말하느냐에 따라 번역 느낌을 다르게 잡고 싶을 때", "merge 101-401이나 group 계열 설정과 함께 대화 문맥을 보강하고 싶을 때"],
        "before": ["기본값은 꺼짐입니다.", "화자명이 비어 있는 대사는 이 설정의 체감 효과가 작을 수 있습니다.", "이 설정은 화자명을 게임 대사에 새로 써 넣는 기능이 아닙니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 Include speaker name을 켭니다.", "화자명이 있는 이벤트 대사를 번역합니다.", "말투와 호칭이 더 안정적으로 유지되는지 비교합니다.", "필요하면 프롬프트나 용어사전의 인물 표기 기준도 함께 조정합니다."],
        "result": ["화자별 말투가 의도대로 유지되는지 확인합니다.", "번역 결과에 화자명이 불필요하게 본문으로 들어가지 않았는지 확인합니다.", "화자명이 없는 이벤트에서는 기대한 변화가 없는지 확인합니다."],
        "notices": [("중요", "이 설정은 AI 입력에 참고용 화자 정보를 붙이는 기능입니다. 게임 데이터의 화자명 자체를 수정하지 않습니다.")],
        "confusion": [("MV와 MZ 모두 같은 효과인가요?", "화자 정보가 실제로 제공되는 방식은 프로젝트 구조에 따라 다를 수 있습니다. 화자명이 없는 데이터에서는 효과가 제한됩니다."), ("화자명을 번역문 앞에 붙이는 기능인가요?", "아닙니다. 화자명은 번역 판단을 돕는 정보로 전달되며, 본문에 표시하기 위한 접두어가 아닙니다.")],
    },
    "guide/401-block-unit-for-consistency-duplicate/index.html": {
        "summary": "401 Block Unit for Consistency/Duplicate은 번역일관성과 추출중복 검사에서 MVMZ 401 대사를 한 줄씩이 아니라 같은 대사 블록 단위로 비교할지 정하는 설정입니다.",
        "when": ["여러 줄 대사를 한 덩어리로 보고 일관성을 검사하고 싶을 때", "한 줄 단위 중복보다 대사 블록 전체의 반복 여부가 더 중요할 때", "번역일관성 또는 추출중복 도구의 결과가 너무 잘게 쪼개져 보일 때"],
        "before": ["기본값은 꺼짐입니다.", "현재 추출 결과에 대사 블록 정보가 맞게 준비되어 있어야 합니다.", "이 설정은 추출 자체보다 검사 도구의 비교 단위에 영향을 줍니다."],
        "steps": ["설정 화면에서 MVMZ 영역의 401 Block Unit for Consistency/Duplicate을 확인합니다.", "대사 블록 단위로 검사하고 싶으면 켭니다.", "줄 단위로 짧은 반복 표현을 찾고 싶으면 끕니다.", "번역일관성 또는 추출중복 도구를 실행합니다.", "검사 결과가 블록 단위로 표시되는지 확인합니다.", "필요한 경우 설정을 바꿔 다시 검사합니다."],
        "result": ["번역일관성 결과에서 원문/번역 후보가 블록 단위로 묶여 보이는지 확인합니다.", "추출중복 결과에서 반복 블록이 의도한 단위로 잡히는지 확인합니다.", "수정 후 적용하거나 저장할 때 블록의 줄 수와 순서가 유지되는지 확인합니다."],
        "notices": [("주의", "블록 단위 후보를 직접 수정할 때는 원래 블록의 줄 수와 순서를 최대한 유지하세요. 줄 수가 크게 달라지면 결과 반영이 어긋날 수 있습니다."), ("권장", "짧은 감탄사나 반복 단어를 찾을 때는 꺼짐, 긴 대사 흐름의 일관성을 볼 때는 켜짐을 비교하세요.")],
        "confusion": [("추출 결과도 다시 만들어지나요?", "아닙니다. 이 설정은 주로 번역일관성, 추출중복 같은 검사 도구의 비교 단위를 바꿉니다."), ("모든 MVMZ 파일에 적용되나요?", "일반적인 이벤트 401 대사 검사를 기준으로 이해하면 됩니다. 다른 데이터베이스 텍스트는 별도 설정과 흐름을 따릅니다.")],
    },
    "guide/wolf-secondary-exclusion-filter/index.html": {
        "summary": "WOLF 2차 추출 제외 필터는 1차 추출 결과 중 실제 번역 대상으로 다시 뽑을 항목을 규칙으로 선별하는 화면입니다.",
        "when": ["2차 추출 결과에 불필요한 문장이 많이 섞일 때", "번역해야 할 문장이 누락되어 조건을 넓혀야 할 때", "파일, 명령, 이벤트, 텍스트 패턴 기준으로 추출 범위를 조정할 때"],
        "before": ["1차 추출 결과가 준비되어 있어야 합니다.", "현재 2차 추출 결과의 누락/과다 추출 예시를 먼저 확인합니다.", "정규식을 바꾼 뒤 추출 결과를 확인합니다."],
        "steps": ["WOLF 2차 추출 제외 필터 화면을 엽니다.", "프리셋을 기준으로 규칙을 불러옵니다.", "필요한 규칙만 활성화합니다.", "파일, 경로, 명령 ID, 텍스트 조건을 확인합니다.", "저장한 뒤 2차 추출을 다시 실행합니다.", "추출 결과를 열어 의도한 항목이 들어왔는지 확인합니다."],
        "result": ["추출 항목 수와 실제 문장을 함께 확인합니다.", "결과가 바뀌었다면 필요한 범위를 다시 번역합니다."],
        "notices": [("중요", "필터 저장만으로 기존 추출/번역 결과가 자동 갱신되지는 않습니다.")],
    },
    "guide/vxvxa-message-block-unit/index.html": {
        "summary": "Message Block Unit은 VXVXA의 401 메시지를 한 줄씩이 아니라 메시지 블록 단위로 추출하고 적용하도록 바꾸는 설정입니다.",
        "when": ["VXVXA 대사가 여러 줄로 이어지고 줄 단위 번역이 문맥을 깨뜨릴 때", "401 대사를 MVMZ처럼 묶음 단위로 다루고 싶을 때", "번역 결과를 적용했을 때 줄 순서나 묶음이 어긋나는지 확인해야 할 때"],
        "before": ["현재 엔진이 VXVXA인지 확인합니다.", "대상 파일에 메시지 블록 마커가 있는 경우에만 블록 단위 처리가 적용됩니다.", "기존 추출 결과와 방식이 달라지므로 설정 변경 후에는 다시 추출합니다."],
        "steps": ["설정 화면에서 VXVXA 탭을 엽니다.", "Message Extract 영역의 Message Block Unit을 켜거나 끕니다.", "VXVXA 추출을 다시 실행합니다.", "code_401 결과가 대사 묶음 단위로 정리되었는지 확인합니다.", "번역 후 적용하고 실제 게임에서 줄 수와 대사 순서를 확인합니다."],
        "result": ["여러 줄 대사가 하나의 번역 단위로 보이는지 확인합니다.", "적용 후 대사 줄 수가 어긋나지 않는지 확인합니다."],
        "notices": [("중요", "블록 번역 결과의 줄 수가 원본과 맞지 않으면 해당 블록 적용이 건너뛰어질 수 있습니다.")],
    },
    "guide/cmd-122-secondary-duplicate-handling/index.html": {
        "summary": "Cmd 122 2차 추출 중복처리는 WOLF의 SET_STRING 명령 후보가 2차 추출에서 반복될 때 중복 처리를 보정하는 설정입니다.",
        "when": ["WOLF 2차 추출 결과에서 같은 SET_STRING 후보가 반복될 때", "동일한 문자열 후보가 여러 위치에서 중복 번역 대상으로 잡힐 때", "SET_STRING 자체는 유지하면서 반복 후보만 줄이고 싶을 때"],
        "before": ["현재 프로젝트가 WOLF 계열인지 확인합니다.", "반복 항목이 WOLF Command ID 122 또는 SET_STRING 후보인지 확인합니다.", "설정을 바꾼 뒤에는 2차 추출 결과를 다시 만들어 비교합니다."],
        "steps": ["WOLF 2차 추출 결과에서 반복되는 SET_STRING 후보를 확인합니다.", "Cmd 122 2차 추출 중복처리 설정을 켜거나 끕니다.", "2차 추출을 다시 실행합니다.", "반복 항목이 줄었는지, 필요한 문장이 빠지지 않았는지 비교합니다."],
        "result": ["SET_STRING 후보가 의도대로 정리되었는지 확인합니다.", "필요한 후보가 빠졌다면 설정을 끄고 결과를 비교합니다."],
        "notices": [("주의", "이 문서의 122는 RPG Maker 명령 코드가 아니라 WOLF의 SET_STRING 명령 ID입니다.")],
    },
    "guide/ctf-fast-image-extraction/index.html": {
        "summary": "CTF 이미지 추출과 적용은 DAT, CCN, EXE에서 PNG를 꺼내고 교체 이미지를 원래 slot에 다시 넣는 흐름입니다.",
        "when": ["CTF 게임의 이미지를 확인하거나 교체할 때", "투명 PNG를 편집해 다시 적용할 때"],
        "before": ["원본 DAT, CCN, EXE를 백업합니다.", "추출 폴더의 image_manifest.json을 유지합니다."],
        "steps": ["도구의 CTF Crypter에서 이미지를 엽니다.", "추출과 source를 선택합니다.", "PNG를 편집하되 파일명과 alpha를 유지합니다.", "같은 source에 교체 PNG를 적용합니다.", "게임을 실행해 결과를 확인합니다."],
        "result": ["교체 이미지와 투명 영역을 확인합니다.", "오류가 나면 원본 PNG와 manifest로 되돌립니다."],
        "notices": [("중요", "기존 worker 수 기반 고속 추출 설정은 제거됐습니다.")],
    },
    "guide/ctf-secondary-exclusion-filter/index.html": {
        "summary": "CTF 2차 추출 제외 필터는 ClickTeam Fusion 계열 프로젝트에서 2차 추출 대상으로 삼을 텍스트를 규칙으로 선별하는 화면입니다.",
        "when": ["CTF 2차 추출 결과에 필요 없는 값이 많이 섞일 때", "특정 역할, 카테고리, 식별자에 해당하는 텍스트만 골라내고 싶을 때", "TextId, Context, Value 패턴으로 번역 대상을 조정할 때"],
        "before": ["CTF 프로젝트의 1차 추출 결과가 준비되어 있어야 합니다.", "현재 2차 추출 결과에서 과다 추출/누락 예시를 먼저 확인합니다.", "정규식 조건을 바꾼 뒤 추출 결과를 확인합니다."],
        "steps": ["프리셋으로 기본 규칙을 불러옵니다.", "사용할 규칙만 활성화합니다.", "카테고리, Role, Source Kind, Identifier 조건을 확인합니다.", "TextId, Context, Value 정규식을 조정합니다.", "저장 후 2차 추출을 다시 실행합니다."],
        "result": ["규칙이 의도대로 적용되었는지 추출 결과에서 확인합니다.", "결과가 바뀌었다면 필요한 범위를 다시 번역합니다."],
        "notices": [("중요", "필터 편집은 앞으로 만들 2차 추출 결과에 영향을 주며, 기존 결과를 자동으로 다시 고치지는 않습니다.")],
    },
    "guide/bakin-secondary-exclusion-filter/index.html": {
        "summary": "Bakin 2차 추출 제외 필터는 조건과 일치하는 후보를 Bakin 추출2 결과에서 제외하는 규칙을 편집하는 화면입니다.",
        "when": ["Bakin 추출2 결과에 번역하지 않을 후보가 섞일 때", "추출 파일명, domain, RBR 경로, 원문 정규식을 조합해 제외 조건을 만들 때", "기본 분류기만으로 현재 프로젝트의 제외 범위가 부족할 때"],
        "before": ["Bakin 1차 추출과 추출2 결과가 준비되어 있어야 합니다.", "제외하려는 항목의 추출 파일명, domain, RBR 경로, 원문 예시를 먼저 확인합니다.", "규칙에 매칭된 항목은 mapping에도 들어가지 않을 수 있습니다."],
        "steps": ["Bakin 2차 추출 제외 필터 화면을 엽니다.", "제외할 규칙만 활성화합니다.", "규칙 이름, 추출 파일, 도메인 정규식, RBR 경로 정규식, 원문 정규식을 확인합니다.", "저장 후 Bakin 추출2를 다시 실행합니다.", "제외 대상과 필요한 문장 누락 여부를 확인합니다."],
        "result": ["제외 대상이 결과 JSON에서 빠졌는지 확인합니다.", "필요한 문장까지 빠지지 않았는지 추출 결과에서 확인합니다."],
        "notices": [("주의", "Bakin 2차 추출 제외 필터는 포함 규칙이 아니라 제외 규칙입니다. 조건을 너무 넓게 잡으면 필요한 문장도 빠질 수 있습니다.")],
    },
    "guide/srpg-secondary-extraction-filter/index.html": {
        "summary": "SRPG 2차 추출 필터는 SRPG Studio 2차 추출에서 통과시킬 문자열 위치를 지정하는 설정입니다.",
        "when": ["SRPG Studio 2차 추출에서 번역 대상이 너무 넓거나 좁을 때", "이벤트 명령, 이름/설명, 창/폰트, String Table, JS Plugin 일본어 등 특정 범위를 골라 추출하고 싶을 때", "파일명, JSON 경로, 텍스트 정규식 조건으로 추출 대상을 조정해야 할 때"],
        "before": ["이 필터는 WOLF/CTF/Bakin의 제외 필터와 다르게, 먼저 추출할 대상을 지정하는 필터입니다.", "대상 파일, 경로 패턴, 텍스트 정규식은 포함 조건으로 이해합니다.", "제외 파일, 제외 경로, 제외 텍스트 정규식은 포함된 결과 안에서 다시 빼는 보조 조건입니다."],
        "steps": ["설정 화면에서 SRPG Studio 탭을 엽니다.", "2차 추출 필터를 엽니다.", "프리셋을 기준으로 필요한 규칙을 불러옵니다.", "원본 종류, 대상 파일, 경로 패턴, 텍스트 정규식을 확인합니다.", "필요한 경우 제외 파일, 제외 경로, 제외 텍스트 정규식으로 통과 결과를 좁힙니다.", "저장 후 SRPG Studio 2차 추출을 다시 실행합니다."],
        "result": ["추출 결과에 의도한 SRPG Studio 문자열 위치만 들어왔는지 확인합니다.", "필요한 문장이 빠졌다면 포함 조건을 넓히고, 불필요한 항목이 많다면 제외 조건을 추가합니다."],
        "notices": [("중요", "SRPG 2차 추출 필터의 기본 방향은 제외가 아니라 추출 대상 지정입니다. 제외 항목은 통과된 결과를 다시 줄이는 보조 조건으로 다루세요.")],
    },
    "guide/livemaker-font-settings/index.html": {
        "summary": "LiveMaker 폰트 설정은 LiveMaker 적용 과정에서 사용할 AIMT_LiveMaker_KR.ttf 생성용 원본 폰트를 선택하는 설정입니다.",
        "when": ["LiveMaker 번역 후 한글이 네모나 빈 글자로 보일 때", "기본 한글 폰트를 찾지 못했다는 표시가 보일 때", "게임에 맞는 다른 한글 폰트를 사용하고 싶을 때", "FontMod 적용 후 실제 로드된 폰트를 확인해야 할 때"],
        "before": ["한글 글리프가 포함된 ttf, otf, woff 폰트를 준비합니다.", "상업용 작품에 사용할 폰트라면 라이선스를 먼저 확인합니다.", "폰트 변경은 번역문 내용이 아니라 실행 중 글자 표시 방식에 영향을 줍니다."],
        "steps": ["설정 화면에서 LiveMaker 탭을 엽니다.", "AIMT_LiveMaker_KR.ttf 생성용 폰트 항목을 확인합니다.", "System Fonts 또는 Select File로 사용할 폰트를 선택합니다.", "현재 선택 항목이 바뀌었는지 확인합니다.", "LiveMaker 적용을 다시 진행하고 게임에서 한글 표시를 확인합니다."],
        "result": ["게임 실행 시 한글이 정상적으로 보이는지 확인합니다.", "필요하면 LiveMaker FontMod 로그 확인으로 로드된 폰트와 요청된 폰트를 비교합니다."],
        "notices": [("주의", "폰트가 선택되어도 게임 화면 폭, 줄바꿈, 글리프 지원 여부는 실제 실행 화면에서 반드시 확인해야 합니다.")],
    },
    "guide/include-tl-translations/index.html": {
        "summary": "Ren'Py TL 준비는 대상 언어의 TL을 새로 만들거나 기존 TL을 복제하고 번역 데이터를 추출하는 흐름입니다.",
        "when": ["game/tl 아래에 새 번역 언어를 만들 때", "기존 TL을 복제해 재번역할 때", "기존 TL에서 번역 데이터만 다시 추출할 때"],
        "before": ["Ren'Py Extract1로 RAW를 준비합니다.", "대상 언어 이름과 기존 TL 교체 여부를 확인합니다."],
        "steps": ["도구에서 Ren'Py TL 준비를 엽니다.", "새 TL 준비 또는 기존 TL 재추출을 고릅니다.", "대상 언어와 원본을 선택합니다.", "언어 적용 방법을 선택하고 실행합니다.", "생성된 번역 데이터를 확인합니다."],
        "result": ["game/tl/<대상 언어>와 추출 JSON을 확인합니다.", "Preferences 또는 시작 언어 적용을 게임에서 확인합니다."],
        "notices": [("주의", "기존 대상 TL은 AIMT 작업 백업에 보관한 뒤 교체됩니다.")],
    },
    "guide/extraction/index.html": {
        "summary": "추출은 게임 파일에서 번역할 수 있는 텍스트를 찾아 작업용 파일로 준비하는 단계입니다.",
        "when": ["새 프로젝트를 시작할 때", "게임 파일이 바뀐 뒤 번역 대상을 다시 만들 때", "누락된 문장이 있는지 확인할 때"],
        "before": ["프로젝트 폴더가 올바른지 확인합니다.", "게임 형식에 맞는 엔진별 가이드를 확인합니다.", "이전 추출 결과를 덮어쓸 수 있으므로 필요한 파일을 보관합니다."],
        "steps": ["프로젝트와 게임 형식을 확인합니다.", "추출 옵션을 확인합니다.", "추출을 실행합니다.", "완료 메시지와 생성된 파일을 확인합니다."],
        "result": ["추출 결과 목록에 번역 대상이 표시되는지 확인합니다.", "예상보다 항목이 적으면 엔진별 제한과 추출 옵션을 확인합니다."],
    },
    "guide/translation/index.html": {
        "summary": "번역은 추출된 원문을 선택한 번역 방식으로 번역하는 단계입니다.",
        "when": ["추출 결과가 준비되었을 때", "일부 파일만 다시 번역할 때", "번역 설정을 바꾼 뒤 결과를 새로 만들 때"],
        "before": ["API 키, 모델, 번역 설정을 확인합니다.", "원문 언어와 결과 언어를 확인합니다."],
        "steps": ["번역할 파일이나 범위를 선택합니다.", "번역 설정을 확인합니다.", "번역을 실행합니다.", "오류 메시지와 생성 결과를 확인합니다."],
        "result": ["번역 결과 파일이 생성되었는지 확인합니다.", "일부 문장을 열어 용어와 문체가 유지되는지 확인합니다.", "오류가 나면 키, 모델, 요청 제한을 확인합니다."],
    },
    "guide/apply-and-instant-apply/index.html": {
        "summary": "적용과 즉시적용은 번역 결과를 게임 프로젝트에 반영하는 단계입니다.",
        "when": ["번역 결과를 실제 게임에서 확인하려 할 때", "일부 결과만 빠르게 반영해야 할 때", "적용 후 문제가 생겨 다시 확인해야 할 때"],
        "before": ["번역 결과가 준비되어 있어야 합니다.", "게임을 실행 중이라면 파일 잠금 문제가 없는지 확인합니다.", "되돌릴 수 있도록 적용 전 파일을 보관합니다."],
        "steps": ["적용할 결과와 대상 프로젝트를 확인합니다.", "적용 또는 즉시적용을 선택합니다.", "완료 메시지를 확인합니다.", "게임을 실행해 실제 화면을 확인합니다."],
        "result": ["게임 화면에 번역문이 반영되었는지 확인합니다.", "깨짐, 누락, 적용 실패가 있으면 적용 대상과 엔진별 제한을 확인합니다."],
    },
    "guide/quick-translation/index.html": {
        "summary": "빠른번역은 짧은 문장이나 일부 내용을 빠르게 번역해 설정과 모델 상태를 확인하는 기능입니다.",
        "when": ["API 키와 모델이 정상인지 시험할 때", "짧은 문장을 즉시 번역해야 할 때"],
        "before": ["API 키와 모델이 준비되어 있어야 합니다.", "원문 언어와 결과 언어를 확인합니다.", "프롬프트나 용어사전이 결과에 영향을 줄 수 있습니다."],
        "steps": ["번역할 문장을 입력합니다.", "사용할 번역 방식과 모델을 확인합니다.", "빠른번역을 실행합니다.", "결과와 오류 메시지를 확인합니다."],
        "result": ["짧은 문장이 정상 번역되는지 확인합니다.", "실패하면 API 키, 모델, 네트워크 상태를 확인합니다."],
    },
    "guide/faq/index.html": {
        "before": ["프로젝트 폴더가 올바른지 확인합니다.", "추출, 번역, 적용 중 어느 단계에서 문제가 생겼는지 구분합니다.", "오류 메시지가 있다면 문구를 그대로 확인합니다.", "API 관련 문제는 키, 모델, 사용량, 네트워크를 순서대로 확인합니다."],
        "steps": ["최근에 바꾼 설정을 확인합니다.", "화면에 표시된 오류 메시지와 작업 단계를 함께 확인합니다.", "엔진별 가이드에서 해당 형식의 제한 사항을 확인합니다."],
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
            "before": ["게임 형식이 이 문서와 맞는지 확인합니다.", "원본 게임 파일을 보관합니다."],
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
        ("https://cloud.google.com/docs/authentication/provide-credentials-adc", "Vertex AI 인증", "Vertex AI에서 사용할 Google 인증 환경을 준비합니다."),
        ("https://platform.openai.com/api-keys", "OpenAI API Keys", "OpenAI API 키를 만들고 관리합니다."),
        ("https://developers.openai.com/api/docs/quickstart", "OpenAI API Quickstart", "OpenAI API 키 준비와 첫 요청 흐름을 확인합니다."),
        ("https://platform.claude.com/", "Claude Console", "Claude API 사용을 위한 콘솔에 접속합니다."),
        ("https://console.x.ai/", "xAI Console", "xAI API 키와 사용량을 관리합니다."),
        ("https://docs.x.ai/docs/overview", "xAI API 문서", "xAI API의 인증과 모델 사용 방법을 확인합니다."),
        ("https://openrouter.ai/settings/keys", "OpenRouter API Keys", "OpenRouter API 키를 만들고 사용량 제한을 관리합니다."),
        ("https://openrouter.ai/docs/api/reference/authentication", "OpenRouter 인증 문서", "OpenRouter API 키와 Bearer 인증 방식을 확인합니다."),
        ("https://platform.deepseek.com/api_keys", "DeepSeek API Keys", "DeepSeek API 키를 만들고 관리합니다."),
        ("https://api-docs.deepseek.com/api/deepseek-api", "DeepSeek 인증 문서", "DeepSeek API 인증과 호출 방식을 확인합니다."),
        ("https://developers.deepl.com/docs/getting-started/auth", "DeepL 인증 문서", "DeepL API 인증 키 확인 위치와 보안 주의사항을 확인합니다."),
        ("https://developers.deepl.com/docs/getting-started/managing-api-keys", "DeepL API 키 관리", "DeepL API 키 생성, 사용량, 제한 설정을 확인합니다."),
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
        case "readiness":
            return _section("시작 전에 확인할 것", _ul(list(metadata["before"])))
        case "procedure":
            heading = "진행 순서" if page_type in {"workflow", "engine"} else "따라 하기"
            return _section(heading, _ol(list(metadata["steps"])))
        case "details":
            return _section(str(metadata.get("details_title", "화면과 항목")), content)
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
    if path == "guide/settings-screen/index.html":
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
        _image_block(from_path, "guide/assets/bottom-area/image.png", "AIMT 화면 전체"),
        "<h2>전체 화면</h2>",
        _p("AIMT 화면은 크게 영역1 사이드바, 영역2 메인뷰, 영역3 커맨드바로 나누어 볼 수 있습니다. 먼저 전체 화면의 위치 관계를 확인한 뒤, 필요한 영역의 설명과 관련 문서로 이동하세요."),
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


def _api_key_article() -> str:
    path = "guide/api-key-settings/index.html"
    details = _image_block(DIST_ROOT / path, "guide/assets/api-key-settings/image.png", "API KEY 설정 화면")
    details += _table(
        ("제공자", "입력값"),
        [
            ("Gemini, OpenAI, OpenAI-compatible, Claude", "각 제공자가 발급한 API 키"),
            ("xAI, DeepSeek, OpenRouter, DeepL", "각 제공자가 발급한 API 키"),
            ("Vertex", "Google Cloud Project ID"),
        ],
    )
    details += _p("Vertex는 Project ID와 함께 Google 인증 환경과 번역 설정의 리전이 준비되어 있어야 합니다. Google Translate와 Papago는 이 화면에서 키를 등록하지 않습니다.")
    details += _p("키는 그룹으로 정리하거나 Ungrouped에 둘 수 있습니다. ON인 키만 사용 후보가 되며, 그룹을 삭제해도 키는 Ungrouped로 이동합니다.")
    return _render_article_body(path, "API KEY 설정", "feature", PAGE_METADATA[path], details)


def _cache_management_article() -> str:
    path = "guide/cache-management/index.html"
    prompt_link = _link("guide/prompt/index.html", "프롬프트의 DB 사전 캐시 관리", DIST_ROOT / path)
    details = _table(
        ("항목", "삭제되는 내용"),
        [
            ("백업", "AIMT가 만든 작업 백업"),
            ("추출·번역·매핑", "재작업과 적용에 쓰는 결과"),
            ("로그·체크", "오류 기록과 검사 결과"),
            ("엔진별 항목", "해당 엔진의 중간 상태"),
        ],
    )
    details += f"<p>MVMZ 자동 사전의 프로젝트별 세션을 보고 내보내거나 가져오려면 {prompt_link}를 사용합니다. 이 페이지의 캐시 삭제와는 다른 기능입니다.</p>"
    return _render_article_body(path, "캐시 관리", "feature", PAGE_METADATA[path], details)


def _wolf_rpg_editor_article() -> str:
    path = "guide/wolf-rpg-editor/index.html"
    details = _table(
        ("단계", "결과"),
        [
            ("추출1", "BasicData와 MapData를 1차 작업 데이터로 변환합니다."),
            ("추출2", "필터를 적용해 AIMT_Extract에 번역용 JSON을 만듭니다."),
            ("적용1", "번역 JSON을 1차 작업 상태에 반영합니다."),
            ("적용2", "반영된 데이터를 게임의 Data 폴더에 씁니다."),
        ],
    )
    details += f'<p>아카이브 준비가 필요하면 {_link("guide/wolf-unpack-repack/index.html", "WOLF 언팩/리팩", DIST_ROOT / path)}을 먼저 확인합니다. 추출 범위를 바꾸려면 {_link("guide/wolf-secondary-exclusion-filter/index.html", "WOLF 2차 추출 제외 필터", DIST_ROOT / path)}를 사용합니다.</p>'
    metadata = {
        "summary": "WOLF RPG Editor 게임의 아카이브 준비부터 추출1, 추출2, 번역, 적용1, 적용2까지 이어지는 작업 흐름입니다.",
        "when": ["WOLF 게임을 처음 번역할 때", "추출1·2와 적용1·2의 순서를 확인할 때", "적용2 전에 필요한 확인 사항을 찾을 때"],
        "before": ["Project Hub에서 WOLF 엔진과 게임 폴더를 선택합니다.", "원본 게임을 별도로 보관합니다.", "Data가 아카이브로 묶여 있으면 먼저 언팩합니다."],
        "steps": ["추출1을 실행합니다.", "필요하면 WOLF 2차 추출 제외 필터를 조정합니다.", "추출2를 실행하고 AIMT_Extract의 JSON을 확인합니다.", "필요한 파일을 번역하고 일관성·이스케이프·빈칸을 검수합니다.", "적용1을 실행합니다.", "적용2를 실행하고 표시되는 파일명·인코딩 확인을 처리합니다.", "게임을 실행해 대사, 메뉴, 파일 로딩을 확인합니다."],
        "result": ["필요한 대사와 메뉴가 번역되었는지 확인합니다.", "글자 깨짐, 누락 파일, 로딩 오류가 없는지 확인합니다.", "문제가 있으면 같은 프로젝트에서 추출2부터 다시 진행합니다."],
        "notices": [("중요", "추출한 프로젝트와 적용할 프로젝트가 같아야 합니다."), ("주의", "적용2에서 CP949 저장 불가 파일을 건너뛰면 해당 파일에는 번역이 반영되지 않습니다.")],
    }
    return _render_article_body(path, "WOLF RPG Editor", "engine", metadata, details)


def _wolf_archive_article() -> str:
    path = "guide/wolf-unpack-repack/index.html"
    details = _table(
        ("항목", "선택 기준"),
        [
            ("언팩 대상", "미리보기에서 풀 디렉터리만 선택합니다."),
            ("리팩 대상 폴더", "아카이브로 만들 폴더를 선택합니다."),
            ("버전", "2.01, 2.10, 2.20, 2.225, 3.00, 3.14, 3.31, 3.50 중 원본과 맞는 값을 선택합니다."),
            ("출력 확장자", ".wolf, .data, .pak, .bin, .assets, .content, .res, .resource 중 선택합니다."),
            ("키 참조 파일", "보호된 아카이브에서 원본 키가 필요할 때만 선택합니다."),
        ],
    )
    metadata = {
        "summary": "WOLF 아카이브의 내부 디렉터리를 선택해 풀거나, 작업 폴더를 지정한 버전과 확장자로 다시 묶는 도구입니다.",
        "when": ["게임 데이터가 .wolf나 .assets 같은 아카이브로 묶여 있을 때", "수정한 폴더를 WOLF 아카이브로 다시 만들 때"],
        "before": ["Project Hub에서 올바른 WOLF 게임 폴더를 선택합니다.", "원본 아카이브를 별도로 보관합니다.", "게임과 편집기에서 대상 파일을 닫습니다."],
        "steps": ["작업 도구의 WOLF에서 언팩을 엽니다.", "아카이브와 모드를 확인하고 풀 디렉터리를 선택합니다.", "언팩을 실행하고 생성된 Data 구조를 확인합니다.", "리팩이 필요하면 작업 도구의 WOLF에서 리팩을 엽니다.", "대상 폴더, 원본 버전, 출력 확장자를 선택합니다.", "보호 키가 필요한 경우에만 키 참조 파일을 선택합니다.", "리팩을 실행하고 출력 경로와 검증 로그를 확인합니다."],
        "result": ["언팩 후 선택한 디렉터리의 파일이 정상적으로 열리는지 확인합니다.", "리팩 결과는 대상 폴더 옆에 같은 이름과 선택한 확장자로 생성됩니다.", "게임을 실행해 아카이브를 정상적으로 읽는지 확인합니다."],
        "notices": [("중요", "리팩 버전이 원본과 다르면 게임이 아카이브를 읽지 못할 수 있습니다."), ("주의", "같은 이름의 출력 아카이브가 이미 있으면 리팩이 중단됩니다. 기존 파일을 확인한 뒤 다시 실행하세요.")],
    }
    return _render_article_body(path, "언팩/리팩", "feature", metadata, details)


REVIEWED_VERSION_ONLY_PATHS: set[str] = {
    "guide/features-screen/index.html",
    "guide/quick-translation/index.html",
    "guide/project-conversion/index.html",
    "guide/wolf-secondary-exclusion-filter/index.html",
    "guide/srpg-secondary-extraction-filter/index.html",
    "guide/srpg-studio-manual-build/index.html",
    "guide/srpg-studio-unpack/index.html",
    "guide/translation-consistency/index.html",
}


def _replace_doc_version(article: str) -> str:
    return re.sub(
        r'(?is)<p\b[^>]*class=["\'][^"\']*doc-version[^"\']*["\'][^>]*>.*?</p>',
        _doc_version(),
        article,
        count=1,
    )


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
        source_text = _git_source_text_for(path)
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
    basic_workflow_path = "guide/basic-workflow/index.html"
    basic_workflow_metadata = _metadata_for(basic_workflow_path, "기본 작업 흐름", "workflow")
    return {
        basic_workflow_path: _render_article_body(
            basic_workflow_path,
            "기본 작업 흐름",
            "workflow",
            basic_workflow_metadata,
            _render_links(list(basic_workflow_metadata["links"]), DIST_ROOT / basic_workflow_path),
        ),
        "guide/engine-guides/index.html": _hub_article(
            "guide/engine-guides/index.html",
            "엔진별 가이드",
            "게임 제작 도구나 엔진별로 다른 준비사항과 작업 흐름을 확인하는 영역입니다.",
            [
                ("guide/rpg-maker-mvmz/index.html", "RPG Maker MV/MZ"),
                ("guide/rpg-maker-vxvxa/index.html", "RPG Maker VX/VXA"),
                ("guide/wolf-rpg-editor/index.html", "WOLF RPG Editor"),
                ("guide/clickteam-fusion-coming-soon/index.html", "ClickTeam Fusion"),
                ("guide/tyranobuilder-tyranoscript/index.html", "TyranoBuilder/TyranoScript"),
                ("guide/pixel-game-maker-mv/index.html", "Pixel Game Maker MV"),
                ("guide/srpg-studio/index.html", "SRPG Studio"),
                ("guide/livemaker/index.html", "LiveMaker"),
                ("guide/bakin/index.html", "Bakin"),
                ("guide/renpy/index.html", "Ren'Py"),
                ("guide/csv-tsv/index.html", "CSV/TSV"),
                ("guide/multi-regex-engines/index.html", "HTML·범용 정규식 엔진"),
            ],
        ),
        "guide/features/index.html": _hub_article(
            "guide/features/index.html",
            "기능별 설명",
            "AIMT 화면의 각 영역과 도구별 기능을 찾아보는 영역입니다.",
            [
                ("guide/features-screen/index.html", "화면 영역"),
                ("guide/settings-screen/index.html", "설정 화면"),
                ("guide/workspace-tools/index.html", "작업 도구"),
                ("guide/quickslot/index.html", "퀵슬롯"),
            ],
        ),
        "guide/features-screen/index.html": _screen_area_article(),
        "guide/view-switching/index.html": _hub_article(
            "guide/view-switching/index.html",
            "화면전환",
            "AIMT의 화면 표시 방식과 명령 입력 화면으로 이동하는 기능을 함께 확인하는 영역입니다.",
            [
                ("guide/viewer/index.html", "Viewer"),
                ("guide/console/index.html", "Console"),
            ],
        ),
        "guide/troubleshooting/index.html": _hub_article(
            "guide/troubleshooting/index.html",
            "문제 해결",
            "오류, 적용 실패, 결과 이상, 사용량 문제처럼 작업 중 막히는 상황을 확인하는 영역입니다.",
            [
                ("guide/faq/index.html", "자주 나오는 질문"),
            ],
        ),
        "guide/advanced-reference/index.html": _hub_article(
            "guide/advanced-reference/index.html",
            "참고 자료",
            "AIMT에서 함께 참고하기 좋은 외부 사이트, API 제공자 문서, 출처 링크를 모은 영역입니다.",
            [
                ("guide/rpg-maker-command-code-reference/index.html", "RPG Maker 명령 코드 참고"),
                ("guide/extraction-files-reference/index.html", "추출 파일별 설명"),
                ("guide/external-utilities/index.html", "외부 유틸리티"),
                ("guide/provider-reference-links/index.html", "제공자별 참고 링크"),
            ],
        ),
        "guide/provider-reference-links/index.html": _render_article_body(
            "guide/provider-reference-links/index.html",
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


def _append_screen_area_groups(nav: list[dict[str, Any]], by_path: dict[str, dict[str, Any]], parent_depth: int) -> None:
    group_depth = parent_depth + 1
    child_depth = group_depth + 1
    for group_id, title, child_paths in SCREEN_AREA_NAV_GROUPS:
        nav.append(_virtual_nav_group(f"screen-{group_id}", title, group_depth))
        for child_path in child_paths:
            if child_path in EXCLUDE_FROM_NAV_PATHS:
                continue
            if child_path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
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
        parent_path = ""
        if group_id == "translation":
            parent_path = "guide/translation-settings/index.html"
            _ensure_path_entry(by_path, parent_path)
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
        if parent_path:
            try:
                parent_entry = dict(by_path[parent_path])
            except KeyError:
                continue
            parent_entry["depth"] = group_depth
            nav.append(parent_entry)
        else:
            nav.append(_virtual_nav_group(f"settings-{group_id}", title, group_depth))
        nav.extend(children)


def _make_nav(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        path = str(entry["path"])
        normalized_path = RENAMED_PAGE_PATHS.get(path, path)
        if normalized_path in by_path and path != normalized_path:
            continue
        nav_entry = dict(entry)
        nav_entry["path"] = normalized_path
        by_path[normalized_path] = nav_entry
    for path, title in {**GROUP_PAGES, **ADVANCED_SUBGROUP_PAGES, **SETTING_REFERENCE_GROUP_PAGES, **FEATURE_SUBGROUP_PAGES, **EXTERNAL_REFERENCE_PAGES}.items():
        by_path[path] = {"path": path, "title": title, "depth": 1, "order": -1, "hasChildren": True, "virtual": path in VIRTUAL_GROUP_PAGES}
    for path in SETTINGS_PAGE_CHILD_PATHS:
        _ensure_path_entry(by_path, path)
    for path in SCREEN_AREA_NAV_CHILD_PATHS:
        _ensure_path_entry(by_path, path)
    for path in ENGINE_PATHS:
        _ensure_path_entry(by_path, path)
    for path in FEATURE_ENGINE_TOOL_PATHS:
        _ensure_path_entry(by_path, path)
    for path in FEATURE_QUICKSLOT_PATHS:
        _ensure_path_entry(by_path, path)
    for path, title in TITLE_OVERRIDES.items():
        if path in by_path:
            by_path[path]["title"] = title

    root = by_path.pop("guide/index.html")
    root["depth"] = 0
    root["title"] = TITLE_OVERRIDES["guide/index.html"]

    buckets: dict[str, list[dict[str, Any]]] = {
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
        "guide/workspace-tools/index.html": [],
        "guide/features-engine-tools/index.html": [],
        "guide/quickslot/index.html": [],
        "guide/features/index.html": [],
    }
    for path, entry in list(by_path.items()):
        if path in NAV_ONLY_EXCLUDE_PATHS:
            continue
        if path in EXCLUDE_FROM_NAV_PATHS:
            continue
        if path in WORKSPACE_TOOL_LINK_ONLY_PATHS:
            continue
        if path in MERGED_SCREEN_PAGE_PATHS or path in SCREEN_AREA_LINK_ONLY_PATHS or path in SCREEN_AREA_NAV_CHILD_PATHS:
            continue
        if path == SETTINGS_PAGE_PATH:
            continue
        if path in GROUP_PAGES or path in ADVANCED_SUBGROUP_PAGES or path in FEATURE_SUBGROUP_PAGES or path in settings_reference_parent_paths:
            continue
        if path == "guide/quickslot/index.html":
            continue
        title = str(entry["title"])
        settings_parent = ""
        if title.lower().startswith("code:"):
            continue
        if path in SETTINGS_PAGE_CHILD_ORDER:
            group = "guide/features/index.html"
        elif path in WORKFLOW_PATHS:
            group = "guide/features/index.html"
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
                elif path in FEATURE_NESTED_CHILD_PATHS and path not in FEATURE_NESTED_PARENT_PATHS and path not in FEATURE_QUICKSLOT_PATHS:
                    continue
                elif path in FEATURE_SCREEN_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-screen/index.html"].append(entry)
                elif path in FEATURE_WORKSPACE_TOOL_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/workspace-tools/index.html"].append(entry)
                elif path in FEATURE_ENGINE_TOOL_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/features-engine-tools/index.html"].append(entry)
                elif path in FEATURE_QUICKSLOT_PATHS:
                    entry["depth"] = 3
                    feature_buckets["guide/quickslot/index.html"].append(entry)
                else:
                    feature_buckets["guide/features/index.html"].append(entry)
            else:
                buckets[group].append(entry)

    nav = [root]
    for group_path in GROUP_PAGES:
        group_entry = dict(by_path[group_path])
        group_entry["depth"] = 1
        nav.append(group_entry)
        if group_path == "guide/engine-guides/index.html":
            children = sorted(
                buckets[group_path],
                key=lambda item: (ENGINE_NAV_ORDER.get(str(item["path"]), 999999), _sort_key(item)),
            )
        else:
            children = sorted(buckets[group_path], key=_sort_key)
        if group_path == "guide/features/index.html":
            for subgroup_path in [
                "guide/features-screen/index.html",
                SETTINGS_PAGE_PATH,
                "guide/workspace-tools/index.html",
                "guide/quickslot/index.html",
            ]:
                subgroup_entry = dict(by_path[subgroup_path])
                subgroup_entry["depth"] = 2
                nav.append(subgroup_entry)
                if subgroup_path == SETTINGS_PAGE_PATH:
                    _append_settings_groups(nav, by_path, 2)
                    continue
                if subgroup_path == "guide/features-screen/index.html":
                    _append_screen_area_groups(nav, by_path, 2)
                    continue
                if subgroup_path == "guide/workspace-tools/index.html":
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
    code_block_style = (
        "pre,.code{color:#7ee787}"
        "pre code,.code code{padding:0;border-radius:0;background:transparent;color:inherit}"
    )
    basic_workflow_nav_style = (
        ".nav-single-group>summary{cursor:default;pointer-events:none}"
        ".nav-single-group>summary .nav-link{cursor:pointer;pointer-events:auto}"
        ".nav-caret.nav-caret-static:before{content:\"\" !important;display:block;width:3px;height:3px;border-radius:999px;background:var(--muted);opacity:.72}"
        ".nav-single-group[open]>summary .nav-caret-static{transform:none}"
        ".nav-basic-workflow-row:hover .nav-caret-static,.nav-basic-workflow-row:has(.nav-link[aria-current=\"page\"]) .nav-caret-static{color:var(--muted)}"
    )
    guide_callout_style = (
        ".guide-callout{--callout-color:#2563eb;--callout-bg:#eff6ff;--callout-border:#bfdbfe;--callout-title:#1d4ed8;--callout-text:#1e3a8a;--callout-shadow:rgba(30,58,138,.10);display:block;margin:18px 0;padding:16px 18px;border:1px solid var(--callout-border);border-radius:12px;background:var(--callout-bg);color:var(--callout-text);box-shadow:0 8px 24px var(--callout-shadow)}.guide-callout:before{content:none}.guide-callout-title{margin:0 0 6px;color:var(--callout-title);font-size:16px;font-weight:800;line-height:1.35}.guide-callout-body{min-width:0;color:var(--callout-text);font-size:14px;line-height:1.6}.guide-callout-body>:first-child{margi"
        "n-top:0}.guide-callout-body>:last-child{margin-bottom:0}.guide-callout[data-callout=\"abstract\"],.guide-callout[data-callout=\"summary\"],.guide-callout[data-callout=\"tldr\"],.guide-callout[data-callout=\"tip\"],.guide-callout[data-callout=\"hint\"],.guide-callout[data-callout=\"important\"]{--callout-color:#0891b2;--callout-bg:#ecfeff;--callout-border:#a5f3fc;--callout-title:#0e7490;--callout-text:#164e63;--callout-shadow:rgba(14,116,144,.10)}.guide-callout[data-callout=\"success\"],.guide-callout[data-callout=\"check\"],.guide-callout[data-callout=\"done\"]{--callout-color:#16a34a;--callout-bg:#f0fdf4;--callout-border:#bbf7d0;--callout-title:#15803d;--callout-text:#14532d;--callout-shadow:rgba(21,128,61,.10)}.guide-callout[data-callout=\"question\"],.guide-callout[data-callout=\"help\"],.guide-callout[data-callout=\"faq\"],.guide-callout[data-callout=\"warning\"],.guide-callout[data-callout=\"caution\"],.guide-"
        "callout[data-callout=\"attention\"]{--callout-color:#f59e0b;--callout-bg:#fffbeb;--callout-border:#fcd34d;--callout-title:#b45309;--callout-text:#78350f;--callout-shadow:rgba(120,53,15,.12)}.guide-callout[data-callout=\"failure\"],.guide-callout[data-callout=\"fail\"],.guide-callout[data-callout=\"missing\"],.guide-callout[data-callout=\"danger\"],.guide-callout[data-callout=\"error\"],.guide-callout[data-callout=\"bug\"]{--callout-color:#dc2626;--callout-bg:#fef2f2;--callout-border:#fecaca;--callout-title:#b91c1c;--callout-text:#7f1d1d;--callout-shadow:rgba(127,29,29,.12)}.guide-callout[data-callout=\"example\"]{--callout-color:#7c3aed;--callout-bg:#f5f3ff;--callout-border:#ddd6fe;--callout-title:#6d28d9;--callout-text:#4c1d95;--callout-shadow:rgba(76,29,149,.12)}.guide-callout[data-callout=\"quote\"],.guide-callout[data-callout=\"cite\"]{--callout-color:#64748b;--callout-bg:#f8fafc;--callout-border:#cbd5e"
        "1;--callout-title:#475569;--callout-text:#334155;--callout-shadow:rgba(51,65,85,.10)}:root[data-theme=\"dark\"] .guide-callout,body[data-theme=\"dark\"] .guide-callout{--callout-color:#60a5fa;--callout-bg:rgba(37,99,235,.16);--callout-border:rgba(96,165,250,.46);--callout-title:#bfdbfe;--callout-text:#dbeafe;--callout-shadow:rgba(0,0,0,.22)}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"abstract\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"summary\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"tldr\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"tip\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"hint\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"important\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"abstract\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"summary\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"tldr"
        "\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"tip\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"hint\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"important\"]{--callout-color:#22d3ee;--callout-bg:rgba(8,145,178,.16);--callout-border:rgba(103,232,249,.42);--callout-title:#a5f3fc;--callout-text:#cffafe}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"success\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"check\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"done\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"success\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"check\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"done\"]{--callout-color:#22c55e;--callout-bg:rgba(22,163,74,.16);--callout-border:rgba(134,239,172,.42);--callout-title:#bbf7d0;--callout-text:#dcfce7}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"qu"
        "estion\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"help\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"faq\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"warning\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"caution\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"attention\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"question\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"help\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"faq\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"warning\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"caution\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"attention\"]{--callout-color:#f59e0b;--callout-bg:rgba(245,158,11,.12);--callout-border:rgba(245,158,11,.55);--callout-title:#fbbf24;--callout-text:#fde68a}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"failu"
        "re\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"fail\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"missing\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"danger\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"error\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"bug\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"failure\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"fail\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"missing\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"danger\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"error\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"bug\"]{--callout-color:#ef4444;--callout-bg:rgba(220,38,38,.14);--callout-border:rgba(252,165,165,.44);--callout-title:#fca5a5;--callout-text:#fee2e2}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"example\"],body[data-"
        "theme=\"dark\"] .guide-callout[data-callout=\"example\"]{--callout-color:#a78bfa;--callout-bg:rgba(124,58,237,.16);--callout-border:rgba(196,181,253,.42);--callout-title:#ddd6fe;--callout-text:#ede9fe}:root[data-theme=\"dark\"] .guide-callout[data-callout=\"quote\"],:root[data-theme=\"dark\"] .guide-callout[data-callout=\"cite\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"quote\"],body[data-theme=\"dark\"] .guide-callout[data-callout=\"cite\"]{--callout-color:#94a3b8;--callout-bg:rgba(100,116,139,.16);--callout-border:rgba(203,213,225,.36);--callout-title:#e2e8f0;--callout-text:#cbd5e1}@media(prefers-color-scheme:dark){:root:not([data-theme=\"light\"]) .guide-callout{--callout-color:#60a5fa;--callout-bg:rgba(37,99,235,.16);--callout-border:rgba(96,165,250,.46);--callout-title:#bfdbfe;--callout-text:#dbeafe;--callout-shadow:rgba(0,0,0,.22)}:root:not([data-theme=\"light\"]) .guide-callout[data-callou"
        "t=\"abstract\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"summary\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"tldr\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"tip\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"hint\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"important\"]{--callout-color:#22d3ee;--callout-bg:rgba(8,145,178,.16);--callout-border:rgba(103,232,249,.42);--callout-title:#a5f3fc;--callout-text:#cffafe}:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"success\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"check\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"done\"]{--callout-color:#22c55e;--callout-bg:rgba(22,163,74,.16);--callout-border:rgba(134,239,172,.42);--callout-title:#bbf7d0;--callout-text:#dcfce7}:root:not([data-theme=\"light\"]) .guide-callou"
        "t[data-callout=\"question\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"help\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"faq\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"warning\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"caution\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"attention\"]{--callout-color:#f59e0b;--callout-bg:rgba(245,158,11,.12);--callout-border:rgba(245,158,11,.55);--callout-title:#fbbf24;--callout-text:#fde68a}:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"failure\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"fail\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"missing\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"danger\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"error\"],:root:not([data-theme=\"light\"])"
        " .guide-callout[data-callout=\"bug\"]{--callout-color:#ef4444;--callout-bg:rgba(220,38,38,.14);--callout-border:rgba(252,165,165,.44);--callout-title:#fca5a5;--callout-text:#fee2e2}:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"example\"]{--callout-color:#a78bfa;--callout-bg:rgba(124,58,237,.16);--callout-border:rgba(196,181,253,.42);--callout-title:#ddd6fe;--callout-text:#ede9fe}:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"quote\"],:root:not([data-theme=\"light\"]) .guide-callout[data-callout=\"cite\"]{--callout-color:#94a3b8;--callout-bg:rgba(100,116,139,.16);--callout-border:rgba(203,213,225,.36);--callout-title:#e2e8f0;--callout-text:#cbd5e1}}"
    )
    replacements = {
        "blockquote{margin:20px 0;padding:12px 18px;border-left:4px solid var(--accent);background:var(--soft);border-radius:12px}": "blockquote{margin:20px 0;padding:0 0 0 14px;border-left:3px solid var(--accent);background:transparent;border-radius:0}",
        ".callout{border-radius:12px;padding:1rem;background:var(--soft)}": ".callout{border-radius:0;padding:0;background:transparent}",
        ".bookmark{display:flex;width:100%;align-items:stretch;border:1px solid var(--line);border-radius:12px;overflow:hidden;text-decoration:none}": ".bookmark{display:flex;width:100%;align-items:stretch;border:0;border-radius:0;overflow:visible;text-decoration:none}",
        ".bookmark-info{padding:12px 14px}": ".bookmark-info{padding:0}",
        ".selected-value{display:inline-block;padding:0 .5em;background:var(--soft);border-radius:3px;margin:.3em .5em .3em 0}": ".selected-value{display:inline;font-weight:700;background:transparent;border-radius:0;margin:0 .25em 0 0}",
        '.nav-list>.nav-link[href$="guide/basic-workflow/index.html"]{position:relative;padding-left:33px}.nav-list>.nav-link[href$="guide/basic-workflow/index.html"]:before{content:"";position:absolute;left:11px;top:50%;width:5px;height:5px;margin-top:-2.5px;border-radius:999px;background:var(--muted);opacity:.75}.nav-list>.nav-link[href$="guide/basic-workflow/index.html"]:hover:before,.nav-list>.nav-link[href$="guide/basic-workflow/index.html"][aria-current="page"]:before{background:var(--accent);opacity:1}': "",
        '.nav-list .nav-link[href$="guide/basic-workflow/index.html"]{position:relative;padding-left:33px}.nav-list .nav-link[href$="guide/basic-workflow/index.html"]:before{content:"";position:absolute;left:11px;top:50%;width:5px;height:5px;margin-top:-2.5px;border-radius:999px;background:var(--muted);opacity:.75}.nav-list .nav-link[href$="guide/basic-workflow/index.html"]:hover:before,.nav-list .nav-link[href$="guide/basic-workflow/index.html"][aria-current="page"]:before{background:var(--accent);opacity:1}': "",
        '.nav-workflow-link{display:flex;align-items:center;gap:10px;padding-left:11px}.nav-workflow-link .nav-dot{width:7px;height:7px;flex:0 0 7px;border-radius:999px;background:var(--muted);opacity:.78}.nav-workflow-link:hover .nav-dot,.nav-workflow-link[aria-current="page"] .nav-dot{background:var(--accent);opacity:1}': "",
        '.nav-single{display:grid;grid-template-columns:24px minmax(0,1fr);align-items:center;margin:2px 0;border-radius:10px}.nav-single .nav-link{margin:0;min-width:0;overflow:hidden;text-overflow:ellipsis}.nav-caret-static:before{content:"•";font-size:18px;line-height:1}.nav-basic-workflow-row:hover .nav-caret-static,.nav-basic-workflow-row:has(.nav-link[aria-current="page"]) .nav-caret-static{color:var(--accent)}': "",
        '.nav-single-group>summary{cursor:default}.nav-single-group>summary .nav-link{cursor:pointer}.nav-caret-static:before{content:"•";font-size:18px;line-height:1}.nav-single-group[open]>summary .nav-caret-static{transform:none}.nav-basic-workflow-row:hover .nav-caret-static,.nav-basic-workflow-row:has(.nav-link[aria-current="page"]) .nav-caret-static{color:var(--accent)}': "",
        '.nav-single-group>summary{cursor:default;pointer-events:none}.nav-single-group>summary .nav-link{cursor:pointer;pointer-events:auto}.nav-caret-static:before{content:"";display:block;width:5px;height:5px;border-radius:999px;background:currentColor}.nav-single-group[open]>summary .nav-caret-static{transform:none}.nav-basic-workflow-row:hover .nav-caret-static,.nav-basic-workflow-row:has(.nav-link[aria-current="page"]) .nav-caret-static{color:var(--accent)}': "",
        '.nav-single-group>summary{cursor:default;pointer-events:none}.nav-single-group>summary .nav-link{cursor:pointer;pointer-events:auto}.nav-caret.nav-caret-static:before{content:"" !important;display:block;width:5px;height:5px;border-radius:999px;background:currentColor}.nav-single-group[open]>summary .nav-caret-static{transform:none}.nav-basic-workflow-row:hover .nav-caret-static,.nav-basic-workflow-row:has(.nav-link[aria-current="page"]) .nav-caret-static{color:var(--accent)}': "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if code_block_style not in text:
        text = text.rstrip() + "\n" + code_block_style + "\n"
    if basic_workflow_nav_style not in text:
        text = text.rstrip() + "\n" + basic_workflow_nav_style + "\n"
    if guide_callout_style not in text:
        text = text.rstrip() + "\n" + guide_callout_style + "\n"
    edit_guide.write_text(css_path, text)


def main() -> int:
    _ensure_group_pages()
    _remove_deleted_pages()
    entries = edit_guide.get_nav_entries(DIST_ROOT)
    group_articles = _build_group_articles()
    reviewed_articles = {
        "guide/api-key-settings/index.html": _api_key_article(),
        "guide/cache-management/index.html": _cache_management_article(),
        "guide/provider-reference-links/index.html": group_articles["guide/provider-reference-links/index.html"],
        "guide/wolf-rpg-editor/index.html": _wolf_rpg_editor_article(),
        "guide/wolf-unpack-repack/index.html": _wolf_archive_article(),
    }
    all_paths = {entry["path"] for entry in edit_guide.list_files(DIST_ROOT, include_unlisted=True) if not entry.get("virtual")}

    for path in sorted(all_paths):
        html_path = DIST_ROOT / path
        if not html_path.exists():
            continue
        text = edit_guide.read_text(html_path)
        try:
            original_article, title_source_text, uses_current_article = _article_from_current_or_git(path, text)
        except ValueError:
            continue
        title = TITLE_OVERRIDES.get(path, edit_guide.parse_title(title_source_text, html_path.parent.name))
        article = reviewed_articles.get(path)
        if article is None:
            article = original_article if uses_current_article else group_articles.get(path) or _render_article(path, title, original_article)
        if path in REVIEWED_VERSION_ONLY_PATHS:
            article = _replace_doc_version(article)
        updated = _replace_article_safe(text, article)
        updated = re.sub(r"(?is)<title>.*?</title>", f"<title>{_escape(title)} · AIMT Guide</title>", updated, count=1)
        edit_guide.write_text(html_path, updated)

    new_entries = _make_nav(edit_guide.get_nav_entries(DIST_ROOT))
    changed = edit_guide.rewrite_navs(DIST_ROOT, new_entries)
    _flatten_nested_card_styles()
    edit_guide.rebuild_search_index(DIST_ROOT)
    page_count = len([entry for entry in edit_guide.list_files(DIST_ROOT) if not entry.get("virtual")])
    print(f"Renewed guide articles and navigation. nav_rewritten={changed}, pages={page_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
