// Phil's iPhone - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO and External Notifications
    if (typeof io !== 'undefined') {
        const socket = window.globalSocket || io();

        // Request permission for browser notifications on first user interaction.
        // Modern browsers require a user gesture (click/tap) to show the permission prompt.
        const initNotifications = () => {
            if ("Notification" in window && Notification.permission === "default") {
                Notification.requestPermission().then(permission => {
                    console.log("Notification permission result:", permission);
                });
            }
            document.removeEventListener('click', initNotifications);
            document.removeEventListener('touchstart', initNotifications);
        };

        document.addEventListener('click', initNotifications, { passive: true });
        document.addEventListener('touchstart', initNotifications, { passive: true });

        // Handle incoming system notifications for background alerts
        // Toast notifications are handled globally in templates/base.html
        // (spawnNotification). Removing OS-level Notification(...) here prevents duplicate/"compromised"
        // behavior and keeps system_notification handling consistent.
        socket.on('system_notification', function(data) {
            // no-op (toast handled in base.html)
        });
    }

    // Navigation Elements
    const userMenu = document.querySelector('.user-menu');
    const dropdown = document.querySelector('.dropdown');

    // Sidebar Contact Filter
    const sidebarSearch = document.getElementById('sidebar-contact-search');
    if (sidebarSearch) {
        sidebarSearch.addEventListener('input', function(e) {
            const filter = e.target.value.toLowerCase();
            const contactButtons = document.querySelectorAll('.user-list .user-btn');
            
            contactButtons.forEach(btn => {
                const name = btn.textContent.toLowerCase();
                if (name.includes(filter)) {
                    btn.style.display = 'flex';
                } else {
                    btn.style.display = 'none';
                }
            });
        });
    }

    // Filter URL parameter handling for index page
    const urlParams = new URLSearchParams(window.location.search);
    const category = urlParams.get('category');
    if (category) {
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(function(btn) {
            btn.classList.remove('active');
            if (btn.getAttribute('href').includes('category=' + category)) {
                btn.classList.add('active');
            }
        });
    }
    // File upload click handling
    const fileUploadAreas = document.querySelectorAll('.file-upload');
    fileUploadAreas.forEach(function(uploadArea) {
        const fileInput = uploadArea.querySelector('input[type="file"]');
        if (fileInput) {
            uploadArea.addEventListener('click', function() {
                fileInput.click();
            });
            
            // Show file name when selected
            fileInput.addEventListener('change', function() {
                if (fileInput.files.length > 0) {
                    const fileName = fileInput.files[0].name;
                    const hint = uploadArea.querySelector('.file-hint');
                    if (hint) {
                        hint.textContent = 'Selected: ' + fileName;
                    }
                }
            });
        }
    });

    const themeToggle = document.querySelector('#theme-toggle-btn') || document.querySelector('.theme-toggle');
    if (themeToggle) {
        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', savedTheme);
        



        themeToggle.addEventListener('click', function() {
            // Tiny animation hook (CSS handles the actual animation)
            themeToggle.classList.remove('theme-switching');
            // Force reflow so animation re-triggers reliably
            // eslint-disable-next-line no-unused-expressions
            themeToggle.offsetWidth;
            themeToggle.classList.add('theme-switching');

            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            themeToggle.innerHTML = newTheme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';

            // Cleanup class after animation completes
            window.setTimeout(() => {
                themeToggle.classList.remove('theme-switching');
            }, 260);
        });

        // Set icon based on current theme
        themeToggle.innerHTML = savedTheme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }



    // Fade-in animation on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.item-card, .hero, .auth-box').forEach(el => {
        observer.observe(el);
    });

    // Form validation feedback
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
            let valid = true;
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    input.style.borderColor = '#dc3545';
                    valid = false;
                } else {
                    input.style.borderColor = '';
                }
            });
            if (!valid) {
                e.preventDefault();
            }
        });
        // Real-time validation
        form.querySelectorAll('input, textarea, select').forEach(input => {
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.style.borderColor = '#dc3545';
                }
            });
            input.addEventListener('input', function() {
                this.style.borderColor = '';
            });
        });
    });
});
