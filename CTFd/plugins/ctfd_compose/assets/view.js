CTFd._internal.challenge.data = undefined;
CTFd._internal.challenge.renderer = null;
CTFd._internal.challenge.preRender = function () {};
CTFd._internal.challenge.render = null;

let composeTimerInterval = null;

if (window.$ === undefined && CTFd.lib && CTFd.lib.$) {
    window.$ = CTFd.lib.$;
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function showAlert(title, html) {
    if (CTFd._functions && CTFd._functions.events && CTFd._functions.events.eventAlert) {
        CTFd._functions.events.eventAlert({ title: title, html: html, button: "OK" });
    } else {
        alert(`${title}: ${html}`);
    }
}

function loadContainerInfo() {
    if (!CTFd._internal.challenge.data || !CTFd._internal.challenge.data.id) return;
    const challengeId = CTFd._internal.challenge.data.id;
    const url = `/api/v1/plugins/ctfd_compose/container?challenge_id=${challengeId}`;

    $('#compose-loading').show();
    $('#compose-stopped').hide();
    $('#compose-running').hide();

    CTFd.fetch(url, {
        method: 'GET',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(res => {
        $('#compose-loading').hide();
        if (composeTimerInterval) {
            clearInterval(composeTimerInterval);
            composeTimerInterval = null;
        }

        if (res.success && res.data && res.data.status === 'running') {
            const data = res.data;
            $('#compose-badge').removeClass('bg-secondary bg-danger bg-light text-dark').addClass('bg-success text-white').text('Running');
            $('#compose-connection-input').val(data.connection);

            if (data.redirect_type === 'http') {
                $('#compose-link-open').attr('href', data.connection).show();
            } else {
                $('#compose-link-open').hide();
            }

            $('#compose-renews-left').text(data.renews_left);
            if (data.renews_left <= 0) {
                $('#compose-btn-renew').prop('disabled', true);
            } else {
                $('#compose-btn-renew').prop('disabled', false);
            }

            let remaining = data.remaining_time;
            $('#compose-timer').text(formatTime(remaining));

            composeTimerInterval = setInterval(() => {
                remaining -= 1;
                if (remaining <= 0) {
                    clearInterval(composeTimerInterval);
                    composeTimerInterval = null;
                    loadContainerInfo();
                } else {
                    $('#compose-timer').text(formatTime(remaining));
                }
            }, 1000);

            $('#compose-stopped').hide();
            $('#compose-running').show();
        } else {
            $('#compose-badge').removeClass('bg-success text-white').addClass('bg-secondary text-white').text('Stopped');
            $('#compose-running').hide();
            $('#compose-stopped').show();
        }
    })
    .catch(err => {
        $('#compose-loading').hide();
        $('#compose-stopped').show();
        console.error("Error fetching container info:", err);
    });
}

CTFd._internal.challenge.postRender = function () {
    loadContainerInfo();
};

CTFd._internal.challenge.startContainer = function () {
    if (!CTFd._internal.challenge.data || !CTFd._internal.challenge.data.id) return;
    const challengeId = CTFd._internal.challenge.data.id;
    const url = `/api/v1/plugins/ctfd_compose/container`;

    $('#compose-stopped').hide();
    $('#compose-loading-text').text("Deploying container via docker compose...");
    $('#compose-loading').show();

    CTFd.fetch(url, {
        method: 'POST',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challengeId })
    })
    .then(r => r.json())
    .then(res => {
        $('#compose-loading').hide();
        if (res.success) {
            loadContainerInfo();
            showAlert("Success", "Your container instance has been deployed!");
        } else {
            showAlert("Error", res.message || "Failed to launch container");
            loadContainerInfo();
        }
    })
    .catch(err => {
        $('#compose-loading').hide();
        showAlert("Error", "Network or server error while starting container.");
        loadContainerInfo();
    });
};

CTFd._internal.challenge.renewContainer = function () {
    if (!CTFd._internal.challenge.data || !CTFd._internal.challenge.data.id) return;
    const challengeId = CTFd._internal.challenge.data.id;
    const url = `/api/v1/plugins/ctfd_compose/container`;

    $('#compose-btn-renew').prop('disabled', true).text("Renewing...");

    CTFd.fetch(url, {
        method: 'PATCH',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challengeId })
    })
    .then(r => r.json())
    .then(res => {
        $('#compose-btn-renew').prop('disabled', false);
        if (res.success) {
            loadContainerInfo();
            showAlert("Success", res.message || "Container duration extended!");
        } else {
            showAlert("Error", res.message || "Failed to renew container.");
            loadContainerInfo();
        }
    })
    .catch(err => {
        $('#compose-btn-renew').prop('disabled', false);
        showAlert("Error", "Network error while renewing container.");
    });
};

CTFd._internal.challenge.destroyContainer = function () {
    if (!CTFd._internal.challenge.data || !CTFd._internal.challenge.data.id) return;
    if (!confirm("Are you sure you want to stop and destroy this container instance?")) return;

    const challengeId = CTFd._internal.challenge.data.id;
    const url = `/api/v1/plugins/ctfd_compose/container`;

    $('#compose-running').hide();
    $('#compose-loading-text').text("Stopping container...");
    $('#compose-loading').show();

    CTFd.fetch(url, {
        method: 'DELETE',
        headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challengeId })
    })
    .then(r => r.json())
    .then(res => {
        $('#compose-loading').hide();
        if (res.success) {
            loadContainerInfo();
            showAlert("Success", "Your container has been destroyed.");
        } else {
            showAlert("Error", res.message || "Failed to stop container.");
            loadContainerInfo();
        }
    })
    .catch(err => {
        $('#compose-loading').hide();
        showAlert("Error", "Network error while stopping container.");
        loadContainerInfo();
    });
};

CTFd._internal.challenge.copyConn = function () {
    const input = document.getElementById("compose-connection-input");
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value).then(() => {
        const btn = document.getElementById("compose-btn-copy");
        if (btn) {
            const original = btn.innerHTML;
            btn.innerHTML = `<i class="fas fa-check text-success"></i>`;
            setTimeout(() => { btn.innerHTML = original; }, 1500);
        }
    });
};

CTFd._internal.challenge.submit = function (preview) {
    const challengeId = CTFd._internal.challenge.data.id;
    const submission = $('#challenge-input').val();

    const body = {
        'challenge_id': challengeId,
        'submission': submission,
    };
    const params = {};
    if (preview) params['preview'] = true;

    return CTFd.api.post_challenge_attempt(params, body).then(function (response) {
        return response;
    });
};
