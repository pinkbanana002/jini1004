# 쿠팡 로켓배송 자동화 웹앱

원본 Jupyter Notebook(`로켓배송_자동화_상세대량_수강생전용_260330.ipynb`, 19셀)을 로컬 단일 사용자용 웹앱으로 재구축.

## 진행 상황

- [x] 1순위: 프로젝트 초기 설정 / 환경 구성
- [x] 2순위: UI 기본 골격 (FastAPI + 순수 HTML/JS + WebSocket)
- [x] 3순위: 1단계 기능 (Cell 0 ~ Cell 6) — 실사용 테스트 성공
- [x] 4순위: 2단계 기능 (Cell 6-1 ~ Cell 10) — **실 사용 E2E 검증 완료 (1건 등록 성공)**
- [x] 4.5순위: UX 보강 (초기화 버튼 · 기본 진입 화면 · 체크리스트 중복 방지 · 2단계 락 해제)
- [x] 4.6순위 (2026-05-12): 2단계 견적서 팝업 통일 + 쿠팡 봇 감지 Plan A + 1단계 속도 개선
- [x] 4.7순위 (2026-05-14): 1단계 옵션 그룹 분리 (색상 × 사이즈 카르테시안) + 시트 와이프 방지 3중 보호망
- [ ] 5순위 이후: (보류) 좌측 메뉴 순서 변경 / (경미) PowerShell 이모지 cp949 디코딩 / (경미) google.generativeai deprecation 마이그레이션 / (정리) FORCE-DEBUG / DEBUG-PRICE / DEBUG-DIAG 진단 로그 누적

## 실 사용 검증 완료 (2026-04-19)

체크포인트 스냅샷: `webapp/_backups/stable_20260419/`

- **1단계 → 체크리스트 → 2단계 → Cell 10까지 엔드투엔드 성공**
- 쿠팡 상품 **1건 자동등록 성공** (DAILY_LIMIT 50 중 1건, 실계정)
- `🔄 새로 시작` 버튼으로 다음 상품 등록 준비 가능 (시트·로그·진행바·체크리스트 모두 리셋)

## 기술 스택

- 백엔드: FastAPI (Python)
- 프론트: 순수 HTML + Vanilla JS (React/빌드툴/번들러 없음)
- 실시간 로그: WebSocket
- Selenium + gspread + Gemini API

## 폴더 구조

```
webapp/
  server.py                     # FastAPI 엔트리
  modules/
    stage1.py                   # 1단계 통합 실행 (Cell 0~6 이식)
    stage2.py                   # 2단계 오케스트레이터 (exec 기반)
    stage2_cells/               # 원본 Cell 6-1~10 verbatim 보관 (exec 대상)
  static/                       # index.html, app.js, style.css
  logs/                         # 일자별 실행 로그
  _backups/                     # 백업·체크포인트 (stable_20260419 포함, 런타임 미사용)
templates/, fonts/              # 상세페이지 제작 리소스
chrome_profile/                 # 쿠팡 로그인 세션 유지용 크롬 프로파일
temp_downloads/                 # 크롬 기본 다운로드 폴더
완료된_상품/                     # 상품별 결과물 (대표이미지/상세페이지/추가이미지)
시작.bat                         # 좀비 프로세스 정리 → 서버 기동
로켓배송_자동화_..ipynb           # 원본 Notebook (수정 금지, 복사 원천)
```

## 주요 변경 이력 (시간 순)

