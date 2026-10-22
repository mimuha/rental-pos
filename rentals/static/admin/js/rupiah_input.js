(function () {
    'use strict';

    function normalize(value) {
        var text = value === null || value === undefined ? '' : String(value).trim();
        text = text.replace(/[\u00a0\u202f]/g, '').replace(/\s+/g, '');
        text = text.replace(/^rp\.?/i, '');
        return text;
    }

    function parse(value) {
        var text = normalize(value);
        if (!text) return 0;

        if (text.indexOf(',') !== -1) {
            text = text.replace(/\./g, '').replace(',', '.');
        } else if (/^-?\d{1,3}(\.\d{3})+$/.test(text)) {
            text = text.replace(/\./g, '');
        }

        var number = parseFloat(text);
        return isNaN(number) ? 0 : number;
    }

    function format(value) {
        var text = normalize(value);
        if (!text) return '';

        var negative = text.charAt(0) === '-';
        if (negative) text = text.slice(1);

        if (text.indexOf(',') !== -1) {
            text = text.replace(/\./g, '');
        } else if (/^\d{1,3}(\.\d{3})+$/.test(text)) {
            text = text.replace(/\./g, '');
        }

        var parts = text.split(',');
        var integer = parts[0].replace(/\D/g, '');
        var decimal = parts.length > 1
            ? parts.slice(1).join('').replace(/\D/g, '').slice(0, 2)
            : '';

        integer = integer.replace(/^0+(?=\d)/, '');

        var grouped = '';
        for (var i = 0; i < integer.length; i++) {
            if (i > 0 && (integer.length - i) % 3 === 0) grouped += '.';
            grouped += integer.charAt(i);
        }

        if (!grouped && decimal) grouped = '0';

        var result = grouped;
        if (decimal) result += ',' + decimal;
        return (negative && result ? '-' : '') + result;
    }

    function formatInput(input) {
        var raw = input.value;
        var caret = input.selectionStart || 0;
        var digitsBefore = (raw.slice(0, caret).match(/\d/g) || []).length;
        var typedComma = raw.charAt(caret - 1) === ',';
        var formatted = format(raw);

        input.value = formatted;

        if (document.activeElement !== input) return;

        var position;
        if (typedComma) {
            var commaIndex = formatted.indexOf(',');
            position = commaIndex === -1 ? formatted.length : commaIndex + 1;
        } else if (digitsBefore === 0) {
            position = 0;
        } else {
            position = 0;
            var counted = 0;
            while (position < formatted.length && counted < digitsBefore) {
                if (/\d/.test(formatted.charAt(position))) counted += 1;
                position += 1;
            }
        }

        input.setSelectionRange(position, position);
    }

    function init() {
        var inputs = document.querySelectorAll('input.rupiah-input');
        Array.prototype.forEach.call(inputs, function (input) {
            input.addEventListener('input', function () {
                formatInput(input);
            });
            input.addEventListener('blur', function () {
                input.value = format(input.value);
            });
        });
    }

    window.RupiahFormat = {
        parse: parse,
        format: format
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
