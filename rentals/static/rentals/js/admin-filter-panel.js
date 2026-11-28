(function () {
    function createElement(tagName, className, textContent) {
        const element = document.createElement(tagName);
        if (className) {
            element.className = className;
        }
        if (textContent) {
            element.textContent = textContent;
        }
        return element;
    }

    function getCurrentPath() {
        return window.location.pathname;
    }

    function getResetHref(panel) {
        const extraActionLinks = Array.from(panel.querySelectorAll('#changelist-filter-extra-actions a[href]'));
        const clearLink = extraActionLinks.find(function (link) {
            const text = link.textContent.trim().toLowerCase();
            return text.indexOf('clear') !== -1 ||
                text.indexOf('hapus') !== -1 ||
                text.indexOf('reset') !== -1 ||
                text.indexOf('✖') !== -1 ||
                text.indexOf('×') !== -1;
        });

        if (clearLink) {
            return clearLink.href;
        }

        if (extraActionLinks.length > 0) {
            return extraActionLinks[extraActionLinks.length - 1].href;
        }

        return getCurrentPath();
    }

    function enhanceFilterPanel() {
        const panel = document.getElementById('changelist-filter');
        const changeList = document.getElementById('changelist');

        if (!panel || !changeList || panel.dataset.enhanced === 'true') {
            return;
        }

        panel.dataset.enhanced = 'true';

        changeList.classList.add('rental-filter-collapsed');

        const openButton = createElement('button', 'rental-filter-open is-visible', 'Tampilkan Filter');
        openButton.type = 'button';
        openButton.setAttribute('aria-label', 'Tampilkan filter');
        openButton.insertAdjacentHTML('afterbegin', '<span class="rental-filter-title-icon" aria-hidden="true"></span>');

        var objectTools = document.querySelector('#toolbar .object-tools');
        if (!objectTools) {
            objectTools = document.createElement('ul');
            objectTools.className = 'object-tools';
            var toolbar = document.getElementById('toolbar');
            if (toolbar) {
                toolbar.appendChild(objectTools);
            }
        }
        var li = document.createElement('li');
        li.appendChild(openButton);
        if (objectTools.firstChild) {
            objectTools.insertBefore(li, objectTools.firstChild);
        } else {
            objectTools.appendChild(li);
        }

        openButton.addEventListener('click', function () {
            changeList.classList.remove('rental-filter-collapsed');
            openButton.classList.remove('is-visible');
        });

        const header = panel.querySelector('#changelist-filter-header');

        if (header) {
            header.innerHTML = '<span class="rental-filter-title-icon" aria-hidden="true"></span><span>Filter</span>';

            const closeButton = createElement('button', 'rental-filter-close');
            closeButton.type = 'button';
            closeButton.setAttribute('aria-label', 'Tutup filter');
            closeButton.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
            header.appendChild(closeButton);

            closeButton.addEventListener('click', function () {
                changeList.classList.add('rental-filter-collapsed');
                openButton.classList.add('is-visible');
            });
        }

        const selectedOptions = Array.from(panel.querySelectorAll('.rental-filter-group li.selected'))
            .filter(function (item) {
                return item.previousElementSibling || item.nextElementSibling;
            })
            .filter(function (item) {
                return !item.matches('.rental-filter-group li:first-child');
            });

        // Pilihan langsung diterapkan saat diklik, jadi ringkasan dan reset
        // hanya perlu muncul ketika ada filter yang aktif.
        if (selectedOptions.length === 0) {
            return;
        }

        const activeWrap = createElement('div', 'rental-active-filters');
        activeWrap.appendChild(createElement('h3', null, 'Filter aktif'));

        const chips = createElement('div', 'rental-active-filter-chips');
        selectedOptions.forEach(function (item) {
            const group = item.closest('.rental-filter-group');
            const firstLink = group ? group.querySelector('li:first-child a') : null;
            const currentLink = item.querySelector('a');
            const title = group ? group.dataset.filterTitle : 'Filter';
            const chip = createElement('a', 'rental-filter-chip');
            chip.href = firstLink ? firstLink.href : getCurrentPath();
            chip.textContent = title + ': ' + (currentLink ? currentLink.textContent.trim() : item.textContent.trim());
            chip.insertAdjacentHTML('beforeend', '<span aria-hidden="true">&times;</span>');
            chips.appendChild(chip);
        });
        activeWrap.appendChild(chips);
        panel.appendChild(activeWrap);

        const actions = createElement('div', 'rental-filter-actions');
        const resetButton = createElement('a', 'rental-filter-reset', 'Reset semua');
        resetButton.href = getResetHref(panel);
        actions.appendChild(resetButton);
        panel.appendChild(actions);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', enhanceFilterPanel);
    } else {
        enhanceFilterPanel();
    }
}());
