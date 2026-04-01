/**
 * Mobile Menu Drawer - Handle slide-in drawer and overlay
 */

// Ensure all nav dropdowns start collapsed on mobile (runs on page load)
document.addEventListener('DOMContentLoaded', function() {
    if (window.innerWidth < 992) {
        collapseAllDropdowns();
    }
});

// Function to collapse all dropdowns
function collapseAllDropdowns() {
    // Remove show class from all dropdown menus
    document.querySelectorAll('.navbar-nav .dropdown-menu').forEach(menu => {
        menu.classList.remove('show');
    });
    
    // Set aria-expanded to false and remove show class from toggles
    document.querySelectorAll('.navbar-nav .dropdown-toggle').forEach(toggle => {
        toggle.setAttribute('aria-expanded', 'false');
        toggle.classList.remove('show');
    });
    
    // Remove show class from dropdown containers
    document.querySelectorAll('.navbar-nav .dropdown').forEach(dropdown => {
        dropdown.classList.remove('show');
    });
}

// Main menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const overlay = document.getElementById('mobileMenuOverlay');
    const navbarCollapse = document.getElementById('navbarNav');
    const navbarToggler = document.querySelector('.navbar-toggler');
    
    if (!overlay || !navbarCollapse) return;
    
    // Show overlay when menu opens
    navbarCollapse.addEventListener('show.bs.collapse', function() {
        // FORCE collapse ALL dropdowns first
        collapseAllDropdowns();
        
        // Then show overlay and prevent body scroll
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    });
    
    // Also collapse dropdowns after menu is fully shown (backup)
    navbarCollapse.addEventListener('shown.bs.collapse', function() {
        collapseAllDropdowns();
    });
    
    // Hide overlay when menu closes
    navbarCollapse.addEventListener('hide.bs.collapse', function() {
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    });
    
    // Close menu when clicking overlay
    overlay.addEventListener('click', function() {
        if (navbarToggler) {
            navbarToggler.click();
        }
    });
    
    // Close menu when clicking a non-dropdown link
    const navLinks = navbarCollapse.querySelectorAll('.nav-link:not(.dropdown-toggle)');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                if (navbarToggler) {
                    navbarToggler.click();
                }
            }
        });
    });
    
    // Close menu when clicking a dropdown item
    const dropdownItems = navbarCollapse.querySelectorAll('.dropdown-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                if (navbarToggler) {
                    navbarToggler.click();
                }
            }
        });
    });
});
