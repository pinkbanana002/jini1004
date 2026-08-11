// 3순위: 1단계 실행 + WebSocket 실시간 로그 + 체크리스트.

// ====================== Toast (alert 대체, 우측 하단 floating) ======================
function showToast(msg, level = "info", duration = 4500) {
    let box = document.getElementById("toast-container");
    if (!box) {
        box = document.createElement("div");
        box.id = "toast-container";
        box.className = "toast-container";
        document.body.appendChild(box);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${level}`;
    toast.textContent = String(msg);
    toast.onclick = () => { try { toast.remove(); } catch {} };
    box.appendChild(toast);
    setTimeout(() => { try { toast.remove(); } catch {} }, duration);
}

const panelContent = document.getElementById("panel-content");
const menuItems = document.querySelectorAll(".menu-item");
const menuByKey = {};
menuItems.forEach((b) => (menuByKey[b.dataset.menu] = b));

const state = {
    running: false,
    stage2Running: false,
    categoryRunning: false,
    catSelectedProducts: [],
    catFavorites: [],
    catSelectedCategory: null,  // {path, category_id, keyword, label, fromFavorite:bool}
    catCandidates: [],
    catSearchOpen: false,
    stage1CompletedChecklist: false,
    checklistDismissed: false,  // 세션 내에서 체크리스트 모달을 한 번 닫았는지
    ws: null,
    ws2: null,
    wsCat: null,
    currentPanel: null,
};

const panels = {
    settings: renderSettings,
    stage1: renderStage1,
    stage2: renderStage2,
    category: renderCategory,
};

menuItems.forEach((btn) => {
    btn.addEventListener("click", () => {
        if (btn.disabled) return;
        const key = btn.dataset.menu;
        if (state.running && key !== "stage1") {
            showToast("1단계 실행 중에는 다른 메뉴로 이동할 수 없습니다.", "warn");
            return;
        }
        if (state.stage2Running && key !== "stage2") {
            showToast("2단계 실행 중에는 다른 메뉴로 이동할 수 없습니다.", "warn");
            return;
        }
        if (state.categoryRunning && key !== "category") {
            showToast("카테고리 추가 등록 실행 중에는 다른 메뉴로 이동할 수 없습니다.", "warn");
            return;
        }
        menuItems.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.currentPanel = key;
        const fn = panels[key];
        if (fn) fn();
    });
});

function esc(v) {
    if (v == null) return "";
    return String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;")
        .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderPlaceholder(title, desc, priority) {
    panelContent.innerHTML = `
        <div class="panel-section">
            <h2>${esc(title)}</h2>
            <p class="section-desc">${esc(desc)}</p>
            <div class="placeholder-box">
                여기에 실제 기능이 들어갑니다.<br>
                <small>(${priority}순위에서 구현 예정)</small>
            </div>
        </div>`;
}

function updateMenuLocks() {
    // Stage 2: 락 해제 — 1단계 체크리스트와 무관하게 접근 가능.
    // 단, 1단계 자동화가 실행 중일 때만 비활성.
    menuByKey.stage2.disabled = state.running;
    const lock = menuByKey.stage2.querySelector(".menu-lock");
    if (lock) lock.style.display = "none";
    // Stage 1 실행 중이면 settings / category / stage2 잠금
    // Stage 2 실행 중이면 settings / category / stage1 잠금
    // Category 실행 중이면 나머지 모두 잠금
    const anyRunning = state.running || state.stage2Running || state.categoryRunning;
    menuByKey.settings.classList.toggle("locked", anyRunning);
    if (menuByKey.category) menuByKey.category.classList.toggle("locked", anyRunning);
    if (state.stage2Running || state.categoryRunning) {
        menuByKey.stage1.classList.add("locked");
        menuByKey.stage1.disabled = true;
    } else {
        menuByKey.stage1.classList.remove("locked");
        menuByKey.stage1.disabled = false;
    }
    if (state.categoryRunning) {
        menuByKey.stage2.classList.add("locked");
        menuByKey.stage2.disabled = true;
    }
}

// ====================== 설정 메뉴 ======================

async function renderSettings() {
    panelContent.innerHTML = `<div class="panel-section"><div class="loading">불러오는 중...</div></div>`;
    let data;
    try {
        const res = await fetch("/api/settings");
        data = await res.json();
    } catch (e) {
        panelContent.innerHTML = `<div class="panel-section"><div class="error-box">설정을 불러올 수 없습니다.</div></div>`;
        return;
    }
    const warning = data.is_configured ? "" : `
        <div class="warning-box">⚠️ 설정 먼저 완료해주세요. 아래 필수 정보를 모두 입력 후 저장하세요.</div>`;
    const pwPh = "••••••• (저장됨, 바꾸려면 새 값 입력)";

    panelContent.innerHTML = `
        <div class="panel-section">
            <h2>⚙️ 설정</h2>
            <p class="section-desc">로컬 전용입니다. 입력값은 <code>webapp/.env</code> 에만 저장됩니다.</p>
            ${warning}
            <form id="settings-form" class="settings-form">
                <section class="form-section">
                    <h3>📄 구글 시트</h3>
                    <div class="field">
                        <label>credentials.json 파일</label>
                        <div class="file-upload-area ${data.has_credentials ? 'uploaded' : ''}" id="credentials-drop">
                            <input type="file" id="credentials-input" accept=".json" hidden>
                            ${data.has_credentials
                                ? `<div class="file-status">✅ 현재 파일: credentials.json
                                    <button type="button" class="btn-small" id="change-credentials">변경</button></div>`
                                : `<div class="file-prompt">파일을 여기로 끌어놓거나
                                    <button type="button" class="btn-small" id="select-credentials">파일 선택</button></div>`}
                        </div>
                    </div>
                    <div class="field"><label>구글 시트 URL <span class="req">*</span></label>
                        <input type="text" name="google_sheet_url" value="${esc(data.google_sheet_url)}" placeholder="https://docs.google.com/spreadsheets/d/..."></div>
                    <div class="field"><label>시트 탭 이름</label>
                        <input type="text" name="target_sheet_name" value="${esc(data.target_sheet_name)}" placeholder="상품등록목록"></div>
                </section>
                <section class="form-section">
                    <h3>🔑 API / 쿠팡 계정</h3>
                    <div class="field"><label>Gemini API Key <span class="req">*</span></label>
                        <input type="password" name="gemini_api_key" autocomplete="off" placeholder="${data.has_gemini_api_key ? pwPh : 'AIzaSy...'}"></div>
                    <div class="field"><label>쿠팡 Supply ID <span class="req">*</span></label>
                        <input type="text" name="supply_id" value="${esc(data.supply_id)}" autocomplete="off"></div>
                    <div class="field"><label>쿠팡 Supply PW <span class="req">*</span></label>
                        <input type="password" name="supply_pw" autocomplete="off" placeholder="${data.has_supply_pw ? pwPh : ''}"></div>
                </section>
                <section class="form-section">
                    <h3>🏢 브랜드 정보</h3>
                    <div class="field"><label>브랜드명</label>
                        <input type="text" name="my_brand_name" value="${esc(data.my_brand_name)}" placeholder="몰투데이"></div>
                    <div class="field"><label>업체명</label>
                        <input type="text" name="my_company_name" value="${esc(data.my_company_name)}" placeholder="분홍바나나"></div>
                    <div class="field"><label>CS 전화번호</label>
                        <input type="text" name="my_phone_number" value="${esc(data.my_phone_number)}" placeholder="1577-7011"></div>
                </section>
                <section class="form-section collapsible">
                    <h3 class="collapsible-header" id="price-toggle"><span class="collapse-arrow">▸</span> 💰 가격 수식 (고급 설정)</h3>
                    <div class="collapsible-body" id="price-body">
                        <div class="field"><label>1688 단가 배수</label>
                            <input type="number" step="1" name="exchange_factor" value="${esc(data.exchange_factor)}"><small>기본 350</small></div>
                        <div class="field"><label>추가 물류비 (원)</label>
                            <input type="number" step="1" name="add_logistics_cost" value="${esc(data.add_logistics_cost)}"><small>기본 4000</small></div>
                        <div class="field"><label>판매가 배수</label>
                            <input type="number" step="0.01" name="sale_price_rate" value="${esc(data.sale_price_rate)}"><small>기본 1.67</small></div>
                        <div class="field"><label>권장가 배수</label>
                            <input type="number" step="0.01" name="rec_price_rate" value="${esc(data.rec_price_rate)}"><small>기본 1.30</small></div>
                        <div class="field"><label>반올림 단위</label>
                            <input type="number" step="1" name="round_unit" value="${esc(data.round_unit)}"><small>-2 = 100원 단위</small></div>
                    </div>
                </section>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">💾 저장</button>
                    <span id="save-status" class="save-status"></span>
                </div>
            </form>
        </div>`;
    bindSettingsHandlers();
}

function bindSettingsHandlers() {
    const toggle = document.getElementById("price-toggle");
    const body = document.getElementById("price-body");
    const arrow = toggle.querySelector(".collapse-arrow");
    body.style.display = "none";
    toggle.addEventListener("click", () => {
        const open = body.style.display !== "none";
        body.style.display = open ? "none" : "block";
        arrow.textContent = open ? "▸" : "▾";
    });
    const drop = document.getElementById("credentials-drop");
    const input = document.getElementById("credentials-input");
    const selectBtn = document.getElementById("select-credentials");
    const changeBtn = document.getElementById("change-credentials");
    if (selectBtn) selectBtn.addEventListener("click", () => input.click());
    if (changeBtn) changeBtn.addEventListener("click", () => input.click());
    input.addEventListener("change", (e) => {
        if (e.target.files[0]) uploadCredentials(e.target.files[0]);
    });
    drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("dragover"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop.addEventListener("drop", (e) => {
        e.preventDefault();
        drop.classList.remove("dragover");
        if (e.dataTransfer.files[0]) uploadCredentials(e.dataTransfer.files[0]);
    });
    document.getElementById("settings-form").addEventListener("submit", saveSettings);
}

async function uploadCredentials(file) {
    const fd = new FormData();
    fd.append("file", file);
    try {
        const res = await fetch("/api/credentials", { method: "POST", body: fd });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("업로드 실패: " + (err.detail || "알 수 없는 오류"), "error");
            return;
        }
        renderSettings();
    } catch (e) { showToast("업로드 실패: " + e.message, "error"); }
}

async function saveSettings(e) {
    e.preventDefault();
    const f = e.target;
    const payload = {};
    ["google_sheet_url","target_sheet_name","gemini_api_key","supply_id","supply_pw",
     "my_brand_name","my_company_name","my_phone_number",
     "exchange_factor","add_logistics_cost","sale_price_rate","rec_price_rate","round_unit"
    ].forEach((k) => payload[k] = f[k].value.trim());
    const status = document.getElementById("save-status");
    status.textContent = "저장 중...";
    status.className = "save-status";
    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await res.text());
        status.textContent = "✅ 저장 완료!";
        status.className = "save-status success";
        setTimeout(renderSettings, 800);
    } catch (err) {
        status.textContent = "❌ 저장 실패: " + err.message;
        status.className = "save-status error";
    }
}

// ====================== 1단계 메뉴 ======================

async function renderStage1() {
    panelContent.innerHTML = `
        <div class="panel-section">
            <h2>1단계 · 구글시트 작성</h2>
            <p class="section-desc">1688 크롤링 → 이미지 다운로드 → 시트 업로드 → AI SEO 분석 + 옵션 번역</p>

            <div class="stage-toolbar">
                <button id="btn-stage1-start" class="btn-start">▶️ 1단계 시작</button>
                <button id="btn-stage1-stop" class="btn-stop" style="display:none">⏹️ 중지</button>
                <button id="btn-stage1-reset" class="btn-secondary" title="체크리스트·로그·진행바 초기화">🔄 새로 시작</button>
                <div id="stage1-progress" class="progress-box">
                    <div class="progress-label" id="stage1-progress-label">대기 중</div>
                    <div class="progress-bar"><div class="progress-fill" id="stage1-progress-fill" style="width:0%"></div></div>
                </div>
            </div>

            <div class="log-console" id="stage1-log">
                <div class="log-line log-info">여기에 실시간 로그가 표시됩니다. [▶️ 1단계 시작] 버튼을 누르세요.</div>
            </div>
        </div>`;

    document.getElementById("btn-stage1-start").addEventListener("click", startStage1);
    document.getElementById("btn-stage1-stop").addEventListener("click", stopStage1);
    document.getElementById("btn-stage1-reset").addEventListener("click", resetWorkspace);
    // 실행 중이면 리셋 비활성
    document.getElementById("btn-stage1-reset").disabled = state.running || state.stage2Running;

    connectStage1WS();
    // status 1회 동기화
    try {
        const res = await fetch("/api/stage1/status");
        const s = await res.json();
        state.running = s.running;
        state.stage1CompletedChecklist = s.checklist_done;
        updateStage1UI(s.running);
        updateProgress(s.progress);
        updateMenuLocks();
    } catch {}
}

function connectStage1WS() {
    if (state.ws) { try { state.ws.close(); } catch {} }
    // 재연결 시 전체 replay 방지용 since 타임스탬프 전달
    const since = state.stage1LastEventTs || 0;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/stage1?since=${since}`);
    state.ws = ws;
    // retry 카운터 "즉시 리셋" 제거 — 최소 1개 메시지 수신 + 5초 안정 유지 시에만 리셋
    state.stage1MsgReceived = false;
    if (state.stage1ResetTimer) { clearTimeout(state.stage1ResetTimer); state.stage1ResetTimer = null; }
    ws.onopen = () => {
        state.stage1ResetTimer = setTimeout(() => {
            if (state.stage1MsgReceived && state.ws === ws && ws.readyState === WebSocket.OPEN) {
                state.stage1RetryCount = 0;
            }
        }, 5000);
    };
    ws.onmessage = (ev) => {
        state.stage1MsgReceived = true;
        const msg = JSON.parse(ev.data);
        if (msg.ts) state.stage1LastEventTs = msg.ts;  // 재연결 시 이 시점 이후만 요청
        if (msg.type === "log") appendLog(msg.msg, msg.level);
        else if (msg.type === "progress") updateProgress(msg);
        else if (msg.type === "done") handleDone(msg);
        else if (msg.type === "snapshot") {
            state.running = msg.running;
            updateStage1UI(msg.running);
            updateProgress(msg.progress);
            updateMenuLocks();
        }
    };
    ws.onclose = () => {
        if (state.stage1ResetTimer) { clearTimeout(state.stage1ResetTimer); state.stage1ResetTimer = null; }
        // 자동 재연결 (현재 패널이 stage1일 때) — 지수 백오프 + 최대 5회
        if (state.currentPanel !== "stage1") return;
        const n = (state.stage1RetryCount = (state.stage1RetryCount || 0) + 1);
        if (n > 5) {
            console.warn("[ws/stage1] 최대 재시도(5회) 초과 — 자동 재연결 중단");
            return;
        }
        const delay = 1500 * Math.pow(2, n - 1); // 1.5s → 3s → 6s → 12s → 24s
        setTimeout(connectStage1WS, delay);
    };
}

