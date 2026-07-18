let ws = null;
let selectedNumber = null;
let messageCache = [];

function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(protocol + '//' + location.host + '/api/ws/user');

    ws.onopen = function () { updateStatus('connected'); };
    ws.onclose = function () { updateStatus('disconnected'); setTimeout(connectWS, 3000); };
    ws.onerror = function () { updateStatus('disconnected'); };
    ws.onmessage = function (e) {
        var msg = JSON.parse(e.data);
        if (msg.event === 'sms_received') {
            addSMS(msg.data);
        }
    };
    setInterval(function () { if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 30000);
}

function updateStatus(state) {
    var dot = document.getElementById('wsDot');
    var txt = document.getElementById('wsStatus');
    dot.className = 'dot';
    if (state === 'connected') {
        dot.classList.add('connected');
        txt.textContent = 'Bağlı';
    } else if (state === 'connecting') {
        dot.classList.add('connecting');
        txt.textContent = 'Bağlanıyor...';
    } else {
        dot.classList.add('disconnected');
        txt.textContent = 'Bağlantı Kesik';
    }
}

// --- Providers ---
function loadProviders() {
    fetch('/api/sms/providers')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var sel = document.getElementById('providerSelect');
            sel.innerHTML = data.providers.map(function (p) {
                var selected = p === data.active ? 'selected' : '';
                return '<option value="' + p + '" ' + selected + '>' + p + '</option>';
            }).join('');
            document.getElementById('providerStatus').textContent = '✓ ' + data.active;
        });
}

function onProviderChange() {
    var name = document.getElementById('providerSelect').value;
    if (!name) return;
    fetch('/api/sms/provider?name=' + encodeURIComponent(name), { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function () {
            document.getElementById('providerStatus').textContent = '✓ ' + name;
            loadCountries();
            releaseNumber();
        });
}

// --- Countries ---
function loadCountries() {
    var sel = document.getElementById('countrySelect');
    sel.innerHTML = '<option value="">Yükleniyor...</option>';
    sel.disabled = true;
    fetch('/api/sms/countries')
        .then(function (r) { return r.json(); })
        .then(function (countries) {
            sel.innerHTML = '<option value="">— Ülke Seçin —</option>' +
                countries.map(function (c) {
                    return '<option value="' + c.code + '">' + (c.flag || '') + ' ' + c.name + ' (+' + c.code + ')</option>';
                }).join('');
            sel.disabled = false;
        })
        .catch(function () {
            sel.innerHTML = '<option value="">Yüklenemedi</option>';
        });
}

function onCountryChange() {
    var code = document.getElementById('countrySelect').value;
    var numSel = document.getElementById('numberSelect');
    var btn = document.getElementById('selectBtn');
    if (!code) {
        numSel.innerHTML = '<option value="">Önce ülke seçin</option>';
        numSel.disabled = true;
        btn.disabled = true;
        return;
    }
    numSel.innerHTML = '<option value="">Numaralar yükleniyor...</option>';
    numSel.disabled = true;
    btn.disabled = true;

    fetch('/api/sms/numbers?country=' + encodeURIComponent(code))
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.numbers || data.numbers.length === 0) {
                numSel.innerHTML = '<option value="">Bu ülkede numara yok</option>';
                return;
            }
            numSel.innerHTML = data.numbers.map(function (n) {
                return '<option value="' + n + '">' + n + '</option>';
            }).join('');
            numSel.disabled = false;
            btn.disabled = false;
        })
        .catch(function () {
            numSel.innerHTML = '<option value="">Yüklenemedi</option>';
        });
}

// --- Number Selection ---
function selectNumber() {
    var num = document.getElementById('numberSelect').value;
    if (!num) return;
    selectedNumber = num;

    fetch('/api/sms/select?number=' + encodeURIComponent(num), { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function () {
            document.getElementById('displayNumber').textContent = num;
            document.getElementById('displayCountry').textContent = 'Hazır — Siteye bu numarayı girin';
            document.getElementById('displayBadge').innerHTML = '<span class="provider-badge">🔔 SMS bekleniyor</span>';
            document.getElementById('selectBtn').style.display = 'none';
            document.getElementById('releaseBtn').style.display = 'inline-block';
            document.getElementById('numberSelect').disabled = true;
            document.getElementById('countrySelect').disabled = true;
            loadMessages();
        });
}

function releaseNumber() {
    selectedNumber = null;
    document.getElementById('displayNumber').textContent = '—';
    document.getElementById('displayCountry').textContent = 'Bir ülke ve numara seçin';
    document.getElementById('displayBadge').innerHTML = '';
    document.getElementById('selectBtn').style.display = 'inline-block';
    document.getElementById('selectBtn').disabled = false;
    document.getElementById('releaseBtn').style.display = 'none';
    document.getElementById('numberSelect').disabled = false;
    document.getElementById('countrySelect').disabled = false;
    onCountryChange();
}

// --- Messages ---
function loadMessages() {
    fetch('/api/sms/messages')
        .then(function (r) { return r.json(); })
        .then(function (msgs) {
            messageCache = msgs;
            renderMessages();
        });
}

function renderMessages() {
    var chat = document.getElementById('smsChat');
    chat.innerHTML = '';
    messageCache.forEach(function (msg) {
        appendMessage(msg, false);
    });
    scrollToBottom();
    document.getElementById('msgCount').textContent = messageCache.length;
}

function addSMS(data) {
    messageCache.push(data);
    appendMessage(data, true);
    scrollToBottom();
    document.getElementById('msgCount').textContent = messageCache.length;
}

function appendMessage(data, animate) {
    var chat = document.getElementById('smsChat');
    var code = data.code || data.code_only || '';

    var div = document.createElement('div');
    div.className = 'sms-msg incoming';
    if (animate) div.style.animation = 'fadeIn 0.3s ease';

    var senderDisplay = data.from || data.sender || 'Bilinmeyen';
    var time = data.received_at ? new Date(data.received_at).toLocaleTimeString('tr-TR') : new Date().toLocaleTimeString('tr-TR');

    var html = '<div class="bubble">';
    html += '<span class="sender-tag">' + escapeHtml(senderDisplay) + '</span> ';
    html += escapeHtml(data.content || data.text || '(içerik yok)');
    if (code) {
        html += '<div class="code-badge">' + escapeHtml(code) + '</div>';
    }
    html += '</div>';
    html += '<div class="meta"><span>' + time + '</span>';
    if (data.provider) html += '<span>· ' + data.provider + '</span>';
    html += '</div>';

    div.innerHTML = html;
    chat.appendChild(div);

    // Remove empty state if present
    var empty = chat.querySelector('.empty-state');
    if (empty) empty.remove();
}

function scrollToBottom() {
    var chat = document.getElementById('smsChat');
    setTimeout(function () { chat.scrollTop = chat.scrollHeight; }, 50);
}

function clearMessages() {
    messageCache = [];
    var chat = document.getElementById('smsChat');
    chat.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>SMS bekleniyor...</p></div>';
    document.getElementById('msgCount').textContent = '0';
}

function escapeHtml(text) {
    if (!text) return '';
    var d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

// Poll for messages every 5 seconds when a number is selected
setInterval(function () {
    if (selectedNumber) loadMessages();
}, 5000);

// Init
document.addEventListener('DOMContentLoaded', function () {
    updateStatus('connecting');
    connectWS();
    loadProviders();
    loadCountries();
});
