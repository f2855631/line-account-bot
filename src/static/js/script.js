let selectedCid = ""; 
let selectedTarget = "";
let formula = "";
let datePicker = null; 
let currentEditId = null; 
let selectedRecord = null; 
let isHistoryMode = false;

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

async function init(liffId) {
    selectedCid = localStorage.getItem('last_book_id') || "";
    document.getElementById("date-display").innerText = formatFullDate(new Date());
    
    datePicker = flatpickr("#date-picker-trigger", {
        wrap: true, static: true, locale: "zh_tw", defaultDate: "today", disableMobile: "true",
        onChange: (selectedDates) => { 
            if(selectedDates.length) {
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
        selectedCid = urlParams.get('bookId') || (context ? (context.groupId || context.userId) : selectedCid);
        
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

async function loadMembers(cid) {
    const container = document.getElementById('nameListContainer');
    const cached = localStorage.getItem(`members_${cid}`);

    if (!isHistoryMode) {
        if (cached) renderMemberList(JSON.parse(cached));
    }

    try {
        const res = await fetch(`/api/get-members?contextId=${cid}&t=${Date.now()}`);
        const data = await res.json();
        const members = data.members || [];
        localStorage.setItem(`members_${cid}`, JSON.stringify(members));
        if (!isHistoryMode) renderMemberList(members);
    } catch (e) { 
        if (!cached && !isHistoryMode) container.innerHTML = "讀取失敗，請檢查網路"; 
    }
}

const AVATAR_COLORS = ['#88C170','#FFBD59','#CC8899','#7BA7CC','#C17088','#88A4C1','#B8CC70','#CC7059'];
function getAvatarColor(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function toggleCardActions(cardId) {
    const actions = document.getElementById(cardId);
    if (!actions) return;
    document.querySelectorAll('.name-card-actions.open').forEach(el => {
        if (el.id !== cardId) el.classList.remove('open');
    });
    actions.classList.toggle('open');
}

function renderMemberList(members) {
    const container = document.getElementById('nameListContainer');
    container.innerHTML = members.map((m, idx) => {
        const color = getAvatarColor(m.target_name);
        const firstChar = m.target_name.charAt(0);
        const cardId = `card-actions-${idx}`;
        return `
        <div class="name-card">
            <div class="name-card-main" onclick="showInputPage('${m.target_name}')">
                <div class="member-avatar" style="background:${color};">${firstChar}</div>
                <div class="name-info">
                    <span class="name-text">${m.target_name}</span>
                    <span class="month-total">本月累積 $${Math.round(m.amount || 0)}</span>
                </div>
                <button class="record-btn" onclick="event.stopPropagation(); showInputPage('${m.target_name}')">記帳</button>
                <button class="more-btn" onclick="event.stopPropagation(); toggleCardActions('${cardId}')">⋯</button>
            </div>
            <div class="name-card-actions" id="${cardId}">
                <button class="action-btn-rename" onclick="doRename('${m.target_name}', event)">改名</button>
                <button class="action-btn-delete" onclick="doDelete('${m.target_name}', event)">刪除</button>
            </div>
        </div>`;
    }).join('') || "<p style='text-align:center; padding:20px; color:#888;'>尚未建立成員</p>";
}

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
                clearFormula();
                document.getElementById('note-input').value = "";
                showToast(`✅ 成功記帳 $${amount}`);
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

function initMonthSelector() {
    const selector = document.getElementById('month-selector');
    if (!selector) return;

    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    selector.innerHTML = '<option value="">全部</option>';

    for (let i = 0; i < 24; i++) {
        let y = currentYear;
        let m = currentMonth - i;
        while (m <= 0) { m += 12; y -= 1; }
        const monthStr = String(m).padStart(2, '0');
        const option = document.createElement('option');
        option.value = `${y}-${monthStr}`;
        option.textContent = `${y}年 ${m}月`;
        selector.appendChild(option);
    }

    selector.value = `${currentYear}-${String(currentMonth).padStart(2, '0')}`;
}

async function fetchHistory() {
    const content = document.getElementById('history-list-content');
    const monthSelector = document.getElementById('month-selector');
    const month = monthSelector ? monthSelector.value : "";
    
    document.getElementById('history-actions-bar').style.display = 'none';
    content.innerHTML = "<p style='text-align:center; padding:20px;'>讀取中...</p>";

    try {
        const query = new URLSearchParams({ contextId: selectedCid, target: selectedTarget || "", month: month });
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
    document.getElementById('note-input').value = (selectedRecord.item_name === "手機即時記帳" || selectedRecord.item_name === "一般消費") ? "" : selectedRecord.item_name;

    let recordDate = new Date();
    if (selectedRecord.expense_date && selectedRecord.expense_date.includes('-')) {
        const [year, month, day] = selectedRecord.expense_date.split('-').map(Number);
        recordDate = new Date(year, month - 1, day);
    }

    datePicker.setDate(recordDate, true);
    document.getElementById("date-display").innerText = formatFullDate(recordDate);

    const okBtn = document.getElementById('btn-ok');
    if (okBtn) { okBtn.innerText = "更新"; okBtn.classList.add('edit-mode'); okBtn.disabled = false; }

    document.documentElement.classList.remove('history-mode');
    document.getElementById('history-drawer').classList.remove('open');
    document.getElementById('drawer-overlay').classList.remove('active');
    document.getElementById('page-list').style.display = 'none';
    document.getElementById('page-input').style.display = 'flex';
    document.getElementById('page-input').classList.add('active');
}

async function startDeleteRecord() {
    if (!selectedRecord) return;

    const label = selectedRecord.item_name === "手機即時記帳"
        ? `$${Math.round(selectedRecord.amount)}`
        : `${selectedRecord.item_name}（$${Math.round(selectedRecord.amount)}）`;

    const confirmed = await showConfirm(`確定要刪除這筆紀錄？\n成員：${selectedRecord.target_name}\n項目：${label}\n日期：${selectedRecord.expense_date}`);
    if (!confirmed) return;

    const btn = document.querySelector('.btn-delete-record');
    btn.disabled = true;
    btn.innerText = "刪除中...";

    try {
        const res = await fetch('/api/delete', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: selectedRecord.id, contextId: selectedCid })
        });
        const result = await res.json();

        if (result.success) {
            selectedRecord = null;
            document.getElementById('history-actions-bar').style.display = 'none';
            await fetchHistory();
            await loadMembers(selectedCid);
            showToast("紀錄已刪除");
        } else {
            showToast("刪除失敗，請稍後再試", true);
        }
    } catch (e) {
        showToast("刪除失敗，請檢查網路狀態", true);
    } finally {
        btn.disabled = false;
        btn.innerText = "刪除紀錄";
    }
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

function hideInputPage() { 
    document.getElementById('page-input').style.display = 'none';
    document.getElementById('page-input').classList.remove('active'); 
    document.getElementById('page-list').style.display = 'flex'; 
    window.scrollTo(0, 0); 
    selectedTarget = ""; formula = ""; currentEditId = null;
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
        const res = await fetch('/api/add-target', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ contextId: selectedCid, target_name: name })
        });
        const result = await res.json();
        if (result.success) {
            input.value = "";
            await loadMembers(selectedCid);
            showToast(`「${name}」已成功新增`);
        } else {
            showToast("新增失敗，請稍後再試", true);
        }
    } catch (e) {
        showToast("新增失敗，請檢查網路狀態", true);
    } finally {
        btn.disabled = false;
        btn.innerText = "確認";
    }
}

function showConfirm(message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:99998;display:flex;justify-content:center;align-items:center;';
        const box = document.createElement('div');
        box.style.cssText = 'background:white;border-radius:16px;padding:24px;width:80%;max-width:320px;box-shadow:0 10px 30px rgba(0,0,0,0.2);';
        const msgDiv = document.createElement('div');
        msgDiv.style.cssText = 'font-size:15px;line-height:1.8;color:#4A4A4A;margin-bottom:16px;';
        message.split('\n').forEach(line => {
            const d = document.createElement('div');
            d.innerText = line;
            msgDiv.appendChild(d);
        });
        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:10px;margin-top:16px;';
        const cancelBtn = document.createElement('button');
        cancelBtn.innerText = '取消';
        cancelBtn.style.cssText = 'flex:1;padding:12px;border:1.5px solid #E8E7E3;border-radius:10px;background:white;color:#8E8E8E;font-size:15px;font-weight:600;';
        const confirmBtn = document.createElement('button');
        confirmBtn.innerText = '確定';
        confirmBtn.style.cssText = 'flex:1;padding:12px;border:none;border-radius:10px;background:#CC6666;color:white;font-size:15px;font-weight:600;';
        btnRow.appendChild(cancelBtn);
        btnRow.appendChild(confirmBtn);
        box.appendChild(msgDiv);
        box.appendChild(btnRow);
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        confirmBtn.onclick = () => { overlay.remove(); resolve(true); };
        cancelBtn.onclick = () => { overlay.remove(); resolve(false); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(false); } };
    });
}