| # | 대상 파일 | 위치 | 변경 이유 |
|---|-----------|------|-----------|
| ① | `webapp/modules/stage2.py` | `run_stage2` 셀 루프 내 Cell 8 직전 훅 | 전체 `taskkill /F /IM chrome.exe` 대신 PowerShell `Get-CimInstance` 로 PATH_PROFILE 쓰는 크롬만 정확히 종료 (개인 크롬 보호) |
| ② | `webapp/modules/stage2_cells/03_cell_7.py` | `close_all_explorer_windows()` | `Shell.Application.Windows()` 에 `explorer.exe` 필터 추가 — IE/Edge/기타 윈도우 오폭 종료 방지 |
| ③ | `webapp/.env` | 전체 | 실사용 필수값 입력 (MY_BRAND_NAME · MY_COMPANY_NAME · MY_PHONE_NUMBER · GEMINI_API_KEY) |
| ④ | `webapp/modules/stage1.py` | Cell 6 `analyze_seo_only` 프롬프트 본문 | 쿠팡 SEO 최적화 — 짧은 명사형 25~40자, 구두점·조사·서술형·색상·수량·사이즈·유아 키워드 금지 |
| ⑤ | `webapp/modules/stage1.py` | `analyze_seo_only` 응답 파싱부 | 코드펜스(` ```json `) 자동 제거, JSON 파싱 실패 시 raw 앞200자 로그, tags 리스트→쉼표문자열, name 구두점 정리 |
| ⑥ | `webapp/modules/stage2_cells/08_cell_9_1.py` | 법적서류 N/A 체크 블록 | 페이지 내 모든 "N/A" 라벨을 스크롤하며 순회 클릭 — DOM 위치 변동 / 동적 렌더 대응 |
| ⑦ | `webapp/modules/stage2.py` | `_ui_input` 로그인 대기 루프 | deadline 300초 → 60초 단축 (실사용 시 1분 내 수동 로그인 가능) |
| ⑧ | `webapp/server.py` + `webapp/static/app.js` | `/api/reset` 엔드포인트 · `resetWorkspace()` · 부트 시 1단계 기본 진입 · `checklistDismissed` 플래그 | 체크리스트 팝업 중복 방지 + 새 상품 등록용 초기화 버튼 + 환영화면 스킵 |
| ⑨ | `webapp/static/app.js` | `renderStage2` 툴바 + `updateStage2UI` + `resetWorkspace` 공통화 | 2단계 화면에도 동일한 🔄 새로 시작 버튼 추가, 1·2단계가 같은 초기화 핸들러 공유 |
| ⑩ | `webapp/static/app.js` + `webapp/server.py` | `updateMenuLocks` · `renderStage2` · `/api/stage2/start` | 2단계 락 해제 — 1단계 체크리스트 없이도 바로 2단계 진입 가능 (설정·credentials만 갖춰지면) |
| ⑪ | `webapp/server.py` + `webapp/modules/stage2.py` + `webapp/static/app.js` | `gate_signal` payload · `showQuoteGateModal` | 2단계 견적서 팝업을 카테고리 추가등록 팝업과 동일한 UI 로 통일 — 상품명/파일명/[폴더 열기]/[엑셀로 열기] 카드 + `pending_gate_payload` 재연결 복원 |
| ⑫ | `webapp/modules/stage2_cells/06_cell_8.py` | `launch_robot_chrome` cmd 플래그 + attach 직후 CDP | 쿠팡 봇 감지 (Access Denied) Plan A — `--disable-blink-features=AutomationControlled` + `Page.addScriptToEvaluateOnNewDocument` 로 `navigator.webdriver` 등 위장 |
| ⑬ | `webapp/modules/stage1.py` | Cell 4-1 sleep 5곳 (261/295 죽은코드/330·336 죽은코드/782/834) | 1단계 속도 개선 — sleep 랜덤화로 평균 단축 + 인간 패턴. `collect_opts_from_dropdown` 죽은 함수 정리 |
| ⑭ | `webapp/modules/stage1.py` | Cell 5 `worksheet.clear()` 직전 + Cell 6 `backup_sheet.clear()` 직전 + `batch_update` 직전 | 시트 와이프 방지 3중 보호망 — 메인 탭 이름 검증 / 백업 탭 이름 검증 / batch_update range 형식 검증 |
| ⑮ | `webapp/modules/stage1.py` | `get_all_options` 안 + 라인 805 받는 쪽 | **옵션 그룹 분리** (색상 × 사이즈 카르테시안 곱) — 박스 부모 클래스(`flex-wrap`/`flex-col`)로 그룹 메타 (`'group'` 필드) 부여, 받는 쪽에서 메타 기반 분리. 1차원 list + 단일 키 `'옵션'` 유지로 기존 호환 |

## 중요 규칙

- **원본 Notebook 로직은 한 글자도 바꾸지 말고 복사.** 버그가 나도 먼저 원본과 문자 단위로 대조할 것. 최적화·리팩토링 금지. `stage2_cells/*.py` 는 원본 셀 그대로 보관된 exec 대상이므로 특별히 주의.
- **파일 수정 후 서버 재시작 필요** (FastAPI reload 비활성). `시작.bat` 재실행.
- `시작.bat`에 **좀비 프로세스 자동 종료 로직 있음** — 재시작 시 포트 충돌 걱정 없음.
- **1단계 화면 UI는 완성됨. 건드리지 말 것.** 기존 DOM·상태·흐름 유지.
- 체크리스트: ① 썸네일 수정 ② 상세페이지 수정 ③ 구글시트 확인.
- 2단계 Cell 8 직전 훅은 PATH_PROFILE 프로필을 쓰는 크롬만 선택적으로 종료 — 개인 크롬 세션은 건드리지 않음.
- 견적서 확인 게이트: Cell 9 완료 후 자동 대기, 사용자가 확인 체크 후 수동 승인 필요.
- 모든 백업은 `webapp/_backups/` 한 곳에 모음. 루트 / modules / static 여기저기 `*_backup_*` 파일 만들지 말 것.

## 다음 작업

- **(보류) 좌측 메뉴 순서 변경** — 현재 [1단계][2단계][추가 등록][설정]. UX 의견 수렴 후 재배치.
- **(경미) UnicodeDecodeError** — PowerShell 이모지가 cp949 디코딩에서 실패. 메인 흐름엔 영향 없음, 로그만 간헐적으로 깨짐.
- **(경미) google.generativeai deprecation** — 향후 `google-genai` 패키지로 마이그레이션 필요. 현재는 경고만 뜨고 정상 동작.

## 이미 발견된 주의점

- Selenium `img.size['width']`는 렌더 너비 — 웹앱 컨테이너에서는 축소됨. 분류 기준은 `naturalWidth` 사용. (`stage1.py classify_images`)
- alicdn 이미지 중 일부는 lazy load — `src` 대신 `data-src`에 실제 URL. 둘 다 체크.
- 페이지 하단 레이지 로딩: `classify_images` 호출 전 `scrollTo(0, scrollHeight)` 루프로 강제 렌더 필요.
- Gemini 응답이 마크다운 코드펜스(` ```json `)로 감싸 오는 경우 있음 — 파서가 자동 제거.
- 쿠팡 첫 접속 시 PATH_PROFILE이 비어 있으면 수동 로그인 1회 필요, 이후에는 세션 유지됨.
