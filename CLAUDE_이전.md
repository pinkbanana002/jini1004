# 쿠팡 로켓배송 자동화 웹앱

원본 Jupyter Notebook(`로켓배송_자동화_상세대량_수강생전용_260330.ipynb`, 19셀)을 로컬 단일 사용자용 웹앱으로 재구축.

## 진행 상황

- [x] 1순위: 프로젝트 초기 설정 / 환경 구성
- [x] 2순위: UI 기본 골격 (FastAPI + 순수 HTML/JS + WebSocket)
- [x] 3순위: 1단계 기능 (Cell 0 ~ Cell 6) — 완료 및 실사용 테스트 성공
- [ ] 4순위: 2단계 기능 (Cell 6-1 ~ Cell 10)
- [ ] 5순위 이후: 미정

## 기술 스택

- 백엔드: FastAPI (Python)
- 프론트: 순수 HTML + Vanilla JS (React/빌드툴/번들러 없음)
- 실시간 로그: WebSocket
- Selenium + gspread + Gemini API

## 폴더 구조

```
webapp/
  server.py              # FastAPI 엔트리
  modules/stage1.py      # 1단계 통합 실행 (Cell 0~6 이식)
  modules/stage2.py      # [예정] 2단계 통합 실행
  static/                # index.html, app.js, style.css
  logs/                  # 일자별 실행 로그
templates/, fonts/       # 상세페이지 제작 리소스
chrome_profile/          # 크롬 프로파일 고정
temp_downloads/          # 크롬 기본 다운로드 폴더
완료된_상품/              # 상품별 결과물 (대표이미지/상세페이지/추가이미지)
시작.bat                  # 좀비 프로세스 정리 → 서버 기동
로켓배송_자동화_..ipynb    # 원본 Notebook (수정 금지, 복사 원천)
```

## 중요 규칙

- **원본 Notebook 로직은 한 글자도 바꾸지 말고 복사.** 버그가 나도 먼저 원본과 문자 단위로 대조할 것. 최적화·리팩토링 금지.
- **파일 수정 후 서버 재시작 필요** (FastAPI는 리로드 비활성). `시작.bat` 재실행.
- `시작.bat`에 **좀비 프로세스 자동 종료 로직 있음** — 재시작 시 포트 충돌 걱정 없음.
- **1단계 화면 UI는 완성됨. 건드리지 말 것.** 2단계 작업 시 기존 DOM·상태·흐름 유지.
- 체크리스트: ① 썸네일 수정 ② 상세페이지 수정 ③ 구글시트 확인 (3개 전부 체크 시 2단계 이동 활성화).

## 다음 작업 (4순위: 2단계 기능)

**범위**: 원본 Cell 6-1 ~ Cell 10
**제외**: Cell 11 (추가등록 메뉴는 별도 순위에서 처리)

**기능 순서**:
1. 이미지 리사이징
2. 상세페이지 제작
3. 쿠팡 다운로드
4. 견적서 작성
5. 쿠팡 상품 등록
6. 이관

**이식 원칙**: stage1.py와 동일한 패턴 — `modules/stage2.py`에 `run_stage2(config, log, progress, should_stop)` 함수로 구성. 원본 셀 경계·변수명·print 문구 그대로 유지. `input()` 등 인터랙티브 블로킹만 제거하고 UI 콜백으로 대체.

## 이미 발견된 주의점

- Selenium `img.size['width']`는 렌더 너비 — 웹앱 컨테이너에서는 축소됨. 분류 기준은 `naturalWidth` 사용. (stage1.py `classify_images` 참고)
- alicdn 이미지 중 일부는 lazy load — `src` 대신 `data-src`에 실제 URL. 둘 다 체크.
- 페이지 하단 레이지 로딩: `classify_images` 호출 전 `scrollTo(0, scrollHeight)` 루프로 강제 렌더 필요.