function appendLog(msg, level = "info") {
    const box = document.getElementById("stage1-log");
    if (!box) return;
    const line = document.createElement("div");
    line.className = `log-line log-${level}`;
    line.textContent = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function updateProgress(p) {
    const label = document.getElementById("stage1-progress-label");
    const fill = document.getElementById("stage1-progress-fill");
    if (!label || !fill) return;
    const step = p?.step || 0;
    const total = p?.total || 7;
    const pct = step ? Math.min(100, (step / total) * 100) : 0;
    fill.style.width = pct + "%";
    label.textContent = step ? `Cell ${step}/${total} · ${p.label || ""}` : "대기 중";
}

function updateStage1UI(isRunning) {
    const startBtn = document.getElementById("btn-stage1-start");
    const stopBtn = document.getElementById("btn-stage1-stop");
    const resetBtn = document.getElementById("btn-stage1-reset");
    if (!startBtn || !stopBtn) return;
    startBtn.disabled = isRunning;
    startBtn.style.display = isRunning ? "none" : "inline-block";
    stopBtn.style.display = isRunning ? "inline-block" : "none";
    if (resetBtn) resetBtn.disabled = isRunning || state.stage2Running;
}

async function startStage1() {
    try {
        const res = await fetch("/api/stage1/start", { method: "POST" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "시작 실패", "error");
            if ((err.detail || "").includes("설정")) {
                // 설정 메뉴로 자동 이동
                menuByKey.settings.click();
            }
            return;
        }
        // 로그 초기화
        const box = document.getElementById("stage1-log");
        if (box) box.innerHTML = "";
        state.running = true;
        // 새 실행 시작 → 체크리스트 dismiss 플래그 해제 (완료 후 팝업 다시 보여줌)
        state.checklistDismissed = false;
        updateStage1UI(true);
        updateMenuLocks();
    } catch (e) { showToast("시작 실패: " + e.message, "error"); }
}

// 1단계/2단계 공통 초기화 — 버튼 어디에서 눌러도 동일하게 작동.
async function resetWorkspace() {
    if (state.running || state.stage2Running) {
        showToast("실행 중에는 초기화할 수 없습니다.", "warn");
        return;
    }
    if (!confirm("작업 상태를 초기화하시겠습니까?\n(체크리스트·로그·진행바가 모두 리셋됩니다)")) return;
    try {
        const res = await fetch("/api/reset", { method: "POST" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("초기화 실패: " + (err.detail || res.statusText), "error");
            return;
        }
    } catch (e) {
        showToast("초기화 실패: " + e.message, "error");
        return;
    }
    // DOM 정리 (현재 렌더되어 있는 요소만 있으면 정리)
    document.getElementById("checklist-modal")?.remove();
    document.getElementById("quote-gate-modal")?.remove();
    const box1 = document.getElementById("stage1-log");
    if (box1) box1.innerHTML = `<div class="log-line log-info">초기화되었습니다. [▶️ 1단계 시작] 버튼을 눌러 새 작업을 시작하세요.</div>`;
    const box2 = document.getElementById("stage2-log");
    if (box2) box2.innerHTML = `<div class="log-line log-info">여기에 실시간 로그가 표시됩니다.</div>`;
    const fill1 = document.getElementById("stage1-progress-fill");
    if (fill1) fill1.style.width = "0%";
    const lbl1 = document.getElementById("stage1-progress-label");
    if (lbl1) lbl1.textContent = "대기 중";
    const fill2 = document.getElementById("stage2-progress-fill");
    if (fill2) fill2.style.width = "0%";
    const lbl2 = document.getElementById("stage2-progress-label");
    if (lbl2) lbl2.textContent = "대기 중";
    const counter = document.getElementById("stage2-counter");
    if (counter) counter.style.display = "none";
    // state 리셋
    state.stage1CompletedChecklist = false;
    state.checklistDismissed = false;
    updateMenuLocks();
}

// 뒤로 호환을 위해 남겨둠 (버튼 핸들러가 이 이름을 직접 바인딩한 경우 대비)
const resetStage1 = resetWorkspace;

async function stopStage1() {
    if (!confirm("1단계 실행을 중지하시겠습니까?")) return;
    try {
        await fetch("/api/stage1/stop", { method: "POST" });
    } catch (e) { showToast("중지 실패: " + e.message, "error"); }
}

function handleDone(msg) {
    // run_id 기반 dedup: WS 재연결로 동일 done 이벤트가 다시 오면 UI 처리 스킵.
    if (msg.run_id && state.lastHandledDoneId === msg.run_id) return;
    if (msg.run_id) state.lastHandledDoneId = msg.run_id;

    state.running = false;
    updateStage1UI(false);
    updateMenuLocks();
    if (msg.ok) {
        appendLog("🎉 1단계가 성공적으로 완료되었습니다!", "success");
        // WebSocket 재접속 시 이전 done 이벤트 재수신으로 팝업이 또 뜨는 버그 방지:
        // 한 세션 내에서 이미 닫은 적 있거나 체크리스트 완료 상태면 재표시 안 함.
        if (!state.checklistDismissed && !state.stage1CompletedChecklist) {
            showChecklistModal();
        }
    } else {
        appendLog(`❌ 실행 중단: ${msg.error || "알 수 없는 오류"}`, "error");
    }
}

// ====================== 체크리스트 모달 ======================

function showChecklistModal() {
    const existing = document.getElementById("checklist-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "checklist-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
        <div class="modal-box">
            <h2>✅ 1단계 완료!</h2>
            <p class="modal-desc">2단계로 넘어가기 전에 아래 3가지를 꼭 확인해주세요.</p>

            <label class="check-row">
                <input type="checkbox" class="check-item" id="check1">
                <span><strong>① 썸네일 수정</strong></span>
            </label>
            <label class="check-row">
                <input type="checkbox" class="check-item" id="check2">
                <span><strong>② 상세페이지 수정</strong></span>
            </label>
            <label class="check-row">
                <input type="checkbox" class="check-item" id="check3">
                <span><strong>③ 구글시트 확인</strong></span>
            </label>

            <div class="modal-actions">
                <button id="btn-checklist-later" class="btn-secondary">나중에 확인</button>
                <button id="btn-checklist-proceed" class="btn-primary" disabled>2단계로 이동 →</button>
            </div>
        </div>`;
    document.body.appendChild(modal);

    const boxes = modal.querySelectorAll(".check-item");
    const proceed = document.getElementById("btn-checklist-proceed");
    if ([...boxes].every((x) => x.checked)) { proceed.disabled=false; setTimeout(() => proceed.click(), 400); }
    boxes.forEach((b) => b.addEventListener("change", () => {
        const allChecked = [...boxes].every((x) => x.checked);
        proceed.disabled = !allChecked;
        // 3개 모두 체크되면 버튼 클릭 없이 자동으로 2단계로 진행
        if (allChecked) { setTimeout(() => proceed.click(), 400); }
    }));
    document.getElementById("btn-checklist-later").addEventListener("click", () => {
        state.checklistDismissed = true;
        modal.remove();
    });
    proceed.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/stage1/checklist", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ item1: true, item2: true, item3: true }),
            });
            if (!res.ok) throw new Error(await res.text());
            state.stage1CompletedChecklist = true;
            state.checklistDismissed = true;
            updateMenuLocks();
            modal.remove();
            // 자동으로 2단계 이동
            menuByKey.stage2.click();
        } catch (e) { showToast("체크리스트 저장 실패: " + e.message, "error"); }
    });
}

// ====================== 2단계 메뉴 ======================

async function renderStage2() {
    // 2단계 락 해제: 1단계 체크리스트 여부와 상관없이 진입 가능.
    panelContent.innerHTML = `
        <div class="panel-section">
            <h2>2단계 · 상품 등록</h2>
            <p class="section-desc">이미지 리사이징 → 상세페이지 제작 → 서플라이허브 다운로드 → 견적서 → 쿠팡 등록 → 이관</p>

            <div class="stage-toolbar">
                <button id="btn-stage2-start" class="btn-start">▶️ 2단계 시작</button>
                <button id="btn-stage2-stop" class="btn-stop" style="display:none">⏹️ 중지</button>
                <button id="btn-stage2-reset" class="btn-secondary" title="체크리스트·로그·진행바 초기화">🔄 새로 시작</button>
                <div id="stage2-progress" class="progress-box">
                    <div class="progress-label" id="stage2-progress-label">대기 중</div>
                    <div class="progress-bar"><div class="progress-fill" id="stage2-progress-fill" style="width:0%"></div></div>
                </div>
            </div>

            <div id="stage2-counter" class="stage2-counter" style="display:none">
                <span class="counter-label">📦 현재 등록</span>
                <span class="counter-value"><span id="stage2-counter-current">0</span> / <span id="stage2-counter-limit">50</span>개</span>
            </div>

            <div class="log-console" id="stage2-log">
                <div class="log-line log-info">여기에 실시간 로그가 표시됩니다. [▶️ 2단계 시작] 버튼을 누르세요.</div>
            </div>
        </div>`;

    document.getElementById("btn-stage2-start").addEventListener("click", startStage2);
    document.getElementById("btn-stage2-stop").addEventListener("click", stopStage2);
    document.getElementById("btn-stage2-reset").addEventListener("click", resetWorkspace);
    document.getElementById("btn-stage2-reset").disabled = state.running || state.stage2Running;

    connectStage2WS();
    try {
        const res = await fetch("/api/stage2/status");
        const s = await res.json();
        state.stage2Running = s.running;
        updateStage2UI(s.running);
        updateStage2Progress(s.progress);
        updateStage2Counter(s.counter, s.progress);
        updateMenuLocks();
    } catch {}
}

function connectStage2WS() {
    if (state.ws2) { try { state.ws2.close(); } catch {} }
    const since = state.stage2LastEventTs || 0;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/stage2?since=${since}`);
    state.ws2 = ws;
    state.stage2MsgReceived = false;
    if (state.stage2ResetTimer) { clearTimeout(state.stage2ResetTimer); state.stage2ResetTimer = null; }
    ws.onopen = () => {
        state.stage2ResetTimer = setTimeout(() => {
            if (state.stage2MsgReceived && state.ws2 === ws && ws.readyState === WebSocket.OPEN) {
                state.stage2RetryCount = 0;
            }
        }, 5000);
    };
    ws.onmessage = (ev) => {
        state.stage2MsgReceived = true;
        const msg = JSON.parse(ev.data);
        if (msg.ts) state.stage2LastEventTs = msg.ts;
        if (msg.type === "log") appendStage2Log(msg.msg, msg.level);
        else if (msg.type === "progress") updateStage2Progress(msg);
        else if (msg.type === "counter") updateStage2Counter({ current: msg.current, limit: msg.limit });
        else if (msg.type === "gate") handleStage2Gate(msg.name, msg.payload);
        else if (msg.type === "done") handleStage2Done(msg);
        else if (msg.type === "snapshot") {
            state.stage2Running = msg.running;
            updateStage2UI(msg.running);
            updateStage2Progress(msg.progress);
            updateStage2Counter(msg.counter, msg.progress);
            // 새로고침/재접속 시 대기 중인 게이트 복원
            if (msg.pending_gate && !document.getElementById("quote-gate-modal")) {
                handleStage2Gate(msg.pending_gate, msg.pending_gate_payload);
            }
            updateMenuLocks();
        }
    };
    ws.onclose = () => {
        if (state.stage2ResetTimer) { clearTimeout(state.stage2ResetTimer); state.stage2ResetTimer = null; }
        // 지수 백오프 + 최대 5회 (현재 패널이 stage2일 때)
        if (state.currentPanel !== "stage2") return;
        const n = (state.stage2RetryCount = (state.stage2RetryCount || 0) + 1);
        if (n > 5) {
            console.warn("[ws/stage2] 최대 재시도(5회) 초과 — 자동 재연결 중단");
            return;
        }
        const delay = 1500 * Math.pow(2, n - 1);
        setTimeout(connectStage2WS, delay);
    };
}

function appendStage2Log(msg, level = "info") {
    const box = document.getElementById("stage2-log");
    if (!box) return;
    const line = document.createElement("div");
    line.className = `log-line log-${level}`;
    line.textContent = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function updateStage2Progress(p) {
    const label = document.getElementById("stage2-progress-label");
    const fill = document.getElementById("stage2-progress-fill");
    if (!label || !fill) return;
    const step = p?.step || 0;
    const total = p?.total || 9;
    const pct = step ? Math.min(100, (step / total) * 100) : 0;
    fill.style.width = pct + "%";
    label.textContent = step ? `Cell ${step}/${total} · ${p.label || ""}` : "대기 중";
}

function updateStage2Counter(counter, progress) {
    const wrap = document.getElementById("stage2-counter");
    if (!wrap) return;
    // Cell 9-1 진행 중일 때만 노출
    const inRegistration = progress?.label?.includes("9-1") || progress?.label?.includes("쿠팡 상품 등록");
    if (inRegistration) {
        wrap.style.display = "flex";
    }
    if (!counter) return;
    const cur = document.getElementById("stage2-counter-current");
    const lim = document.getElementById("stage2-counter-limit");
    if (cur) cur.textContent = counter.current ?? 0;
    if (lim) lim.textContent = counter.limit ?? 50;
}

function updateStage2UI(isRunning) {
    const startBtn = document.getElementById("btn-stage2-start");
    const stopBtn = document.getElementById("btn-stage2-stop");
    const resetBtn = document.getElementById("btn-stage2-reset");
    if (!startBtn || !stopBtn) return;
    startBtn.disabled = isRunning;
    startBtn.style.display = isRunning ? "none" : "inline-block";
    stopBtn.style.display = isRunning ? "inline-block" : "none";
    if (resetBtn) resetBtn.disabled = isRunning || state.running;
}

async function startStage2() {
    try {
        const res = await fetch("/api/stage2/start", { method: "POST" });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(err.detail || "시작 실패", "error");
            return;
        }
        const box = document.getElementById("stage2-log");
        if (box) box.innerHTML = "";
        state.stage2Running = true;
        updateStage2UI(true);
        updateMenuLocks();
    } catch (e) { showToast("시작 실패: " + e.message, "error"); }
}

async function stopStage2() {
    if (!confirm("2단계 실행을 중지하시겠습니까? 현재 단계 종료 후 중단됩니다.")) return;
    try {
        await fetch("/api/stage2/stop", { method: "POST" });
    } catch (e) { showToast("중지 실패: " + e.message, "error"); }
}

function handleStage2Gate(name, payload) {
    if (name !== "quote_ready") return;
    showQuoteGateModal(payload || { files: [], count: 0 });
}

// 견적서 확인 모달 20260512:
// 카테고리 추가등록 팝업(showCategoryQuotationModal)과 동일한 UI 로 통일.
// buildQuotationFileCard / revealPath / openPath 그대로 재사용.
// 체크박스 게이트는 제거됨 — 폴더 열기 / 엑셀로 열기로 검수 흐름 일원화.
function showQuoteGateModal(payload) {
    if (document.getElementById("quote-gate-modal")) return;
    const files = Array.isArray(payload?.files) ? payload.files : [];
    const count = payload?.count ?? files.length;

    const modal = document.createElement("div");
    modal.id = "quote-gate-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
        <div class="modal-box">
            <h2>📋 견적서 수정 후 등록 시작</h2>
            <p class="modal-desc">
                ✅ <strong>${count}</strong>개 견적서가 상품 폴더에 저장됐어요.
            </p>
            <div id="quote-gate-files" style="max-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;margin:12px 0;"></div>
            <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px;font-size:13px;color:#92400e;margin-bottom:12px;line-height:1.5;">
                💡 엑셀에서 <strong>카테고리/가격/옵션</strong> 등을 확인·수정한 후
                <strong>저장(Ctrl+S)</strong>하세요. 저장이 안 된 상태로 진행하면 빈 견적서가 업로드됩니다.
            </div>
            <div class="modal-actions">
                <button id="btn-quote-cancel" class="btn-secondary">❌ 취소</button>
                <button id="btn-quote-proceed" class="btn-primary">✅ 수정 완료 → 등록 시작</button>
            </div>
        </div>`;
    document.body.appendChild(modal);

    const filesWrap = modal.querySelector("#quote-gate-files");
    if (!files.length) {
        filesWrap.innerHTML = `<div style="color:#94a3b8;font-size:13px;text-align:center;padding:14px;">파일 정보가 전달되지 않았습니다.</div>`;
    } else {
        files.forEach((f) => filesWrap.appendChild(buildQuotationFileCard(f)));
    }

    modal.querySelector("#btn-quote-cancel").addEventListener("click", () => modal.remove());

    const proceed = modal.querySelector("#btn-quote-proceed");
    proceed.addEventListener("click", async () => {
        proceed.disabled = true;
        try {
            const res = await fetch("/api/stage2/continue", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ gate: "quote_ready" }),
            });
            if (!res.ok) throw new Error(await res.text());
            modal.remove();
        } catch (e) {
            proceed.disabled = false;
            showToast("진행 실패: " + e.message, "error");
        }
    });
}

function handleStage2Done(msg) {
    // run_id 기반 dedup: 재연결로 동일 done 이 다시 오면 alert 재노출 방지
    if (msg.run_id && state.lastHandledStage2DoneId === msg.run_id) return;
    if (msg.run_id) state.lastHandledStage2DoneId = msg.run_id;
    // 완료/에러 시 게이트 모달이 남아있으면 제거
    const gm = document.getElementById("quote-gate-modal");
    if (gm) gm.remove();
    state.stage2Running = false;
    updateStage2UI(false);
    updateMenuLocks();
    if (msg.ok) {
        appendStage2Log("🎉 2단계가 성공적으로 완료되었습니다!", "success");
        showToast("🎉 2단계 완료!\n쿠팡 상품 등록과 시트 이관이 모두 끝났습니다.", "success", 8000);
    } else {
        appendStage2Log(`❌ 실행 중단: ${msg.error || "알 수 없는 오류"}`, "error");
    }
}

// ====================== 카테고리 추가 등록 ======================

async function renderCategory() {
    panelContent.innerHTML = `
        <div class="panel-section">
            <h2>🗂️ 카테고리 추가 등록</h2>
            <p class="section-desc">완료된 상품을 다른 카테고리 견적서로 재등록합니다. 즐겨찾기로 카테고리를 재사용할 수 있어요.</p>

            <!-- 선택된 카테고리 칩 (항상 최상단에 노출) -->
            <div id="cat-selected-chip-wrap" style="display:none;background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:14px;margin-bottom:16px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:11px;font-weight:700;color:#1d4ed8;background:#dbeafe;padding:3px 8px;border-radius:6px;">선택됨</span>
                    <span id="cat-selected-chip-text" style="flex:1;font-size:14px;font-weight:600;color:#0f172a;word-break:break-all;"></span>
                    <button id="btn-cat-chip-clear" title="선택 취소" style="background:none;border:none;color:#64748b;font-size:16px;cursor:pointer;padding:2px 6px;">✕</button>
                </div>
            </div>

            <!-- 박스 1: 상품 선택 -->
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin-bottom:16px;">
                <div style="font-size:13px;font-weight:700;color:#334155;margin-bottom:10px;">
                    📦 상품 선택 <span style="color:#94a3b8;font-weight:400">(완료 탭)</span>
                    <button id="btn-cat-refresh" style="float:right;background:#f1f5f9;border:1px solid #e2e8f0;color:#475569;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:11px;font-family:inherit;">새로고침</button>
                </div>
                <div id="cat-product-list" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:12px;max-height:240px;overflow-y:auto;">
                    <div style="color:#94a3b8;font-size:13px;text-align:center;padding:20px 0;">로딩 중...</div>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:6px;">* 완료 탭의 유니크 상품 목록입니다</div>
            </div>

            <!-- 박스 2: 카테고리 선택 -->
            <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;margin-bottom:16px;">
                <div style="font-size:13px;font-weight:700;color:#334155;margin-bottom:10px;">
                    🗂️ 카테고리 선택
                </div>

                <!-- 즐겨찾기 드롭다운 -->
                <div style="margin-bottom:12px;">
                    <div style="font-size:12px;color:#64748b;margin-bottom:6px;">⭐ 즐겨찾기에서 선택</div>
                    <div id="cat-fav-list" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:8px;">
                        <div style="color:#94a3b8;font-size:13px;text-align:center;padding:10px 0;">불러오는 중...</div>
                    </div>
                </div>

                <!-- 새 카테고리 검색 토글 -->
                <button id="btn-cat-toggle-search" type="button"
                    style="width:100%;padding:10px;background:#f1f5f9;border:1.5px dashed #cbd5e1;border-radius:10px;color:#475569;cursor:pointer;font-size:13px;font-family:inherit;font-weight:600;">
                    ＋ 새 카테고리 검색
                </button>

                <!-- 검색 영역 (숨김) -->
                <div id="cat-search-area" style="display:none;margin-top:12px;padding:14px;background:#fafafa;border:1px solid #e2e8f0;border-radius:10px;">
                    <div style="display:flex;gap:8px;">
                        <input id="cat-search-input" type="text" placeholder="예: 앞치마, 청소용품..."
                            style="flex:1;padding:10px 14px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px;font-family:inherit;color:#0f172a;outline:none;">
                        <button id="btn-cat-search" class="btn-primary" style="padding:0 18px;">검색</button>
                    </div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:6px;">* 쿠팡허브에서 이 키워드로 카테고리를 찾아와요</div>

                    <div id="cat-search-results" style="display:none;margin-top:12px;"></div>
                </div>
            </div>

            <!-- 실행 -->
            <div class="stage-toolbar" style="margin-bottom:16px;">
                <button id="btn-cat-start" class="btn-start" disabled>🚀 견적서 다운로드 → 등록 시작</button>
                <button id="btn-cat-stop" class="btn-stop" style="display:none">⏹️ 중지</button>
            </div>

            <!-- 로그 -->
            <div id="cat-log-wrap" style="display:none">
                <div class="progress-box" style="margin-bottom:10px;">
                    <div class="progress-label" id="cat-prog-label">대기 중</div>
                    <div class="progress-bar"><div class="progress-fill" id="cat-prog-fill" style="width:0%"></div></div>
                </div>
                <button id="cat-login-btn" class="btn-primary" style="display:none;width:100%;margin-bottom:10px;">
                    ✅ 로그인 완료 → 계속
                </button>
                <div class="log-console" id="cat-log"></div>
            </div>
        </div>`;

    document.getElementById("btn-cat-refresh").addEventListener("click", loadCatProducts);
    document.getElementById("btn-cat-start").addEventListener("click", startCategoryRegister);
    document.getElementById("btn-cat-stop").addEventListener("click", stopCategoryRegister);
    document.getElementById("btn-cat-chip-clear").addEventListener("click", clearCatCategory);
    document.getElementById("btn-cat-toggle-search").addEventListener("click", toggleCatSearch);
    document.getElementById("btn-cat-search").addEventListener("click", searchCatCandidates);
    document.getElementById("cat-search-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); searchCatCandidates(); }
    });
    document.getElementById("cat-login-btn").addEventListener("click", () => catContinue("login"));

    // 초기 렌더
    renderCatSelectedChip();
    if (state.catSearchOpen) {
        document.getElementById("cat-search-area").style.display = "block";
    }
    refreshCatStartEnabled();

    loadCatProducts();
    loadCatFavorites();

    // status 1회 동기화
    try {
        const res = await fetch("/api/category/status");
        if (res.ok) {
            const s = await res.json();
            state.categoryRunning = !!s.running;
            updateCategoryUI(state.categoryRunning);
            if (state.categoryRunning) connectCategoryWS();
            updateMenuLocks();
        }
    } catch {}
}

// ── 선택 카테고리 칩 ──────────────────────────────────────

function renderCatSelectedChip() {
    const wrap = document.getElementById("cat-selected-chip-wrap");
    const text = document.getElementById("cat-selected-chip-text");
    if (!wrap || !text) return;
    if (state.catSelectedCategory) {
        wrap.style.display = "block";
        const c = state.catSelectedCategory;
        const label = c.label ? `⭐ ${c.label} · ` : "";
        text.textContent = `${label}${c.path || c.keyword || "(이름 없음)"}`;
    } else {
        wrap.style.display = "none";
    }
}

function clearCatCategory() {
    state.catSelectedCategory = null;
    renderCatSelectedChip();
    refreshCatStartEnabled();
    // 즐겨찾기 라디오 선택 해제
    document.querySelectorAll('#cat-fav-list input[type="radio"]').forEach((r) => (r.checked = false));
    document.querySelectorAll('#cat-search-results input[type="radio"]').forEach((r) => (r.checked = false));
}

function refreshCatStartEnabled() {
    const btn = document.getElementById("btn-cat-start");
    if (!btn) return;
    btn.disabled = state.categoryRunning
        || !state.catSelectedProducts.length
        || !state.catSelectedCategory;
}

// ── 즐겨찾기 ─────────────────────────────────────────────

async function loadCatFavorites() {
    const wrap = document.getElementById("cat-fav-list");
    if (!wrap) return;
    try {
        const res = await fetch("/api/category/favorites");
        const data = await res.json();
        state.catFavorites = data.favorites || [];
    } catch (e) {
        state.catFavorites = [];
        wrap.innerHTML = `<div style="color:#ef4444;font-size:13px;text-align:center;padding:10px 0;">즐겨찾기 불러오기 실패</div>`;
        return;
    }
    if (!state.catFavorites.length) {
        wrap.innerHTML = `<div style="color:#94a3b8;font-size:13px;text-align:center;padding:12px 0;">저장된 즐겨찾기가 없어요. ‘＋ 새 카테고리 검색’ 으로 추가하세요.</div>`;
        return;
    }
    wrap.innerHTML = "";
    state.catFavorites.forEach((fav) => {
        const row = document.createElement("label");
        row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;border:1px solid transparent;margin-bottom:4px;transition:all 0.15s;";
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "cat-fav-radio";
        radio.style.cssText = "width:16px;height:16px;cursor:pointer;accent-color:#1d4ed8;";
        radio.addEventListener("change", () => {
            state.catSelectedCategory = {
                path: fav.path,
                category_id: fav.category_id || "",
                keyword: fav.keyword || "",
                label: fav.label || "",
                fromFavorite: true,
            };
            renderCatSelectedChip();
            refreshCatStartEnabled();
            // 검색 결과 라디오 해제
            document.querySelectorAll('#cat-search-results input[type="radio"]').forEach((r) => (r.checked = false));
        });

        const textWrap = document.createElement("div");
        textWrap.style.cssText = "flex:1;min-width:0;";
        const title = document.createElement("div");
        title.style.cssText = "font-size:13px;font-weight:600;color:#0f172a;";
        title.textContent = fav.label || fav.path;
        const sub = document.createElement("div");
        sub.style.cssText = "font-size:11px;color:#64748b;margin-top:2px;word-break:break-all;";
        sub.textContent = fav.path;
        textWrap.appendChild(title);
        textWrap.appendChild(sub);

        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.textContent = "✕";
        delBtn.title = "즐겨찾기 삭제";
        delBtn.style.cssText = "opacity:0;background:none;border:none;color:#94a3b8;cursor:pointer;font-size:14px;padding:2px 6px;transition:opacity 0.15s;";
        delBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!confirm(`"${fav.label || fav.path}" 즐겨찾기를 삭제할까요?`)) return;
            try {
                const res = await fetch(`/api/category/favorites/${encodeURIComponent(fav.id)}`, { method: "DELETE" });
                if (!res.ok) throw new Error(await res.text());
                // 삭제된 항목이 현재 선택이면 선택 해제
                if (state.catSelectedCategory && state.catSelectedCategory.fromFavorite
                    && state.catSelectedCategory.path === fav.path) {
                    clearCatCategory();
                }
                loadCatFavorites();
            } catch (err) { showToast("삭제 실패: " + err.message, "error"); }
        });

        row.onmouseover = () => { row.style.background = "#f0f9ff"; delBtn.style.opacity = "1"; };
        row.onmouseout = () => { row.style.background = ""; delBtn.style.opacity = "0"; };

        row.appendChild(radio);
        row.appendChild(textWrap);
        row.appendChild(delBtn);
        wrap.appendChild(row);
    });
}

// ── 새 카테고리 검색 ─────────────────────────────────────

function toggleCatSearch() {
    state.catSearchOpen = !state.catSearchOpen;
    const area = document.getElementById("cat-search-area");
    const btn = document.getElementById("btn-cat-toggle-search");
    if (!area || !btn) return;
    area.style.display = state.catSearchOpen ? "block" : "none";
    btn.textContent = state.catSearchOpen ? "− 검색 닫기" : "＋ 새 카테고리 검색";
    if (state.catSearchOpen) {
        setTimeout(() => document.getElementById("cat-search-input")?.focus(), 50);
    }
}

async function searchCatCandidates() {
    const input = document.getElementById("cat-search-input");
    const btn = document.getElementById("btn-cat-search");
    const resultsWrap = document.getElementById("cat-search-results");
    if (!input || !btn || !resultsWrap) return;
    const keyword = input.value.trim();
    if (!keyword) { showToast("키워드를 입력해주세요.", "warn"); return; }

    btn.disabled = true;
    btn.textContent = "검색 중...";
    resultsWrap.style.display = "block";
    resultsWrap.innerHTML = `<div style="color:#64748b;font-size:13px;text-align:center;padding:16px 0;">쿠팡허브에서 후보를 불러오는 중... (Chrome 창이 뜰 수 있어요)</div>`;

    try {
        const res = await fetch("/api/category/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            resultsWrap.innerHTML = `<div style="color:#ef4444;font-size:13px;padding:10px 0;">❌ ${esc(err.detail || res.statusText)}</div>`;
            return;
        }
        const data = await res.json();
        if (data.needs_login) {
            resultsWrap.innerHTML = `<div style="color:#b45309;font-size:13px;padding:10px 0;">🔑 쿠팡 로그인이 필요합니다. 방금 열린 Chrome에서 로그인 후 다시 "검색"을 눌러주세요.</div>`;
            return;
        }
        state.catCandidates = data.candidates || [];
        renderCatCandidates(keyword);
    } catch (e) {
        resultsWrap.innerHTML = `<div style="color:#ef4444;font-size:13px;padding:10px 0;">❌ 검색 실패: ${esc(e.message)}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "검색";
    }
}

function renderCatCandidates(keyword) {
    const wrap = document.getElementById("cat-search-results");
    if (!wrap) return;
    if (!state.catCandidates.length) {
        wrap.innerHTML = `<div style="color:#94a3b8;font-size:13px;padding:10px 0;">후보가 없어요. 다른 키워드로 시도해보세요.</div>`;
        return;
    }

    const listId = "cat-candidate-list";
    wrap.innerHTML = `
        <div style="font-size:12px;color:#64748b;margin-bottom:8px;">🔍 후보 ${state.catCandidates.length}개 — 하나를 선택하세요</div>
        <div id="${listId}" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:8px;max-height:220px;overflow-y:auto;"></div>
        <div style="margin-top:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
            <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#334155;cursor:pointer;">
                <input type="checkbox" id="cat-save-fav" checked style="accent-color:#1d4ed8;"> ⭐ 즐겨찾기에 저장
            </label>
            <input id="cat-fav-label" type="text" placeholder="라벨 (예: 주방 앞치마)" value="${esc(keyword)}"
                style="flex:1;min-width:160px;padding:8px 12px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:13px;font-family:inherit;outline:none;">
        </div>
        <button id="btn-cat-confirm" class="btn-primary" style="width:100%;margin-top:10px;">이 카테고리로 결정</button>
    `;

    const list = document.getElementById(listId);
    state.catCandidates.forEach((cand, idx) => {
        const row = document.createElement("label");
        row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;border:1px solid transparent;margin-bottom:3px;";
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "cat-cand-radio";
        radio.dataset.idx = String(idx);
        radio.style.cssText = "width:16px;height:16px;cursor:pointer;accent-color:#1d4ed8;";
        radio.addEventListener("change", () => {
            // 즐겨찾기 라디오 해제 (시각만, 실제 선택은 '결정' 눌러야 state에 반영)
            document.querySelectorAll('#cat-fav-list input[type="radio"]').forEach((r) => (r.checked = false));
        });
        const span = document.createElement("span");
        span.style.cssText = "font-size:13px;color:#0f172a;word-break:break-all;";
        span.textContent = cand.path;
        row.onmouseover = () => (row.style.background = "#f0f9ff");
        row.onmouseout = () => (row.style.background = "");
        row.appendChild(radio);
        row.appendChild(span);
        list.appendChild(row);
    });

    document.getElementById("btn-cat-confirm").addEventListener("click", async () => {
        const chosen = document.querySelector('#cat-candidate-list input[type="radio"]:checked');
        if (!chosen) { showToast("후보 중 하나를 선택해주세요.", "warn"); return; }
        const cand = state.catCandidates[Number(chosen.dataset.idx)];
        const labelInput = document.getElementById("cat-fav-label");
        const saveFav = document.getElementById("cat-save-fav")?.checked;
        const label = (labelInput?.value || "").trim() || keyword;

        state.catSelectedCategory = {
            path: cand.path,
            category_id: cand.category_id || "",
            keyword,
            label,
            fromFavorite: false,
            saveAsFavorite: !!saveFav,
        };
        renderCatSelectedChip();
        refreshCatStartEnabled();

        // 즐겨찾기 즉시 저장 (실행 전에도 보존)
        if (saveFav) {
            try {
                await fetch("/api/category/favorites", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        label, keyword,
                        path: cand.path,
                        category_id: cand.category_id || "",
                    }),
                });
                loadCatFavorites();
            } catch (e) { /* 즐겨찾기 저장 실패는 무시하고 진행 */ }
        }

        // 검색 영역 닫기
        state.catSearchOpen = false;
        document.getElementById("cat-search-area").style.display = "none";
        document.getElementById("btn-cat-toggle-search").textContent = "＋ 새 카테고리 검색";
    });
}

