// Phil's iPhone - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger) {
        hamburger.addEventListener('click', function() {
            // Mobile: animate side drop using CSS transform
            const isOpen = navMenu.classList.contains('open');
            navMenu.classList.toggle('open', !isOpen);
            navMenu.style.display = 'block';
            navMenu.style.transform = '';

        });
    }
    
    // User dropdown menu
    const userMenu = document.querySelector('.user-menu');
    const dropdown = document.querySelector('.dropdown');

    if (userMenu && dropdown) {
        userMenu.addEventListener('click', function(e) {
            // Toggle dropdown only when clicking the username area.
            if (e.target.tagName === 'A' && e.target.href.includes('logout')) {
                // Let logout link work normally.
                return;
            }

            if (!dropdown) return;
            e.preventDefault();
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        // Guard: pages may not have these elements
        if (!userMenu || !dropdown) return;
        if (!userMenu.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
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

    // Dark Mode Toggle
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        // Load saved theme
        const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            themeToggle.innerHTML = newTheme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
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
