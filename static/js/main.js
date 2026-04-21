/* CHE GOLOSO - Main JavaScript */

(function() {
    'use strict';

    // Initialize Bootstrap tooltips
    document.addEventListener('DOMContentLoaded', function() {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    });

    // Auto-dismiss Django message alerts after 5 seconds
    // Only target alerts with data-bs-dismiss="alert" button (flash messages),
    // not modal/UI alerts used by other components.
    document.addEventListener('DOMContentLoaded', function() {
        const alerts = document.querySelectorAll('.alert.alert-dismissible:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    });

    // Confirm delete actions
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-confirm]')) {
            const message = e.target.dataset.confirm || '¿Está seguro de realizar esta acción?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        }
    });

    // Format currency inputs
    document.addEventListener('input', function(e) {
        if (e.target.matches('.currency-input')) {
            formatCurrencyInput(e.target);
        }
    });

    function formatCurrencyInput(input) {
        let value = input.value.replace(/[^\d,]/g, '');
        if (value) {
            // Format with thousands separator
            let parts = value.split(',');
            parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
            input.value = parts.join(',');
        }
    }

    // Form validation enhancement
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.classList.contains('needs-validation')) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        }
    });

    // Loading overlay
    window.showLoading = function() {
        let overlay = document.querySelector('.loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.classList.remove('hidden');
    };

    window.hideLoading = function() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    };

    // Toast notifications
    window.showToast = function(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toastId = 'toast-' + Date.now();
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };

        const bgMap = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        };

        const html = `
            <div class="toast ${bgMap[type]} text-white" id="${toastId}" role="alert">
                <div class="toast-body d-flex align-items-center">
                    <i class="fas fa-${iconMap[type]} me-2"></i>
                    ${message}
                    <button type="button" class="btn-close btn-close-white ms-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', html);
        const toastEl = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();

        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    };

    // AJAX helper
    window.fetchJSON = async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };
        if (options.headers) {
            mergedOptions.headers = { ...defaultOptions.headers, ...options.headers };
        }

        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error en la solicitud');
            }
            
            return data;
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    };

    // Get CSRF cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Format numbers as Argentine currency
    window.formatCurrency = function(value) {
        if (value === null || value === undefined) return '$0';
        
        const number = parseFloat(value);
        if (isNaN(number)) return '$0';

        const formatted = number.toLocaleString('es-AR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });

        return '$' + formatted;
    };

    // Parse Argentine currency string to number
    window.parseCurrency = function(str) {
        if (!str) return 0;
        
        // Remove currency symbol and spaces
        let cleaned = str.replace(/[$\s]/g, '');
        
        // Handle Argentine format (. for thousands, , for decimals)
        cleaned = cleaned.replace(/\./g, '').replace(',', '.');
        
        return parseFloat(cleaned) || 0;
    };

    // Print specific element
    window.printElement = function(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>Imprimir</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>
                    body { padding: 20px; }
                    @media print {
                        .no-print { display: none !important; }
                    }
                </style>
            </head>
            <body>
                ${element.innerHTML}
                <script>
                    window.onload = function() {
                        window.print();
                        window.close();
                    };
                </script>
            </body>
            </html>
        `);
        printWindow.document.close();
    };

    // Debounce function
    window.debounce = function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };

    // ─── Dark Mode Toggle ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {
        const toggle = document.getElementById('darkModeToggle');
        const icon = document.getElementById('darkModeIcon');
        if (!toggle || !icon) return;

        function applyTheme(dark) {
            if (dark) {
                document.documentElement.setAttribute('data-theme', 'dark');
                icon.className = 'fas fa-sun';
                toggle.title = 'Cambiar a modo claro';
            } else {
                document.documentElement.removeAttribute('data-theme');
                icon.className = 'fas fa-moon';
                toggle.title = 'Cambiar a modo oscuro';
            }
        }

        // Init from localStorage (already applied in <head>, but sync icon)
        const isDark = localStorage.getItem('che-darkmode') === 'true';
        applyTheme(isDark);

        toggle.addEventListener('click', function() {
            const nowDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const next = !nowDark;
            localStorage.setItem('che-darkmode', next);
            applyTheme(next);
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // F1 - Help
        if (e.key === 'F1') {
            e.preventDefault();
            // Show help modal or redirect
        }

        // Escape - Close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            });
        }
    });

})();
