/*
 * Mengubah dropdown pilihan pendek (status, metode pembayaran) di form dua
 * kolom menjadi tombol pilihan. <select> asli tetap ada (disembunyikan) dan
 * menjadi sumber nilai yang dikirim ke server.
 */
(function () {
    'use strict';

    var SELECTORS = [
        '.rental-form-layout select#id_status',
        '.rental-form-layout select#id_method'
    ];

    function build(select) {
        if (select.dataset.rentalPills === 'true') {
            return;
        }
        select.dataset.rentalPills = 'true';
        select.classList.add('rental-pills-source');

        var group = document.createElement('div');
        group.className = 'rental-pills';
        group.setAttribute('role', 'radiogroup');
        var label = document.querySelector('label[for="' + select.id + '"]');
        if (label) {
            group.setAttribute('aria-label', label.textContent.replace(':', '').trim());
        }

        var buttons = [];
        Array.prototype.forEach.call(select.options, function (option) {
            if (!option.value) {
                return;
            }
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'rental-pill';
            button.setAttribute('role', 'radio');
            button.dataset.value = option.value;
            button.textContent = option.textContent;
            button.addEventListener('click', function () {
                select.value = option.value;
                select.dispatchEvent(new Event('change', {bubbles: true}));
            });
            buttons.push(button);
            group.appendChild(button);
        });

        function sync() {
            buttons.forEach(function (button) {
                var active = button.dataset.value === select.value;
                button.setAttribute('aria-checked', active ? 'true' : 'false');
                button.tabIndex = active || (!select.value && button === buttons[0]) ? 0 : -1;
            });
        }

        group.addEventListener('keydown', function (event) {
            var index = buttons.indexOf(document.activeElement);
            if (index === -1) {
                return;
            }
            var delta = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1
                : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 0;
            if (delta) {
                event.preventDefault();
                var next = buttons[(index + delta + buttons.length) % buttons.length];
                next.focus();
                next.click();
            }
        });

        select.addEventListener('change', sync);
        select.parentNode.insertBefore(group, select.nextSibling);
        sync();
    }

    function start() {
        document.querySelectorAll(SELECTORS.join(',')).forEach(build);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