async function loadCatProducts() {
    const listEl = document.getElementById("cat-product-list");
    if (!listEl) return;
    listEl.innerHTML = `<div style="color:#94a3b8;font-size:13px;text-align:center;padding:16px 0;">불러오는 중...</div>`;
    state.catSelectedProducts = [];
    refreshCatStartEnabled();
    try {
        const res = await fetch("/api/category/products");
        const data = await res.json();
        if (!data.products || !data.products.length) {
            listEl.innerHTML = `<div style="color:#94a3b8;font-size:13px;text-align:center;padding:16px 0;">완료된 상품이 없어요</div>`;
            return;
        }
        listEl.innerHTML = "";
        // 정렬 기준 라벨 (사용자가 왜 이 순서인지 이해할 수 있게)
        const sortLabelMap = {
            "sheet_timestamp_desc": "최신순 (시트 등록 시각)",
            "folder_mtime_desc": "최신순 (폴더 수정 시각)",
            "sheet_row_desc": "최신순 (시트 입력 역순)",
        };
        const sortLabel = sortLabelMap[data.sort_by] || data.sort_by || "기본순";
        const hdr = document.createElement("div");
        hdr.style.cssText = "font-size:11px;color:#94a3b8;margin:-4px 0 8px 2px;";
        hdr.textContent = `📊 ${data.count ?? data.products.length}개 · ${sortLabel}`;
        listEl.appendChild(hdr);

        data.products.forEach((prod, idx) => {
            const item = document.createElement("label");
            item.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;cursor:pointer;border:1px solid transparent;margin-bottom:5px;transition:all 0.15s;";
            const cb = document.createElement("input");
            cb.type = "checkbox";
            cb.dataset.idx = String(idx);
            cb.style.cssText = "width:16px;height:16px;cursor:pointer;accent-color:#1d4ed8;";
            cb.addEventListener("change", () => toggleCatSelection(cb, prod));
            const span = document.createElement("span");
            span.style.cssText = "font-size:13px;color:#334155;flex:1;min-width:0;";
            span.textContent = prod.name;
            item.appendChild(cb);
            item.appendChild(span);
            // 폴더 mtime 이 있으면 우측에 날짜 힌트 (상위 3개까지만 표시)
            if (prod.mtime && idx < 3) {
                const dt = new Date(prod.mtime * 1000);
                const hint = document.createElement("span");
                hint.style.cssText = "font-size:10px;color:#cbd5e1;font-family:'JetBrains Mono',monospace;flex-shrink:0;";
                const mm = String(dt.getMonth() + 1).padStart(2, "0");
                const dd = String(dt.getDate()).padStart(2, "0");
                const hh = String(dt.getHours()).padStart(2, "0");
                const mi = String(dt.getMinutes()).padStart(2, "0");
                hint.textContent = `${mm}/${dd} ${hh}:${mi}`;
                item.appendChild(hint);
            }
            item.onmouseover = () => (item.style.background = "#f0f9ff");
            item.onmouseout = () => (item.style.background = "");
            listEl.appendChild(item);
        });
    } catch (e) {
        listEl.innerHTML = `<div style="color:#ef4444;font-size:13px;text-align:center;padding:16px 0;">불러오기 실패</div>`;
    }
}

