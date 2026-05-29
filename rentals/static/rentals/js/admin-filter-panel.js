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
        const openButton = createElement('button', 'rental-filter-open', 'Tampilkan Filter');
        openButton.type = 'button';
        openButton.setAttribute('aria-label', 'Tampilkan filter');
        openButton.insertAdjacentHTML('afterbegin', '<span class="rental-filter-title-icon" aria-hidden="true"></span>');
        document.body.appendChild(openButton);
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
            closeButton.textContent = 'x';
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
            chip.insertAdjacentHTML('beforeend', '<span aria-hidden="true">x</span>');
            chips.appendChild(chip);
        });

        if (selectedOptions.length === 0) {
            activeWrap.classList.add('is-empty');
            chips.appendChild(createElement('span', 'rental-filter-empty', 'Belum ada filter aktif'));
        }

        activeWrap.appendChild(chips);
        panel.appendChild(activeWrap);

        const actions = createElement('div', 'rental-filter-actions');

        const resetButton = createElement('a', 'rental-filter-reset', 'Reset Semua');
        resetButton.href = getResetHref(panel);
        actions.appendChild(resetButton);

        const applyButton = createElement('a', 'rental-filter-apply', 'Terapkan Filter');
        applyButton.href = window.location.href;
        actions.appendChild(applyButton);

        panel.appendChild(actions);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', enhanceFilterPanel);
    } else {
        enhanceFilterPanel();
    }
}());
