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
        let popupScrollHandler = null;
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
            if (popupScrollHandler) window.removeEventListener('scroll', popupScrollHandler, true);
            popupScrollHandler = null;
            window.removeEventListener('resize', closePopup);
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

            if (top + popupRect.height > window.scrollY + window.innerHeight - margin) {
                top = anchorRect.bottom + window.scrollY - popupRect.height;
            }
            if (top < window.scrollY + margin) top = window.scrollY + margin;

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
            popupScrollHandler = closePopup;
            window.addEventListener('scroll', popupScrollHandler, true);

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

        var favoriteBtn = document.getElementById('rental-nav-favorite-btn');
        if (favoriteBtn) {
            function getCsrfToken() {
                var m = document.cookie.match(/csrftoken=([^;]+)/);
                return m ? m[1] : '';
            }

            function getMenuItems() {
                var menus = [];
                items.forEach(function (item) {
                    var cl = item.className.split(/\s+/);
                    var key = '';
                    for (var i = 0; i < cl.length; i++) {
                        if (cl[i].indexOf('model-') === 0) { key = cl[i].substring(6); break; }
                    }
                    if (!key) return;
                    var titleEl = item.querySelector('.rental-nav-label');
                    var iconEl = item.querySelector('.rental-nav-icon');
                    var linkEl = item.querySelector('.rental-nav-submenu a');
                    menus.push({
                        key: key,
                        title: titleEl ? titleEl.textContent.trim() : '',
                        iconHtml: iconEl ? iconEl.innerHTML : '',
                        url: linkEl ? linkEl.href : '#'
                    });
                });
                return menus;
            }

            function fetchFavorites(cb) {
                fetch('/admin/rentals/favorites/').then(function (r) { return r.json(); }).then(function (d) {
                    cb(d.favorites || []);
                }).catch(function () { cb([]); });
            }

            function positionFavPopup(popup, anchor) {
                var ar = anchor.getBoundingClientRect();
                var sr = sidebarColumn ? sidebarColumn.getBoundingClientRect() : sidebar.getBoundingClientRect();
                var pr = popup.getBoundingClientRect();
                var m = 8;
                if (isDesktopCollapsedMode()) {
                    var left = sr.right + m + window.scrollX - 20;
                    var top = ar.top + (ar.height / 2) - (pr.height / 2) + window.scrollY;
                    if (top + pr.height > window.scrollY + window.innerHeight - m) top = ar.bottom + window.scrollY - pr.height;
                    if (top < window.scrollY + m) top = window.scrollY + m;
                    if (left + pr.width > window.innerWidth - m) left = window.innerWidth - pr.width - m;
                    popup.style.transformOrigin = 'left center';
                    popup.style.position = 'absolute';
                    popup.style.left = left + 'px';
                    popup.style.top = top + 'px';
                } else {
                    var top2 = ar.bottom + m - 10 + window.scrollY;
                    if (top2 + pr.height > window.innerHeight - m) {
                        top2 = Math.max(m, ar.top - pr.height - m + window.scrollY);
                    }
                    if (top2 < m) top2 = m;
                    popup.style.transformOrigin = 'top center';
                    popup.style.position = 'absolute';
                    popup.style.left = ar.left + window.scrollX + 'px';
                    popup.style.top = top2 + 'px';
                }
            }

            function showFavPopup(mode, favorites) {
                closePopup();
                var allMenus = getMenuItems();
                var popup = document.createElement('div');
                popup.className = 'rental-nav-popup rental-nav-fav-popup';
                popup.setAttribute('role', 'menu');

                var inner = document.createElement('div');
                inner.className = 'rental-nav-popup-inner';

                var header = document.createElement('div');
                header.className = 'rental-nav-fav-header';
                var title = document.createElement('span');
                title.className = 'rental-nav-fav-title';
                title.textContent = mode === 'edit' ? 'Edit Favorit' : 'Menu Favorit';
                header.appendChild(title);

                var actionBtn = document.createElement('button');
                actionBtn.type = 'button';
                actionBtn.className = 'rental-nav-fav-action';
                actionBtn.textContent = mode === 'edit' ? 'Selesai' : 'Edit';
                actionBtn.addEventListener('click', function () {
                    if (mode === 'edit') {
                        fetchFavorites(function (f) { showFavPopup('view', f); });
                    } else {
                        showFavPopup('edit', favorites);
                    }
                });
                header.appendChild(actionBtn);
                inner.appendChild(header);

                if (mode === 'edit') {
                    var list = document.createElement('div');
                    list.className = 'rental-nav-fav-list';
                    allMenus.forEach(function (menu) {
                        var favObj = null;
                        favorites.forEach(function (f) { if (f.menu_key === menu.key) favObj = f; });
                        var isFav = Boolean(favObj);

                        var row = document.createElement('label');
                        row.className = 'rental-nav-fav-edit-item' + (isFav ? ' is-active' : '');

                        var icon = document.createElement('span');
                        icon.className = 'rental-nav-fav-item-icon';
                        icon.innerHTML = menu.iconHtml;
                        row.appendChild(icon);

                        var name = document.createElement('span');
                        name.className = 'rental-nav-fav-item-name';
                        name.textContent = menu.title;
                        row.appendChild(name);

                        var toggle = document.createElement('input');
                        toggle.type = 'checkbox';
                        toggle.className = 'rental-nav-fav-toggle';
                        toggle.checked = isFav;
                        (function (menuKey, toggleEl, rowEl) {
                            var localFavId = favObj ? favObj.id : null;
                            toggleEl.addEventListener('change', function () {
                                if (toggleEl.checked) {
                                    fetch('/admin/rentals/favorites/', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                                        body: JSON.stringify({ menu_key: menuKey })
                                    }).then(function (r) { return r.json(); }).then(function (d) {
                                        if (d.ok) {
                                            localFavId = d.favorite.id;
                                            favorites.push({ id: d.favorite.id, menu_key: menuKey });
                                            rowEl.classList.add('is-active');
                                        }
                                    });
                                } else if (localFavId) {
                                    fetch('/admin/rentals/favorites/' + localFavId + '/delete/', {
                                        method: 'POST',
                                        headers: { 'X-CSRFToken': getCsrfToken() }
                                    }).then(function (r) { return r.json(); }).then(function (d) {
                                        if (d.ok) {
                                            favorites = favorites.filter(function (f) { return f.id !== localFavId; });
                                            localFavId = null;
                                            rowEl.classList.remove('is-active');
                                        }
                                    });
                                }
                            });
                        })(menu.key, toggle, row);
                        row.appendChild(toggle);
                        list.appendChild(row);
                    });
                    inner.appendChild(list);
                } else {
                    if (favorites.length === 0) {
                        var empty = document.createElement('div');
                        empty.className = 'rental-nav-fav-empty';
                        empty.textContent = 'Belum ada menu favorit. Klik Edit untuk menambahkan.';
                        inner.appendChild(empty);
                    } else {
                        var vlist = document.createElement('div');
                        vlist.className = 'rental-nav-fav-list';
                        favorites.forEach(function (fav) {
                            var menu = null;
                            allMenus.forEach(function (m) { if (m.key === fav.menu_key) menu = m; });
                            if (!menu) return;
                            var link = document.createElement('a');
                            link.className = 'rental-nav-fav-item';
                            link.href = menu.url;
                            var icon = document.createElement('span');
                            icon.className = 'rental-nav-fav-item-icon';
                            icon.innerHTML = menu.iconHtml;
                            link.appendChild(icon);
                            var name = document.createElement('span');
                            name.className = 'rental-nav-fav-item-name';
                            name.textContent = menu.title;
                            link.appendChild(name);
                            link.addEventListener('click', function () { closePopup(); });
                            vlist.appendChild(link);
                        });
                        inner.appendChild(vlist);
                    }
                }

                popup.appendChild(inner);
                document.body.appendChild(popup);
                positionFavPopup(popup, favoriteBtn);

                popup.addEventListener('mouseenter', clearPopupCloseTimer);
                popup.addEventListener('mouseleave', function () {
                    if (favHoverMedia.matches) { scheduleHoverPopupClose(); }
                });

                window.requestAnimationFrame(function () { popup.classList.add('is-visible'); });

                docMousedownHandler = function (e) {
                    if (popup.contains(e.target) || favoriteBtn.contains(e.target)) return;
                    closePopup();
                };
                docKeydownHandler = function (e) { if (e.key === 'Escape') closePopup(); };
                document.addEventListener('mousedown', docMousedownHandler, true);
                document.addEventListener('keydown', docKeydownHandler, true);
                window.addEventListener('resize', closePopup);
                popupScrollHandler = function (e) {
                    if (popup.contains(e.target)) return;
                    closePopup();
                };
                window.addEventListener('scroll', popupScrollHandler, true);

                currentPopup = popup;
                currentAnchor = favoriteBtn;
            }

            var favHoverMedia = window.matchMedia('(hover: hover)');

            favoriteBtn.addEventListener('mouseenter', function () {
                if (!favHoverMedia.matches) return;
                clearPopupCloseTimer();
                if (currentAnchor !== favoriteBtn) {
                    fetchFavorites(function (favs) { showFavPopup('view', favs); });
                }
            });

            favoriteBtn.addEventListener('mouseleave', function () {
                if (favHoverMedia.matches) { scheduleHoverPopupClose(); }
            });

            favoriteBtn.addEventListener('click', function () {
                if (currentAnchor === favoriteBtn) { closePopup(); return; }
                fetchFavorites(function (favs) { showFavPopup('view', favs); });
            });
        }

    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRentalNavSidebar);
    } else {
        initRentalNavSidebar();
    }
}());
