// ============================================================
// UI Helpers：Toast 通知、確認對話框、輸入對話框
// ============================================================

function showToast(msg, isError = false) {
    const existing = document.getElementById('toast-msg');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.id = 'toast-msg';
    toast.innerText = msg;
    toast.style.cssText = `position:fixed;top:30px;left:50%;transform:translateX(-50%);background:${isError ? '#CC6666' : '#88C170'};color:white;padding:14px 28px;border-radius:24px;font-size:17px;font-weight:700;z-index:9999;box-shadow:0 6px 20px rgba(0,0,0,0.25);opacity:1;transition:opacity 0.4s ease;white-space:nowrap;`;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 400); }, 2000);
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