function toggleCatSelection(checkbox, prod) {
    if (checkbox.checked) {
        state.catSelectedProducts.push(prod);
    } else {
        state.catSelectedProducts = state.catSelectedProducts.filter((p) => p.name !== prod.name);
    }
    refreshCatStartEnabled();
}

async function startCategoryRegister() {
    if (!state.catSelectedProducts.length) {
        showToast("상품을 1개 이상 선택해주세요!", "warn");
        return;
    }
    if (!state.catSelectedCategory) {
        showToast("카테고리를 먼저 선택해주세요! (즐겨찾기 또는 새 카테고리 검색)", "warn");
        return;
    }
    const sel = state.catSelectedCategory;
    document.getElementById("cat-log-wrap").style.display = "block";
    document.getElementById("cat-log").innerHTML = "";
    appendCatLog(`🚀 카테고리 추가 등록 시작! "${sel.label || sel.path}"`, "info");

    const payload = {
        products: state.catSelectedProducts,
        keyword: sel.keyword || (sel.path ? sel.path.split(">").slice(-1)[0].trim() : ""),
        category_id: sel.category_id || "",
        path: sel.path || "",
        save_as_favorite: !sel.fromFavorite && !!sel.saveAsFavorite,
        favorite_label: sel.label || "",
    };
    try {
        const res = await fetch("/api/category/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            appendCatLog(`❌ 시작 실패: ${err.detail || res.statusText}`, "error");
            return;
        }
    } catch (e) {
        appendCatLog(`❌ 오류: ${e.message}`, "error");
        return;
    }
    state.categoryRunning = true;
    updateCategoryUI(true);
    updateMenuLocks();
    connectCategoryWS();
}

