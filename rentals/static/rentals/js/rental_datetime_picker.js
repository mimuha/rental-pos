/*
 * Date & time picker untuk widget tanggal-waktu admin (p.datetime) dan
 * input tanggal tunggal (.vDateField). Satu popup memuat kalender dan jam.
 * Nilai tetap ditulis ke input bawaan Django (dd-mm-yyyy dan HH.mm) sehingga
 * validasi server dan rental_calculator.js tidak berubah.
 */
(function () {
    'use strict';

    if (typeof window.flatpickr !== 'function') {
        return;
    }

    var DATE_FORMAT = 'd-m-Y';
    var MINUTE_STEP = 5;

    function pad(n) {
        return (n < 10 ? '0' : '') + n;
    }

    function parseTime(raw) {
        var match = /^\s*(\d{1,2})[:.](\d{1,2})/.exec(raw || '');
        if (!match) {
            return null;
        }
        var hours = parseInt(match[1], 10);
        var minutes = parseInt(match[2], 10);
        if (hours > 23 || minutes > 59) {
            return null;
        }
        return [hours, minutes];
    }

    // Parse "dd-mm-yyyy" (juga dd/mm/yyyy dan yyyy-mm-dd) sambil mempertahankan
    // jam dari kolom jam; tanpa ini flatpickr mengembalikan jam ke 00.00.
    function makeParser(timeInput) {
        return function (str) {
            var raw = String(str || '').trim();
            var y, m, d;
            var match = /^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})/.exec(raw);
            if (match) {
                d = parseInt(match[1], 10); m = parseInt(match[2], 10); y = parseInt(match[3], 10);
            } else {
                match = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(raw);
                if (!match) {
                    return undefined;
                }
                y = parseInt(match[1], 10); m = parseInt(match[2], 10); d = parseInt(match[3], 10);
            }
            var time = timeInput ? parseTime(timeInput.value) : null;
            var date = new Date(y, m - 1, d, time ? time[0] : 0, time ? time[1] : 0, 0, 0);
            return date.getMonth() === m - 1 ? date : undefined;
        };
    }

    function fire(el, type) {
        el.dispatchEvent(new Event(type, {bubbles: true}));
    }

    function roundToStep(date) {
        var d = new Date(date.getTime());
        d.setMinutes(Math.round(d.getMinutes() / MINUTE_STEP) * MINUTE_STEP, 0, 0);
        return d;
    }

    function addFooter(instance, timeInput) {
        var footer = document.createElement('div');
        footer.className = 'rental-fp-footer';

        var chips = document.createElement('div');
        chips.className = 'rental-fp-chips';

        function chip(label, handler) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'rental-fp-chip';
            button.textContent = label;
            button.addEventListener('click', handler);
            chips.appendChild(button);
        }

        function keepTime(base) {
            var current = instance.selectedDates[0];
            if (current) {
                base.setHours(current.getHours(), current.getMinutes(), 0, 0);
            } else if (timeInput) {
                var parsed = parseTime(timeInput.value);
                if (parsed) {
                    base.setHours(parsed[0], parsed[1], 0, 0);
                }
            }
            return base;
        }

        chip('Hari ini', function () {
            instance.setDate(keepTime(new Date()), true);
        });
        chip('Besok', function () {
            var tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            instance.setDate(keepTime(tomorrow), true);
        });
        if (timeInput) {
            chip('Sekarang', function () {
                instance.setDate(roundToStep(new Date()), true);
            });
        }
        footer.appendChild(chips);

        var actions = document.createElement('div');
        actions.className = 'rental-fp-actions';

        var cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'rental-fp-cancel';
        cancel.textContent = 'Batal';
        cancel.addEventListener('click', function () {
            var original = instance._rentalInitial;
            if (original) {
                instance.input.value = original.date;
                if (timeInput) {
                    timeInput.value = original.time;
                }
                instance.setDate(original.date || null, false, DATE_FORMAT);
                fire(instance.input, 'input');
                if (timeInput) {
                    fire(timeInput, 'input');
                }
            }
            instance.close();
        });

        var apply = document.createElement('button');
        apply.type = 'button';
        apply.className = 'rental-fp-apply';
        apply.textContent = 'Terapkan';
        apply.addEventListener('click', function () {
            instance.close();
        });

        actions.appendChild(cancel);
        actions.appendChild(apply);
        footer.appendChild(actions);
        instance.calendarContainer.appendChild(footer);
    }

    function initDateTime(paragraph) {
        if (paragraph.dataset.rentalPicker === 'true') {
            return;
        }
        var dateInput = paragraph.querySelector('input.vDateField');
        var timeInput = paragraph.querySelector('input.vTimeField');
        if (!dateInput || !timeInput || /__prefix__/.test(dateInput.id)) {
            return;
        }
        paragraph.dataset.rentalPicker = 'true';

        var syncing = false;

        var instance = window.flatpickr(dateInput, {
            locale: 'id',
            dateFormat: DATE_FORMAT,
            parseDate: makeParser(timeInput),
            enableTime: true,
            time_24hr: true,
            minuteIncrement: MINUTE_STEP,
            allowInput: true,
            disableMobile: true,
            positionElement: paragraph,
            ignoredFocusElements: [timeInput],
            onReady: function (selectedDates, value, fp) {
                fp.calendarContainer.classList.add('rental-fp');
                addFooter(fp, timeInput);
                var parsed = parseTime(timeInput.value);
                if (selectedDates[0] && parsed) {
                    syncing = true;
                    fp.setDate(new Date(
                        selectedDates[0].getFullYear(), selectedDates[0].getMonth(),
                        selectedDates[0].getDate(), parsed[0], parsed[1]
                    ), false);
                    syncing = false;
                }
            },
            onOpen: function (selectedDates, value, fp) {
                fp._rentalInitial = {date: dateInput.value, time: timeInput.value};
                var parsed = parseTime(timeInput.value);
                if (parsed && selectedDates[0]) {
                    syncing = true;
                    var d = new Date(selectedDates[0].getTime());
                    d.setHours(parsed[0], parsed[1], 0, 0);
                    fp.setDate(d, false);
                    syncing = false;
                }
            },
            onChange: function (selectedDates) {
                if (syncing || !selectedDates[0]) {
                    return;
                }
                var d = selectedDates[0];
                timeInput.value = pad(d.getHours()) + '.' + pad(d.getMinutes());
                fire(dateInput, 'input');
                fire(timeInput, 'input');
            },
            onClose: function () {
                fire(dateInput, 'change');
                fire(timeInput, 'change');
            }
        });

        // Klik atau fokus pada kolom jam membuka popup yang sama. Flatpickr
        // memindahkan fokus ke kalender saat dibuka, jadi fokus dikembalikan
        // ke kolom jam agar jam tetap bisa diketik.
        var refocusing = false;

        function openFromTime() {
            if (refocusing) {
                return;
            }
            if (!instance.isOpen) {
                instance.open();
            }
            refocusing = true;
            setTimeout(function () {
                timeInput.focus({preventScroll: true});
                refocusing = false;
            }, 0);
        }

        timeInput.addEventListener('focus', openFromTime);
        timeInput.addEventListener('click', function () {
            if (!instance.isOpen) {
                openFromTime();
            }
        });

        // Jam yang diketik langsung disinkronkan ke popup.
        timeInput.addEventListener('change', function () {
            var parsed = parseTime(timeInput.value);
            if (!parsed) {
                return;
            }
            var base = instance.selectedDates[0] || null;
            if (!base) {
                return;
            }
            syncing = true;
            var d = new Date(base.getTime());
            d.setHours(parsed[0], parsed[1], 0, 0);
            instance.setDate(d, false);
            syncing = false;
            timeInput.value = pad(parsed[0]) + '.' + pad(parsed[1]);
        });
    }

    function initDateOnly(input) {
        if (input.dataset.rentalPicker === 'true' || /__prefix__/.test(input.id)) {
            return;
        }
        if (input.closest('p.datetime')) {
            return;
        }
        input.dataset.rentalPicker = 'true';
        window.flatpickr(input, {
            locale: 'id',
            dateFormat: DATE_FORMAT,
            allowInput: true,
            disableMobile: true,
            onReady: function (selectedDates, value, fp) {
                fp.calendarContainer.classList.add('rental-fp');
            }
        });
    }

    // Input tanggal biasa (mis. filter Laporan Keuangan). Nilai yang dikirim tetap
    // yyyy-mm-dd; tampilan memakai dd-mm-yyyy lewat altInput.
    function initPlainDate(input) {
        if (input.dataset.rentalPicker === 'true') {
            return;
        }
        input.dataset.rentalPicker = 'true';
        window.flatpickr(input, {
            locale: 'id',
            dateFormat: 'Y-m-d',
            altInput: true,
            altFormat: DATE_FORMAT,
            altInputClass: input.className,
            allowInput: true,
            disableMobile: true,
            onReady: function (selectedDates, value, fp) {
                fp.calendarContainer.classList.add('rental-fp');
                if (fp.altInput && input.id) {
                    fp.altInput.id = input.id + '_display';
                    var label = document.querySelector('label[for="' + input.id + '"]');
                    if (label) {
                        label.setAttribute('for', fp.altInput.id);
                    }
                }
            }
        });
    }

    // Pilihan bulan (Dashboard). Nilai yang dikirim yyyy-mm; tampilan "November 2026".
    function initMonth(input) {
        if (input.dataset.rentalPicker === 'true' || typeof window.monthSelectPlugin !== 'function') {
            return;
        }
        input.dataset.rentalPicker = 'true';
        window.flatpickr(input, {
            locale: 'id',
            plugins: [new window.monthSelectPlugin({shorthand: false, dateFormat: 'Y-m', altFormat: 'F Y'})],
            dateFormat: 'Y-m',
            altInput: true,
            altFormat: 'F Y',
            altInputClass: input.className,
            disableMobile: true,
            onReady: function (selectedDates, value, fp) {
                fp.calendarContainer.classList.add('rental-fp');
                if (fp.altInput && input.id) {
                    fp.altInput.id = input.id + '_display';
                    var label = document.querySelector('label[for="' + input.id + '"]');
                    if (label) {
                        label.setAttribute('for', fp.altInput.id);
                    }
                }
            }
        });
    }

    function scan(root) {
        root.querySelectorAll('input[data-rental-date]').forEach(initPlainDate);
        root.querySelectorAll('input[data-rental-month]').forEach(initMonth);
        root.querySelectorAll('p.datetime').forEach(initDateTime);
        root.querySelectorAll('input.vDateField').forEach(initDateOnly);
    }

    function start() {
        scan(document);
        // Baris inline yang ditambah lewat "Tambahkan ... lagi".
        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) {
                        scan(node);
                        if (node.matches && node.matches('p.datetime')) {
                            initDateTime(node);
                        }
                    }
                });
            });
        });
        observer.observe(document.body, {childList: true, subtree: true});
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
