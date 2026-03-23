// ============================================================
// History：歷史紀錄查詢、選取、編輯、刪除
// 依賴全域變數：selectedCid, selectedTarget, datePicker,
//               currentEditId, formula（定義於 script.js）
// ============================================================

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
