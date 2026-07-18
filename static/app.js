let ws = null;
let currentUser = null;

function setUser() {
    const userId = document.getElementById('userId').value.trim() || 'user-' + Date.now();
    document.getElementById('userId').value = userId;
    currentUser = userId;
    document.getElementById('userBadge').textContent = userId;
    document.getElementById('userBadge').style.display = 'inline-block';
    document.getElementById('afterLogin').style.display = 'block';
    connectWebSocket();
    loadDIDs();
    loadMyDID();
    refreshSimDidSelect();
}

function connectWebSocket() {
    if (ws) { ws.close(); }
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(protocol + '//' + location.host + '/api/ws/' + currentUser);

    ws.onopen = function () { updateWSStatus('connected'); };
    ws.onclose = function () {
        updateWSStatus('disconnected');
        setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = function () { updateWSStatus('disconnected'); };
    ws.onmessage = function (event) {
        var msg = JSON.parse(event.data);
        handleWSEvent(msg);
    };

    setInterval(function () {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 30000);
}

function updateWSStatus(state) {
    var dot = document.getElementById('wsDot');
    var text = document.getElementById('wsStatus');
    dot.className = 'dot';
    if (state === 'connected') {
        dot.classList.add('connected');
        text.textContent = 'Bağli';
    } else if (state === 'connecting') {
        dot.classList.add('connecting');
        text.textContent = 'Bağlaniyor...';
    } else {
        dot.classList.add('disconnected');
        text.textContent = 'Bağlanti Kesik';
    }
}

function loadDIDs() {
    var el = document.getElementById('didList');
    fetch('/api/did/')
        .then(function (r) { return r.json(); })
        .then(function (dids) {
            if (dids.length === 0) {
                el.innerHTML = '<div class="empty">Müsait numara yok</div>';
                return;
            }
            el.innerHTML = '<div class="did-grid">' +
                dids.map(function (d) {
                    return '<div class="did-card" onclick="allocateDID(\'' + d.number + '\')">' +
                        '<div class="number">' + d.number + '</div>' +
                        '<span class="status-badge ' + d.status + '">' + d.status + '</span></div>';
                }).join('') + '</div>';
            refreshSimDidSelect();
        })
        .catch(function (e) { el.innerHTML = '<div class="empty">Yüklenemedi: ' + e.message + '</div>'; });
}

function allocateDID(number) {
    fetch('/api/did/allocate?user_id=' + encodeURIComponent(currentUser), { method: 'POST' })
        .then(function (r) {
            if (!r.ok) throw new Error('Talep başarisiz');
            return r.json();
        })
        .then(function (did) {
            loadDIDs();
            loadMyDID();
            addEvent('system', did.number + ' numarasi size tahsis edildi');
        })
        .catch(function (e) { addEvent('system', 'Tahsis hatasi: ' + e.message); });
}

function loadMyDID() {
    var el = document.getElementById('myDid');
    fetch('/api/did/my/' + encodeURIComponent(currentUser))
        .then(function (r) {
            if (!r.ok) throw new Error('No DID');
            return r.json();
        })
        .then(function (did) {
            el.innerHTML = '<div class="selected-did">' +
                '<div class="label">TAHSIS EDILEN NUMARA</div>' +
                '<div class="num">' + did.number + '</div>' +
                '<div style="margin-top:1rem">' +
                '<button class="btn danger" onclick="releaseDID(\'' + did.number + '\')">Numarayi Serbest Birak</button>' +
                '</div></div>';
            refreshSimDidSelect();
        })
        .catch(function () {
            el.innerHTML = '<div class="empty">Henüz bir numara seçmediniz.</div>';
        });
}

function releaseDID(number) {
    fetch('/api/did/release/' + encodeURIComponent(number), { method: 'POST' })
        .then(function () {
            loadDIDs();
            loadMyDID();
            addEvent('system', number + ' serbest birakildi');
        })
        .catch(function (e) { addEvent('system', 'Serbest birakma hatasi: ' + e.message); });
}

function handleWSEvent(msg) {
    switch (msg.event) {
        case 'call_incoming':
            addEvent('call', 'Gelen çağri: ' + msg.data.from);
            break;
        case 'sms_received':
            addEvent('sms', 'SMS alindi: ' + msg.data.content);
            if (msg.data.code) {
                addEvent('code', 'Dogrulama kodu: <span class="code">' + msg.data.code + '</span>');
            }
            break;
        case 'pong':
            break;
    }
}

var eventId = 0;
function addEvent(type, html) {
    var log = document.getElementById('eventLog');
    var iconMap = { call: '📞', sms: '✉️', code: '🔑', system: '⚙️' };
    var clsMap = { call: 'call', sms: 'sms', code: 'code', system: 'system' };

    var child = document.createElement('div');
    child.className = 'event';
    child.innerHTML = '<div class="event-icon ' + (clsMap[type] || 'system') + '">' + (iconMap[type] || '⚙️') + '</div>' +
        '<div class="event-details">' +
        '<div class="time">' + new Date().toLocaleTimeString('tr-TR') + '</div>' +
        '<div class="desc">' + html + '</div></div>';

    var empty = log.querySelector('.empty');
    if (empty) empty.remove();

    log.prepend(child);

    while (log.children.length > 100) log.removeChild(log.lastChild);
}

function simulateSms() {
    var from = document.getElementById('simSmsFrom').value || '+905551234567';
    var text = document.getElementById('simSmsText').value || 'Dogrulama kodunuz: 482916';

    fetch('/api/did/my/' + encodeURIComponent(currentUser))
        .then(function (r) {
            if (!r.ok) throw new Error('Once bir DID numarasi tahsis edin');
            return r.json();
        })
        .then(function (did) {
            var payload = {
                from: from,
                to: did.number,
                text: text,
                call_id: 'sim-sms-' + Date.now()
            };
            return fetch('/api/webhook/incoming', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        })
        .then(function (r) { return r.json(); })
        .then(function () { addEvent('system', 'SMS gonderildi (simulasyon)'); })
        .catch(function (e) { addEvent('system', 'SMS simulasyon hatasi: ' + e.message); });
}

function simulateCall() {
    var from = document.getElementById('simCallFrom').value || '+905551234567';
    var to = document.getElementById('simCallDid').value;

    if (!to) {
        fetch('/api/did/my/' + encodeURIComponent(currentUser))
            .then(function (r) {
                if (!r.ok) throw new Error('Once bir DID numarasi tahsis edin');
                return r.json();
            })
            .then(function (did) { return did.number; })
            .then(function (num) { doSimulateCall(from, num); })
            .catch(function (e) { addEvent('system', 'Cagri simulasyon hatasi: ' + e.message); });
    } else {
        doSimulateCall(from, to);
    }
}

function doSimulateCall(from, to) {
    var payload = {
        from: from,
        to: to,
        call_id: 'sim-call-' + Date.now()
    };
    fetch('/api/webhook/incoming', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(function (r) { return r.json(); })
        .then(function () { addEvent('system', 'Cagri gonderildi (simulasyon)'); })
        .catch(function (e) { addEvent('system', 'Cagri simulasyon hatasi: ' + e.message); });
}

function refreshSimDidSelect() {
    var sel = document.getElementById('simCallDid');
    fetch('/api/did/')
        .then(function (r) { return r.json(); })
        .then(function (dids) {
            sel.innerHTML = '<option value="">— Mevcut DID\'ler —</option>' +
                dids.filter(function (d) { return d.status === 'available'; })
                    .map(function (d) {
                        return '<option value="' + d.number + '">' + d.number + ' (' + d.status + ')</option>';
                    }).join('');
        })
        .catch(function () {});
}

document.addEventListener('DOMContentLoaded', function () {
    updateWSStatus('connecting');
    setUser();
});
