(function() {
    'use strict';

    function init() {
        if (!document.querySelector('.app-rentals.model-rental')) return;

        function parseDateValue(raw) {
            if (!raw) return null;
            raw = raw.trim();
            // ISO: YYYY-MM-DD
            var isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
            if (isoMatch) {
                return new Date(+isoMatch[1], +isoMatch[2] - 1, +isoMatch[3]);
            }
            // Locale: DD/MM/YYYY
            var localeMatch = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
            if (localeMatch) {
                return new Date(+localeMatch[3], +localeMatch[2] - 1, +localeMatch[1]);
            }
            // Try native parse as fallback
            var d = new Date(raw);
            return isNaN(d.getTime()) ? null : d;
        }

        function parseTimeValue(raw) {
            if (!raw) return [0, 0];
            raw = raw.trim();
            var parts = raw.split(':');
            var h = parseInt(parts[0], 10) || 0;
            var m = parseInt(parts[1], 10) || 0;
            return [h, m];
        }

        function parseDatetime(dateId, timeId) {
            var dateEl = document.getElementById(dateId);
            if (!dateEl || !dateEl.value) return null;

            var dateVal = parseDateValue(dateEl.value);
            if (!dateVal) return null;

            var timeEl = document.getElementById(timeId);
            if (timeEl && timeEl.value) {
                var tm = parseTimeValue(timeEl.value);
                dateVal.setHours(tm[0], tm[1], 0, 0);
            }
            return dateVal;
        }

        function formatRupiah(value) {
            if (value === null || value === undefined || isNaN(value)) return '-';
            value = Math.round(value);
            var s = value.toString();
            var result = '';
            var len = s.length;
            for (var i = 0; i < len; i++) {
                if (i > 0 && (len - i) % 3 === 0) result += '.';
                result += s[i];
            }
            return 'Rp' + result;
        }

        function calculate() {
            var start = parseDatetime('id_start_at_0', 'id_start_at_1');
            if (!start) return;

            var expectedReturn = parseDatetime('id_expected_return_at_0', 'id_expected_return_at_1');
            var returned = parseDatetime('id_returned_at_0', 'id_returned_at_1');
            var end = returned || expectedReturn;
            if (!end) return;

            var seconds = Math.max((end.getTime() - start.getTime()) / 1000, 0);
            var days = Math.max(1, Math.ceil(seconds / 86400));

            var dailyRate = parseFloat(document.getElementById('id_daily_rate').value) || 0;
            var discount = parseFloat(document.getElementById('id_discount_amount').value) || 0;
            var additionalFee = parseFloat(document.getElementById('id_additional_fee').value) || 0;

            var subtotal = dailyRate * days;
            var total = subtotal + additionalFee - discount;

            var subtotalEl = document.querySelector('.field-subtotal_rupiah .readonly');
            var totalEl = document.querySelector('.field-total_amount_rupiah .readonly');

            if (subtotalEl) subtotalEl.textContent = formatRupiah(subtotal);
            if (totalEl) totalEl.textContent = formatRupiah(total);
        }

        var fieldIds = [
            'id_start_at_0', 'id_start_at_1',
            'id_expected_return_at_0', 'id_expected_return_at_1',
            'id_returned_at_0', 'id_returned_at_1',
            'id_daily_rate', 'id_discount_amount', 'id_additional_fee'
        ];

        fieldIds.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.addEventListener('input', calculate);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
