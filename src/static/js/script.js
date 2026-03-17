let selectedCid = ""; 
let selectedTarget = "";
let formula = "";
let datePicker = null; 
let currentEditId = null; 
let selectedRecord = null; 

// 1. 格式化日期顯示
function formatFullDate(date) {
    const days = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${days[date.getDay()]}`;
}

// ✅ 安全地將 Date 物件轉為 YYYY-MM-DD
function getLocalDateString(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// 2. 初始化 LIFF 與套件
async function init(liffId) {
    selectedCid = localStorage.getItem('last_book_id') || "";
    document.getElementById("date-display").innerText = formatFullDate(new Date());
    
    // 初始化日期選擇器 (加入 static: true 確保置中佈局不受干擾)
    datePicker = flatpickr("#date-picker-trigger", {
        wrap: true,
        static: true, // 💡 確保在 flex 容器中正確置中
        locale: "zh_tw", 
        defaultDate: "today", 
        disableMobile: "true",
        onChange: (selectedDates) => { 
            if(selectedDates.length) {
                document.getElementById("date-display").innerText = formatFullDate(selectedDates[0]);
            }
        }
    });
    
    try {
        if (!liff.id) {
            await liff.init({ liffId: liffId });
        }
        
        if (!liff.isLoggedIn()) { 
            liff.login(); 
            return; 
        }
        
        const urlParams = new URLSearchParams(window.location.search);
        const context = liff.getContext();
        
        selectedCid = urlParams.get('bookId') || (context ? (context.groupId || context.userId) : selectedCid);
        
        if (selectedCid) {
            localStorage.setItem('last_book_id', selectedCid);
            await loadMembers(selectedCid);
        }

        console.log("✅ LIFF 資料初始化完成");
    } catch (err) { 
        console.error("LIFF Init Error:", err); 
    }
}

// 3. 讀取與渲染成員清單
async function loadMembers(cid) {
    const container = document.getElementById('nameListContainer');
    const cached = localStorage.getItem(`members_${cid}`);
    if (cached) renderMemberList(JSON.parse(cached));

    try {
        const res = await fetch(`/api/get-members?contextId=${cid}&t=${Date.now()}`);
        const data = await res.json();
        const members = data.members || [];
        localStorage.setItem(`members_${cid}`, JSON.stringify(members));
        renderMemberList(members);
    } catch (e) { 
        if (!cached) container.innerHTML = "讀取失敗，請檢查網路"; 
    }
}

function renderMemberList(members) {
    const container = document.getElementById('nameListContainer');
    container.innerHTML = members.map(m => `
        <div class="name-card" onclick="showInputPage('${m.target_name}')">
            <div class="name-info">
                <span class="name-text">${m.target_name}</span>
                <span class="month-total">本月累積 $${Math.round(m.amount || 0)}</span>
            </div>
            <button class="del-btn" onclick="doDelete('${m.target_name}', event)">刪除</button>
        </div>
    `).join('') || "<p style='text-align:center; padding:20px; color:#888;'>尚未建立成員</p>";
}

// 4. 記帳頁面顯示
function showInputPage(name) {
    selectedTarget = name; formula = ""; currentEditId = null;
    document.getElementById('target-title').innerText = `正在為 ${name} 記帳`;
    document.getElementById('amount-display').innerText = "0";
    document.getElementById('note-input').value = "";
    
    // 重置按鈕狀態
    const submitBtn = document.getElementById('btn-submit-record');
    submitBtn.innerText = "完成送出";
    submitBtn.style.background = "var(--primary-accent)";
    submitBtn.disabled = false;
    
    const today = new Date();
    datePicker.setDate(today);
    document.getElementById("date-display").innerText = formatFullDate(today);
    
    document.getElementById('page-list').style.display = 'none';
    const inputPage = document.getElementById('page-input');
    inputPage.style.display = 'flex'; 
    inputPage.classList.add('active');
    
    window.scrollTo(0, 0);
}

// 5. 執行送出 (加入防連點機制)
async function doSend() {
    let amount = calculateResult();
    if (amount === 0 && formula !== "0") return alert("請輸入有效金額"); 
    
    const submitBtn = document.getElementById('btn-submit-record');
    submitBtn.disabled = true; // 鎖定按鈕防止連點
    submitBtn.innerText = "處理中...";

    const note = document.getElementById('note-input').value.trim();
    const selectedDate = datePicker.selectedDates[0] || new Date();
    
    try {
        if (currentEditId) {
            const dateStr = getLocalDateString(selectedDate);
            const payload = {
                id: currentEditId,
                contextId: selectedCid,
                amount: amount,
                item: note || "手機即時記帳",
                date: dateStr
            };

            const res = await fetch('/api/update', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            
            if (result.success) {
                alert("更新成功");
                hideInputPage();
                loadMembers(selectedCid);
            }
        } else {
            const y = selectedDate.getFullYear();
            const m = selectedDate.getMonth() + 1;
            const d = selectedDate.getDate();
            const datePrefix = `${y}/${m}/${d}`;

            if (liff.isInClient()) {
                const triggerText = note 
                    ? `${datePrefix} ${selectedTarget} ${amount} ${note}` 
                    : `${datePrefix} ${selectedTarget} ${amount}`;
                
                await liff.sendMessages([{ type: 'text', text: triggerText }]);
                liff.closeWindow(); 
            } else {
                alert(`[網頁模擬] 發送：\n${datePrefix} ${selectedTarget} ${amount} ${note || ""}`);
                hideInputPage();
            }
        }
    } catch (e) { 
        alert("送出失敗，請檢查網路狀態"); 
    } finally {
        // 無論成功失敗，最後都要解鎖按鈕
        submitBtn.disabled = false;
        submitBtn.innerText = currentEditId ? "更新紀錄" : "完成送出";
    }
}

// --- 歷史紀錄動線邏輯優化 ---

// 💡 從首頁直接打開全體歷史
function openGlobalHistory() {
    selectedTarget = ""; // 全體查詢
    
    document.getElementById('page-list').style.display = 'none';
    const inputPage = document.getElementById('page-input');
    inputPage.style.display = 'flex'; 
    
    const drawer = document.getElementById('history-drawer');
    drawer.classList.add('open');
    
    document.getElementById('history-title-name').innerText = "全體歷史紀錄";
    fetchHistory();
}

// 💡 計算機內切換歷史
function toggleHistory() { 
    const drawer = document.getElementById('history-drawer');
    const isOpening = !drawer.classList.contains('open');
    
    if (isOpening) {
        drawer.classList.add('open');
        const titleText = selectedTarget ? `${selectedTarget} 的紀錄` : "全體歷史紀錄";
        document.getElementById('history-title-name').innerText = titleText;
        fetchHistory();
    } else {
        closeHistoryDrawer();
    }
}

// 💡 智慧判斷關閉動線
function closeHistoryDrawer() {
    const drawer = document.getElementById('history-drawer');
    drawer.classList.remove('open');
    
    // 如果沒有 selectedTarget，代表是從「首頁」進來的，延遲後切換回首頁
    if (!selectedTarget) {
        setTimeout(() => {
            hideInputPage();
        }, 300);
    }
}

async function fetchHistory() {
    const content = document.getElementById('history-list-content');
    const monthSelector = document.getElementById('month-selector');
    const month = monthSelector ? monthSelector.value : "";
    
    document.getElementById('history-actions-bar').style.display = 'none';
    content.innerHTML = "<p style='text-align:center; padding:20px;'>讀取中...</p>";

    try {
        const query = new URLSearchParams({
            contextId: selectedCid,
            target: selectedTarget || "", 
            month: month 
        });

        const res = await fetch(`/api/get-history?${query.toString()}`);
        const data = await res.json();
        
        if (!data.records || data.records.length === 0) {
            content.innerHTML = `<p style='text-align:center; padding:50px; color:#999;'>尚無紀錄</p>`;
            return;
        }

        content.innerHTML = data.records.map(h => `
            <div class="history-item" onclick="selectRecord(this, '${encodeURIComponent(JSON.stringify(h))}')">
                <div class="history-item-left">
                    <div style="display: flex; align-items: baseline; gap: 8px;">
                        <span style="font-size:16px; font-weight:600; color:var(--text-main);">${h.item_name}</span>
                        <span style="font-size:12px; color:var(--text-light);">${h.expense_date}</span>
                    </div>
                    <div style="font-size:12px; color:var(--primary-accent);">${h.target_name}</div>
                </div>
                <div class="history-item-right">
                    <div style="font-weight:700; font-size:20px; color:var(--primary-accent);">$${Math.round(h.amount)}</div>
                </div>
            </div>
        `).join('');
    } catch (e) { 
        content.innerHTML = "<p style='text-align:center; padding:20px;'>讀取失敗</p>"; 
    }
}

function selectRecord(el, hJson) {
    selectedRecord = JSON.parse(decodeURIComponent(hJson));
    document.querySelectorAll('.history-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('history-actions-bar').style.display = 'flex';
}

function startEditRecord() {
    if (!selectedRecord) return;
    currentEditId = selectedRecord.id;
    selectedTarget = selectedRecord.target_name; 
    formula = Math.round(selectedRecord.amount).toString();
    renderFormula();
    document.getElementById('target-title').innerText = `正在為 ${selectedTarget} 編輯紀錄`;
    document.getElementById('note-input').value = (selectedRecord.item_name === "手機即時記帳") ? "" : selectedRecord.item_name;
    
    let recordDate = new Date();
    if (selectedRecord.expense_date && selectedRecord.expense_date.includes('-')) {
        const [year, month, day] = selectedRecord.expense_date.split('-').map(Number);
        recordDate = new Date(year, month - 1, day);
    }
    
    datePicker.setDate(recordDate, true); 
    document.getElementById("date-display").innerText = formatFullDate(recordDate);
    
    const submitBtn = document.getElementById('btn-submit-record');
    submitBtn.innerText = "更新紀錄";
    submitBtn.style.background = "var(--primary-yellow)";
    
    document.getElementById('history-drawer').classList.remove('open');
    document.getElementById('page-list').style.display = 'none';
    document.getElementById('page-input').style.display = 'flex';
    document.getElementById('page-input').classList.add('active');
}

async function startDeleteRecord() {
    if (!selectedRecord) return;

    const label = selectedRecord.item_name === "手機即時記帳"
        ? `$${Math.round(selectedRecord.amount)}`
        : `${selectedRecord.item_name}（$${Math.round(selectedRecord.amount)}）`;

    if (!confirm(`確定要刪除這筆紀錄嗎？\n\n成員：${selectedRecord.target_name}\n項目：${label}\n日期：${selectedRecord.expense_date}`)) return;

    const btn = document.querySelector('.btn-delete-record');
    btn.disabled = true;
    btn.innerText = "刪除中...";

    try {
        const res = await fetch('/api/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: selectedRecord.id,
                contextId: selectedCid
            })
        });
        const result = await res.json();

        if (result.success) {
            selectedRecord = null;
            document.getElementById('history-actions-bar').style.display = 'none';
            await fetchHistory();         // 重新整理抽屜列表
            await loadMembers(selectedCid); // 更新首頁本月累計金額
        } else {
            alert("刪除失敗，請稍後再試");
        }
    } catch (e) {
        alert("刪除失敗，請檢查網路狀態");
    } finally {
        btn.disabled = false;
        btn.innerText = "刪除紀錄";
    }
}

// --- Parser 核心邏輯 ---
function calculateResult() {
    if (!formula || formula === "-") return 0; 
    try {
        let cleanFormula = formula.replace(/×/g, '*').replace(/÷/g, '/');

        const lastChar = cleanFormula.slice(-1);
        if (["+", "-", "*", "/"].includes(lastChar)) {
            cleanFormula = cleanFormula.slice(0, -1);
        }

        const res = Function('"use strict";return (' + cleanFormula + ')')();
        
        if (isNaN(res) || !isFinite(res)) return 0;

        const rounded = Math.round(res);
        formula = rounded.toString(); 
        renderFormula(); 
        return rounded;
    } catch (e) { 
        return 0; 
    }
}

function press(v) {
    if (formula === "" && (v === "0" || v === "00")) return;
    
    if (formula === "" && v === "-") {
        formula = "-";
        renderFormula();
        return;
    }

    const lastChar = formula.slice(-1);
    const ops = ["+", "-", "*", "/", "×", "÷", "."];
    
    if (ops.includes(lastChar) && ops.includes(v)) {
        formula = formula.slice(0, -1) + v;
    } else {
        formula += v;
    }
    
    renderFormula();
}

function hideInputPage() { 
    document.getElementById('page-input').style.display = 'none';
    document.getElementById('page-input').classList.remove('active'); 
    
    const listPage = document.getElementById('page-list');
    listPage.style.display = 'flex'; 
    
    window.scrollTo(0, 0); 
    
    selectedTarget = "";
    formula = "";
    currentEditId = null;
    renderFormula();
}

function setNote(val) { document.getElementById('note-input').value = val; }
function backspace() { formula = formula.slice(0, -1); renderFormula(); }
function clearFormula() { formula = ""; renderFormula(); }
function renderFormula() { 
    const display = document.getElementById('amount-display');
    display.innerText = formula === "" ? "0" : formula.replace(/\*/g, '×').replace(/\//g, '÷'); 
}

async function doCreate() {
    const input = document.getElementById('new-target-input');
    const btn = document.querySelector('.btn-add');
    const name = input.value.trim();
    if (!name) return;

    btn.disabled = true;
    btn.innerText = "...";

    try {
        await fetch('/api/add-target', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ contextId: selectedCid, target_name: name })
        });
        input.value = ""; 
        await loadMembers(selectedCid);
    } finally {
        btn.disabled = false;
        btn.innerText = "確認";
    }
}

async function doDelete(name, event) {
    event.stopPropagation();
    if (!confirm(`確定要刪除 ${name} 及其所有紀錄嗎？`)) return;
    await fetch('/api/delete-target', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ contextId: selectedCid, target_name: name })
    });
    await loadMembers(selectedCid);
}