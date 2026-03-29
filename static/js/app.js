let currentTab = 'home';
let statusInterval = null;

function showAlert(msg, type='info') {
    const box = document.getElementById('alert-box');
    box.textContent = msg;
    box.style.display = 'block';
    
    if (type === 'error') box.style.background = 'rgba(234, 42, 42, 0.2)';
    else if (type === 'success') box.style.background = 'rgba(67, 160, 71, 0.2)';
    else box.style.background = 'rgba(92, 107, 192, 0.2)';
    
    setTimeout(() => { box.style.display = 'none'; }, 4000);
}

async function switchTab(tabId) {
    if (tabId === currentTab) return;
    
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
    
    document.querySelector(`.tab-btn[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(tabId).style.display = 'block';
    currentTab = tabId;
    
    // Cleanup Prior Camera
    if (statusInterval) clearInterval(statusInterval);
    document.getElementById('reg-camera-stream').src = "";
    document.getElementById('att-camera-stream').src = "";
    
    if (tabId === 'home') {
        await fetch('/api/set_mode', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode: null}) });
    } else if (tabId === 'register') {
        await fetch('/api/set_mode', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode: null}) });
    } else if (tabId === 'attendance') {
        const res = await fetch('/api/set_mode', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode: 'attendance'}) });
        if (res.ok) {
            document.getElementById('att-camera-stream').src = "/video_feed?" + new Date().getTime();
            fetchAttendance();
            setInterval(fetchAttendance, 5000); 
        }
    }
}

async function startRegistration() {
    const id = document.getElementById('reg-id').value;
    const name = document.getElementById('reg-name').value;
    
    if (!id || !name) return showAlert('Please enter ID and Name', 'error');
    
    const res = await fetch('/api/set_mode', { 
        method: 'POST', 
        headers:{'Content-Type':'application/json'}, 
        body: JSON.stringify({mode: 'register', id: id, name: name}) 
    });
    
    const data = await res.json();
    if (data.status === 'success') {
        document.getElementById('reg-camera-stream').src = "/video_feed?" + new Date().getTime();
        statusInterval = setInterval(checkRegProgress, 500);
    } else {
        showAlert(data.message, 'error');
    }
}

async function checkRegProgress() {
    const res = await fetch('/api/status');
    const data = await res.json();
    
    if (data.mode === 'register') {
        const pct = data.sampleNum;
        document.getElementById('reg-fill').style.width = pct + '%';
        document.getElementById('reg-status').innerText = 'Capturing: ' + pct + '/100';
    } else if (data.mode === 'register_done') {
        clearInterval(statusInterval);
        document.getElementById('reg-fill').style.width = '100%';
        document.getElementById('reg-status').innerText = 'Capture Complete! You can now Train the AI.';
        document.getElementById('reg-camera-stream').src = "";
        showAlert('Face modeling complete!', 'success');
    }
}

async function trainProfile() {
    showAlert('Training LBPH Recognizer... please wait.', 'info');
    const res = await fetch('/api/train', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({}) });
    const data = await res.json();
    if (data.status === 'success') {
        showAlert(data.message, 'success');
        document.getElementById('reg-id').value = "";
        document.getElementById('reg-name').value = "";
        document.getElementById('reg-fill').style.width = '0%';
        document.getElementById('reg-status').innerText = 'Ready for enrollment.';
    } else {
        showAlert(data.message, 'error');
    }
}

async function markAttendance() {
    const res = await fetch('/api/mark_attendance', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'success') {
        showAlert(data.message, 'success');
        fetchAttendance();
    } else {
        showAlert(data.message, 'error');
    }
}

async function fetchAttendance() {
    if (currentTab !== 'attendance') return;
    const res = await fetch('/api/get_attendance');
    const data = await res.json();
    if (data.status === 'success') {
        const tbody = document.getElementById('attendance-tbody');
        tbody.innerHTML = '';
        data.data.forEach(row => {
            tbody.innerHTML += `<tr><td>${row.id}</td><td>${row.name}</td><td>${row.date}</td><td>${row.time}</td></tr>`;
        });
    }
}

async function exportExcel() {
    const res = await fetch('/api/export');
    const data = await res.json();
    if (data.status === 'success') showAlert(data.message, 'success');
    else showAlert(data.message, 'error');
}