function showDialog(title, defaultValue = "") {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:99998;display:flex;justify-content:center;align-items:center;';
        const box = document.createElement('div');
        box.style.cssText = 'background:white;border-radius:16px;padding:24px;width:80%;max-width:320px;box-shadow:0 10px 30px rgba(0,0,0,0.2);';
        const titleDiv = document.createElement('div');
        titleDiv.innerText = title;
        titleDiv.style.cssText = 'font-size:16px;font-weight:600;color:#4A4A4A;margin-bottom:16px;text-align:center;';
        const input = document.createElement('input');
        input.type = 'text';
        input.value = defaultValue;
        input.style.cssText = 'width:100%;box-sizing:border-box;border:1.5px solid #E8E7E3;border-radius:8px;padding:10px 12px;font-size:15px;outline:none;color:#4A4A4A;margin-bottom:16px;';
        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:10px;';
        const cancelBtn = document.createElement('button');
        cancelBtn.innerText = '取消';
        cancelBtn.style.cssText = 'flex:1;padding:12px;border:1.5px solid #E8E7E3;border-radius:10px;background:white;color:#8E8E8E;font-size:15px;font-weight:600;';
        const confirmBtn = document.createElement('button');
        confirmBtn.innerText = '確認';
        confirmBtn.style.cssText = 'flex:1;padding:12px;border:none;border-radius:10px;background:#88C170;color:white;font-size:15px;font-weight:600;';
        btnRow.appendChild(cancelBtn);
        btnRow.appendChild(confirmBtn);
        box.appendChild(titleDiv);
        box.appendChild(input);
        box.appendChild(btnRow);
        overlay.appendChild(box);
        document.body.appendChild(overlay);
        setTimeout(() => { input.focus(); }, 100);
        confirmBtn.onclick = () => { const val = input.value.trim(); overlay.remove(); resolve(val || null); };
        cancelBtn.onclick = () => { overlay.remove(); resolve(null); };
        overlay.onclick = (e) => { if (e.target === overlay) { overlay.remove(); resolve(null); } };
        input.onkeydown = (e) => { if (e.key === 'Enter') { const val = input.value.trim(); overlay.remove(); resolve(val || null); } };
    });
}