async function stopCategoryRegister() {
    if (!confirm("카테고리 추가 등록을 중지하시겠습니까?")) return;
    try {
        await fetch("/api/category/stop", { method: "POST" });
    } catch (e) { showToast("중지 실패: " + e.message, "error"); }
}

function connectCategoryWS() {
    if (state.wsCat) { try { state.wsCat.close(); } catch {} }
    const since = state.categoryLastEventTs || 0;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws/category?since=${since}`);
    state.wsCat = ws;
    state.categoryMsgReceived = false;
    if (state.categoryResetTimer) { clearTimeout(state.categoryResetTimer); state.categoryResetTimer = null; }
    ws.onopen = () => {
        state.categoryResetTimer = setTimeout(() => {
            if (state.categoryMsgReceived && state.wsCat === ws && ws.readyState === WebSocket.OPEN) {
                state.categoryRetryCount = 0;
            }
        }, 5000);
    };
    ws.onmessage = (ev) => {
        state.categoryMsgReceived = true;
        const msg = JSON.parse(ev.data);
        if (msg.ts) state.categoryLastEventTs = msg.ts;
        if (msg.type === "log") appendCatLog(msg.msg, msg.level || "info");
        else if (msg.type === "progress") {
            const step = msg.step || 0;
            const total = msg.total || 1;
            const pct = Math.min(100, Math.round((step / total) * 100));
            const fill = document.getElementById("cat-prog-fill");
            const label = document.getElementById("cat-prog-label");
            if (fill) fill.style.width = pct + "%";
            if (label) label.textContent = `${msg.label || "-"} · ${pct}%`;
        } else if (msg.type === "gate") {
            if (msg.name === "login") {
                const btn = document.getElementById("cat-login-btn");
                if (btn) btn.style.display = "block";
            } else if (msg.name === "quotation") {
                showCategoryQuotationModal(msg.payload || { files: [], count: 0 });
            }
        } else if (msg.type === "done") {
            // run_id 기반 dedup: 재연결로 동일 done 이 다시 오면 처리 스킵
            if (msg.run_id && state.lastHandledCatDoneId === msg.run_id) return;
            if (msg.run_id) state.lastHandledCatDoneId = msg.run_id;
            state.categoryRunning = false;
            updateCategoryUI(false);
            updateMenuLocks();
            document.getElementById("cat-quotation-modal")?.remove();
            if (msg.ok) {
                // 미구현 플래그가 실려있으면 수동 업로드 확정 안내
                if (msg.upload_pending) {
                    const count = msg.count ?? (msg.files ? msg.files.length : 0);
                    appendCatLog("✅ 견적서 자동 작성 완료!", "success");
                    appendCatLog(`📂 ${count}개 상품의 견적서가 폴더에 저장되었습니다.`, "info");
                    if (msg.chrome_kept) {
                        appendCatLog("🌐 크롬 창이 유지되어 있습니다. 같은 창에서 대량상품등록으로 이동 가능.", "info");
                    }
                    const fileLines = (msg.files || [])
                        .map((f) => `• ${f.product_name}\n   ${f.excel_path}`)
                        .join("\n\n");
                    const chromeNote = msg.chrome_kept
                        ? `🌐 크롬 창은 종료되지 않았습니다.\n같은 창에서 대량상품등록 페이지로 이동하면 재로그인 없이 업로드 가능합니다.\nhttps://wing.coupang.com/tenants/seller-web/products/bulk-registration\n\n`
                        : "";
                    showToast(
                        `✅ 견적서 자동 작성 완료!\n` +
                        `📂 ${count}개 상품의 견적서가 폴더에 저장되었습니다.\n` +
                        `⚠️ 쿠팡 자동 업로드는 아직 미구현입니다.\n` +
                        `엑셀을 확인하신 후 쿠팡허브에서 수동으로 업로드해주세요.\n` +
                        chromeNote +
                        (fileLines ? `━━━━━━━━\n${fileLines}` : ""),
                        "warn",
                        15000
                    );
                } else {
                    appendCatLog("🎉 카테고리 추가 등록 완료!", "success");
                }
            } else {
                appendCatLog(`❌ 실패: ${msg.error || ""}`, "error");
            }
            if (state.wsCat) { try { state.wsCat.close(); } catch {} state.wsCat = null; }
        } else if (msg.type === "snapshot") {
            state.categoryRunning = !!msg.running;
            updateCategoryUI(state.categoryRunning);
            updateMenuLocks();
        }
    };
    ws.onclose = () => {
        if (state.categoryResetTimer) { clearTimeout(state.categoryResetTimer); state.categoryResetTimer = null; }
        // 실행 중이고 아직 현재 패널이 category 일 때만 재연결 — 지수 백오프 + 최대 5회
        if (!(state.categoryRunning && state.currentPanel === "category")) return;
        const n = (state.categoryRetryCount = (state.categoryRetryCount || 0) + 1);
        if (n > 5) {
            console.warn("[ws/category] 최대 재시도(5회) 초과 — 자동 재연결 중단");
            return;
        }
        const delay = 1500 * Math.pow(2, n - 1);
        setTimeout(connectCategoryWS, delay);
    };
}

