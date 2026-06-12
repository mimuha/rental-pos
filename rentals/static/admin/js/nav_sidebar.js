(function () {
    function initRentalNavSidebar() {
        const sidebar = document.getElementById('nav-sidebar');
        if (!sidebar || sidebar.dataset.rentalEnhanced === 'true') {
            return;
        }

        sidebar.dataset.rentalEnhanced = 'true';

        const sidebarColumn = sidebar.closest('.admin-sidebar-col');
        const collapseButton = sidebar.querySelector('.rental-nav-collapse');
        const searchInput = sidebar.querySelector('#nav-filter');
        const items = Array.from(sidebar.querySelectorAll('.rental-nav-item'));

        function setCollapsed(isCollapsed) {
            if (!sidebarColumn) {
                return;
            }
            sidebarColumn.classList.toggle('rental-nav-collapsed', isCollapsed);
            localStorage.setItem('rental.admin.navCollapsed', isCollapsed ? 'true' : 'false');
            if (collapseButton) {
                collapseButton.setAttribute('aria-label', isCollapsed ? 'Tampilkan menu' : 'Sembunyikan menu');
            }
            if (!isCollapsed) {
                // close any open popup when the menu is expanded
                closePopup();
            }
        }

        if (collapseButton) {
            collapseButton.addEventListener('click', function () {
                setCollapsed(!sidebarColumn.classList.contains('rental-nav-collapsed'));
            });
        }

        if (localStorage.getItem('rental.admin.navCollapsed') !== 'false') {
            setCollapsed(true);
        }

        var searchBtn = sidebar.querySelector('.rental-nav-search-btn');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', function () {
                setCollapsed(false);
                searchInput.focus();
            });
        }

        if (searchInput) {
            const filterMenu = function () {
                const query = searchInput.value.trim().toLowerCase();

                items.forEach(function (item) {
                    const title = (item.dataset.menuTitle || item.textContent).toLowerCase();
                    const isMatch = title.indexOf(query) !== -1;
                    item.hidden = Boolean(query && !isMatch);
                    if (query && isMatch) {
                        item.open = true;
                    }
                });

                sidebar.querySelectorAll('.rental-nav-section').forEach(function (section) {
                    const hasVisibleItem = Array.from(section.querySelectorAll('.rental-nav-item')).some(function (item) {
                        return !item.hidden;
                    });
                    section.hidden = Boolean(query && !hasVisibleItem);
                });
            };

            searchInput.addEventListener('input', filterMenu);
            searchInput.addEventListener('keydown', function (event) {
                if (event.key === 'Escape') {
                    searchInput.value = '';
                    filterMenu();
                }
            });

            document.addEventListener('keydown', function (event) {
                if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
                    event.preventDefault();
                    setCollapsed(false);
                    searchInput.focus();
                }
            });
        }

        // Popup handling for collapsed menu
        let currentPopup = null;
        let currentAnchor = null;
        let docMousedownHandler = null;
        let docKeydownHandler = null;
        let popupCloseTimer = null;
        const desktopCollapsedMedia = window.matchMedia('(min-width: 1200px)');

        function isDesktopCollapsedMode() {
            return Boolean(
                sidebarColumn
                && sidebarColumn.classList.contains('rental-nav-collapsed')
                && desktopCollapsedMedia.matches
            );
        }

        function isCollapsedMode() {
            return Boolean(sidebarColumn && sidebarColumn.classList.contains('rental-nav-collapsed'));
        }

        function clearPopupCloseTimer() {
            if (popupCloseTimer) {
                window.clearTimeout(popupCloseTimer);
                popupCloseTimer = null;
            }
        }

        function scheduleHoverPopupClose() {
            clearPopupCloseTimer();
            popupCloseTimer = window.setTimeout(function () {
                const isStillHoveringPopup = currentPopup && currentPopup.matches(':hover');
                const isStillHoveringAnchor = currentAnchor && currentAnchor.matches(':hover');
                if (!isStillHoveringPopup && !isStillHoveringAnchor) {
                    closePopup();
                }
            }, 120);
        }

        function closePopup() {
            if (!currentPopup) return;
            clearPopupCloseTimer();
            try { currentPopup.remove(); } catch (e) {}
            currentPopup = null;
            currentAnchor = null;
            if (docMousedownHandler) document.removeEventListener('mousedown', docMousedownHandler, true);
            if (docKeydownHandler) document.removeEventListener('keydown', docKeydownHandler, true);
            window.removeEventListener('resize', closePopup);
            window.removeEventListener('scroll', closePopup, true);
        }

        function showPopupForItem(item, summary) {
            closePopup();
            const submenu = item.querySelector('.rental-nav-submenu');
            if (!submenu) return;

            const labelEl = item.querySelector('.rental-nav-label');
            const label = labelEl ? labelEl.textContent.trim() : '';

            const popup = document.createElement('div');
            popup.className = 'rental-nav-popup';
            popup.setAttribute('role', 'menu');

            const inner = document.createElement('div');
            inner.className = 'rental-nav-popup-inner';

            if (label) {
                const title = document.createElement('div');
                title.className = 'rental-nav-popup-title';
                title.textContent = label;
                inner.appendChild(title);
            }

            const submenuClone = submenu.cloneNode(true);
            submenuClone.style.display = 'block';
            inner.appendChild(submenuClone);
            popup.appendChild(inner);
            document.body.appendChild(popup);
            popup.addEventListener('mouseenter', clearPopupCloseTimer);
            popup.addEventListener('mouseleave', function () {
                if (isDesktopCollapsedMode()) {
                    scheduleHoverPopupClose();
                }
            });

            // position popup next to collapsed sidebar
            const anchorRect = summary.getBoundingClientRect();
            const sidebarRect = sidebarColumn ? sidebarColumn.getBoundingClientRect() : sidebar.getBoundingClientRect();
            const popupRect = popup.getBoundingClientRect();

            const margin = 8;
            // shift popup 20px lebih mendekati sidebar untuk tampilan lebih rapat
            let left = sidebarRect.right + margin + window.scrollX - 20;
            let top = anchorRect.top + (anchorRect.height / 2) - (popupRect.height / 2) + window.scrollY;

            if (top + popupRect.height > window.innerHeight - margin) {
                top = window.innerHeight - popupRect.height - margin;
            }
            if (top < margin) top = margin;

            if (left + popupRect.width > window.innerWidth - margin) {
                left = window.innerWidth - popupRect.width - margin;
            }

            popup.style.position = 'absolute';
            popup.style.left = left + 'px';
            popup.style.top = top + 'px';
            window.requestAnimationFrame(function () {
                popup.classList.add('is-visible');
            });

            docMousedownHandler = function (e) {
                if (popup.contains(e.target) || summary.contains(e.target)) return;
                closePopup();
            };
            docKeydownHandler = function (e) {
                if (e.key === 'Escape') closePopup();
            };

            document.addEventListener('mousedown', docMousedownHandler, true);
            document.addEventListener('keydown', docKeydownHandler, true);
            window.addEventListener('resize', closePopup);
            window.addEventListener('scroll', closePopup, true);

            // close when clicking a link (allow navigation)
            popup.querySelectorAll('a').forEach(function (a) {
                a.addEventListener('click', function () {
                    closePopup();
                });
            });

            currentPopup = popup;
            currentAnchor = item;
        }

        // Attach click handlers to summary elements to show popup when collapsed
        items.forEach(function (item) {
            const summary = item.querySelector('summary');
            if (!summary) return;

            item.addEventListener('mouseenter', function () {
                if (!isDesktopCollapsedMode()) {
                    return;
                }
                clearPopupCloseTimer();
                if (currentAnchor !== item) {
                    showPopupForItem(item, summary);
                }
            });

            item.addEventListener('mouseleave', function () {
                if (isDesktopCollapsedMode()) {
                    scheduleHoverPopupClose();
                }
            });

            summary.addEventListener('click', function (event) {
                if (!isCollapsedMode()) {
                    // allow normal expand/collapse when nav is expanded
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                if (isDesktopCollapsedMode()) {
                    showPopupForItem(item, summary);
                    return;
                }
                if (currentAnchor === item) {
                    closePopup();
                    return;
                }
                showPopupForItem(item, summary);
            });
        });

    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRentalNavSidebar);
    } else {
        initRentalNavSidebar();
    }
}());
