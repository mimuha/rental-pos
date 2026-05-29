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
        }

        if (collapseButton) {
            collapseButton.addEventListener('click', function () {
                setCollapsed(!sidebarColumn.classList.contains('rental-nav-collapsed'));
            });
        }

        if (localStorage.getItem('rental.admin.navCollapsed') === 'true') {
            setCollapsed(true);
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
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initRentalNavSidebar);
    } else {
        initRentalNavSidebar();
    }
}());