async function catContinue(gate) {
    const loginBtn = document.getElementById("cat-login-btn");
    if (loginBtn) loginBtn.style.display = "none";
    document.getElementById("cat-quotation-modal")?.remove();
    try {
        await fetch("/api/category/continue", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gate }),
        });
        appendCatLog("▶️ 계속 진행합니다...", "info");
    } catch (e) {
        appendCatLog(`❌ 계속 진행 실패: ${e.message}`, "error");
    }
}

// ── 견적서 수정 게이트 모달 ──────────────────────────────

function showCategoryQuotationModal(payload) {
    const existing = document.getElementById("cat-quotation-modal");
    if (existing) existing.remove();
    const files = Array.isArray(payload?.files) ? payload.files : [];
    const count = payload?.count ?? files.length;

    const modal = document.createElement("div");
    modal.id = "cat-quotation-modal";
    modal.className = "modal-overlay";
    modal.innerHTML = `
        <div class="modal-box">
            <h2>📋 견적서 수정 후 등록 시작</h2>
            <p class="modal-desc">
                ✅ <strong>${count}</strong>개 견적서가 상품 폴더에 저장됐어요.
            </p>
            <div id="cat-quotation-files" style="max-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;margin:12px 0;"></div>
            <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px;font-size:13px;color:#92400e;margin-bottom:12px;line-height:1.5;">
                💡 엑셀에서 <strong>카테고리/가격/옵션</strong> 등을 확인·수정한 후
                <strong>저장(Ctrl+S)</strong>하세요. 저장이 안 된 상태로 진행하면 빈 견적서가 업로드됩니다.
            </div>
            <div class="modal-actions">
                <button id="btn-cat-quotation-cancel" class="btn-secondary">❌ 취소</button>
                <button id="btn-cat-quotation-proceed" class="btn-primary">✅ 수정 완료 → 등록 시작</button>
            </div>
        </div>`;
    document.body.appendChild(modal);

    const filesWrap = modal.querySelector("#cat-quotation-files");
    if (!files.length) {
        filesWrap.innerHTML = `<div style="color:#94a3b8;font-size:13px;text-align:center;padding:14px;">파일 정보가 전달되지 않았습니다.</div>`;
    } else {
        files.forEach((f) => filesWrap.appendChild(buildQuotationFileCard(f)));
    }

    modal.querySelector("#btn-cat-quotation-cancel").addEventListener("click", async () => {
        if (!confirm("등록을 취소하시겠습니까? 견적서는 폴더에 남습니다.")) return;
        try {
            await fetch("/api/category/stop", { method: "POST" });
        } catch {}
        modal.remove();
    });
    modal.querySelector("#btn-cat-quotation-proceed").addEventListener("click", () => {
        catContinue("quotation");
    });
}

