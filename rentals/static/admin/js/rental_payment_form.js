/*
 * Form Order payment: kartu "Order terpilih", tombol cepat "Lunasi sisa" dan
 * "Setengah", serta indikator sisa setelah pembayaran ini.
 */
(function () {
    'use strict';

    function init() {
        var card = document.getElementById('payment-order-summary');
        var rentalSelect = document.getElementById('id_rental');
        var amountInput = document.getElementById('id_amount');
        if (!card || !rentalSelect || !amountInput) {
            return;
        }

        var urlTemplate = card.dataset.urlTemplate;
        var isEdit = /\/change\/$/.test(window.location.pathname);
        var initialAmount = parseAmount(amountInput.value);
        var initialRental = rentalSelect.value;
        var state = null;
        var requestId = 0;

        function parseAmount(raw) {
            if (window.RupiahFormat && window.RupiahFormat.parse) {
                return window.RupiahFormat.parse(raw) || 0;
            }
            return parseFloat(String(raw || '').replace(/\./g, '').replace(',', '.')) || 0;
        }

        function formatNumber(value) {
            var text = String(Math.round(value));
            return text.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        }

        function rupiah(value) {
            return 'Rp ' + formatNumber(value);
        }

        function field(name) {
            return card.querySelector('[data-order="' + name + '"]');
        }

        function setText(name, text) {
            var el = field(name);
            if (el) {
                el.textContent = text;
            }
        }

        // Tombol cepat di bawah kolom jumlah.
        var chips = document.createElement('div');
        chips.className = 'rental-amount-chips';
        var payAll = document.createElement('button');
        payAll.type = 'button';
        payAll.className = 'rental-fp-chip';
        payAll.textContent = 'Lunasi sisa';
        payAll.disabled = true;
        var half = document.createElement('button');
        half.type = 'button';
        half.className = 'rental-fp-chip';
        half.textContent = 'Setengah';
        half.disabled = true;
        chips.appendChild(payAll);
        chips.appendChild(half);
        var amountRow = amountInput.closest('.form-row');
        if (amountRow) {
            amountRow.appendChild(chips);
        }

        function setAmount(value) {
            amountInput.value = formatNumber(Math.max(value, 0));
            amountInput.dispatchEvent(new Event('input', {bubbles: true}));
            amountInput.dispatchEvent(new Event('change', {bubbles: true}));
        }

        function remainingBefore() {
            if (!state) {
                return 0;
            }
            var remaining = state.remaining;
            if (isEdit && String(state.id) === String(initialRental)) {
                remaining += initialAmount;
            }
            return remaining;
        }

        function refreshAfter() {
            if (!state) {
                return;
            }
            var before = remainingBefore();
            var diff = before - parseAmount(amountInput.value);
            var after = field('after_text');
            var box = card.querySelector('[data-order-after]');
            box.classList.remove('is-paid', 'is-over');
            if (diff > 0) {
                after.textContent = rupiah(diff);
            } else if (diff === 0) {
                after.textContent = 'Rp 0 - Lunas';
                box.classList.add('is-paid');
            } else {
                after.textContent = 'Kelebihan ' + rupiah(-diff);
                box.classList.add('is-over');
            }
            setText('remaining_text', rupiah(before));
            payAll.textContent = 'Lunasi sisa ' + rupiah(before);
            payAll.disabled = before <= 0;
            half.disabled = before <= 0;
        }

        payAll.addEventListener('click', function () {
            setAmount(remainingBefore());
        });
        half.addEventListener('click', function () {
            setAmount(Math.round(remainingBefore() / 2));
        });
        // Ditunda satu tick agar nilai sudah dirapikan oleh pemformat Rupiah.
        amountInput.addEventListener('input', function () {
            setTimeout(refreshAfter, 0);
        });
        amountInput.addEventListener('change', function () {
            setTimeout(refreshAfter, 0);
        });

        function load() {
            var id = rentalSelect.value;
            if (!id) {
                card.hidden = true;
                state = null;
                payAll.disabled = true;
                half.disabled = true;
                payAll.textContent = 'Lunasi sisa';
                return;
            }
            var current = ++requestId;
            fetch(urlTemplate.replace('/0/', '/' + encodeURIComponent(id) + '/'), {
                credentials: 'same-origin',
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            }).then(function (response) {
                return response.ok ? response.json() : null;
            }).then(function (data) {
                if (current !== requestId || !data || !data.ok) {
                    return;
                }
                data.id = id;
                state = data;
                ['invoice_number', 'customer', 'vehicle', 'period', 'status_label'].forEach(function (name) {
                    setText(name, data[name] || '-');
                });
                setText('total_text', rupiah(data.total));
                setText('paid_text', rupiah(data.paid));
                var badge = field('status_label');
                badge.className = 'rental-status-badge rental-status-badge--' + data.status;
                card.hidden = false;
                refreshAfter();
            }).catch(function () {
                /* Ringkasan bersifat tambahan; form tetap bisa dipakai tanpa ini. */
            });
        }

        rentalSelect.addEventListener('change', load);
        if (window.django && window.django.jQuery) {
            // Select2 (autocomplete) memicu event change lewat jQuery.
            window.django.jQuery(rentalSelect).on('change', load);
        }
        load();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
