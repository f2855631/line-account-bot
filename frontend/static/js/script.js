// ============================================================
// Core：全域狀態、初始化、頁面導航、計算機、送出
// ============================================================

// --- 全域狀態變數 ---
let selectedCid = "";
let selectedTarget = "";
let formula = "";
let datePicker = null;
let currentEditId = null;
let selectedRecord = null;
let isHistoryMode = false;

// --- 日期工具 ---
function formatFullDate(date) {
    const days = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${days[date.getDay()]}`;
}

function getLocalDateString(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// --- 初始化 ---
async function init(liffId) {
    selectedCid = localStorage.getItem('last_book_id') || "";
    document.getElementById("date-display").innerText = formatFullDate(new Date());

    datePicker = flatpickr("#date-picker-trigger", {
        wrap: true, static: true, locale: "zh_tw", defaultDate: "today", disableMobile: "true",
        onChange: (selectedDates) => {
            if (selectedDates.length) {
                document.getElementById("date-display").innerText = formatFullDate(selectedDates[0]);
            }
        }
    });

    try {
        if (!liff.id) await liff.init({ liffId: liffId });
        if (!liff.isLoggedIn()) { liff.login(); return; }

        const urlParams = new URLSearchParams(window.location.search);
        const action = urlParams.get('action');
        isHistoryMode = (action === 'history');

        const context = liff.getContext();
        let ctxId = urlParams.get('bookId')
            || context?.groupId
            || context?.roomId
            || context?.utouId;
        if (!ctxId) {
            try { const p = await liff.getProfile(); ctxId = p.userId; } catch(e) {}
        }
        selectedCid = ctxId || selectedCid;

        if (selectedCid) {
            localStorage.setItem('last_book_id', selectedCid);
            if (!isHistoryMode) {
                await loadMembers(selectedCid);
            }
        }

        initMonthSelector();
        console.log("✅ LIFF 資料初始化完成");
    } catch (err) {
        console.error("LIFF Init Error:", err);
    }
}

// --- 頁面導航 ---
function showInputPage(name) {
    selectedTarget = name; formula = ""; currentEditId = null;
    document.getElementById('target-title').innerText = `正在為 ${name} 記帳`;
    document.getElementById('amount-display').innerText = "0";
    document.getElementById('note-input').value = "";

    const okBtn = document.getElementById('btn-ok');
    if (okBtn) { okBtn.innerText = "OK"; okBtn.disabled = false; okBtn.classList.remove('edit-mode'); }

    const today = new Date();
    datePicker.setDate(today);
    document.getElementById("date-display").innerText = formatFullDate(today);

    document.getElementById('page-list').style.display = 'none';
    const inputPage = document.getElementById('page-input');
    inputPage.style.display = 'flex';
    inputPage.classList.add('active');
    window.scrollTo(0, 0);
}

function hideInputPage() {
    document.getElementById('page-input').style.display = 'none';
    document.getElementById('page-input').classList.remove('active');
    document.getElementById('page-list').style.display = 'flex';
    window.scrollTo(0, 0);
    selectedTarget = ""; formula = ""; currentEditId = null;
    renderFormula();
}

function openIndividualHistory(targetName) {
    selectedTarget = targetName;
    document.getElementById('page-list').style.display = 'none';
    document.getElementById('page-input').style.display = 'flex';
    document.getElementById('history-drawer').classList.add('open');
    document.getElementById('history-title-name').innerText = `${targetName} 的紀錄`;
    fetchHistory();
    window.scrollTo(0, 0);
}

function openGlobalHistory() {
    selectedTarget = "";
    document.getElementById('page-list').style.display = 'none';
    document.getElementById('page-input').style.display = 'flex';
    document.getElementById('history-drawer').classList.add('open');
    document.getElementById('history-title-name').innerText = "全體歷史紀錄";
    fetchHistory();
}

function toggleHistory() {
    const drawer = document.getElementById('history-drawer');
    const isOpening = !drawer.classList.contains('open');
    if (isOpening) {
        drawer.classList.add('open');
        document.getElementById('drawer-overlay').classList.add('active');
        document.getElementById('history-title-name').innerText = selectedTarget ? `${selectedTarget} 的紀錄` : "全體歷史紀錄";
        fetchHistory();
    } else {
        closeHistoryDrawer();
    }
}

function closeHistoryDrawer() {
    document.getElementById('history-drawer').classList.remove('open');
    document.getElementById('drawer-overlay').classList.remove('active');
    if (!selectedTarget) {
        setTimeout(async () => {
            document.documentElement.classList.remove('history-mode');
            hideInputPage();
            if (isHistoryMode && selectedCid) {
                isHistoryMode = false;
                await loadMembers(selectedCid);
            }
        }, 300);
    }
}

// --- 計算機 ---
function press(v) {
    if (formula === "" && (v === "0" || v === "00")) return;
    if (formula === "" && v === "-") { formula = "-"; renderFormula(); return; }
    const lastChar = formula.slice(-1);
    const ops = ["+", "-", "*", "/", "×", "÷", "."];
    if (ops.includes(lastChar) && ops.includes(v)) {
        formula = formula.slice(0, -1) + v;
    } else {
        formula += v;
    }
    renderFormula();
}

function backspace() { formula = formula.slice(0, -1); renderFormula(); }
function clearFormula() { formula = ""; renderFormula(); }
function setNote(val) { document.getElementById('note-input').value = val; }

function renderFormula() {
    const display = document.getElementById('amount-display');
    display.innerText = formula === "" ? "0" : formula.replace(/\*/g, '×').replace(/\//g, '÷');
}

function calculateResult() {
    if (!formula || formula === "-") return 0;
    try {
        let cleanFormula = formula.replace(/×/g, '*').replace(/÷/g, '/');
        const lastChar = cleanFormula.slice(-1);
        if (["+", "-", "*", "/"].includes(lastChar)) cleanFormula = cleanFormula.slice(0, -1);
        const res = math.evaluate(cleanFormula);
        if (typeof res !== 'number' || isNaN(res) || !isFinite(res)) return 0;
        const rounded = Math.round(res);
        formula = rounded.toString();
        renderFormula();
        return rounded;
    } catch (e) { return 0; }
}

// --- 送出記帳 ---
async function doSend() {
    let amount = calculateResult();
    if (amount === 0 && formula !== "0") { showToast("請輸入有效金額", true); return; }

    const okBtn = document.getElementById('btn-ok');
    if (okBtn) { okBtn.disabled = true; okBtn.innerText = "⏳"; }

    const note = document.getElementById('note-input').value.trim();
    const selectedDate = datePicker.selectedDates[0] || new Date();

    try {
        if (currentEditId) {
            const res = await fetch('/api/update', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: currentEditId, contextId: selectedCid, amount: amount,
                    item: note || "一般消費", date: getLocalDateString(selectedDate)
                })
            });
            const result = await res.json();
            if (result.success) {
                currentEditId = null;
                clearFormula();
                document.getElementById('note-input').value = "";
                if (okBtn) { okBtn.classList.remove('edit-mode'); okBtn.innerText = "OK"; }
                showToast(`✅ 更新成功 $${amount}`);
                fetchHistory();
            } else {
                showToast("更新失敗，請稍後再試", true);
            }
        } else {
            let userName = "使用者";
            try { if (liff.isLoggedIn()) { const p = await liff.getProfile(); userName = p.displayName; } } catch(e) {}

            const res = await fetch('/api/add', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    target_name: selectedTarget,
                    amount: amount,
                    item: note || "一般消費",
                    contextId: selectedCid,
                    user_name: userName,
                    date: getLocalDateString(selectedDate)
                })
            });
            const result = await res.json();
            if (result.success) {
                const itemLabel = note ? `・${note}` : "";
                clearFormula();
                document.getElementById('note-input').value = "";
                showToast(`✅ ${selectedTarget} 記帳 $${amount}${itemLabel}`);
                fetchHistory();
            } else {
                showToast("記帳失敗，請稍後再試", true);
            }
        }
    } catch (e) {
        showToast("送出失敗，請檢查網路狀態", true);
    } finally {
        if (okBtn) { okBtn.disabled = false; okBtn.innerText = currentEditId ? "更新" : "OK"; }
    }
}