function buildQuotationFileCard(f) {
    const card = document.createElement("div");
    card.style.cssText = "background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:14px;";
    const productName = f.product_name || "(이름 없음)";
    const filename = f.excel_filename || "(파일명 없음)";
    const excelPath = f.excel_path || "";

    const title = document.createElement("div");
    title.style.cssText = "font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px;";
    title.textContent = `📦 ${productName}`;

    const fname = document.createElement("div");
    fname.style.cssText = "font-size:12px;color:#334155;margin-bottom:6px;";
    fname.textContent = `📄 ${filename}`;

    const pathWrap = document.createElement("div");
    pathWrap.style.cssText = "display:flex;gap:6px;align-items:center;margin-bottom:10px;";
    const code = document.createElement("code");
    code.style.cssText = "flex:1;min-width:0;background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:6px 8px;font-size:11px;color:#475569;word-break:break-all;white-space:normal;";
    code.textContent = excelPath;
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.textContent = "복사";
    copyBtn.className = "btn-small";
    copyBtn.style.cssText = "flex-shrink:0;padding:4px 10px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;cursor:pointer;font-size:11px;";
    copyBtn.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(excelPath);
            copyBtn.textContent = "✓ 복사됨";
            setTimeout(() => (copyBtn.textContent = "복사"), 1500);
        } catch {
            showToast("복사에 실패했습니다. 수동으로 선택해 복사하세요.", "error");
        }
    });
    pathWrap.appendChild(code);
    pathWrap.appendChild(copyBtn);

    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;";
    const revealBtn = document.createElement("button");
    revealBtn.type = "button";
    revealBtn.textContent = "📂 폴더 열기";
    revealBtn.className = "btn-small";
    revealBtn.style.cssText = "padding:6px 12px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;cursor:pointer;font-size:12px;color:#1d4ed8;";
    revealBtn.addEventListener("click", () => revealPath(excelPath));
    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.textContent = "📊 엑셀로 열기";
    openBtn.className = "btn-small";
    openBtn.style.cssText = "padding:6px 12px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;cursor:pointer;font-size:12px;color:#047857;";
    openBtn.addEventListener("click", () => openPath(excelPath));
    btnRow.appendChild(revealBtn);
    btnRow.appendChild(openBtn);

    card.appendChild(title);
    card.appendChild(fname);
    card.appendChild(pathWrap);
    card.appendChild(btnRow);
    return card;
}

