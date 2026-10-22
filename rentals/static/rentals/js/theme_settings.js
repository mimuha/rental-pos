(function () {
    'use strict';

    var settings = document.getElementById('rental-theme-settings');
    if (!settings) return;

    var root = document.documentElement;
    var endpoint = settings.dataset.themeEndpoint;
    var modeButtons = settings.querySelectorAll('[data-theme-mode]');
    var accentButtons = settings.querySelectorAll('[data-theme-accent]');

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    function csrfToken() {
        return getCookie('csrftoken')
            || (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value
            || '';
    }

    function setPressed(buttons, attribute, value) {
        Array.prototype.forEach.call(buttons, function (button) {
            button.setAttribute('aria-pressed', button.dataset[attribute] === value ? 'true' : 'false');
        });
    }

    function apply(mode, accent) {
        root.dataset.theme = mode;
        root.dataset.accent = accent;
        setPressed(modeButtons, 'themeMode', mode);
        setPressed(accentButtons, 'themeAccent', accent);
    }

    function save(mode, accent) {
        if (!endpoint) return;

        fetch(endpoint, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken()
            },
            body: JSON.stringify({mode: mode, accent: accent})
        }).then(function (response) {
            if (!response.ok) throw new Error('Gagal menyimpan tema.');
        }).catch(function (error) {
            console.error(error);
        });
    }

    settings.addEventListener('click', function (event) {
        var button = event.target.closest('button');
        if (!button) return;

        var mode = button.dataset.themeMode || root.dataset.theme || 'auto';
        var accent = button.dataset.themeAccent || root.dataset.accent || 'purple';

        apply(mode, accent);
        save(mode, accent);
    });

    apply(root.dataset.theme || 'auto', root.dataset.accent || 'purple');
})();
