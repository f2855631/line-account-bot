// ============================================================
// Members：成員列表渲染、新增、改名、刪除
// 依賴全域變數：selectedCid（定義於 script.js）
// ============================================================

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
                <div class="card-btn-group">
                    <button class="query-btn" onclick="event.stopPropagation(); openIndividualHistory('${m.target_name}')">查帳</button>
                    <button class="record-btn" onclick="event.stopPropagation(); showInputPage('${m.target_name}')">記帳</button>
                    <button class="more-btn" onclick="event.stopPropagation(); toggleCardActions('${cardId}')">⋯</button>
                </div>
            </div>
            <div class="name-card-actions" id="${cardId}">
                <button class="action-btn-rename" onclick="doRename('${m.target_name}', event)">改名</button>
                <button class="action-btn-delete" onclick="doDelete('${m.target_name}', event)">刪除</button>
            </div>
        </div>`;
    }).join('') || "<p style='text-align:center; padding:20px; color:#888;'>尚未建立成員</p>";
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