async function revealPath(path) {
    if (!path) return;
    try {
        const res = await fetch("/api/util/reveal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("폴더 열기 실패: " + (err.detail || res.statusText), "error");
        }
    } catch (e) {
        showToast("폴더 열기 실패: " + e.message, "error");
    }
}

async function openPath(path) {
    if (!path) return;
    try {
        const res = await fetch("/api/util/open", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast("파일 열기 실패: " + (err.detail || res.statusText), "error");
        }
    } catch (e) {
        showToast("파일 열기 실패: " + e.message, "error");
    }
}

function appendCatLog(msg, level = "info") {
    const box = document.getElementById("cat-log");
    if (!box) return;
    const line = document.createElement("div");
    line.className = `log-line log-${level}`;
    line.textContent = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function updateCategoryUI(isRunning) {
    const startBtn = document.getElementById("btn-cat-start");
    const stopBtn = document.getElementById("btn-cat-stop");
    if (!startBtn || !stopBtn) return;
    startBtn.style.display = isRunning ? "none" : "inline-block";
    stopBtn.style.display = isRunning ? "inline-block" : "none";
    refreshCatStartEnabled();
}

// ====================== 서버 헬스체크 ======================

async function checkServer() {
    const dot = document.getElementById("server-status");
    const text = document.getElementById("server-status-text");
    try {
        const res = await fetch("/api/health");
        if (res.ok) {
            dot.classList.add("online"); dot.classList.remove("offline");
            text.textContent = "서버 연결됨";
        } else throw new Error();
    } catch {
        dot.classList.add("offline"); dot.classList.remove("online");
        text.textContent = "서버 연결 실패";
    }
}

// 최초 상태 초기화
async function initStatus() {
    try {
        const res = await fetch("/api/stage1/status");
        const s = await res.json();
        state.running = s.running;
        state.stage1CompletedChecklist = s.checklist_done;
    } catch {}
    try {
        const res2 = await fetch("/api/stage2/status");
        const s2 = await res2.json();
        state.stage2Running = s2.running;
    } catch {}
    try {
        const res3 = await fetch("/api/category/status");
        if (res3.ok) {
            const s3 = await res3.json();
            state.categoryRunning = !!s3.running;
        }
    } catch {}
    updateMenuLocks();
    // 기본 진입 화면: 1단계 (2단계 실행 중이면 2단계로)
    if (!state.currentPanel) {
        const target = state.stage2Running ? "stage2" : "stage1";
        try { menuByKey[target]?.click(); } catch {}
    }
}

checkServer();
initStatus();
setInterval(checkServer, 10000);

// 컨텐츠 스튜디오 외부 링크 (새 탭, additive only)
const CONTENT_STUDIO_URL = "http://localhost:8101";
document.getElementById("goContentStudio")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    window.open(CONTENT_STUDIO_URL, "_blank", "noopener,noreferrer");
});