function showToast(msg, isError = false) {
    const existing = document.getElementById('toast-msg');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.id = 'toast-msg';
    toast.innerText = msg;
    toast.style.cssText = `position:fixed;bottom:100px;left:50%;transform:translateX(-50%);background:${isError ? '#CC6666' : '#88C170'};color:white;padding:10px 20px;border-radius:20px;font-size:14px;font-weight:600;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.15);opacity:1;transition:opacity 0.4s ease;`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 400); }, 2000);
}

async function doRename(oldName, event) {
    event.stopPropagation();
    event.preventDefault();
    const newName = await showDialog(`請輸入「${oldName}」的新名稱`, oldName);
    if (!newName || !newName.trim()) return;
    if (newName.trim() === oldName) return;

    try {
        const res = await fetch('/api/rename-target', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ contextId: selectedCid, old_name: oldName, new_name: newName.trim() })
        });
        const result = await res.json();
        if (result.success) {
            localStorage.removeItem(`members_${selectedCid}`);
            await loadMembers(selectedCid);
            showToast(`已將「${oldName}」改名為「${newName.trim()}」`);
        } else {
            showToast("改名失敗，請稍後再試", true);
        }
    } catch (e) {
        showToast("改名失敗，請檢查網路狀態", true);
    }
}

async function doDelete(name, event) {
    event.stopPropagation();
    const confirmed = await showConfirm(`確定要刪除「${name}」及其所有紀錄？`);
    if (!confirmed) return;
    await fetch('/api/delete-target', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ contextId: selectedCid, target_name: name })
    });
    localStorage.removeItem(`members_${selectedCid}`);
    await loadMembers(selectedCid);
}