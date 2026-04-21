/* CHE GOLOSO - POS Sidebar: shortcuts, quick pay, products, history */
(function () {
    'use strict';

    // ─── Estado ────────────────────────────────────────────────────────────────
    let sidebarOpen = true;
    let quickProductsCache = null;   // all products loaded once
    let historyLoaded = false;
    let filterNoBarcodeOnly = true;  // default: show only products without barcode

    // ─── Elementos ─────────────────────────────────────────────────────────────
    const sidebar      = document.getElementById('pos-sidebar');
    const toggleBtn    = document.getElementById('sidebar-toggle-btn');
    const toggleIcon   = document.getElementById('sidebar-toggle-icon');
    const closeBtn     = document.getElementById('sidebar-close-btn');
    const tabBtns      = document.querySelectorAll('.sidebar-tab-btn');
    const panes        = document.querySelectorAll('.sidebar-pane');
    const refreshBtn   = document.getElementById('btn-refresh-history');
    const qpSearch     = document.getElementById('quick-products-search');
    const qpList       = document.getElementById('quick-products-list');

    // ─── Init ───────────────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        initToggle();
        initTabs();
        initQuickPayButtons();
        initProductsPane();
        initHistory();
    });

    // ─── Toggle sidebar ─────────────────────────────────────────────────────────
    function setSidebarState(open) {
        sidebarOpen = open;
        sidebar?.classList.toggle('collapsed', !open);
        if (toggleBtn) toggleBtn.classList.toggle('visible', !open);
        if (toggleIcon) toggleIcon.className = open ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
        if (toggleBtn) toggleBtn.title = open ? 'Abrir panel' : 'Abrir panel';
    }

    function initToggle() {
        if (!sidebar) return;
        // Botón externo (solo visible cuando está cerrado)
        toggleBtn?.addEventListener('click', () => setSidebarState(true));
        // Botón X dentro del sidebar
        closeBtn?.addEventListener('click', () => setSidebarState(false));
        // Estado inicial: sidebar abierto, botón externo oculto
        setSidebarState(true);
    }

    // ─── Tabs ───────────────────────────────────────────────────────────────────
    function initTabs() {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => openTab(btn.dataset.tab));
        });
    }

    function openTab(tabId) {
        // Open sidebar if collapsed
        if (!sidebarOpen) {
            setSidebarState(true);
        }
        tabBtns.forEach(b => {
            b.classList.toggle('active', b.dataset.tab === tabId);
            b.setAttribute('aria-selected', b.dataset.tab === tabId);
        });
        panes.forEach(p => {
            p.classList.toggle('active', p.id === `pane-${tabId}`);
        });
        // Load data on demand
        if (tabId === 'history') loadHistory();
        if (tabId === 'products') loadQuickProducts();
    }

    // Expose for external use (keyboard shortcuts, etc.)
    window.POS_sidebar = { openTab, triggerQuickPay };

    // ─── Quick Pay Buttons ──────────────────────────────────────────────────────
    function initQuickPayButtons() {
        document.querySelectorAll('.quick-pay-btn').forEach(btn => {
            btn.addEventListener('click', () => triggerQuickPay(btn.dataset.methodCode));
            btn.addEventListener('keydown', e => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    triggerQuickPay(btn.dataset.methodCode);
                }
            });
        });

        // Keep buttons enabled/disabled in sync with cart
        setInterval(syncQuickPayState, 800);
    }

    function syncQuickPayState() {
        const hasItems = (window.POS_cart?.()?.items?.length || 0) > 0;
        document.querySelectorAll('.quick-pay-btn').forEach(btn => {
            btn.disabled = !hasItems;
        });
    }

    async function triggerQuickPay(methodCode) {
        // Pago Mixto: redirigir al overlay especializado
        if (methodCode === 'mixed') {
            if (window.POS_openMixedCheckout) {
                window.POS_openMixedCheckout();
            } else {
                window.POS_showToast?.('Función de pago mixto no disponible', 'error');
            }
            return;
        }

        const cart = window.POS_cart?.();
        if (!cart || cart.items.length === 0) {
            window.POS_showToast?.('El carrito está vacío', 'warning');
            return;
        }
        const btn = document.querySelector(`.quick-pay-btn[data-method-code="${methodCode}"]`);
        const methodName = btn?.dataset.methodName || methodCode;

        try {
            btn?.classList.add('disabled');
            window.POS_showToast?.(`Procesando con ${methodName}...`, 'info');

            const resp = await fetch(API_URLS.quickCheckout, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ transaction_id: TRANSACTION_ID, method_code: methodCode }),
            });
            const data = await resp.json();

            if (data.success) {
                showQuickPaySuccess(data);
            } else {
                window.POS_showToast?.(data.error || 'Error al cobrar', 'error');
                btn?.classList.remove('disabled');
            }
        } catch (err) {
            console.error('Quick pay error:', err);
            window.POS_showToast?.('Error de conexión', 'error');
            btn?.classList.remove('disabled');
        }
    }

    function showQuickPaySuccess(data) {
        const change = parseFloat(data.change || 0);
        const changeHtml = change > 0
            ? `<div class="alert alert-warning my-3"><i class="fas fa-coins me-2"></i><strong>Vuelto: ${window.POS_formatCurrency?.(change) || '$' + change}</strong></div>`
            : '';

        const html = `
        <div class="modal fade" id="quickPaySuccessModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark text-white">
                    <div class="modal-body text-center py-4">
                        <i class="fas fa-check-circle text-success mb-3" style="font-size:4rem"></i>
                        <h4 class="mb-1">¡Cobrado con ${data.method_name}!</h4>
                        <p class="text-muted mb-1">Ticket: <strong class="text-white">${data.ticket_number}</strong></p>
                        <p class="h4 mb-2">Total: <strong class="text-success">${window.POS_formatCurrency?.(data.total) || '$' + data.total}</strong></p>
                        ${changeHtml}
                        <div class="d-flex justify-content-center gap-3 mt-3">
                            <button class="btn btn-outline-light btn-lg" id="qps-skip">
                                <i class="fas fa-forward me-2"></i>Continuar
                            </button>
                            <button class="btn btn-primary btn-lg" id="qps-print">
                                <i class="fas fa-print me-2"></i>Imprimir
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

        document.getElementById('quickPaySuccessModal')?.remove();
        document.body.insertAdjacentHTML('beforeend', html);

        const el = document.getElementById('quickPaySuccessModal');
        const modal = new bootstrap.Modal(el);
        modal.show();

        el.addEventListener('shown.bs.modal', () => document.getElementById('qps-skip')?.focus(), { once: true });

        document.getElementById('qps-print').addEventListener('click', () => {
            window.open(`/pos/ticket/${data.transaction_id}/`, '_blank', 'width=320,height=500,menubar=no,toolbar=no');
            modal.hide();
            window.location.reload();
        });
        document.getElementById('qps-skip').addEventListener('click', () => {
            modal.hide();
            window.location.reload();
        });
        el.addEventListener('hidden.bs.modal', () => el.remove());

        // Keyboard: P = print, Enter/Esc = skip
        el.addEventListener('keydown', e => {
            if (e.key === 'p' || e.key === 'P') { e.preventDefault(); document.getElementById('qps-print')?.click(); }
        });
    }

    // ─── Products Pane ──────────────────────────────────────────────────────────
    function initProductsPane() {
        if (!qpSearch) return;
        qpSearch.addEventListener('input', () => renderProducts(qpSearch.value.trim().toLowerCase()));

        const toggleBtn = document.getElementById('toggle-no-barcode');
        if (toggleBtn) {
            updateToggleBtnStyle(toggleBtn);
            toggleBtn.addEventListener('click', () => {
                filterNoBarcodeOnly = !filterNoBarcodeOnly;
                updateToggleBtnStyle(toggleBtn);
                renderProducts(qpSearch.value.trim().toLowerCase());
            });
        }
    }

    function updateToggleBtnStyle(btn) {
        if (filterNoBarcodeOnly) {
            btn.style.background = 'rgba(0,210,211,0.25)';
            btn.style.borderColor = '#00d2d3';
            btn.style.color = '#fff';
            btn.title = 'Mostrando solo sin código — click para ver todos';
        } else {
            btn.style.background = 'rgba(0,210,211,0.06)';
            btn.style.borderColor = 'rgba(0,210,211,0.2)';
            btn.style.color = '#00d2d3';
            btn.title = 'Mostrando todos — click para filtrar sin código';
        }
    }

    async function loadQuickProducts() {
        if (quickProductsCache !== null) { renderProducts(qpSearch?.value?.trim().toLowerCase() || ''); return; }

        if (qpList) qpList.innerHTML = '<p style="color:#888;text-align:center;padding:20px 0"><i class="fas fa-spinner fa-spin me-1"></i>Cargando...</p>';

        try {
            // Usar endpoint dedicado que devuelve todos los productos activos
            const resp = await fetch(API_URLS.allProducts);
            const data = await resp.json();
            quickProductsCache = data.products || [];
            renderProducts('');
        } catch (err) {
            console.error('Load products error:', err);
            if (qpList) qpList.innerHTML = '<p style="color:#e74c3c;text-align:center;padding:16px">Error al cargar productos.</p>';
        }
    }

    function renderProducts(filter) {
        if (!qpList || quickProductsCache === null) return;

        let list = quickProductsCache;

        // Filter: only products without barcode
        if (filterNoBarcodeOnly) {
            list = list.filter(p => !p.barcode);
        }

        // Text filter
        if (filter) {
            list = list.filter(p =>
                p.name.toLowerCase().includes(filter) ||
                (p.barcode || '').includes(filter) ||
                (p.sku || '').toLowerCase().includes(filter) ||
                (p.category || '').toLowerCase().includes(filter)
            );
        }

        if (list.length === 0) {
            const msg = filterNoBarcodeOnly
                ? 'Todos los productos tienen código de barras.'
                : 'Sin resultados.';
            qpList.innerHTML = `<p style="color:#888;text-align:center;padding:16px">${msg}</p>`;
            return;
        }

        // Group by category
        const grouped = {};
        list.forEach(p => {
            const cat = p.category || 'Sin categoría';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(p);
        });

        let html = '';
        Object.keys(grouped).sort().forEach(catName => {
            const products = grouped[catName];
            html += `
                <div class="qp-category-header" style="
                    padding:5px 6px;margin-top:6px;margin-bottom:2px;
                    background:rgba(0,210,211,0.06);border-radius:4px;
                    font-size:0.7rem;font-weight:700;color:#00d2d3;
                    text-transform:uppercase;letter-spacing:0.05em;
                    display:flex;justify-content:space-between;align-items:center;
                    cursor:pointer;user-select:none;" data-cat="${catName}">
                    <span><i class="fas fa-tag me-1" style="font-size:0.6rem;"></i>${catName}</span>
                    <span style="font-size:0.62rem;color:#666;">${products.length} prod.</span>
                </div>
            `;
            products.slice(0, 50).forEach(p => {
                const stockColor = p.stock <= 0 ? '#e74c3c' : p.stock <= 5 ? '#f0c040' : '#2ecc71';
                const starClass = p.is_quick ? 'fas' : 'far';
                const starColor = p.is_quick ? '#F5D000' : '#555';
                const hasBarcode = !!p.barcode;
                // SKU badge: prominent for products without barcode
                const codeBadge = hasBarcode
                    ? `<span style="font-size:0.6rem;color:#777;">${p.barcode}</span>`
                    : `<span style="display:inline-block;font-size:0.7rem;font-weight:700;color:#00d2d3;
                            background:rgba(0,210,211,0.12);padding:1px 6px;border-radius:3px;
                            border:1px solid rgba(0,210,211,0.25);font-family:monospace;letter-spacing:0.05em;">
                        ${p.sku || '—'}
                       </span>`;

                html += `
                    <div class="quick-product-item" tabindex="0"
                         data-product-id="${p.id}" data-is-bulk="${p.is_bulk}"
                         role="button" title="${p.name}&#10;Código: ${p.sku || '—'}&#10;Venta: $${p.unit_price}&#10;Stock: ${p.stock}">
                        <span class="quick-product-name" style="flex:1;min-width:0;">
                            ${p.name}
                            <span style="display:block;margin-top:2px;">
                                ${codeBadge}
                            </span>
                        </span>
                        <span style="display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0;gap:1px;">
                            <span style="display:flex;align-items:center;gap:4px;">
                                <span class="quick-product-price" style="font-size:0.76rem;">${window.POS_formatCurrency?.(p.unit_price) || '$' + p.unit_price}</span>
                                <i class="${starClass} fa-star btn-toggle-quick" data-pid="${p.id}"
                                   style="color:${starColor};cursor:pointer;font-size:0.78rem;" title="Acceso rápido"></i>
                            </span>
                            <span style="font-size:0.58rem;color:${stockColor};font-weight:600;">stk: ${p.stock}</span>
                        </span>
                    </div>
                `;
            });
        });

        qpList.innerHTML = html;

        qpList.querySelectorAll('.quick-product-item').forEach(item => {
            const addProduct = () => {
                const id = parseInt(item.dataset.productId);
                document.dispatchEvent(new CustomEvent('pos:addToCart', { detail: { productId: id, quantity: 1 } }));
            };
            item.addEventListener('click', e => {
                if (e.target.closest('.btn-toggle-quick')) return;
                addProduct();
            });
            item.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); addProduct(); } });
        });

        qpList.querySelectorAll('.btn-toggle-quick').forEach(star => {
            star.addEventListener('click', e => {
                e.stopPropagation();
                const pid = parseInt(star.dataset.pid);
                toggleQuickAccess(pid);
            });
        });
    }

    async function toggleQuickAccess(productId) {
        try {
            const resp = await fetch(API_URLS.toggleQuickAccess, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ product_id: productId })
            });
            const data = await resp.json();
            if (!data.success) {
                window.POS_showToast?.(data.error || 'Error', 'danger');
                return;
            }
            // Update cache
            if (quickProductsCache) {
                const p = quickProductsCache.find(x => x.id === productId);
                if (p) p.is_quick = data.is_quick;
            }
            // Re-render product list
            const filterVal = document.getElementById('quick-product-filter')?.value?.toLowerCase()?.trim() || '';
            renderProducts(filterVal || null);
            // Refresh the quick access grid in the main panel
            if (window.POS_refreshQuickAccessGrid) {
                window.POS_refreshQuickAccessGrid(data.buttons);
            }
            window.POS_showToast?.(data.is_quick ? 'Agregado a acceso rápido' : 'Quitado de acceso rápido', 'success');
        } catch (err) {
            console.error('toggleQuickAccess error:', err);
            window.POS_showToast?.('Error al cambiar acceso rápido', 'danger');
        }
    }

    // ─── Sales History ──────────────────────────────────────────────────────────
    function initHistory() {
        refreshBtn?.addEventListener('click', () => { historyLoaded = false; loadHistory(); });
    }

    async function loadHistory() {
        if (historyLoaded) return;
        const list = document.getElementById('sales-history-list');
        if (!list) return;
        list.innerHTML = '<p style="color:#888;text-align:center;padding:16px"><i class="fas fa-spinner fa-spin me-1"></i>Cargando...</p>';

        try {
            const resp = await fetch(API_URLS.salesHistory);
            const data = await resp.json();
            historyLoaded = true;

            if (!data.success || !data.transactions?.length) {
                list.innerHTML = '<p id="history-empty" style="color:#888;font-size:.82rem;text-align:center;padding:20px 0"><i class="fas fa-info-circle me-1"></i>No hay ventas aún.</p>';
                return;
            }

            list.innerHTML = data.transactions.map(tx => `
                <div class="history-item" tabindex="0" data-tx-id="${tx.id}" role="button">
                    <div class="d-flex justify-content-between align-items-baseline">
                        <span class="history-ticket">${tx.ticket_number}</span>
                        <span class="history-time">${tx.completed_at}</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-baseline mt-1">
                        <span class="history-total">${window.POS_formatCurrency?.(tx.total) || '$' + tx.total}</span>
                        <span style="font-size:.7rem;color:#888">${tx.transaction_type}</span>
                    </div>
                    <div class="history-preview">${tx.items_preview}</div>
                    <div class="history-payments">${tx.payments.join(' + ')}</div>
                    <button class="btn btn-outline-info btn-reprint-history"
                            data-tx-id="${tx.id}" title="Reimprimir ticket ${tx.ticket_number}">
                        <i class="fas fa-print me-1"></i>Reimprimir
                    </button>
                </div>
            `).join('');

            list.querySelectorAll('.btn-reprint-history').forEach(btn => {
                btn.addEventListener('click', e => {
                    e.stopPropagation();
                    const txId = btn.dataset.txId;
                    window.open(`/pos/ticket/${txId}/`, '_blank', 'width=320,height=500,menubar=no,toolbar=no');
                });
            });

        } catch (err) {
            console.error('History load error:', err);
            list.innerHTML = '<p style="color:#e74c3c;text-align:center;padding:16px">Error al cargar historial.</p>';
        }
    }

    // ─── Bridge: pos-main exposes addToCart via custom event ────────────────────
    // pos-main.js must listen for this to work:
    // (added at bottom of pos-main.js via the exposed global)
    document.addEventListener('pos:addToCart', async (e) => {
        const { productId, quantity } = e.detail;
        try {
            const resp = await fetch(API_URLS.addToCart, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ transaction_id: TRANSACTION_ID, product_id: productId, quantity }),
            });
            const data = await resp.json();
            if (data.success) {
                window.POS_showToast?.(data.message || 'Producto agregado', 'success');
                window.POS_loadCart?.();
            } else {
                window.POS_showToast?.(data.error || 'Error al agregar', 'error');
            }
        } catch (err) {
            window.POS_showToast?.('Error de conexión', 'error');
        }
    });

})();
