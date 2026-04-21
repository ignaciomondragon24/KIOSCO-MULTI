/* CHE GOLOSO - POS Main JavaScript (Updated) */

(function() {
    'use strict';

    // State
    let cart = {
        items: [],
        subtotal: 0,
        discount: 0,
        total: 0,
        itemCount: 0
    };

    let currentProduct = null;
    let searchTimeout = null;
    let cartFocusIndex = -1; // îndice del cart-item activo por teclado (-1 = ninguno)

    // DOM Elements
    const productSearch = document.getElementById('product-search');
    const searchResults = document.getElementById('search-results');
    const searchResultsList = document.getElementById('search-results-list');
    const cartItems = document.getElementById('cart-items');
    const cartSubtotal = document.getElementById('cart-subtotal');
    const cartDiscount = document.getElementById('cart-discount');
    const discountRow = document.getElementById('discount-row');
    const cartTotal = document.getElementById('cart-total');
    const cartItemsCount = document.getElementById('cart-items-count');
    const btnCheckout = document.getElementById('btn-checkout');
    const btnClearCart = document.getElementById('clear-cart');
    const quickAccessGrid = document.getElementById('quick-access-grid');

    // ── Custom confirm modal (reemplaza confirm() nativo de Chrome) ──────────
    function posConfirm(message, onYes) {
        const id = 'pos-confirm-modal';
        document.getElementById(id)?.remove();
        const html = `
            <div id="${id}" style="position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);animation:fcoFadeIn .15s ease-out;">
                <div style="background:linear-gradient(180deg,#1e1e3a,#161628);border:1px solid rgba(0,210,211,0.18);border-radius:16px;padding:2rem 2.2rem 1.5rem;max-width:380px;width:90vw;text-align:center;box-shadow:0 30px 80px rgba(0,0,0,0.6);">
                    <i class="fas fa-question-circle" style="font-size:2.4rem;color:#00d2d3;margin-bottom:1rem;"></i>
                    <p style="color:#eaeaea;font-size:1.05rem;font-weight:600;margin-bottom:1.5rem;">${message}</p>
                    <div style="display:flex;gap:10px;justify-content:center;">
                        <button type="button" id="${id}-no" style="background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.15);color:#aaa;border-radius:10px;padding:9px 28px;font-weight:600;font-size:0.95rem;cursor:pointer;">Cancelar</button>
                        <button type="button" id="${id}-yes" style="background:rgba(231,76,60,0.12);border:1.5px solid rgba(231,76,60,0.35);color:#e74c3c;border-radius:10px;padding:9px 28px;font-weight:700;font-size:0.95rem;cursor:pointer;">Confirmar</button>
                    </div>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        const overlay = document.getElementById(id);
        const close = () => { overlay.remove(); productSearch?.focus(); };
        document.getElementById(`${id}-no`).addEventListener('click', close);
        document.getElementById(`${id}-yes`).addEventListener('click', () => { overlay.remove(); onYes(); });
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
        const onEsc = (e) => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); document.removeEventListener('keydown', onEsc, true); } if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); overlay.remove(); onYes(); document.removeEventListener('keydown', onEsc, true); } };
        document.addEventListener('keydown', onEsc, true);
        document.getElementById(`${id}-no`).focus();
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        initClock();
        initSearch();
        initCart();
        initQuickAccess();
        initCheckout();
        initActionButtons();
        initKeyboardShortcuts();
        initQuickAddProduct();
        initHeaderSuspended();
        loadCart();
    });
    
    // Header suspended button
    function initHeaderSuspended() {
        const headerSuspendedBtn = document.getElementById('header-suspended-btn');
        if (headerSuspendedBtn) {
            headerSuspendedBtn.addEventListener('click', () => {
                openSuspendedModal();
            });
        }
    }
    
    // Quick add product
    function initQuickAddProduct() {
        const confirmBtn = document.getElementById('confirm-quick-add');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', handleQuickAddProduct);
        }
        
        // Allow Enter key to submit in the modal
        const quickAddForm = document.getElementById('quick-add-product-form');
        if (quickAddForm) {
            quickAddForm.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleQuickAddProduct();
                }
            });
        }
    }
    
    async function handleQuickAddProduct() {
        const barcode = document.getElementById('quick-add-barcode').value;
        const name = document.getElementById('quick-add-name').value.trim();
        const salePrice = document.getElementById('quick-add-sale-price').value;
        const purchasePrice = document.getElementById('quick-add-purchase-price').value || 0;
        const categoryId = document.getElementById('quick-add-category').value;
        const initialStock = document.getElementById('quick-add-stock').value || 0;
        const shouldAddToCart = document.getElementById('quick-add-to-cart').checked;
        
        // Validation
        if (!name) {
            showToast('El nombre del producto es requerido', 'error');
            document.getElementById('quick-add-name').focus();
            return;
        }
        
        if (!salePrice || parseFloat(salePrice) <= 0) {
            showToast('El precio de venta es requerido', 'error');
            document.getElementById('quick-add-sale-price').focus();
            return;
        }
        
        try {
            const response = await fetch('/pos/api/quick-add-product/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    barcode: barcode,
                    name: name,
                    sale_price: parseFloat(salePrice),
                    purchase_price: parseFloat(purchasePrice),
                    category_id: categoryId || null,
                    initial_stock: parseInt(initialStock)
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast(data.message, 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('quickAddProductModal'));
                if (modal) modal.hide();
                
                // Add to cart if checkbox is checked
                if (shouldAddToCart && data.product) {
                    await addToCart(data.product.id, 1);
                }
                
                // Focus back to search
                if (productSearch) {
                    productSearch.value = '';
                    productSearch.focus();
                }
            } else {
                showToast(data.error || 'Error al crear producto', 'error');
            }
        } catch (error) {
            console.error('Quick add product error:', error);
            showToast('Error al crear producto', 'error');
        }
    }

    // Clock
    function initClock() {
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('es-AR');
            const clockEl = document.getElementById('pos-clock');
            if (clockEl) {
                clockEl.innerHTML = `<i class="fas fa-clock me-1"></i>${timeStr}`;
            }
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // Search
    let _scannerTimer = null;
    let _searchAbortController = null;
    function initSearch() {
        if (!productSearch) return;
        
        productSearch.addEventListener('input', function(e) {
            const val = e.target.value.trim();
            // Si parece un barcode en progreso (solo dígitos), dar más tiempo al scanner
            clearTimeout(_scannerTimer);
            if (/^\d+$/.test(val) && val.length < 13) {
                _scannerTimer = setTimeout(() => handleSearch(e), 500);
            } else {
                _scannerTimer = setTimeout(() => handleSearch(e), 150);
            }
        });
        productSearch.addEventListener('keydown', handleSearchKeydown);
        
        document.addEventListener('click', function(e) {
            if (searchResults && !searchResults.contains(e.target) && e.target !== productSearch) {
                hideSearchResults();
            }
        });
    }

    async function handleSearch(e) {
        const query = e.target.value.trim();
        
        // Empezar a buscar desde 1 caracter
        if (query.length < 1) {
            hideSearchResults();
            return;
        }

        // Cancelar búsqueda anterior en vuelo
        if (_searchAbortController) {
            _searchAbortController.abort();
        }
        _searchAbortController = new AbortController();

        try {
            const response = await fetch(
                `${API_URLS.search}?q=${encodeURIComponent(query)}`,
                { signal: _searchAbortController.signal }
            );
            const data = await response.json();
            
            // Verificar que el input no cambió mientras esperábamos
            if (productSearch.value.trim() !== query) return;
            
            if (data.products && data.products.length > 0) {
                showSearchResults(data.products);
            } else {
                // Solo mostrar mensaje si hay al menos 2 caracteres
                if (query.length >= 2) {
                    showSearchResultsEmpty(query);
                } else {
                    hideSearchResults();
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Search error:', error);
            showToast('Error al buscar productos', 'error');
        }
    }
    
    function showSearchResultsEmpty(query) {
        if (!searchResultsList || !searchResults) return;
        
        // Check if it looks like a barcode (numeric, 8-13 digits)
        const isBarcode = /^\d{8,13}$/.test(query);
        
        if (isBarcode) {
            searchResultsList.innerHTML = `
                <div class="search-result-empty text-center p-3">
                    <i class="fas fa-barcode fa-2x text-warning mb-2"></i>
                    <p class="mb-2 text-light">Código de barras no encontrado:</p>
                    <p class="mb-3"><code class="fs-5">${query}</code></p>
                    <p class="text-muted small mb-3">¿Qué desea hacer?</p>
                    <div class="d-flex justify-content-center gap-2 flex-wrap">
                        <button type="button" class="btn btn-success" onclick="openQuickAddProduct('${query}')">
                            <i class="fas fa-plus-circle me-2"></i>Producto Nuevo
                        </button>
                    </div>
                </div>
            `;
        } else {
            searchResultsList.innerHTML = `
                <div class="search-result-empty text-center text-muted p-3">
                    <i class="fas fa-search mb-2"></i>
                    <p class="mb-0">No se encontraron productos para "${query}"</p>
                </div>
            `;
        }
        searchResults.style.display = 'block';
    }
    
    // Open quick add product modal
    window.openQuickAddProduct = function(barcode) {
        const modal = document.getElementById('quickAddProductModal');
        if (!modal) return;
        
        // Reset form
        document.getElementById('quick-add-barcode').value = barcode;
        document.getElementById('quick-add-name').value = '';
        document.getElementById('quick-add-sale-price').value = '';
        document.getElementById('quick-add-purchase-price').value = '';
        document.getElementById('quick-add-category').value = '';
        document.getElementById('quick-add-stock').value = '1';
        document.getElementById('quick-add-to-cart').checked = true;
        
        // Hide search results
        hideSearchResults();
        
        // Clear search input
        if (productSearch) productSearch.value = '';
        
        // Show modal
        new bootstrap.Modal(modal).show();
        
        // Focus on name field
        setTimeout(() => {
            document.getElementById('quick-add-name').focus();
        }, 500);
    };

    function handleSearchKeydown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(_scannerTimer);
            const query = e.target.value.trim();
            
            // Check if it's a barcode (numeric, 8-13 digits)
            if (/^\d{8,13}$/.test(query)) {
                addProductByBarcode(query);
            } else {
                // Select active (highlighted) result, or first if none highlighted
                const activeResult = searchResultsList?.querySelector('.search-result-item.active')
                    || searchResultsList?.querySelector('.search-result-item');
                if (activeResult) {
                    activeResult.click();
                }
            }
        }
        
        // Arrow keys navigation in search results
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            if (searchResults?.style.display !== 'none') {
                e.preventDefault();
                navigateSearchResults(e.key === 'ArrowDown' ? 1 : -1);
            }
        }

        // Escape → cerrar resultados y limpiar
        if (e.key === 'Escape') {
            if (searchResults?.style.display !== 'none') {
                e.preventDefault();
                hideSearchResults();
                productSearch.value = '';
            }
        }

        // Tab desde búsqueda → activar navegación del carrito
        if (e.key === 'Tab' && !e.shiftKey) {
            if (searchResults?.style.display !== 'none') {
                // Tab con resultados abiertos → seleccionar el activo
                e.preventDefault();
                const activeResult = searchResultsList?.querySelector('.search-result-item.active')
                    || searchResultsList?.querySelector('.search-result-item');
                if (activeResult) activeResult.click();
                return;
            }
            if (cart.items?.length > 0) {
                e.preventDefault();
                hideSearchResults();
                setCartFocus(cartFocusIndex >= 0 ? cartFocusIndex : cart.items.length - 1);
            }
        }
    }

    function navigateSearchResults(direction) {
        const items = searchResultsList?.querySelectorAll('.search-result-item');
        if (!items || items.length === 0) return;
        
        const current = searchResultsList.querySelector('.search-result-item.active');
        let newIndex = 0;
        
        if (current) {
            const currentIndex = Array.from(items).indexOf(current);
            newIndex = currentIndex + direction;
            if (newIndex < 0) newIndex = items.length - 1;
            if (newIndex >= items.length) newIndex = 0;
        } else {
            newIndex = direction > 0 ? 0 : items.length - 1;
        }
        
        items.forEach(item => item.classList.remove('active'));
        items[newIndex].classList.add('active');
        items[newIndex].scrollIntoView({ block: 'nearest' });
    }

    function showSearchResults(products) {
        if (!searchResultsList || !searchResults) return;
        
        searchResultsList.innerHTML = products.map(product => {
            const pkgBadge = product.packaging_type
                ? `<span class="badge bg-${product.packaging_type === 'bulk' ? 'primary' : product.packaging_type === 'display' ? 'info' : 'success'} ms-1">${product.packaging_name || product.packaging_type}</span>`
                : '';
            const stockUnit = product.is_granel ? 'g' : product.unit;
            const stockDisplay = product.stock_in_packaging !== undefined
                ? `Stock: ${product.stock_in_packaging} ${product.packaging_name || 'uds'} (${product.stock} uds)`
                : `Stock: ${product.stock} ${stockUnit}`;
            // SKU badge: prominent for products without barcode
            const codeLine = product.barcode
                ? `${product.barcode}`
                : `<span style="font-weight:700;color:#00d2d3;background:rgba(0,210,211,0.15);padding:1px 6px;border-radius:3px;font-family:monospace;border:1px solid rgba(0,210,211,0.3);">${product.sku || '—'}</span>`;

            return `
            <div class="search-result-item" data-product='${JSON.stringify(product)}'>
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <div class="search-result-name">
                            ${product.name}
                            ${pkgBadge}
                            ${(product.is_bulk || product.is_granel) ? '<span class="badge bg-info ms-1">Granel</span>' : ''}
                            ${product.allow_sell_by_amount ? '<span class="badge bg-warning ms-1">$ Monto</span>' : ''}
                        </div>
                        <div class="search-result-info">
                            ${codeLine} | ${stockDisplay}
                            ${product.is_bulk ? `| $${product.unit_price}/${product.unit}` : ''}
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="search-result-price">${formatCurrency(product.unit_price)}</div>
                        ${product.allow_sell_by_amount ? '<button class="btn btn-sm btn-warning sell-by-amount-btn" data-product-id="' + product.id + '"><i class="fas fa-dollar-sign"></i></button>' : ''}
                    </div>
                </div>
            </div>
        `}).join('');
        
        searchResults.style.display = 'block';
        
        // Auto-highlight first result
        const firstItem = searchResultsList.querySelector('.search-result-item');
        if (firstItem) firstItem.classList.add('active');
        
        // Add click handlers for regular items
        searchResultsList.querySelectorAll('.search-result-item').forEach(item => {
            // Mouse hover → highlight this item
            item.addEventListener('mouseenter', function() {
                searchResultsList.querySelectorAll('.search-result-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
            });

            item.addEventListener('click', function(e) {
                // Don't trigger if clicking the sell-by-amount button
                if (e.target.closest('.sell-by-amount-btn')) return;
                
                const product = JSON.parse(this.dataset.product);
                
                // For bulk/granel products, show quantity/weight modal
                if (product.is_bulk || product.is_granel) {
                    showBulkQuantityModal(product);
                } else if (!product.packaging_id && product.packagings && product.packagings.length > 1) {
                    // Producto con varios niveles de empaque y no matchee por barcode
                    // → pedir al usuario que elija unidad / display / bulto.
                    showPackagingSelector(product);
                } else {
                    addToCart(product.id, 1, product.packaging_id || null);
                    hideSearchResults();
                    productSearch.value = '';
                    productSearch.focus();
                }
            });
        });
        
        // Add handlers for sell-by-amount buttons
        searchResultsList.querySelectorAll('.sell-by-amount-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const productItem = this.closest('.search-result-item');
                const product = JSON.parse(productItem.dataset.product);
                showSellByAmountModal(product);
            });
        });
    }
    
    function showPackagingSelector(product) {
        const pkgs = product.packagings || [];
        const unitOption = {
            id: null,
            type_display: 'Unidad',
            name: product.name,
            sale_price: product.unit_price,
            stock_in_packaging: product.stock,
            units_quantity: 1,
            packaging_type: 'unit',
        };
        const options = [unitOption, ...pkgs.filter(p => p.packaging_type !== 'unit')];

        const rowsHtml = options.map((o, i) => {
            const typeClass = o.packaging_type === 'bulk' ? 'primary'
                : o.packaging_type === 'display' ? 'info'
                : 'success';
            return `
            <button type="button" class="list-group-item list-group-item-action pkg-select-btn d-flex justify-content-between align-items-center"
                    data-pkg-id="${o.id || ''}" data-idx="${i}">
                <div class="text-start">
                    <div class="fw-bold">
                        <span class="badge bg-${typeClass} me-1">${o.type_display}</span>
                        ${o.name}
                    </div>
                    <small class="text-muted">Stock: ${o.stock_in_packaging} · ${o.units_quantity} u/empaque</small>
                </div>
                <span class="fs-5 fw-bold">${formatCurrency(o.sale_price)}</span>
            </button>`;
        }).join('');

        const modalHtml = `
        <div class="modal fade" id="packagingSelectorModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Elegí el empaque · ${product.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-0">
                        <div class="list-group list-group-flush">
                            ${rowsHtml}
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

        // Reemplazar modal previo si quedo en el DOM
        const prev = document.getElementById('packagingSelectorModal');
        if (prev) prev.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modalEl = document.getElementById('packagingSelectorModal');
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();

        modalEl.querySelectorAll('.pkg-select-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const idx = parseInt(this.dataset.idx);
                const chosen = options[idx];
                bsModal.hide();
                addToCart(product.id, 1, chosen.id || null);
                hideSearchResults();
                if (productSearch) {
                    productSearch.value = '';
                    productSearch.focus();
                }
            });
        });

        modalEl.addEventListener('hidden.bs.modal', () => modalEl.remove());
    }

    function showBulkQuantityModal(product) {
        const isGranel = !!product.is_granel;
        // Los productos granel de caramelera siempre usan precio/100g como base
        const priceWeight = 100;
        const pricePerKg = isGranel ? (product.sale_price_250g || 0) : 0;
        const unitLabel = isGranel ? 'gramos' : product.unit;
        const defaultVal = isGranel ? '100' : '0.500';
        const stepVal = isGranel ? '1' : '0.001';
        const minVal = isGranel ? '1' : '0.001';

        let priceLabel;
        if (isGranel) {
            priceLabel = `${formatCurrency(product.unit_price)}/100g`;
            if (pricePerKg > 0) {
                priceLabel += ` · ${formatCurrency(pricePerKg)}/kg`;
            }
        } else {
            priceLabel = `${formatCurrency(product.unit_price)}/${product.unit}`;
        }

        function calcTotal(grams) {
            if (!isGranel) return grams * product.unit_price;
            // >= 250g con precio por kilo: regla de tres
            if (pricePerKg > 0 && grams >= 250) {
                return (grams / 1000) * pricePerKg;
            }
            // < 250g o sin precio kilo: proporcional al precio/100g
            return (grams / priceWeight) * product.unit_price;
        }

        function priceBreakdown(grams) {
            if (!isGranel || grams <= 0) return '';
            if (pricePerKg > 0 && grams >= 250) {
                return `<small class="text-warning">${grams}g × ${formatCurrency(pricePerKg)}/kg</small>`;
            }
            return `<small class="text-muted">${grams}g × ${formatCurrency(product.unit_price)}/100g</small>`;
        }

        const stockGrams = product.stock != null ? Math.floor(product.stock) : 0;

        const modalHtml = `
            <div class="modal fade" id="bulkQuantityModal" tabindex="-1">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content bg-dark text-white" style="border:1.5px solid rgba(233,30,140,0.25);border-radius:14px;">
                        <div class="modal-header border-0 pb-1">
                            <div>
                                <h5 class="modal-title mb-0">
                                    <i class="fas fa-candy-cane me-2" style="color:#E91E8C;"></i>${product.name}
                                </h5>
                                <small style="color:#aaa;">${priceLabel}</small>
                            </div>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pt-2">
                            ${isGranel ? `
                            <div class="d-flex gap-2 mb-3">
                                <button type="button" class="btn btn-sm btn-outline-info granel-quick-gram" data-grams="100" style="flex:1;">
                                    100g<br><small style="color:#aaa;">${formatCurrency(calcTotal(100))}</small>
                                </button>
                                <button type="button" class="btn btn-sm ${pricePerKg > 0 ? 'btn-outline-warning' : 'btn-outline-info'} granel-quick-gram" data-grams="250" style="flex:1;">
                                    ¼ kg<br><small style="color:#aaa;">${formatCurrency(calcTotal(250))}</small>
                                </button>
                                <button type="button" class="btn btn-sm ${pricePerKg > 0 ? 'btn-outline-warning' : 'btn-outline-info'} granel-quick-gram" data-grams="500" style="flex:1;">
                                    ½ kg<br><small style="color:#aaa;">${formatCurrency(calcTotal(500))}</small>
                                </button>
                            </div>` : ''}
                            <label class="form-label" style="color:#aaa;font-size:0.82rem;">Peso en gramos</label>
                            <input type="number"
                                   class="form-control form-control-lg text-center"
                                   id="bulk-quantity-input"
                                   min="${minVal}"
                                   step="${stepVal}"
                                   value="${defaultVal}"
                                   autofocus
                                   style="background:#0d0d1f;border:2px solid rgba(233,30,140,0.3);color:#fff;font-weight:700;font-size:1.5rem;border-radius:10px;">
                            ${isGranel ? `<div class="text-end mt-1"><small style="color:${stockGrams > 0 ? '#555' : '#ff6b6b'};font-size:0.75rem;">Disponible: ${stockGrams}g</small></div>` : ''}
                            <div class="mt-3 text-center">
                                <div id="bulk-price-breakdown" style="min-height:1.2em;margin-bottom:4px;"></div>
                                <span class="fs-3 fw-bold" style="color:#00d2d3;" id="bulk-total-preview">${formatCurrency(calcTotal(parseFloat(defaultVal)))}</span>
                            </div>
                        </div>
                        <div class="modal-footer border-0 pt-0">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-primary px-4" id="confirm-bulk-quantity">
                                <i class="fas fa-cart-plus me-1"></i>Agregar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('bulkQuantityModal')?.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = new bootstrap.Modal(document.getElementById('bulkQuantityModal'));
        const input = document.getElementById('bulk-quantity-input');
        const preview = document.getElementById('bulk-total-preview');
        const breakdown = document.getElementById('bulk-price-breakdown');
        const confirmBtn = document.getElementById('confirm-bulk-quantity');

        function updatePreview() {
            const qty = parseFloat(input.value) || 0;
            preview.textContent = formatCurrency(calcTotal(qty));
            if (breakdown) breakdown.innerHTML = priceBreakdown(qty);
            // Validar stock para granel
            if (isGranel && stockGrams > 0 && qty > stockGrams) {
                confirmBtn.disabled = true;
                confirmBtn.title = 'Excede el stock disponible';
                input.style.borderColor = '#ff6b6b';
            } else {
                confirmBtn.disabled = false;
                confirmBtn.title = '';
                input.style.borderColor = 'rgba(233,30,140,0.3)';
            }
        }

        input.addEventListener('input', updatePreview);
        updatePreview();

        // Quick gram buttons
        document.querySelectorAll('.granel-quick-gram').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.dataset.grams;
                updatePreview();
                input.focus();
            });
        });

        confirmBtn.addEventListener('click', () => {
            const qty = parseFloat(input.value) || 0;
            if (qty > 0) {
                // For granel: pass price per gram so backend calculates unit_price * quantity correctly
                const priceOverride = isGranel ? (calcTotal(qty) / qty) : null;
                addToCart(product.id, qty, null, priceOverride);
                modal.hide();
                hideSearchResults();
                productSearch.value = '';
                productSearch.focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                confirmBtn.click();
            }
        });

        modal.show();
        setTimeout(() => input.select(), 200);
    }
    
    function showSellByAmountModal(product) {
        const modalHtml = `
            <div class="modal fade" id="sellByAmountModal" tabindex="-1">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content bg-dark text-white">
                        <div class="modal-header border-secondary bg-warning bg-opacity-25">
                            <h5 class="modal-title"><i class="fas fa-dollar-sign me-2"></i>Venta por Monto</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-2"><strong>${product.name}</strong></p>
                            <p class="text-muted mb-3">Precio: ${formatCurrency(product.unit_price)}/${product.unit}</p>
                            
                            <label class="form-label">¿Cuánto querés vender?</label>
                            <div class="input-group input-group-lg">
                                <span class="input-group-text bg-warning text-dark">$</span>
                                <input type="number" 
                                       class="form-control bg-secondary text-white text-center" 
                                       id="sell-amount-input"
                                       min="1"
                                       step="1"
                                       value="500"
                                       autofocus>
                            </div>
                            
                            <!-- Quick amount buttons -->
                            <div class="d-flex gap-2 mt-3 flex-wrap">
                                <button type="button" class="btn btn-outline-warning quick-amount-btn" data-amount="100">$100</button>
                                <button type="button" class="btn btn-outline-warning quick-amount-btn" data-amount="200">$200</button>
                                <button type="button" class="btn btn-outline-warning quick-amount-btn" data-amount="500">$500</button>
                                <button type="button" class="btn btn-outline-warning quick-amount-btn" data-amount="1000">$1000</button>
                                <button type="button" class="btn btn-outline-warning quick-amount-btn" data-amount="2000">$2000</button>
                            </div>
                            
                            <div class="mt-4 p-3 bg-secondary rounded">
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Cantidad:</span>
                                    <strong id="amount-quantity-preview">-- ${product.unit}</strong>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Total real:</span>
                                    <strong id="amount-total-preview" class="text-warning">$--</strong>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-secondary">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <button type="button" class="btn btn-warning text-dark" id="confirm-sell-amount">
                                <i class="fas fa-cart-plus me-1"></i>Agregar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('sellByAmountModal')?.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('sellByAmountModal'));
        const input = document.getElementById('sell-amount-input');
        const qtyPreview = document.getElementById('amount-quantity-preview');
        const totalPreview = document.getElementById('amount-total-preview');
        const confirmBtn = document.getElementById('confirm-sell-amount');
        
        async function updatePreview() {
            const amount = parseFloat(input.value) || 0;
            if (amount <= 0) {
                qtyPreview.textContent = `-- ${product.unit}`;
                totalPreview.textContent = '$--';
                return;
            }
            
            try {
                const response = await fetch('/pos/api/calculate-by-amount/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN
                    },
                    body: JSON.stringify({
                        product_id: product.id,
                        amount: amount
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    qtyPreview.textContent = `${data.quantity.toFixed(3)} ${data.unit}`;
                    totalPreview.textContent = formatCurrency(data.actual_total);
                }
            } catch (error) {
                console.error('Calculate error:', error);
            }
        }
        
        input.addEventListener('input', debounce(updatePreview, 300));
        
        // Quick amount buttons
        document.querySelectorAll('.quick-amount-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.dataset.amount;
                updatePreview();
            });
        });
        
        confirmBtn.addEventListener('click', async () => {
            const amount = parseFloat(input.value) || 0;
            if (amount <= 0) return;
            
            try {
                const response = await fetch('/pos/api/cart/add-by-amount/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN
                    },
                    body: JSON.stringify({
                        transaction_id: TRANSACTION_ID,
                        product_id: product.id,
                        amount: amount
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    showToast(data.message, 'success');
                    await loadCart();
                    modal.hide();
                    hideSearchResults();
                    productSearch.value = '';
                    productSearch.focus();
                } else {
                    showToast(data.error, 'error');
                }
            } catch (error) {
                console.error('Add by amount error:', error);
                showToast('Error al agregar producto', 'error');
            }
        });
        
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                confirmBtn.click();
            }
        });
        
        modal.show();
        setTimeout(() => {
            input.select();
            updatePreview();
        }, 200);
    }

    function hideSearchResults() {
        if (searchResults) {
            searchResults.style.display = 'none';
        }
    }

    async function addProductByBarcode(barcode) {
        try {
            const response = await fetch(`${API_URLS.search}?q=${barcode}`);
            const data = await response.json();
            
            if (data.products && data.products.length > 0) {
                const product = data.products[0];
                // For bulk/granel products, show weight modal
                if (product.is_bulk || product.is_granel) {
                    showBulkQuantityModal(product);
                } else {
                    addToCart(product.id, 1, product.packaging_id || null);
                    productSearch.value = '';
                }
            } else {
                // Product not found - open modal with options
                openQuickAddProduct(barcode);
            }
        } catch (error) {
            console.error('Barcode search error:', error);
            showToast('Error al buscar producto', 'error');
        }
    }

    // Cart
    function initCart() {
        if (btnClearCart) {
            btnClearCart.addEventListener('click', clearCart);
        }
        document.getElementById('cart-nav-up')?.addEventListener('click', () => {
            if (!cart.items?.length) return;
            navigateCart(-1);
        });
        document.getElementById('cart-nav-down')?.addEventListener('click', () => {
            if (!cart.items?.length) return;
            navigateCart(1);
        });
    }

    // ── Helpers de navegación del carrito por teclado ─────────────────────────
    function setCartFocus(idx) {
        const items = cartItems ? Array.from(cartItems.querySelectorAll('.cart-item')) : [];
        if (!items.length) { cartFocusIndex = -1; return; }
        if (idx < 0) idx = items.length - 1;
        if (idx >= items.length) idx = 0;
        items.forEach(i => i.classList.remove('kb-active'));
        cartFocusIndex = idx;
        items[idx].classList.add('kb-active');
        items[idx].focus();
        items[idx].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        document.getElementById('cart-kb-hint')?.classList.add('visible');
    }

    function clearCartFocus() {
        cartFocusIndex = -1;
        cartItems?.querySelectorAll('.cart-item').forEach(i => i.classList.remove('kb-active'));
        document.getElementById('cart-kb-hint')?.classList.remove('visible');
    }

    function navigateCart(dir) {
        const items = cartItems ? Array.from(cartItems.querySelectorAll('.cart-item')) : [];
        if (!items.length) return;
        const newIdx = cartFocusIndex < 0
            ? (dir > 0 ? 0 : items.length - 1)
            : cartFocusIndex + dir;
        setCartFocus(newIdx);
    }

    async function loadCart() {
        try {
            const response = await fetch(API_URLS.getCart);
            const data = await response.json();
            
            if (data.items) {
                cart = {
                    items: data.items,
                    subtotal: data.totals?.subtotal || 0,
                    discount: data.totals?.discount || 0,
                    total: data.totals?.total || 0,
                    itemCount: data.totals?.items_count || 0
                };
                renderCart();
            }
        } catch (error) {
            console.error('Load cart error:', error);
        }
    }

    async function addToCart(productId, quantity = 1, packagingId = null, unitPrice = null) {
        try {
            const payload = {
                transaction_id: TRANSACTION_ID,
                product_id: productId,
                quantity: quantity
            };
            if (packagingId) {
                payload.packaging_id = packagingId;
            }
            if (unitPrice !== null) {
                payload.unit_price = unitPrice;
            }
            const response = await fetch(API_URLS.addToCart, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload cart to get updated items
                await loadCart();
                if (data.warning) {
                    showToast(data.warning, 'warning');
                } else {
                    showToast(data.message || 'Producto agregado', 'success');
                }
            } else {
                showToast(data.error || 'Error al agregar producto', 'error');
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            showToast('Error al agregar producto', 'error');
        }
    }

    async function updateCartItem(itemId, quantity) {
        try {
            const response = await fetch(`${API_URLS.updateCart}${itemId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    quantity: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                await loadCart();
            } else {
                showToast(data.error || 'Error al actualizar', 'error');
            }
        } catch (error) {
            console.error('Update cart error:', error);
        }
    }

    async function removeCartItem(itemId) {
        try {
            const response = await fetch(`${API_URLS.removeFromCart}${itemId}/remove/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                await loadCart();
                showToast('Producto eliminado', 'info');
            }
        } catch (error) {
            console.error('Remove from cart error:', error);
        }
    }

    async function clearCart() {
        posConfirm('¿Está seguro de vaciar el carrito?', doClearCart);
    }

    async function doClearCart() {
        try {
            const response = await fetch(API_URLS.clearCart, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                cart = { items: [], subtotal: 0, discount: 0, total: 0, itemCount: 0 };
                renderCart();
                showToast('Carrito vaciado', 'info');
            }
        } catch (error) {
            console.error('Clear cart error:', error);
        }
    }

    function renderCart() {
        if (!cartItems) return;
        
        const btnCostSale = document.getElementById('btn-cost-sale');
        const btnInternalConsumption = document.getElementById('btn-internal-consumption');
        const btnMixedPay = document.getElementById('btn-mixed-pay');
        
        if (!cart.items || cart.items.length === 0) {
            cartItems.innerHTML = `
                <div class="cart-empty text-center text-muted py-5">
                    <i class="fas fa-shopping-basket fa-3x mb-3"></i>
                    <p>El carrito está vacío</p>
                    <small>Escanee o busque productos para agregar</small>
                </div>
            `;
            if (btnCheckout) btnCheckout.disabled = true;
            if (btnCostSale) btnCostSale.disabled = true;
            if (btnInternalConsumption) btnInternalConsumption.disabled = true;
            if (btnMixedPay) btnMixedPay.disabled = true;
        } else {
            cartItems.innerHTML = cart.items.map(item => {
                const pkgLabel = item.packaging_name
                    ? `<span class="badge bg-${item.packaging_type === 'bulk' ? 'primary' : item.packaging_type === 'display' ? 'info' : 'success'} ms-1" style="font-size:.65em">${item.packaging_name}</span>`
                    : '';
                // For granel items, show weight in grams as item name
                const displayName = item.is_granel
                    ? `${item.quantity % 1 === 0 ? item.quantity : parseFloat(item.quantity).toFixed(1)}g de ${item.product_name || item.name}`
                    : (item.product_name || item.name);

                // Descuento manual (botón) — ya NO se mezcla con la promo
                const manualDiscount = parseFloat(item.discount || 0);
                const promoDiscount  = parseFloat(item.promotion_discount || 0);
                const hasPromo       = promoDiscount > 0 || !!item.promotion_name;
                const groupName      = item.promotion_group_name || '';

                // Etiqueta descriptiva del tipo de promo
                let promoLabel = 'Promo';
                if (item.promotion_type === 'nxm') {
                    promoLabel = `${item.promotion_qty_required}x${item.promotion_qty_charged}`;
                } else if (item.promotion_type === 'nx_fixed_price') {
                    promoLabel = `${item.promotion_qty_required}x${formatCurrency(item.promotion_final_price)}`;
                } else if (item.promotion_type === 'quantity_discount') {
                    promoLabel = `Dto. ${item.promotion_discount_percent}%`;
                } else if (item.promotion_type === 'second_unit') {
                    promoLabel = `2da un. ${item.promotion_second_unit_discount}% off`;
                } else if (item.promotion_type === 'simple_discount') {
                    promoLabel = `${item.promotion_discount_percent}% off`;
                } else if (item.promotion_type === 'combo') {
                    promoLabel = 'Combo';
                }

                // Detalle: cantidad x precio unitario efectivo
                let promoDetail = '';
                if (hasPromo && item.quantity > 0) {
                    const effectiveUnitPrice = (item.subtotal) / item.quantity;
                    promoDetail = `${parseFloat(item.quantity)} x ${formatCurrency(effectiveUnitPrice)}`;
                }

                // Línea extra con la promo aplicada
                const promoRow = hasPromo ? `
                    <div class="cart-item-promo-row">
                        <span class="promo-tag">
                            <i class="fas fa-tag"></i>Promo ${promoLabel}
                        </span>
                        ${groupName ? `
                            <span class="promo-group" title="Esta promoción está enlazada con otras del mismo grupo">
                                <i class="fas fa-link"></i>Enlazada: ${groupName}
                            </span>
                        ` : ''}
                        ${promoDetail ? `
                            <span class="promo-amount">${promoDetail}</span>
                        ` : ''}
                    </div>
                ` : '';

                return `
                <div class="cart-item" data-item-id="${item.id}">
                    <div class="cart-item-info">
                        <div class="cart-item-name">
                            ${displayName}
                            ${pkgLabel}
                            ${item.is_granel ? '<span class="badge ms-1" style="font-size:.65em;background:rgba(233,30,140,0.2);color:#E91E8C;border:1px solid rgba(233,30,140,0.3);">granel</span>' : ''}
                        </div>
                        <div class="cart-item-price d-flex align-items-center gap-2">
                            <span>${item.is_granel ? formatCurrency(item.unit_price * (item.granel_price_weight_grams || 100)) + `/${item.granel_price_weight_grams || 100}g` : formatCurrency(item.unit_price) + ' c/u'}</span>
                            <button class="btn btn-xs cart-item-discount-btn ${manualDiscount > 0 ? 'btn-success active' : 'btn-outline-warning'}" tabindex="-1"
                                    title="Descuento manual para este producto (separado de la promo)" data-item-id="${item.id}">
                                <i class="fas fa-percent"></i>
                                ${manualDiscount > 0 ? ` -${formatCurrency(manualDiscount)}` : ' Dto.'}
                            </button>
                        </div>
                    </div>
                    <div class="cart-item-quantity">
                        ${item.is_granel ? `
                        <button class="btn btn-sm btn-outline-secondary qty-btn" tabindex="-1" data-action="decrease">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number" class="qty-input" tabindex="-1" value="${item.quantity}" min="1" step="1" style="width:65px;font-size:0.8rem;" title="Gramos">
                        <button class="btn btn-sm btn-outline-secondary qty-btn" tabindex="-1" data-action="increase">
                            <i class="fas fa-plus"></i>
                        </button>
                        ` : `
                        <button class="btn btn-sm btn-outline-secondary qty-btn" tabindex="-1" data-action="decrease">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number" class="qty-input" tabindex="-1" value="${item.quantity}" min="0.001" step="0.001">
                        <button class="btn btn-sm btn-outline-secondary qty-btn" tabindex="-1" data-action="increase">
                            <i class="fas fa-plus"></i>
                        </button>
                        `}
                    </div>
                    <div class="cart-item-subtotal">
                        ${formatCurrency(item.subtotal)}
                    </div>
                    <div class="cart-item-remove" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </div>
                    ${promoRow}
                </div>
            `}).join('');
            
            if (btnCheckout) btnCheckout.disabled = false;
            if (btnCostSale) btnCostSale.disabled = false;
            if (btnInternalConsumption) btnInternalConsumption.disabled = false;
            if (btnMixedPay) btnMixedPay.disabled = false;
            
            // Add event listeners
            cartItems.querySelectorAll('.cart-item').forEach(itemEl => {
                const itemId = itemEl.dataset.itemId;
                
                itemEl.querySelector('.cart-item-remove').addEventListener('click', () => {
                    removeCartItem(itemId);
                });

                itemEl.querySelector('.cart-item-discount-btn')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const itemData = cart.items.find(i => String(i.id) === String(itemId));
                    if (itemData) showItemDiscountModal(itemData);
                });
                
                const qtyInput = itemEl.querySelector('.qty-input');
                qtyInput.addEventListener('change', () => {
                    updateCartItem(itemId, parseFloat(qtyInput.value));
                });
                
                const itemData2 = cart.items.find(i => String(i.id) === String(itemId));
                const granelStep = itemData2 && itemData2.is_granel ? 50 : 1;
                itemEl.querySelectorAll('.qty-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        let qty = parseFloat(qtyInput.value);
                        if (btn.dataset.action === 'increase') {
                            qty += granelStep;
                        } else {
                            qty = Math.max(0, qty - granelStep);
                        }
                        if (qty === 0) {
                            removeCartItem(itemId);
                        } else {
                            updateCartItem(itemId, qty);
                        }
                    });
                });
            });
            
            // ── TECLADO: navegación por ítems del carrito ─────────────────────────────
            const allItems = Array.from(cartItems.querySelectorAll('.cart-item'));
            allItems.forEach((itemEl, idx) => {
                const itemData = cart.items[idx];
                const qtyInput = itemEl.querySelector('.qty-input');

                itemEl.setAttribute('tabindex', '-1');

                itemEl.addEventListener('focus', () => {
                    allItems.forEach(i => i.classList.remove('kb-active'));
                    itemEl.classList.add('kb-active');
                    cartFocusIndex = idx;
                    document.getElementById('cart-kb-hint')?.classList.add('visible');
                });

                itemEl.addEventListener('blur', () => {
                    setTimeout(() => {
                        if (cartItems && !cartItems.contains(document.activeElement)) {
                            clearCartFocus();
                        }
                    }, 80);
                });

                itemEl.addEventListener('keydown', (e) => {
                    switch (e.key) {
                        case 'ArrowUp':
                            e.preventDefault(); e.stopPropagation();
                            setCartFocus(idx - 1 < 0 ? allItems.length - 1 : idx - 1);
                            break;
                        case 'ArrowDown':
                            e.preventDefault(); e.stopPropagation();
                            setCartFocus(idx + 1 >= allItems.length ? 0 : idx + 1);
                            break;
                        case '+': case '=':
                            e.preventDefault(); e.stopPropagation();
                            if (itemData) updateCartItem(itemData.id, (itemData.quantity || 1) + 1);
                            break;
                        case '-': case '_':
                            e.preventDefault(); e.stopPropagation();
                            if (itemData) {
                                const nq = Math.max(0, (itemData.quantity || 1) - 1);
                                if (nq === 0) removeCartItem(itemData.id);
                                else updateCartItem(itemData.id, nq);
                            }
                            break;
                        case 'Delete': case 'Backspace':
                            e.preventDefault(); e.stopPropagation();
                            if (itemData) removeCartItem(itemData.id);
                            setTimeout(() => {
                                const rem = cartItems?.querySelectorAll('.cart-item');
                                if (rem?.length > 0) setCartFocus(Math.min(idx, rem.length - 1));
                                else { clearCartFocus(); productSearch?.focus(); }
                            }, 350);
                            break;
                        case 'Enter':
                            e.preventDefault();
                            if (qtyInput) {
                                qtyInput.classList.add('editing');
                                qtyInput.focus();
                                qtyInput.select();
                            }
                            break;
                        case 'Escape':
                            e.preventDefault(); e.stopPropagation();
                            clearCartFocus();
                            productSearch?.focus();
                            break;
                        case 'Tab':
                            e.preventDefault();
                            if (!e.shiftKey) {
                                if (idx === allItems.length - 1) {
                                    clearCartFocus();
                                    document.getElementById('btn-checkout')?.focus();
                                } else {
                                    setCartFocus(idx + 1);
                                }
                            } else {
                                if (idx === 0) { clearCartFocus(); productSearch?.focus(); }
                                else setCartFocus(idx - 1);
                            }
                            break;
                    }
                });
            });

            // Qty-input: modo edición (Enter/Esc/Tab devuelven al cart-item)
            cartItems.querySelectorAll('.qty-input').forEach((input, idx) => {
                const itemEl = allItems[idx];
                const itemData = cart.items[idx];
                input.addEventListener('focus', () => input.select());
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === 'Escape' || e.key === 'Tab') {
                        e.preventDefault();
                        if (e.key === 'Enter' && itemData)
                            updateCartItem(itemData.id, parseFloat(input.value) || 1);
                        input.classList.remove('editing');
                        setTimeout(() => itemEl?.focus(), 50);
                    }
                });
            });

            // Restaurar kb-active si el carrito se re-renderizó mientras estaba enfocado
            if (cartFocusIndex >= 0 && cartFocusIndex < allItems.length) {
                allItems[cartFocusIndex].classList.add('kb-active');
                document.getElementById('cart-kb-hint')?.classList.add('visible');
            }
        }
        
        // Update totals
        if (cartSubtotal) cartSubtotal.textContent = formatCurrency(cart.subtotal);
        if (cartItemsCount) cartItemsCount.textContent = cart.items?.length || 0;
        
        if (cart.discount > 0) {
            if (cartDiscount) cartDiscount.textContent = `-${formatCurrency(cart.discount)}`;
            if (discountRow) discountRow.style.display = 'flex';
        } else {
            if (discountRow) discountRow.style.display = 'none';
        }
        
        if (cartTotal) cartTotal.textContent = formatCurrency(cart.total);
    }

    // Quick Access
    function initQuickAccess() {
        if (!quickAccessGrid) return;

        quickAccessGrid.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const productId = this.dataset.productId;
                if (!productId) return;
                const isGranel = this.dataset.isGranel === 'true';
                const isBulk = this.dataset.isBulk === 'true';
                if (isGranel || isBulk) {
                    const product = {
                        id: parseInt(productId),
                        name: this.dataset.name || '',
                        is_granel: isGranel,
                        is_bulk: isBulk,
                        unit_price: parseFloat(this.dataset.unitPrice) || 0,
                        sale_price_250g: parseFloat(this.dataset.pricePerKg) || 0,
                        stock: parseFloat(this.dataset.stock) || 0,
                    };
                    showBulkQuantityModal(product);
                } else {
                    addToCart(parseInt(productId), 1);
                }
            });
        });
    }

    function refreshQuickAccessGrid(buttons) {
        if (!quickAccessGrid) return;
        if (!buttons || buttons.length === 0) {
            quickAccessGrid.innerHTML = '<p class="text-muted text-center w-100">No hay botones configurados</p>';
            return;
        }
        let html = '';
        buttons.forEach(b => {
            html += `<button type="button" class="quick-btn" tabindex="-1"
                data-product-id="${b.product_id}"
                data-is-granel="${b.is_granel || false}"
                data-is-bulk="${b.is_bulk || false}"
                data-unit-price="${b.price}"
                data-price-per-kg="${b.sale_price_250g || 0}"
                data-stock="${b.stock || 0}"
                data-name="${b.name}"
                style="background-color: ${b.color};">
                <span class="quick-btn-name">${b.name}</span>
                <span class="quick-btn-price">${formatCurrency(b.price)}</span>
            </button>`;
        });
        quickAccessGrid.innerHTML = html;
        initQuickAccess();
    }

    // Action Buttons
    function initActionButtons() {
        const btnHold = document.getElementById('btn-hold');
        const btnCancel = document.getElementById('btn-cancel');
        const btnDiscount = document.getElementById('btn-discount');
        const btnReprint = document.getElementById('btn-reprint');
        
        // Discount button
        if (btnDiscount) {
            btnDiscount.addEventListener('click', () => {
                if (cart.items.length === 0) {
                    showToast('El carrito está vacío', 'warning');
                    return;
                }
                openDiscountModal();
            });
        }
        
        // Reprint button
        if (btnReprint) {
            btnReprint.addEventListener('click', async () => {
                try {
                    const response = await fetch('/pos/api/last-transaction/');
                    const data = await response.json();
                    
                    if (data.success && data.transaction_id) {
                        window.open(`/pos/ticket/${data.transaction_id}/`, '_blank');
                    } else {
                        showToast('No hay ticket anterior para reimprimir', 'warning');
                    }
                } catch (error) {
                    console.error('Reprint error:', error);
                    showToast('Error al obtener último ticket', 'error');
                }
            });
        }
        
        if (btnHold) {
            btnHold.addEventListener('click', async () => {
                if (cart.items.length === 0) {
                    showToast('El carrito está vacío', 'warning');
                    return;
                }
                
                try {
                    const response = await fetch(`/pos/api/transaction/${TRANSACTION_ID}/suspend/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': CSRF_TOKEN
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showToast('Venta suspendida', 'info');
                        window.location.reload();
                    } else {
                        showToast(data.message || 'Error al suspender', 'error');
                    }
                } catch (error) {
                    console.error('Suspend error:', error);
                }
            });
        }
        
        if (btnCancel) {
            btnCancel.addEventListener('click', async () => {
                if (cart.items.length === 0) {
                    showToast('El carrito está vacío', 'warning');
                    return;
                }
                
                posConfirm('¿Está seguro de cancelar esta venta?', async () => {
                    try {
                        const response = await fetch(`/pos/api/transaction/${TRANSACTION_ID}/cancel/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': CSRF_TOKEN
                            },
                            body: JSON.stringify({ reason: 'Cancelada por cajero' })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            showToast('Venta cancelada', 'info');
                            window.location.reload();
                        } else {
                            showToast(data.message || 'Error al cancelar', 'error');
                        }
                    } catch (error) {
                        console.error('Cancel error:', error);
                    }
                });
            });
        }
        
        // Suspended transactions button
        const btnSuspended = document.getElementById('btn-suspended');
        if (btnSuspended) {
            btnSuspended.addEventListener('click', () => {
                openSuspendedModal();
            });
        }
        
        // Cost Sale button
        const btnCostSale = document.getElementById('btn-cost-sale');
        if (btnCostSale) {
            btnCostSale.addEventListener('click', () => {
                if (cart.items.length === 0) {
                    showToast('El carrito está vacío', 'warning');
                    return;
                }
                openCostSaleModal();
            });
        }
        
        // Internal Consumption button
        const btnInternalConsumption = document.getElementById('btn-internal-consumption');
        if (btnInternalConsumption) {
            btnInternalConsumption.addEventListener('click', () => {
                if (cart.items.length === 0) {
                    showToast('El carrito está vacío', 'warning');
                    return;
                }
                openInternalConsumptionModal();
            });
        }
    }
    
    // Suspended Transactions Modal
    async function openSuspendedModal() {
        try {
            const response = await fetch('/pos/api/suspended-transactions/');
            const data = await response.json();
            
            if (!data.success || !data.transactions || data.transactions.length === 0) {
                showToast('No hay ventas apartadas', 'info');
                return;
            }
            
            // Create modal HTML
            let modalHtml = `
                <div class="modal fade" id="suspendedModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content bg-dark text-light">
                            <div class="modal-header">
                                <h5 class="modal-title"><i class="fas fa-pause-circle me-2"></i>Ventas Apartadas</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="list-group">
            `;
            
            data.transactions.forEach(tx => {
                const date = new Date(tx.created_at);
                const dateStr = date.toLocaleString('es-AR');
                modalHtml += `
                    <div class="list-group-item list-group-item-action bg-secondary text-light d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">Ticket: ${tx.ticket_number || '#' + tx.id}</h6>
                            <small class="text-muted">${dateStr} - ${tx.items_count} producto(s)</small>
                        </div>
                        <div>
                            <span class="badge bg-primary fs-6 me-2">${formatCurrency(tx.total)}</span>
                            <button class="btn btn-success btn-sm" onclick="resumeTransaction(${tx.id})">
                                <i class="fas fa-play me-1"></i>Retomar
                            </button>
                        </div>
                    </div>
                `;
            });
            
            modalHtml += `
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove existing modal if present
            const existingModal = document.getElementById('suspendedModal');
            if (existingModal) existingModal.remove();
            
            // Add modal to DOM
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('suspendedModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading suspended transactions:', error);
            showToast('Error al cargar ventas apartadas', 'error');
        }
    }
    
    // Resume suspended transaction
    window.resumeTransaction = async function(transactionId) {
        try {
            const response = await fetch(`/pos/api/transaction/${transactionId}/resume/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Venta retomada', 'success');
                // Redirect to POS with resumed transaction
                window.location.href = `/pos/?transaction=${transactionId}`;
            } else {
                showToast(data.message || 'Error al retomar venta', 'error');
            }
        } catch (error) {
            console.error('Resume error:', error);
            showToast('Error al retomar venta', 'error');
        }
    };
    
    // Discount Modal Functions
    function openDiscountModal() {
        const discountModal = document.getElementById('discountModal');
        if (!discountModal) return;
        
        const discountValue = document.getElementById('discount-value');
        const discountSymbol = document.getElementById('discount-symbol');
        const discountPreviewAmount = document.getElementById('discount-preview-amount');
        
        // Reset modal
        if (discountValue) discountValue.value = 10;
        document.getElementById('discount-percent').checked = true;
        if (discountSymbol) discountSymbol.textContent = '%';
        
        // Update preview
        updateDiscountPreview();
        
        // Type change handlers
        document.querySelectorAll('input[name="discount-type"]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.value === 'percent') {
                    discountSymbol.textContent = '%';
                } else {
                    discountSymbol.textContent = '$';
                }
                updateDiscountPreview();
            });
        });
        
        // Value change handler
        if (discountValue) {
            discountValue.addEventListener('input', updateDiscountPreview);
        }
        
        const modal = new bootstrap.Modal(discountModal);
        modal.show();
        
        // Focus on value input
        setTimeout(() => discountValue?.focus(), 300);
        
        // Confirm button
        const confirmBtn = document.getElementById('confirm-discount');
        if (confirmBtn) {
            const newBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
            newBtn.addEventListener('click', () => applyDiscount(modal));
        }
    }
    
    function updateDiscountPreview() {
        const discountValue = parseFloat(document.getElementById('discount-value')?.value || 0);
        const isPercent = document.getElementById('discount-percent')?.checked;
        const previewEl = document.getElementById('discount-preview-amount');
        
        if (!previewEl) return;
        
        let discountAmount = 0;
        if (isPercent) {
            discountAmount = cart.subtotal * (discountValue / 100);
        } else {
            discountAmount = discountValue;
        }
        
        previewEl.textContent = formatCurrency(discountAmount);
    }
    
    async function applyDiscount(modal) {
        const discountValue = parseFloat(document.getElementById('discount-value')?.value || 0);
        const isPercent = document.getElementById('discount-percent')?.checked;
        const reason = document.getElementById('discount-reason')?.value || '';
        
        if (discountValue <= 0) {
            showToast('Ingrese un valor de descuento válido', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`/pos/api/transaction/${TRANSACTION_ID}/discount/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    type: isPercent ? 'percent' : 'fixed',
                    value: discountValue,
                    reason: reason
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('Descuento aplicado', 'success');
                modal.hide();
                await loadCart();
            } else {
                showToast(data.error || 'Error al aplicar descuento', 'error');
            }
        } catch (error) {
            console.error('Discount error:', error);
            showToast('Error al aplicar descuento', 'error');
        }
    }
    
    // Cost Sale — uses same overlay style as fast checkout
    let costSaleActive = false;

    function openCostSaleModal() {
        if (!cart.items?.length) { showToast('El carrito está vacío', 'warning'); return; }
        if (costSaleActive || fcoActive) return;

        const methods = (typeof PAYMENT_METHODS !== 'undefined') ? [...PAYMENT_METHODS] : [];
        if (methods.length === 0) { showToast('No hay métodos de pago configurados', 'error'); return; }
        // Remove mixed option for cost sale
        const filteredMethods = methods.filter(m => m.code !== 'mixed');

        // Clean up
        const oldOverlay = document.getElementById('cost-sale-overlay');
        if (oldOverlay) oldOverlay.remove();
        const openModal = document.querySelector('.modal.show');
        if (openModal) { const bsModal = bootstrap.Modal.getInstance(openModal); if (bsModal) bsModal.hide(); }
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');

        costSaleActive = true;
        let selIdx = 0;

        const overlay = document.createElement('div');
        overlay.id = 'cost-sale-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.88);display:flex;align-items:center;justify-content:center;animation:fcoFadeIn .18s ease-out;backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)';

        overlay.innerHTML = `
            <div class="fco-box" style="max-width:580px;">
                <div class="fco-header" style="background:linear-gradient(135deg,rgba(110,168,254,0.08) 0%,rgba(107,33,168,0.06) 100%);">
                    <span class="fco-header-label"><i class="fas fa-tag me-2"></i>VENTA AL COSTO</span>
                    <span class="fco-header-total" id="cso-total" style="color:#6ea8fe;">Calculando...</span>
                </div>
                <div style="padding:12px 20px;background:rgba(110,168,254,0.04);border-bottom:1px solid rgba(110,168,254,0.08);font-size:0.8rem;color:#888;">
                    <i class="fas fa-info-circle me-1" style="color:#6ea8fe;"></i>
                    Productos al <strong style="color:#ddd;">precio de costo</strong>. Ideal para empleados o dueños.
                </div>
                <div style="padding:10px 20px;max-height:140px;overflow-y:auto;border-bottom:1px solid rgba(50,50,75,0.4);" id="cso-items">
                    <div style="text-align:center;color:#666;padding:8px 0;"><i class="fas fa-spinner fa-spin me-1"></i>Calculando costos...</div>
                </div>
                <div style="padding:10px 20px;">
                    <label style="color:#888;font-size:0.78rem;margin-bottom:4px;display:block;">Nota / Quién consume:</label>
                    <input type="text" id="cso-note" placeholder="Ej: Juan Pérez - Empleado"
                           style="width:100%;background:#0c0c1c;border:1.5px solid rgba(50,50,75,0.7);border-radius:8px;color:#eee;padding:7px 12px;font-size:0.85rem;outline:none;"
                           autocomplete="off">
                </div>
                <div class="fco-methods" id="cso-methods">
                    ${filteredMethods.map((m, i) => `
                        <button class="fco-method${i === selIdx ? ' selected' : ''}"
                                data-idx="${i}" data-method-id="${m.id}" data-method-code="${m.code}"
                                tabindex="-1" type="button"
                                style="${i === selIdx ? 'border-color:#6ea8fe;color:#fff;background:rgba(110,168,254,0.08);box-shadow:0 0 18px rgba(110,168,254,0.18)' : ''}">
                            <i class="${m.icon} fco-method-icon"></i>
                            <span class="fco-method-name">${m.name}</span>
                        </button>
                    `).join('')}
                </div>
                <div class="fco-footer">
                    <span class="fco-hint">
                        <kbd>←</kbd><kbd>→</kbd> método
                        <kbd>Enter</kbd> cobrar
                        <kbd>Esc</kbd> cancelar
                    </span>
                    <button type="button" class="btn fco-btn-confirm" id="cso-confirm" disabled
                            style="background:rgba(110,168,254,0.15);border:1.5px solid rgba(110,168,254,0.3);color:#6ea8fe;border-radius:10px;font-weight:700;padding:8px 20px;">
                        <i class="fas fa-check me-2"></i>COBRAR AL COSTO
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const confirmBtn = document.getElementById('cso-confirm');
        const noteInput = document.getElementById('cso-note');
        let costTotal = 0;

        // Fetch cost total
        fetch(API_URLS.calculateCost)
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    costTotal = data.total_cost;
                    document.getElementById('cso-total').textContent = formatCurrency(costTotal);
                    confirmBtn.disabled = false;
                    if (data.items) {
                        document.getElementById('cso-items').innerHTML = data.items.map(item => `
                            <div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:0.8rem;">
                                <span style="color:#bbb;">${item.product_name} x ${item.quantity}</span>
                                <span style="color:#6ea8fe;font-weight:600;">${formatCurrency(item.total)}</span>
                            </div>
                        `).join('');
                    }
                } else {
                    document.getElementById('cso-total').textContent = 'Error';
                }
            })
            .catch(() => { document.getElementById('cso-total').textContent = 'Error'; });

        function getCards() { return Array.from(document.querySelectorAll('#cso-methods .fco-method')); }

        function setSelected(idx) {
            const cards = getCards();
            selIdx = Math.max(0, Math.min(cards.length - 1, idx));
            cards.forEach((c, i) => {
                const isSel = i === selIdx;
                c.classList.toggle('selected', isSel);
                c.style.borderColor = isSel ? '#6ea8fe' : '';
                c.style.color = isSel ? '#fff' : '';
                c.style.background = isSel ? 'rgba(110,168,254,0.08)' : '';
                c.style.boxShadow = isSel ? '0 0 18px rgba(110,168,254,0.18)' : '';
            });
        }

        function closeOverlay(skipFocus) {
            if (!costSaleActive) return;
            costSaleActive = false;
            document.removeEventListener('keydown', onKey, true);
            overlay.remove();
            if (!skipFocus) productSearch?.focus();
        }

        async function doConfirm() {
            const card = getCards()[selIdx];
            if (!card || costTotal <= 0) { showToast('Esperando cálculo de costos...', 'warning'); return; }

            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';

            try {
                const resp = await fetch(API_URLS.costSale, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({
                        transaction_id: TRANSACTION_ID,
                        payments: [{ method_id: parseInt(card.dataset.methodId), method_code: card.dataset.methodCode, amount: costTotal }],
                        note: noteInput?.value || ''
                    })
                });
                const data = await resp.json();
                if (data.success) {
                    closeOverlay(true);
                    showToast(`Venta al costo completada. Total: ${formatCurrency(data.total)}`, 'success');
                    if (data.transaction_id) window.open(`/pos/ticket/${data.transaction_id}/`, '_blank');
                    window.location.reload();
                } else {
                    showToast(data.error || 'Error al procesar', 'error');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR AL COSTO';
                }
            } catch (err) {
                showToast('Error de conexión', 'error');
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR AL COSTO';
            }
        }

        function onKey(e) {
            if (!costSaleActive) return;
            if (document.activeElement === noteInput) {
                if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); if (!confirmBtn.disabled) doConfirm(); }
                else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); closeOverlay(); }
                else if (/^F\d+$/.test(e.key)) { e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation(); }
                return;
            }
            e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
            switch (e.key) {
                case 'Escape': closeOverlay(); break;
                case 'ArrowLeft': case 'ArrowUp': setSelected(selIdx - 1); break;
                case 'ArrowRight': case 'ArrowDown': setSelected(selIdx + 1); break;
                case 'Tab': noteInput?.focus(); break;
                case 'Enter': if (!confirmBtn.disabled) doConfirm(); break;
            }
        }

        document.addEventListener('keydown', onKey, true);
        getCards().forEach((c, i) => c.addEventListener('click', () => { setSelected(i); noteInput?.focus(); }));
        confirmBtn.addEventListener('click', doConfirm);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeOverlay(); });
        setTimeout(() => noteInput?.focus(), 50);
    }
    
    // Internal Consumption Modal Functions
    function openInternalConsumptionModal() {
        const consumptionModal = document.getElementById('internalConsumptionModal');
        if (!consumptionModal) return;
        
        // Populate items list
        const consumptionItems = document.getElementById('consumption-items');
        if (consumptionItems && cart.items) {
            consumptionItems.innerHTML = cart.items.map(item => `
                <div class="d-flex justify-content-between py-1 border-bottom border-secondary">
                    <span>${item.product_name || item.name}</span>
                    <span>x ${item.quantity}</span>
                </div>
            `).join('');
        }
        
        // Fetch real cost value
        const costValue = document.getElementById('consumption-cost-value');
        if (costValue) {
            costValue.textContent = 'Calculando...';
            fetch(API_URLS.calculateCost)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        costValue.textContent = formatCurrency(data.total_cost);
                    }
                })
                .catch(() => {
                    costValue.textContent = 'N/A';
                });
        }
        
        const modal = new bootstrap.Modal(consumptionModal);
        modal.show();
        
        // Setup confirm button
        const confirmBtn = document.getElementById('confirm-consumption');
        if (confirmBtn) {
            // Remove old listeners
            const newBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
            
            newBtn.addEventListener('click', processInternalConsumption);
        }
    }
    
    async function processInternalConsumption() {
        const note = document.getElementById('consumption-note')?.value || '';
        
        if (!note.trim()) {
            showToast('Ingrese quién consume para el registro', 'warning');
            return;
        }
        
        const confirmBtn = document.getElementById('confirm-consumption');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';
        }
        
        try {
            const response = await fetch(API_URLS.internalConsumption, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({
                    transaction_id: TRANSACTION_ID,
                    note: note
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast(`Consumo interno registrado. Ticket: ${data.ticket_number}`, 'success');
                
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('internalConsumptionModal'))?.hide();
                
                if (data.transaction_id) {
                    window.open(`/pos/ticket/${data.transaction_id}/`, '_blank');
                }
                
                window.location.reload();
            } else {
                showToast(data.error || 'Error al registrar consumo', 'error');
                if (confirmBtn) {
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>Confirmar Consumo';
                }
            }
        } catch (error) {
            console.error('Internal consumption error:', error);
            showToast('Error de conexión', 'error');
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>Confirmar Consumo';
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // FAST CHECKOUT OVERLAY — aparece instantáneo, 100% teclado
    // Flujo: Enter en COBRAR → overlay → ←/→ método → Tab monto → Enter cobrar
    // ═══════════════════════════════════════════════════════════════════════════
    let fcoActive = false;

    function openFastCheckout(preselectedMethodCode) {
        if (!cart.items?.length) { showToast('El carrito está vacío', 'warning'); return; }
        if (fcoActive) return;

        const methods = (typeof PAYMENT_METHODS !== 'undefined') ? [...PAYMENT_METHODS] : [];
        if (methods.length === 0) {
            showToast('No hay métodos de pago configurados', 'error');
            return;
        }
        // Agregar opción de pago mixto al final
        const hasMp = methods.some(m => m.code === 'mercadopago');
        const hasCash = methods.some(m => m.code === 'cash');
        if (hasMp && hasCash) {
            methods.push({ id: 'mixed', code: 'mixed', name: 'Mixto (MP + Efectivo)', icon: 'fas fa-exchange-alt' });
        }

        // Limpiar overlay huérfano si existe
        const oldOverlay = document.getElementById('fco-overlay');
        if (oldOverlay) oldOverlay.remove();

        // Cerrar cualquier modal Bootstrap abierto
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const bsModal = bootstrap.Modal.getInstance(openModal);
            if (bsModal) bsModal.hide();
        }
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');

        fcoActive = true;
        const totalAmt = Math.round(parseFloat(cart.total) * 100) / 100;
        // Pre-seleccionar método si viene por atajo de pago rápido
        let selIdx = 0;
        if (preselectedMethodCode) {
            const foundIdx = methods.findIndex(m => m.code === preselectedMethodCode);
            if (foundIdx >= 0) selIdx = foundIdx;
        }

        // ── Crear overlay ─────────────────────────────────────────────────────
        const overlay = document.createElement('div');
        overlay.id = 'fco-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');

        overlay.innerHTML = `
            <div class="fco-box" id="fco-box">
                <div class="fco-header">
                    <span class="fco-header-label"><i class="fas fa-cash-register me-2"></i>COBRAR</span>
                    <span class="fco-header-total">${formatCurrency(totalAmt)}</span>
                </div>
                <div class="fco-methods" id="fco-methods">
                    ${methods.map((m, i) => `
                        <button class="fco-method${i === selIdx ? ' selected' : ''}"
                                data-idx="${i}" data-method-id="${m.id}" data-method-code="${m.code}"
                                tabindex="-1" type="button">
                            <i class="${m.icon} fco-method-icon"></i>
                            <span class="fco-method-name">${m.name}</span>
                        </button>
                    `).join('')}
                </div>
                <div class="fco-amount-section">
                    <div class="fco-amount-group">
                        <label class="fco-amount-label" for="fco-amount">Recibe <span class="fco-currency">$</span></label>
                        <input type="number" id="fco-amount" class="fco-amount-input"
                               value="${totalAmt.toFixed(2)}" min="0" step="0.01" autocomplete="off"
                               inputmode="decimal" placeholder="0.00">
                    </div>
                    <div class="fco-change-row">
                        <span class="fco-change-label">Vuelto</span>
                        <strong id="fco-change" class="fco-change-val">$0</strong>
                    </div>
                </div>
                <div class="fco-footer">
                    <span class="fco-hint">
                        <kbd>←</kbd><kbd>→</kbd> método
                        <kbd>Tab</kbd> monto
                        <kbd>Enter</kbd> cobrar
                        <kbd>Esc</kbd> cancelar
                    </span>
                    <button type="button" class="btn btn-success fco-btn-confirm" id="fco-confirm">
                        <i class="fas fa-check me-2"></i>COBRAR
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const amountInput = document.getElementById('fco-amount');
        const confirmBtn  = document.getElementById('fco-confirm');
        const changeEl    = document.getElementById('fco-change');

        // Modo "pago pendiente" (esperando tarjeta en el Point Smart).
        // Cuando está activo, el overlay se reemplaza por la vista de espera y
        // onKey bloquea todas las teclas excepto Esc (que cancela el cobro).
        let fcoPendingMode = false;

        function getCards() { return Array.from(document.querySelectorAll('.fco-method')); }

        // ── Pending payment (Point Smart) helpers ──────────────────────────
        // Formato MM:SS para el countdown del tiempo restante.
        function formatSecondsMMSS(totalSec) {
            const safe = Math.max(0, Math.floor(totalSec));
            const m = Math.floor(safe / 60);
            const s = safe % 60;
            return `${m}:${s.toString().padStart(2, '0')}`;
        }

        // Reemplaza el contenido de .fco-box con la vista "PAGO PENDIENTE".
        // Devuelve referencias a los nodos interactivos (cancel btn, progress,
        // countdown, iconWrap, msg) o null si no pudo montarse.
        function renderFcoPendingView({ amount, methodName, methodIcon, externalReference, maxSeconds }) {
            const box = overlay.querySelector('.fco-box');
            if (!box) return null;

            const safeIcon = methodIcon || 'fas fa-credit-card';
            const safeName = methodName || 'Tarjeta';
            const safeRef  = externalReference || '—';

            box.innerHTML = `
                <div class="fco-pending-view">
                    <div class="fco-pending-header">
                        <i class="fas fa-hourglass-half me-2"></i>PAGO PENDIENTE
                    </div>
                    <div class="fco-pending-body">
                        <div class="fco-pending-icon-wrap" id="fco-pending-icon-wrap">
                            <i class="${safeIcon} fco-pending-icon"></i>
                        </div>
                        <div class="fco-pending-msg" id="fco-pending-msg">
                            Esperando que el cliente pase la tarjeta en el <strong>Point Smart</strong>
                        </div>
                        <div class="fco-pending-info">
                            <div class="fco-pending-info-item">
                                <span class="fco-pending-info-label">Monto</span>
                                <span class="fco-pending-info-value">${formatCurrency(amount)}</span>
                            </div>
                            <div class="fco-pending-info-item">
                                <span class="fco-pending-info-label">Método</span>
                                <span class="fco-pending-info-value">${safeName}</span>
                            </div>
                        </div>
                        <div class="fco-pending-progress-wrap">
                            <div class="fco-pending-progress-bar">
                                <div class="fco-pending-progress-fill" id="fco-pending-fill" style="width:100%"></div>
                            </div>
                            <span class="fco-pending-countdown" id="fco-pending-countdown">${formatSecondsMMSS(maxSeconds)} restantes</span>
                        </div>
                    </div>
                    <div class="fco-pending-footer">
                        <span class="fco-pending-ref" title="Referencia externa">Ref: <code>${safeRef}</code></span>
                        <button type="button" class="btn btn-outline-danger fco-pending-cancel" id="fco-pending-cancel">
                            <i class="fas fa-times me-2"></i>Cancelar cobro
                        </button>
                    </div>
                </div>
            `;

            return {
                iconWrap:     document.getElementById('fco-pending-icon-wrap'),
                msg:          document.getElementById('fco-pending-msg'),
                progressFill: document.getElementById('fco-pending-fill'),
                countdown:    document.getElementById('fco-pending-countdown'),
                cancelBtn:    document.getElementById('fco-pending-cancel'),
            };
        }

        function setSelected(idx) {
            const cards = getCards();
            selIdx = Math.max(0, Math.min(cards.length - 1, idx));
            cards.forEach((c, i) => c.classList.toggle('selected', i === selIdx));
            // Update confirm button label for MercadoPago / Tarjeta
            const selectedCard = cards[selIdx];
            if (selectedCard && confirmBtn && !confirmBtn.disabled) {
                const code = selectedCard.dataset.methodCode;
                if (code === 'mercadopago') {
                    confirmBtn.innerHTML = '<i class="fas fa-qrcode me-2"></i>CARGAR AL QR';
                } else if (code === 'tarjeta_mp' || code === 'debit' || code === 'credit') {
                    confirmBtn.innerHTML = '<i class="fas fa-credit-card me-2"></i>ENVIAR A POINT';
                } else {
                    confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR';
                }
            }
            // Ajustar el input "Recibe" según el método:
            // - Efectivo: vaciar para que el cajero escriba el billete recibido y vea el vuelto al instante
            // - Otros (MP, tarjeta, etc.): pre-cargar con el total para poder confirmar con un solo Enter
            if (selectedCard && amountInput) {
                const code = selectedCard.dataset.methodCode;
                if (code === 'cash') {
                    amountInput.value = '';
                } else if (code !== 'mixed') {
                    amountInput.value = totalAmt.toFixed(2);
                }
                updateChange();
            }
        }

        function updateChange() {
            const paid  = parseFloat(amountInput.value) || 0;
            const paidR = Math.round(paid * 100);
            const totR  = Math.round(totalAmt * 100);
            const change = paid - totalAmt;
            changeEl.textContent = formatCurrency(Math.max(0, change));
            changeEl.style.color = change >= -0.005 ? '#2ecc71' : '#e74c3c';
            const ok = paidR >= totR;
            confirmBtn.disabled = !ok;
            confirmBtn.classList.toggle('btn-success', ok);
            confirmBtn.classList.toggle('btn-secondary', !ok);
        }

        function closeOverlay(skipFocus) {
            if (!fcoActive) return;
            fcoActive = false;
            document.removeEventListener('keydown', onKey, true);
            overlay.remove();
            if (!skipFocus) productSearch?.focus();
        }

        async function doConfirm() {
            const card = getCards()[selIdx];
            if (!card) { showToast('Seleccioná un método de pago', 'warning'); return; }

            // Si seleccionó Mixto, cerrar FCO y abrir overlay mixto
            if (card.dataset.methodCode === 'mixed') {
                closeOverlay(true);
                openMixedCheckout();
                return;
            }

            const paid = parseFloat(amountInput.value) || 0;
            if (Math.round(paid * 100) < Math.round(totalAmt * 100)) {
                showToast('El monto ingresado es menor al total', 'warning');
                return;
            }

            // MercadoPago QR estático: cargar monto al QR físico y esperar pago
            if (card.dataset.methodCode === 'mercadopago') {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '<i class="fas fa-qrcode fa-beat me-2"></i>Cargando monto al QR...';
                try {
                    await handleFcoMercadoPago(paid, parseInt(card.dataset.methodId));
                } catch (err) {
                    console.error('MP QR FCO error:', err);
                    showToast(err.message || 'Error al cargar el monto al QR', 'error');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-qrcode me-2"></i>CARGAR AL QR';
                }
                return;
            }

            // Tarjeta MP (Point Smart): enviar al posnet y esperar pago
            // 'tarjeta_mp' → acepta cualquier tarjeta
            // 'debit' → fuerza débito en el Point
            // 'credit' → fuerza crédito en el Point
            const cardCode = card.dataset.methodCode;
            if (cardCode === 'tarjeta_mp' || cardCode === 'debit' || cardCode === 'credit') {
                confirmBtn.disabled = true;
                confirmBtn.innerHTML = '<i class="fas fa-credit-card fa-beat me-2"></i>Enviando a Point...';
                let paymentType = null;
                if (cardCode === 'debit') paymentType = 'debit_card';
                else if (cardCode === 'credit') paymentType = 'credit_card';
                try {
                    await handleFcoPointCard(paid, parseInt(card.dataset.methodId), paymentType);
                } catch (err) {
                    console.error('MP Point Card error:', err);
                    showToast(err.message || 'Error al enviar a Point Smart', 'error');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-credit-card me-2"></i>ENVIAR A POINT';
                }
                return;
            }

            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';

            try {
                const resp = await fetch(API_URLS.checkout, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({
                        transaction_id: TRANSACTION_ID,
                        payments: [{ method_id: parseInt(card.dataset.methodId), amount: paid }]
                    })
                });
                const data = await resp.json();
                if (data.success) {
                    closeOverlay(true);
                    showSaleSuccessModal(data);
                } else {
                    showToast(data.error || 'Error al procesar la venta', 'error');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR';
                }
            } catch (err) {
                console.error('Checkout error:', err);
                if (!navigator.onLine) {
                    showToast('Sin conexión a internet', 'error');
                } else {
                    showToast('Error al conectar con el servidor. ¿Está corriendo?', 'error');
                }
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR';
            }
        }

        // ── MercadoPago QR ESTÁTICO flow within Fast Checkout ─────────────
        // No genera un QR nuevo: asigna el monto al QR físico ya impreso
        // y pegado a la caja. El cliente escanea el QR de la caja, no la pantalla.
        async function handleFcoMercadoPago(amount, methodId) {
            // 1. Asignar monto al QR estático en MP
            const intentResp = await fetch('/mercadopago/api/create-qr/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({
                    amount: amount,
                    transaction_id: TRANSACTION_ID
                })
            });
            const intentData = await intentResp.json();
            if (!intentData.success) {
                throw new Error(intentData.error || 'Error al cargar el monto en el QR');
            }

            const paymentIntentId = intentData.payment_intent?.id;
            if (!paymentIntentId) throw new Error('No se recibió ID de pago');

            // Show "scan physical QR" modal (NO QR en pantalla)
            showMpQrModal(amount);
            showToast('Monto cargado. Pedile al cliente que escanee el QR de la caja.', 'info');
            confirmBtn.innerHTML = '<i class="fas fa-qrcode fa-beat me-2"></i>Esperando que escanee...';

            // 2. Poll for payment status
            const maxAttempts = 90;  // 3 minutes
            for (let attempt = 0; attempt < maxAttempts; attempt++) {
                await new Promise(r => setTimeout(r, 2000));

                // Check if overlay was closed (user cancelled)
                if (!fcoActive) {
                    hideMpQrModal();
                    fetch(`/mercadopago/api/cancel/${paymentIntentId}/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': CSRF_TOKEN }
                    }).catch(() => {});
                    return;
                }

                try {
                    const statusResp = await fetch(`/mercadopago/api/status/${paymentIntentId}/`);
                    const statusData = await statusResp.json();

                    if (statusData.status === 'approved') {
                        hideMpQrModal();
                        confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>Aprobado! Finalizando...';
                        showToast('¡Pago con MercadoPago aprobado!', 'success');

                        const checkoutResp = await fetch(API_URLS.checkout, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                            body: JSON.stringify({
                                transaction_id: TRANSACTION_ID,
                                payments: [{ method_id: methodId, amount: amount }]
                            })
                        });
                        const checkoutData = await checkoutResp.json();
                        closeOverlay(true);
                        if (checkoutData.success) {
                            showSaleSuccessModal(checkoutData);
                        } else {
                            showToast('Venta completada por MercadoPago', 'success');
                            setTimeout(() => window.location.reload(), 1200);
                        }
                        return;
                    }

                    if (statusData.status === 'rejected' || statusData.status === 'cancelled' || statusData.status === 'error') {
                        hideMpQrModal();
                        throw new Error(
                            statusData.status === 'rejected' ? 'Pago rechazado' :
                            statusData.status === 'cancelled' ? 'Pago cancelado' :
                            'Error en el pago'
                        );
                    }
                } catch (pollErr) {
                    if (pollErr.message.includes('rechazado') || pollErr.message.includes('cancelado') || pollErr.message.includes('Error')) {
                        throw pollErr;
                    }
                    console.warn('Poll error, retrying...', pollErr);
                }
            }
            hideMpQrModal();
            throw new Error('Tiempo de espera agotado.');
        }

        // ── Point Smart Card flow within Fast Checkout ─────────────────────
        // Muestra la vista "PAGO PENDIENTE" mientras se espera a que el cliente
        // pase la tarjeta en el Point. Se cierra el carrito automáticamente
        // cuando el pago se aprueba, o se cancela el intent si el cajero cierra
        // el overlay (Esc / botón Cancelar / click fuera).
        async function handleFcoPointCard(amount, methodId, paymentType = null) {
            // 1. Create payment intent on Point Smart device
            const body = {
                amount: amount,
                transaction_id: TRANSACTION_ID
            };
            if (paymentType) body.payment_type = paymentType;
            const intentResp = await fetch('/mercadopago/api/create-intent/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify(body)
            });
            const intentData = await intentResp.json();
            if (!intentData.success) {
                throw new Error(intentData.error || 'Error al enviar a Point Smart');
            }

            const paymentIntentId = intentData.payment_intent?.id;
            if (!paymentIntentId) throw new Error('No se recibió ID de pago');
            const externalRef = intentData.payment_intent?.external_reference || '';

            // Leer nombre e ícono del método elegido (para mostrarlos en la vista
            // pendiente y que el cajero los confirme de un vistazo).
            const selectedCard = getCards()[selIdx];
            const methodName = selectedCard?.querySelector('.fco-method-name')?.textContent?.trim() || 'Tarjeta';
            const methodIconClass = selectedCard?.querySelector('.fco-method-icon')?.className
                ?.replace(/\bfco-method-icon\b/, '').trim() || 'fas fa-credit-card';

            // 2. Entrar en modo "pago pendiente": reemplaza la UI del overlay
            //    por la vista de espera (icono grande, monto, método, progress
            //    bar con countdown y botón Cancelar).
            const maxAttempts = 90;       // 90 intentos
            const pollIntervalMs = 2000;  // cada 2 segundos → 180s totales
            const maxSeconds = Math.floor((maxAttempts * pollIntervalMs) / 1000);

            const pending = renderFcoPendingView({
                amount,
                methodName,
                methodIcon: methodIconClass,
                externalReference: externalRef,
                maxSeconds,
            });
            if (!pending) throw new Error('No se pudo montar la vista de espera');

            fcoPendingMode = true;
            let cancelledByUser = false;
            showToast('Cobro enviado al Point Smart. Esperando tarjeta...', 'info');

            // Countdown: actualiza progress bar y texto MM:SS cada segundo.
            let secondsLeft = maxSeconds;
            const countdownId = setInterval(() => {
                secondsLeft = Math.max(0, secondsLeft - 1);
                const pct = Math.max(0, (secondsLeft / maxSeconds) * 100);
                if (pending.progressFill) pending.progressFill.style.width = `${pct}%`;
                if (pending.countdown) pending.countdown.textContent = `${formatSecondsMMSS(secondsLeft)} restantes`;
                if (secondsLeft <= 0) clearInterval(countdownId);
            }, 1000);

            // Botón "Cancelar cobro": marca flag y cierra overlay (el poll loop
            // detecta !fcoActive en el próximo tick y dispara cancel al backend).
            const onCancelClick = () => {
                cancelledByUser = true;
                closeOverlay();
            };
            pending.cancelBtn?.addEventListener('click', onCancelClick);

            const cleanupPending = () => {
                clearInterval(countdownId);
                pending.cancelBtn?.removeEventListener('click', onCancelClick);
                fcoPendingMode = false;
            };

            try {
                // 3. Poll for payment status
                for (let attempt = 0; attempt < maxAttempts; attempt++) {
                    await new Promise(r => setTimeout(r, pollIntervalMs));

                    // Check if overlay was closed (user cancelled via Esc /
                    // botón Cancelar / click fuera del box)
                    if (!fcoActive) {
                        fetch(`/mercadopago/api/cancel/${paymentIntentId}/`, {
                            method: 'POST',
                            headers: { 'X-CSRFToken': CSRF_TOKEN }
                        }).catch(() => {});
                        if (cancelledByUser) {
                            showToast('Cobro cancelado por el cajero', 'info');
                        }
                        return;
                    }

                    try {
                        const statusResp = await fetch(`/mercadopago/api/status/${paymentIntentId}/`);
                        const statusData = await statusResp.json();

                        if (statusData.status === 'approved') {
                            // Feedback visual: ícono verde + mensaje de éxito,
                            // breve pausa para que el cajero vea la confirmación,
                            // luego checkout atómico y cierre del overlay.
                            if (pending.iconWrap) pending.iconWrap.classList.add('approved');
                            if (pending.msg) pending.msg.innerHTML = '<strong>¡Pago aprobado!</strong> Finalizando venta...';
                            if (pending.progressFill) pending.progressFill.style.width = '100%';
                            if (pending.cancelBtn) pending.cancelBtn.disabled = true;
                            showToast('¡Pago con tarjeta aprobado!', 'success');

                            await new Promise(r => setTimeout(r, 700));

                            const checkoutResp = await fetch(API_URLS.checkout, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                                body: JSON.stringify({
                                    transaction_id: TRANSACTION_ID,
                                    payments: [{ method_id: methodId, amount: amount }]
                                })
                            });
                            const checkoutData = await checkoutResp.json();
                            closeOverlay(true);
                            if (checkoutData.success) {
                                showSaleSuccessModal(checkoutData);
                            } else {
                                showToast('Pago aprobado por MercadoPago Point', 'success');
                                setTimeout(() => window.location.reload(), 1200);
                            }
                            return;
                        }

                        if (statusData.status === 'rejected' || statusData.status === 'cancelled' || statusData.status === 'error') {
                            throw new Error(
                                statusData.status === 'rejected' ? 'Pago con tarjeta rechazado' :
                                statusData.status === 'cancelled' ? 'Pago cancelado' :
                                'Error en el pago'
                            );
                        }
                    } catch (pollErr) {
                        if (pollErr.message.includes('rechazado') || pollErr.message.includes('cancelado') || pollErr.message.includes('Error')) {
                            throw pollErr;
                        }
                        console.warn('Point poll error, retrying...', pollErr);
                    }
                }
                throw new Error('Tiempo de espera agotado. Verifique el dispositivo Point.');
            } finally {
                cleanupPending();
            }
        }

        // ── Modal "Esperando pago QR estático" ──────────────────────────────
        // NO genera un QR en pantalla. El cliente tiene que escanear el QR
        // FÍSICO impreso pegado a la caja. Esto solo informa el monto cargado
        // y muestra que estamos esperando confirmación de MP.
        function showMpQrModal(amount) {
            hideMpQrModal();
            const modal = document.createElement('div');
            modal.id = 'mp-qr-modal';
            modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:99999;';
            modal.innerHTML = `
                <div style="background:#fff;padding:40px 50px;border-radius:24px;text-align:center;max-width:480px;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
                    <img src="https://http2.mlstatic.com/frontend-assets/mp-web-navigation/ui-navigation/5.21.22/mercadopago/logo__large@2x.png" style="height:42px;margin-bottom:20px;">
                    <div style="font-size:0.95rem;color:#666;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">Monto cargado al QR</div>
                    <div style="font-size:3rem;font-weight:800;color:#009ee3;margin-bottom:25px;line-height:1;">${formatCurrency(amount)}</div>
                    <div style="background:#fff8e1;border:2px dashed #f5d000;border-radius:14px;padding:18px;margin-bottom:20px;">
                        <div style="font-size:1.05rem;color:#333;font-weight:600;margin-bottom:6px;">
                            <i class="fas fa-hand-point-right me-2" style="color:#E91E8C;"></i>Pedile al cliente que escanee el QR pegado en la caja
                        </div>
                        <div style="font-size:0.85rem;color:#666;">El monto ya está cargado. Cuando lo escanee verá <strong>${formatCurrency(amount)}</strong> en su app.</div>
                    </div>
                    <div style="color:#009ee3;font-weight:600;font-size:0.95rem;">
                        <i class="fas fa-spinner fa-spin me-2"></i>Esperando confirmación de pago...
                    </div>
                    <div style="margin-top:14px;color:#999;font-size:0.78rem;">
                        Cerrá esta pantalla con <kbd>Esc</kbd> para cancelar
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function hideMpQrModal() {
            const m = document.getElementById('mp-qr-modal');
            if (m) m.remove();
        }

        function onKey(e) {
            if (!fcoActive) return;
            // Modo "pago pendiente" (esperando Point Smart): bloquear TODAS
            // las teclas excepto Escape, que cancela el cobro cerrando el
            // overlay (el poll loop detecta !fcoActive y avisa al backend).
            if (fcoPendingMode) {
                e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                if (e.key === 'Escape') closeOverlay();
                return;
            }
            // Capturar TODAS las teclas mientras el overlay está activo
            // para evitar que otros handlers (shortcuts globales, Chrome) las procesen
            if (document.activeElement === amountInput) {
                if (e.key === 'Enter') {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                    if (!confirmBtn.disabled) doConfirm();
                } else if (e.key === 'Escape') {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                    closeOverlay();
                } else if (/^F\d+$/.test(e.key)) {
                    // Bloquear F-keys para que no disparen atajos globales ni acciones de Chrome
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                }
                // Números y demás pasan normal al input
                return;
            }
            // Fuera del input, capturar todo
            e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
            switch (e.key) {
                case 'Escape':
                    closeOverlay();
                    break;
                case 'ArrowLeft':
                case 'ArrowUp':
                    setSelected(selIdx - 1);
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    setSelected(selIdx + 1);
                    break;
                case 'Tab': {
                    const selectedCard = getCards()[selIdx];
                    if (selectedCard?.dataset.methodCode === 'mixed') {
                        closeOverlay(true);
                        openMixedCheckout();
                    } else {
                        amountInput.focus();
                        amountInput.select();
                    }
                    break;
                }
                case 'Enter':
                    if (!confirmBtn.disabled) doConfirm();
                    break;
            }
        }

        document.addEventListener('keydown', onKey, true);

        // Click en tarjeta de método → seleccionarla y saltar al monto
        // Si es Mixto, abrir directamente el overlay de pago mixto
        getCards().forEach((c, i) => c.addEventListener('click', () => {
            if (c.dataset.methodCode === 'mixed') {
                closeOverlay(true);
                openMixedCheckout();
                return;
            }
            setSelected(i);
            amountInput.focus();
            amountInput.select();
        }));

        amountInput.addEventListener('input', updateChange);
        confirmBtn.addEventListener('click', doConfirm);

        // Click fuera del box → cerrar
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeOverlay(); });

        // Inicializar estado: setSelected ajusta el input según el método
        // (vacío si efectivo → vuelto al escribir; total pre-cargado si MP/tarjeta → un Enter confirma)
        setSelected(selIdx);
        setTimeout(() => { amountInput.focus(); amountInput.select(); }, 50);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MIXED CHECKOUT OVERLAY — Pago Mixto: MercadoPago + Efectivo
    // Flujo: Ingresa monto MP → se calcula automáticamente el resto en efectivo
    // ═══════════════════════════════════════════════════════════════════════════
    let mixedActive = false;

    function openMixedCheckout() {
        if (!cart.items?.length) { showToast('El carrito está vacío', 'warning'); return; }
        if (mixedActive || fcoActive) return;

        const methods = (typeof PAYMENT_METHODS !== 'undefined') ? PAYMENT_METHODS : [];
        const mpMethod = methods.find(m => m.code === 'mercadopago');
        const cashMethod = methods.find(m => m.code === 'cash');

        if (!mpMethod || !cashMethod) {
            showToast('Se necesitan los métodos Efectivo y MercadoPago activos', 'error');
            return;
        }

        // Limpiar overlay huérfano
        const old = document.getElementById('mixed-overlay');
        if (old) old.remove();

        // Cerrar cualquier modal Bootstrap abierto
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const bsModal = bootstrap.Modal.getInstance(openModal);
            if (bsModal) bsModal.hide();
        }
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');

        mixedActive = true;
        const totalAmt = Math.round(parseFloat(cart.total) * 100) / 100;

        const overlay = document.createElement('div');
        overlay.id = 'mixed-overlay';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');

        overlay.innerHTML = `
            <div class="fco-box" id="mixed-box" style="max-width:500px;">
                <div class="fco-header">
                    <span class="fco-header-label"><i class="fas fa-exchange-alt me-2"></i>PAGO MIXTO</span>
                    <span class="fco-header-total">${formatCurrency(totalAmt)}</span>
                </div>
                <div style="padding:0 1.2rem;">
                    <p style="color:#888;font-size:0.82rem;margin:0.8rem 0 0.5rem;">
                        <i class="${mpMethod.icon} me-1" style="color:#00b1ea;"></i><strong>MercadoPago</strong> + 
                        <i class="${cashMethod.icon} me-1" style="color:#2ecc71;"></i><strong>Efectivo</strong>
                    </p>
                </div>
                <div class="fco-amount-section" style="gap:0.8rem;">
                    <div class="fco-amount-group">
                        <label class="fco-amount-label" for="mixed-mp-amount">
                            <i class="${mpMethod.icon} me-1" style="color:#00b1ea;"></i>MercadoPago <span class="fco-currency">$</span>
                        </label>
                        <input type="number" id="mixed-mp-amount" class="fco-amount-input"
                               value="" min="0" max="${totalAmt.toFixed(2)}" step="0.01" autocomplete="off"
                               inputmode="decimal" placeholder="Monto con MP...">
                        <div style="margin-top:0.5rem;display:flex;align-items:center;gap:0.5rem;">
                            <button type="button" class="btn btn-info btn-sm" id="mixed-mp-send-point"
                                    style="white-space:nowrap;">
                                <i class="fas fa-mobile-alt me-1"></i>Enviar a Point
                            </button>
                            <span id="mixed-mp-status" class="text-muted small"></span>
                        </div>
                    </div>
                    <div class="fco-amount-group">
                        <label class="fco-amount-label" for="mixed-cash-amount">
                            <i class="${cashMethod.icon} me-1" style="color:#2ecc71;"></i>Efectivo <span class="fco-currency">$</span>
                        </label>
                        <input type="number" id="mixed-cash-amount" class="fco-amount-input"
                               value="" min="0" step="0.01" autocomplete="off"
                               inputmode="decimal" placeholder="Monto en efectivo...">
                    </div>
                    <div class="fco-change-row" style="flex-direction:column;gap:0.3rem;">
                        <div style="display:flex;justify-content:space-between;width:100%;">
                            <span class="fco-change-label">Total Recibido</span>
                            <strong id="mixed-total-received" style="color:#ccc;">$0</strong>
                        </div>
                        <div style="display:flex;justify-content:space-between;width:100%;">
                            <span class="fco-change-label">Vuelto</span>
                            <strong id="mixed-change" class="fco-change-val">$0</strong>
                        </div>
                    </div>
                </div>
                <div class="fco-footer">
                    <span class="fco-hint">
                        <kbd>Tab</kbd> cambiar campo
                        <kbd>Enter</kbd> cobrar
                        <kbd>Esc</kbd> cancelar
                    </span>
                    <button type="button" class="btn btn-success fco-btn-confirm" id="mixed-confirm" disabled>
                        <i class="fas fa-check me-2"></i>COBRAR MIXTO
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const mpInput    = document.getElementById('mixed-mp-amount');
        const cashInput  = document.getElementById('mixed-cash-amount');
        const confirmBtn = document.getElementById('mixed-confirm');
        const changeEl   = document.getElementById('mixed-change');
        const totalRecEl = document.getElementById('mixed-total-received');
        const mpSendBtn  = document.getElementById('mixed-mp-send-point');
        const mpStatusEl = document.getElementById('mixed-mp-status');
        let mpPollInterval = null;

        function updateMixed() {
            const mpAmt   = parseFloat(mpInput.value) || 0;
            const cashAmt = parseFloat(cashInput.value) || 0;
            const totalPaid = mpAmt + cashAmt;
            const change = totalPaid - totalAmt;

            totalRecEl.textContent = formatCurrency(totalPaid);
            changeEl.textContent = formatCurrency(Math.max(0, change));
            changeEl.style.color = change >= -0.005 ? '#2ecc71' : '#e74c3c';

            const ok = Math.round(totalPaid * 100) >= Math.round(totalAmt * 100) && mpAmt > 0 && cashAmt > 0;
            confirmBtn.disabled = !ok;
            confirmBtn.classList.toggle('btn-success', ok);
            confirmBtn.classList.toggle('btn-secondary', !ok);
        }

        // ── MercadoPago Point integration ──────────────────────────────────
        mpSendBtn.addEventListener('click', async () => {
            const mpAmt = parseFloat(mpInput.value) || 0;
            if (mpAmt <= 0) {
                showToast('Ingresá el monto de MercadoPago primero', 'warning');
                mpInput.focus();
                return;
            }

            try {
                mpSendBtn.disabled = true;
                mpSendBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Enviando...';
                mpStatusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Conectando con Point...';
                mpStatusEl.className = 'text-info small';

                const response = await fetch('/mercadopago/api/create-intent/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN
                    },
                    body: JSON.stringify({
                        amount: mpAmt,
                        transaction_id: TRANSACTION_ID
                    })
                });

                const data = await response.json();

                if (data.success) {
                    mpStatusEl.innerHTML = '<i class="fas fa-check text-success"></i> Enviado al Point';
                    mpStatusEl.className = 'text-success small';
                    mpSendBtn.innerHTML = '<i class="fas fa-check me-1"></i>Enviado';
                    mpInput.readOnly = true;
                    mpInput.style.opacity = '0.7';

                    showToast('Pago enviado al Point. Esperando confirmación...', 'info');

                    if (data.payment_intent && data.payment_intent.id) {
                        mixedPollMpStatus(data.payment_intent.id);
                    }
                } else {
                    throw new Error(data.error || 'Error al conectar con Mercado Pago');
                }
            } catch (error) {
                console.error('MP Point error (mixed):', error);
                mpStatusEl.innerHTML = '<i class="fas fa-times text-danger"></i> Error';
                mpStatusEl.className = 'text-danger small';
                mpSendBtn.disabled = false;
                mpSendBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                showToast(error.message || 'Error al conectar con Mercado Pago Point', 'error');
            }
        });

        function mixedPollMpStatus(paymentIntentId) {
            let attempts = 0;
            const maxAttempts = 60;

            mpPollInterval = setInterval(async () => {
                attempts++;
                if (attempts > maxAttempts) {
                    clearInterval(mpPollInterval);
                    mpPollInterval = null;
                    mpStatusEl.innerHTML = '<i class="fas fa-clock text-warning"></i> Tiempo agotado';
                    mpSendBtn.disabled = false;
                    mpSendBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                    mpInput.readOnly = false;
                    mpInput.style.opacity = '1';
                    return;
                }
                try {
                    const resp = await fetch(`/mercadopago/api/status/${paymentIntentId}/`);
                    const data = await resp.json();

                    if (data.status === 'approved' || data.status === 'FINISHED') {
                        clearInterval(mpPollInterval);
                        mpPollInterval = null;
                        mpStatusEl.innerHTML = '<i class="fas fa-check-circle text-success"></i> ¡Pago aprobado!';
                        mpSendBtn.classList.remove('btn-info');
                        mpSendBtn.classList.add('btn-success');
                        mpSendBtn.innerHTML = '<i class="fas fa-check me-1"></i>Aprobado';
                        showToast('¡Pago con MercadoPago aprobado! Ingresá el efectivo.', 'success');
                        cashInput.focus();
                        cashInput.select();
                    } else if (data.status === 'rejected' || data.status === 'cancelled' || data.status === 'CANCELED') {
                        clearInterval(mpPollInterval);
                        mpPollInterval = null;
                        mpStatusEl.innerHTML = '<i class="fas fa-times-circle text-danger"></i> Rechazado';
                        mpSendBtn.disabled = false;
                        mpSendBtn.classList.remove('btn-success');
                        mpSendBtn.classList.add('btn-info');
                        mpSendBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                        mpInput.readOnly = false;
                        mpInput.style.opacity = '1';
                        showToast('Pago de MercadoPago rechazado o cancelado', 'warning');
                    } else {
                        mpStatusEl.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Esperando... (${attempts}s)`;
                    }
                } catch (err) {
                    console.error('Mixed MP poll error:', err);
                }
            }, 2000);
        }

        // Cuando se escribe el monto de MP, auto-completar el de efectivo
        mpInput.addEventListener('input', () => {
            const mpAmt = parseFloat(mpInput.value) || 0;
            const remaining = totalAmt - mpAmt;
            if (remaining > 0 && mpAmt > 0) {
                cashInput.value = remaining.toFixed(2);
            } else if (mpAmt >= totalAmt) {
                cashInput.value = '';
            }
            updateMixed();
        });

        cashInput.addEventListener('input', updateMixed);

        function closeMixed(skipFocus) {
            if (!mixedActive) return;
            mixedActive = false;
            if (mpPollInterval) { clearInterval(mpPollInterval); mpPollInterval = null; }
            document.removeEventListener('keydown', onMixedKey, true);
            overlay.remove();
            if (!skipFocus) productSearch?.focus();
        }

        async function doMixedConfirm() {
            const mpAmt   = parseFloat(mpInput.value) || 0;
            const cashAmt = parseFloat(cashInput.value) || 0;
            const totalPaid = mpAmt + cashAmt;

            if (Math.round(totalPaid * 100) < Math.round(totalAmt * 100)) {
                showToast('El monto total es menor al total a cobrar', 'warning');
                return;
            }
            if (mpAmt <= 0 || cashAmt <= 0) {
                showToast('Ambos montos deben ser mayores a 0', 'warning');
                return;
            }

            confirmBtn.disabled = true;
            confirmBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';

            try {
                const resp = await fetch(API_URLS.checkout, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                    body: JSON.stringify({
                        transaction_id: TRANSACTION_ID,
                        payments: [
                            { method_id: mpMethod.id, amount: mpAmt },
                            { method_id: cashMethod.id, amount: cashAmt }
                        ]
                    })
                });
                const data = await resp.json();
                if (data.success) {
                    closeMixed(true);
                    showSaleSuccessModal(data);
                } else {
                    showToast(data.error || 'Error al procesar la venta', 'error');
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR MIXTO';
                }
            } catch (err) {
                console.error('Mixed checkout error:', err);
                showToast('Error al conectar con el servidor', 'error');
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = '<i class="fas fa-check me-2"></i>COBRAR MIXTO';
            }
        }

        function onMixedKey(e) {
            if (!mixedActive) return;
            if (document.activeElement === mpInput || document.activeElement === cashInput) {
                if (e.key === 'Enter') {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                    if (!confirmBtn.disabled) doMixedConfirm();
                } else if (e.key === 'Escape') {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                    closeMixed();
                } else if (e.key === 'Tab') {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                    if (document.activeElement === mpInput) { cashInput.focus(); cashInput.select(); }
                    else { mpInput.focus(); mpInput.select(); }
                } else if (/^F\d+$/.test(e.key)) {
                    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                }
                return;
            }
            e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
            if (e.key === 'Escape') closeMixed();
            else if (e.key === 'Tab') { mpInput.focus(); mpInput.select(); }
            else if (e.key === 'Enter' && !confirmBtn.disabled) doMixedConfirm();
        }

        document.addEventListener('keydown', onMixedKey, true);

        confirmBtn.addEventListener('click', doMixedConfirm);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeMixed(); });

        updateMixed();
        setTimeout(() => { mpInput.focus(); }, 50);
    }

    // Expose for sidebar quick-pay button
    window.POS_openMixedCheckout = openMixedCheckout;

    // Checkout (legacy init — ahora solo conecta el botón COBRAR al overlay rápido)
    function initCheckout() {
        const checkoutModal = document.getElementById('checkoutModal');
        const confirmPayment = document.getElementById('confirm-payment');
        const checkoutTotal = document.getElementById('checkout-total');
        const totalReceived = document.getElementById('total-received');
        const changeAmount = document.getElementById('change-amount');
        const paymentInputs = document.getElementById('payment-inputs');
        
        if (!btnCheckout) return;

        // Tab cycling para el botón COBRAR
        btnCheckout.addEventListener('keydown', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                e.preventDefault();
                productSearch?.focus();
            }
            if (e.key === 'Tab' && e.shiftKey) {
                e.preventDefault();
                if (cart.items?.length > 0) setCartFocus(cart.items.length - 1);
                else productSearch?.focus();
            }
        });

        // Abrir fast checkout al hacer click
        btnCheckout.addEventListener('click', openFastCheckout);

        // ── Mantener modal antiguo funcional (backup / ventas al costo etc.) ──
        if (!checkoutModal) return;
        
        // Payment method checkboxes
        document.querySelectorAll('.payment-method-check').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const methodId = this.dataset.methodId;
                const methodName = this.dataset.methodName;
                const methodCode = this.dataset.methodCode;
                
                if (this.checked) {
                    // Check if Mercado Pago Point Smart method (tarjeta_mp / mp_point / debit / credit).
                    // 'mercadopago' code = QR estático: NO usa Point, se cobra como cualquier otro
                    // método después de que el cliente escanea el QR impreso desde el panel de MP.
                    // 'debit' / 'credit' → Point forzado al tipo de tarjeta correspondiente.
                    const isMercadoPago = methodCode === 'tarjeta_mp' || methodCode === 'mp_point'
                                       || methodCode === 'debit' || methodCode === 'credit';
                    
                    // Add input
                    const inputHtml = `
                        <div class="payment-method-input mb-3" id="input-method-${methodId}">
                            <label class="form-label">${methodName}</label>
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" 
                                       class="form-control bg-dark text-white payment-amount" 
                                       data-method-id="${methodId}"
                                       data-method-code="${methodCode || ''}"
                                       step="0.01" 
                                       min="0"
                                       value="${cart.total.toFixed(2)}">
                            </div>
                            ${isMercadoPago ? `
                            <div class="mt-2">
                                <button type="button" class="btn btn-info btn-sm btn-mp-point" data-method-id="${methodId}">
                                    <i class="fas fa-mobile-alt me-1"></i>Enviar a Point
                                </button>
                                <span class="ms-2 mp-status text-muted small" id="mp-status-${methodId}"></span>
                            </div>
                            ` : ''}
                        </div>
                    `;
                    if (paymentInputs) {
                        paymentInputs.insertAdjacentHTML('beforeend', inputHtml);
                        
                        // Focus the input
                        const input = paymentInputs.querySelector(`[data-method-id="${methodId}"]`);
                        if (input) {
                            input.focus();
                            input.select();
                            input.addEventListener('input', updatePaymentTotals);
                            // Teclado: Tab → confirm; Enter → confirmar si habilitado
                            input.addEventListener('keydown', (ev) => {
                                if (ev.key === 'Tab' && !ev.shiftKey) {
                                    ev.preventDefault();
                                    const allAmts = Array.from(paymentInputs.querySelectorAll('.payment-amount'));
                                    const ci = allAmts.indexOf(input);
                                    if (allAmts[ci + 1]) {
                                        allAmts[ci + 1].focus();
                                    } else {
                                        document.getElementById('confirm-payment')?.focus();
                                    }
                                }
                                if (ev.key === 'Tab' && ev.shiftKey) {
                                    ev.preventDefault();
                                    const allAmts = Array.from(paymentInputs.querySelectorAll('.payment-amount'));
                                    const ci = allAmts.indexOf(input);
                                    if (allAmts[ci - 1]) {
                                        allAmts[ci - 1].focus();
                                    } else {
                                        document.querySelector('.payment-method-check')?.focus();
                                    }
                                }
                                if (ev.key === 'Enter') {
                                    ev.preventDefault();
                                    const btn = document.getElementById('confirm-payment');
                                    if (btn && !btn.disabled) btn.click();
                                }
                            });
                        }
                        
                        // Add Mercado Pago Point button handler
                        if (isMercadoPago) {
                            const mpBtn = paymentInputs.querySelector(`.btn-mp-point[data-method-id="${methodId}"]`);
                            if (mpBtn) {
                                mpBtn.addEventListener('click', () => handleMercadoPagoPoint(methodId));
                            }
                        }
                    }
                } else {
                    // Remove input
                    const inputDiv = document.getElementById(`input-method-${methodId}`);
                    if (inputDiv) inputDiv.remove();
                }
                
                updatePaymentTotals();
            });
        });
        
        // Handle Mercado Pago Point integration
        async function handleMercadoPagoPoint(methodId) {
            const input = document.querySelector(`.payment-amount[data-method-id="${methodId}"]`);
            const statusEl = document.getElementById(`mp-status-${methodId}`);
            const mpBtn = document.querySelector(`.btn-mp-point[data-method-id="${methodId}"]`);

            if (!input) return;

            const amount = parseFloat(input.value) || 0;
            if (amount <= 0) {
                showToast('Ingrese un monto válido', 'warning');
                return;
            }

            // Derivar payment_type según el código del método:
            // debit → débito forzado; credit → crédito forzado; tarjeta_mp → cualquiera
            const methodCode = input.dataset.methodCode || '';
            let paymentType = null;
            if (methodCode === 'debit') paymentType = 'debit_card';
            else if (methodCode === 'credit') paymentType = 'credit_card';

            try {
                mpBtn.disabled = true;
                mpBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Enviando...';
                statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Conectando con Point...';
                statusEl.className = 'ms-2 mp-status text-info small';

                const body = {
                    amount: amount,
                    transaction_id: TRANSACTION_ID
                };
                if (paymentType) body.payment_type = paymentType;

                const response = await fetch('/mercadopago/api/create-intent/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': CSRF_TOKEN
                    },
                    body: JSON.stringify(body)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    statusEl.innerHTML = '<i class="fas fa-check text-success"></i> Enviado al Point';
                    statusEl.className = 'ms-2 mp-status text-success small';
                    mpBtn.innerHTML = '<i class="fas fa-check me-1"></i>Enviado';
                    
                    // Start polling for payment status
                    if (data.payment_intent && data.payment_intent.id) {
                        pollMercadoPagoStatus(data.payment_intent.id, methodId, statusEl, mpBtn);
                    }
                    
                    showToast('Pago enviado al Point. Esperando confirmación...', 'info');
                } else {
                    throw new Error(data.error || 'Error al conectar con Mercado Pago');
                }
            } catch (error) {
                console.error('MP Point error:', error);
                statusEl.innerHTML = '<i class="fas fa-times text-danger"></i> Error';
                statusEl.className = 'ms-2 mp-status text-danger small';
                mpBtn.disabled = false;
                mpBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                showToast(error.message || 'Error al conectar con Mercado Pago Point', 'error');
            }
        }
        
        // Poll for Mercado Pago payment status
        async function pollMercadoPagoStatus(paymentIntentId, methodId, statusEl, mpBtn) {
            let attempts = 0;
            const maxAttempts = 60; // 2 minutes max
            
            const pollInterval = setInterval(async () => {
                attempts++;
                
                if (attempts > maxAttempts) {
                    clearInterval(pollInterval);
                    statusEl.innerHTML = '<i class="fas fa-clock text-warning"></i> Tiempo agotado';
                    mpBtn.disabled = false;
                    mpBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                    return;
                }
                
                try {
                    const response = await fetch(`/mercadopago/api/status/${paymentIntentId}/`);
                    const data = await response.json();
                    
                    if (data.status === 'approved' || data.status === 'FINISHED') {
                        clearInterval(pollInterval);
                        statusEl.innerHTML = '<i class="fas fa-check-circle text-success"></i> ¡Pago aprobado!';
                        mpBtn.classList.remove('btn-info');
                        mpBtn.classList.add('btn-success');
                        mpBtn.innerHTML = '<i class="fas fa-check me-1"></i>Aprobado';
                        showToast('¡Pago con Mercado Pago aprobado!', 'success');
                    } else if (data.status === 'rejected' || data.status === 'cancelled' || data.status === 'CANCELED') {
                        clearInterval(pollInterval);
                        statusEl.innerHTML = '<i class="fas fa-times-circle text-danger"></i> Rechazado';
                        mpBtn.disabled = false;
                        mpBtn.innerHTML = '<i class="fas fa-mobile-alt me-1"></i>Reintentar';
                        showToast('Pago rechazado o cancelado', 'warning');
                    } else {
                        // Still processing
                        statusEl.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Esperando... (${attempts}s)`;
                    }
                } catch (error) {
                    console.error('Poll error:', error);
                }
            }, 2000); // Poll every 2 seconds
        }
        
        function updatePaymentTotals() {
            let total = 0;
            if (paymentInputs) {
                paymentInputs.querySelectorAll('.payment-amount').forEach(input => {
                    total += parseFloat(input.value) || 0;
                });
            }
            
            if (totalReceived) totalReceived.textContent = formatCurrency(total);
            
            const change = total - cart.total;
            if (changeAmount) changeAmount.textContent = formatCurrency(Math.max(0, change));
            
            // Enable confirm button if total received >= cart total
            if (confirmPayment) confirmPayment.disabled = total < cart.total;
        }
        
        if (confirmPayment) {
            confirmPayment.addEventListener('click', async () => {
                const payments = [];
                if (paymentInputs) {
                    paymentInputs.querySelectorAll('.payment-amount').forEach(input => {
                        const amount = parseFloat(input.value) || 0;
                        if (amount > 0) {
                            payments.push({
                                method_id: parseInt(input.dataset.methodId),
                                amount: amount
                            });
                        }
                    });
                }
                
                if (payments.length === 0) {
                    showToast('Seleccione un método de pago', 'warning');
                    return;
                }
                
                try {
                    confirmPayment.disabled = true;
                    confirmPayment.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Procesando...';
                    
                    const response = await fetch(API_URLS.checkout, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': CSRF_TOKEN
                        },
                        body: JSON.stringify({
                            transaction_id: TRANSACTION_ID,
                            payments: payments
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        bootstrap.Modal.getInstance(checkoutModal).hide();
                        
                        // Show success modal with print option
                        showSaleSuccessModal(data);
                    } else {
                        showToast(data.error || 'Error al procesar la venta', 'error');
                    }
                } catch (error) {
                    console.error('Checkout error:', error);
                    showToast('Error al procesar la venta', 'error');
                } finally {
                    confirmPayment.disabled = false;
                    confirmPayment.innerHTML = '<i class="fas fa-check me-2"></i>Confirmar Pago';
                }
            });
            // Shift+Tab desde confirm-payment → último input de monto
            confirmPayment.addEventListener('keydown', (e) => {
                if (e.key === 'Tab' && e.shiftKey) {
                    e.preventDefault();
                    const allAmts = paymentInputs?.querySelectorAll('.payment-amount');
                    if (allAmts && allAmts.length > 0) {
                        allAmts[allAmts.length - 1].focus();
                    } else {
                        document.querySelector('.payment-method-check')?.focus();
                    }
                }
            });
        }
    }
    
    // ─── Descuento sobre ítem específico del carrito ─────────────────────────────
    function showItemDiscountModal(item) {
        const itemTotal = item.unit_price * item.quantity;
        const hasDiscount = item.discount > 0;

        const html = `
        <div class="modal fade" id="itemDiscountModal" tabindex="-1">
            <div class="modal-dialog modal-sm modal-dialog-centered">
                <div class="modal-content bg-dark text-white">
                    <div class="modal-header border-secondary py-2">
                        <h6 class="modal-title mb-0">
                            <i class="fas fa-percent me-2 text-warning"></i>Descuento solo en este producto
                        </h6>
                        <button type="button" class="btn-close btn-close-white btn-sm" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body pb-2">
                        <p class="mb-1 fw-bold">${item.product_name || item.name}</p>
                        <p class="text-muted small mb-3">
                            ${item.quantity} × ${formatCurrency(item.unit_price)} =
                            <strong class="text-white">${formatCurrency(itemTotal)}</strong>
                        </p>
                        ${hasDiscount ? `
                        <div class="alert alert-success py-1 px-2 mb-3 d-flex justify-content-between align-items-center">
                            <span class="small">Descuento actual: <strong>-${formatCurrency(item.discount)}</strong></span>
                            <button type="button" class="btn btn-sm btn-outline-danger py-0" id="btn-remove-item-discount">
                                <i class="fas fa-times me-1"></i>Quitar
                            </button>
                        </div>` : ''}
                        <!-- Tipo -->
                        <div class="btn-group w-100 mb-3" role="group">
                            <input type="radio" class="btn-check" name="item-disc-type" id="idt-percent" value="percent" checked>
                            <label class="btn btn-outline-secondary btn-sm" for="idt-percent">
                                <i class="fas fa-percent me-1"></i>%
                            </label>
                            <input type="radio" class="btn-check" name="item-disc-type" id="idt-fixed" value="fixed">
                            <label class="btn btn-outline-secondary btn-sm" for="idt-fixed">
                                <i class="fas fa-dollar-sign me-1"></i>Monto $
                            </label>
                        </div>
                        <!-- Presets rápidos -->
                        <div class="d-flex gap-1 mb-2 flex-wrap" id="item-disc-presets">
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="5">5%</button>
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="10">10%</button>
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="15">15%</button>
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="20">20%</button>
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="25">25%</button>
                            <button class="btn btn-outline-warning btn-sm preset-btn" data-val="50">50%</button>
                        </div>
                        <!-- Valor -->
                        <div class="input-group input-group-sm mb-2">
                            <span class="input-group-text bg-dark text-warning border-secondary" id="item-disc-symbol">%</span>
                            <input type="number" id="item-disc-value" class="form-control bg-secondary text-white border-secondary"
                                   min="0.01" step="0.01" value="10" placeholder="Valor">
                        </div>
                        <!-- Preview -->
                        <div class="text-center small text-muted mb-1" id="item-disc-preview">
                            Descuento: <strong id="item-disc-preview-amount" class="text-success">—</strong>
                            &nbsp;→ Subtotal: <strong id="item-disc-preview-sub" class="text-white">—</strong>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary py-2">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-warning btn-sm" id="btn-apply-item-discount">
                            <i class="fas fa-check me-1"></i>Aplicar
                        </button>
                    </div>
                </div>
            </div>
        </div>`;

        document.getElementById('itemDiscountModal')?.remove();
        document.body.insertAdjacentHTML('beforeend', html);

        const modal   = new bootstrap.Modal(document.getElementById('itemDiscountModal'));
        const valEl   = document.getElementById('item-disc-value');
        const symEl   = document.getElementById('item-disc-symbol');
        const prevAmt = document.getElementById('item-disc-preview-amount');
        const prevSub = document.getElementById('item-disc-preview-sub');
        const applyBtn= document.getElementById('btn-apply-item-discount');

        function getType() {
            return document.querySelector('input[name="item-disc-type"]:checked')?.value || 'percent';
        }

        function updatePreview() {
            const type = getType();
            const val = parseFloat(valEl.value) || 0;
            let disc = 0;
            if (type === 'percent') disc = itemTotal * val / 100;
            else disc = val;
            disc = Math.min(disc, itemTotal);
            prevAmt.textContent = formatCurrency(disc);
            prevSub.textContent = formatCurrency(itemTotal - disc);
            applyBtn.disabled = val <= 0;
        }

        // Cambio de tipo → actualizar símbolo, presets y preview
        document.querySelectorAll('input[name="item-disc-type"]').forEach(r => {
            r.addEventListener('change', () => {
                const isPercent = getType() === 'percent';
                symEl.textContent = isPercent ? '%' : '$';
                // Actualizar presets
                const presets = document.getElementById('item-disc-presets');
                if (isPercent) {
                    presets.innerHTML = `
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="5">5%</button>
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="10">10%</button>
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="15">15%</button>
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="20">20%</button>
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="25">25%</button>
                        <button class="btn btn-outline-warning btn-sm preset-btn" data-val="50">50%</button>`;
                } else {
                    const presetAmts = [100, 200, 500, 1000].filter(v => v < itemTotal);
                    presets.innerHTML = presetAmts.map(v =>
                        `<button class="btn btn-outline-warning btn-sm preset-btn" data-val="${v}">${formatCurrency(v)}</button>`
                    ).join('');
                }
                bindPresets();
                updatePreview();
            });
        });

        function bindPresets() {
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    valEl.value = btn.dataset.val;
                    updatePreview();
                });
            });
        }

        bindPresets();
        valEl.addEventListener('input', updatePreview);
        updatePreview();

        // Quitar descuento existente
        document.getElementById('btn-remove-item-discount')?.addEventListener('click', async () => {
            modal.hide();
            await applyItemDiscount(item.id, 'remove', 0);
        });

        applyBtn.addEventListener('click', async () => {
            const val = parseFloat(valEl.value) || 0;
            if (val <= 0) return;
            modal.hide();
            await applyItemDiscount(item.id, getType(), val);
        });

        // Atajos de teclado dentro del modal
        document.getElementById('itemDiscountModal').addEventListener('keydown', e => {
            if (e.key === 'Enter') { e.preventDefault(); applyBtn.click(); }
        });

        modal.show();
        setTimeout(() => { valEl.focus(); valEl.select(); }, 300);
    }

    async function applyItemDiscount(itemId, type, value) {
        try {
            const resp = await fetch(`${API_URLS.cartItemDiscount}${itemId}/discount/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ type, value }),
            });
            const data = await resp.json();
            if (data.success) {
                showToast(data.message, 'success');
                await loadCart();
            } else {
                showToast(data.error || 'Error al aplicar descuento', 'error');
            }
        } catch (err) {
            console.error('Item discount error:', err);
            showToast('Error de conexión', 'error');
        }
    }

    // Show sale success modal with print option
    function showSaleSuccessModal(data) {
        // Limpiar backdrops huérfanos de Bootstrap
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');

        const changeHtml = data.change > 0 ? `
            <div style="background:rgba(241,196,15,0.06);border:1px solid rgba(241,196,15,0.15);border-radius:12px;padding:12px 18px;margin-bottom:1.2rem;display:inline-flex;align-items:center;gap:10px;">
                <i class="fas fa-coins" style="color:#f1c40f;font-size:1.2rem;"></i>
                <span style="font-weight:700;color:#f1c40f;font-size:1.15rem;">Vuelto: ${formatCurrency(data.change)}</span>
            </div>` : '';

        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="saleSuccessModal" tabindex="-1" data-bs-backdrop="static" style="z-index:10050;">
                <div class="modal-dialog modal-dialog-centered" style="max-width:420px;">
                    <div class="modal-content" style="background:linear-gradient(180deg,#1e1e3a 0%,#161628 100%);border:1px solid rgba(46,204,113,0.2);border-radius:20px;color:#eaeaea;overflow:hidden;">
                        <div class="modal-body text-center" style="padding:2.5rem 2rem 2rem;">
                            <div style="margin-bottom:1.2rem;">
                                <div style="width:72px;height:72px;margin:0 auto;border-radius:50%;background:rgba(46,204,113,0.08);border:2px solid rgba(46,204,113,0.25);display:flex;align-items:center;justify-content:center;">
                                    <i class="fas fa-check" style="font-size:2.2rem;color:#2ecc71;"></i>
                                </div>
                            </div>
                            <h3 style="font-weight:700;margin-bottom:0.4rem;color:#fff;font-size:1.3rem;">¡Venta Completada!</h3>
                            <p style="color:#666;font-size:0.8rem;margin-bottom:1rem;">
                                Ticket: <strong style="color:#00d2d3;font-family:'Courier New',monospace;letter-spacing:0.02em;">${data.ticket_number}</strong>
                            </p>
                            <div style="font-size:2.2rem;font-weight:800;color:#2ecc71;margin-bottom:1rem;text-shadow:0 0 20px rgba(46,204,113,0.2);">
                                ${formatCurrency(data.total)}
                            </div>
                            ${changeHtml}
                            <div style="display:flex;justify-content:center;gap:10px;margin-top:0.8rem;">
                                <button type="button" class="btn" id="btnSkipPrint"
                                    style="background:rgba(255,255,255,0.05);border:1.5px solid rgba(255,255,255,0.12);color:#aaa;border-radius:10px;padding:10px 24px;font-weight:600;font-size:0.95rem;transition:all 0.15s;">
                                    <i class="fas fa-forward me-2"></i>Continuar
                                </button>
                                <button type="button" class="btn" id="btnPrintTicket"
                                    style="background:rgba(0,210,211,0.08);border:1.5px solid rgba(0,210,211,0.25);color:#00d2d3;border-radius:10px;padding:10px 24px;font-weight:600;font-size:0.95rem;transition:all 0.15s;">
                                    <i class="fas fa-print me-2"></i>Imprimir
                                </button>
                            </div>
                            <p style="color:#444;font-size:0.65rem;margin-top:1rem;margin-bottom:0;">
                                <kbd style="background:#222240;color:#00d2d3;padding:1px 5px;border-radius:3px;font-size:0.6rem;border:1px solid #3a3a5a;">Enter</kbd> continuar
                                &ensp;
                                <kbd style="background:#222240;color:#00d2d3;padding:1px 5px;border-radius:3px;font-size:0.6rem;border:1px solid #3a3a5a;">P</kbd> imprimir
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('saleSuccessModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const successModal = document.getElementById('saleSuccessModal');
        const modal = new bootstrap.Modal(successModal);
        modal.show();
        
        // Foco en "Continuar" al mostrar el modal (navegación por teclado)
        successModal.addEventListener('shown.bs.modal', () => {
            document.getElementById('btnSkipPrint')?.focus();
        }, { once: true });
        
        // Print ticket button
        document.getElementById('btnPrintTicket').addEventListener('click', () => {
            // Abrir ventana del ticket (se auto-imprime y auto-cierra sola)
            const printWin = window.open(`/pos/ticket/${data.transaction_id}/`, '_blank', 'width=320,height=500,menubar=no,toolbar=no,location=no,status=no');
            if (printWin) {
                printWin.focus();
            }
            modal.hide();
            window.location.reload();
        });
        
        // Skip print button
        document.getElementById('btnSkipPrint').addEventListener('click', () => {
            modal.hide();
            window.location.reload();
        });
        
        // Cleanup on hide
        successModal.addEventListener('hidden.bs.modal', () => {
            successModal.remove();
        });
    }

    // Keyboard Shortcuts
    // ─── Keyboard shortcuts (dynamic, from server) ───────────────────────────

    // Build a lookup map:  key → action  (e.g. 'F8' → 'checkout')
    let shortcutMap = {};

    // Map action → button element ID for badge updates
    const ACTION_BUTTON_MAP = {
        'help': null,
        'search_focus': null,
        'clear_cart': null,
        'hold': 'btn-hold',
        'suspended': 'btn-suspended',
        'discount': 'btn-discount',
        'cancel': 'btn-cancel',
        'checkout': 'btn-checkout',
        'reprint': 'btn-reprint',
        'cost_sale': 'btn-cost-sale',
        'internal_consumption': 'btn-internal-consumption',
        'dashboard': null,
    };

    function buildShortcutMap(shortcuts) {
        shortcutMap = {};
        (shortcuts || []).forEach(sc => {
            if (sc.is_enabled && sc.key && sc.key !== 'none') {
                shortcutMap[sc.key] = sc.action;
            }
        });
        // Update shortcut badges on buttons
        updateShortcutBadges(shortcuts || []);
    }

    function updateShortcutBadges(shortcuts) {
        // Build action→key map
        const actionKeyMap = {};
        shortcuts.forEach(sc => {
            actionKeyMap[sc.action] = (sc.key && sc.key !== 'none') ? sc.key : null;
        });
        // Update each button badge
        Object.entries(ACTION_BUTTON_MAP).forEach(([action, btnId]) => {
            if (!btnId) return;
            const btn = document.getElementById(btnId);
            if (!btn) return;
            let badge = btn.querySelector('.shortcut-badge');
            const keyLabel = actionKeyMap[action] || null;
            if (keyLabel) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'shortcut-badge';
                    btn.appendChild(badge);
                }
                badge.textContent = keyLabel;
                badge.style.display = '';
            } else if (badge) {
                badge.style.display = 'none';
            }
        });
        // Also update quick pay buttons' key badges in sidebar
        document.querySelectorAll('.quick-pay-btn').forEach(btn => {
            const methodCode = btn.dataset.methodCode;
            const payAction = 'pay_' + methodCode;
            const keyLabel = actionKeyMap[payAction] || null;
            let keyBadge = btn.querySelector('.pay-key');
            if (keyLabel) {
                if (!keyBadge) {
                    keyBadge = document.createElement('span');
                    keyBadge.className = 'pay-key';
                    btn.appendChild(keyBadge);
                }
                keyBadge.textContent = keyLabel;
                keyBadge.style.display = '';
                keyBadge.classList.remove('none');
            } else if (keyBadge) {
                keyBadge.style.display = 'none';
            }
        });
    }

    // Expose so pos-sidebar.js can refresh after admin changes
    window.POS_rebuildShortcuts = buildShortcutMap;

    function dispatchAction(action) {
        switch (action) {
            case 'help':                showShortcutsHelp(); break;
            case 'search_focus':
                if (productSearch) { productSearch.focus(); productSearch.select(); }
                break;
            case 'clear_cart':          clearCart(); break;
            case 'hold':                document.getElementById('btn-hold')?.click(); break;
            case 'suspended':           document.getElementById('btn-suspended')?.click(); break;
            case 'discount':            document.getElementById('btn-discount')?.click(); break;
            case 'cancel':              document.getElementById('btn-cancel')?.click(); break;
            case 'checkout':
                if (btnCheckout && !btnCheckout.disabled) openFastCheckout();
                break;
            case 'reprint':             document.getElementById('btn-reprint')?.click(); break;
            case 'cost_sale':           document.getElementById('btn-cost-sale')?.click(); break;
            case 'internal_consumption':document.getElementById('btn-internal-consumption')?.click(); break;
            case 'sales_history':
                // Open sidebar → history tab
                if (window.POS_sidebar) window.POS_sidebar.openTab('history');
                break;
            case 'dashboard':
                posConfirm('¿Salir del POS?', () => { window.location.href = '/dashboard/'; });
                break;
            case 'pay_mixed':
                if (btnCheckout && !btnCheckout.disabled) openMixedCheckout();
                break;
            // pay_* actions → quick checkout
            default:
                if (action.startsWith('pay_')) {
                    const methodCode = action.replace('pay_', '');
                    if (btnCheckout && !btnCheckout.disabled) openFastCheckout(methodCode);
                }
        }
    }

    function initKeyboardShortcuts() {
        // Build map from pre-loaded shortcuts
        buildShortcutMap(typeof INITIAL_SHORTCUTS !== 'undefined' ? INITIAL_SHORTCUTS : []);

        document.addEventListener('keydown', function(e) {
            // Get active modal
            const activeModal = document.querySelector('.modal.show');
            
            // Modal-specific shortcuts
            if (activeModal) {
                const modalId = activeModal.id;
                
                // Checkout modal shortcuts
                if (modalId === 'checkoutModal') {
                    // Enter to confirm payment (only if not typing in an input field)
                    if (e.key === 'Enter' && !e.target.tagName.match(/INPUT|TEXTAREA/)) {
                        e.preventDefault();
                        const confirmBtn = document.getElementById('confirm-payment');
                        if (confirmBtn && !confirmBtn.disabled) {
                            confirmBtn.click();
                        }
                    }
                    // Escape to close modal
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        bootstrap.Modal.getInstance(activeModal).hide();
                    }
                    // Number keys 1-9 for payment method selection
                    if (e.key >= '1' && e.key <= '9' && !e.target.tagName.match(/INPUT|TEXTAREA/)) {
                        e.preventDefault();
                        const methodIndex = parseInt(e.key) - 1;
                        const checkboxes = document.querySelectorAll('.payment-method-check');
                        if (checkboxes[methodIndex]) {
                            checkboxes[methodIndex].checked = !checkboxes[methodIndex].checked;
                            checkboxes[methodIndex].dispatchEvent(new Event('change'));
                        }
                    }
                }
                
                // Quantity modal shortcuts
                if (modalId === 'quantityModal') {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        document.getElementById('confirm-quantity')?.click();
                    }
                }
                
                // Cost sale modal shortcuts
                if (modalId === 'costSaleModal') {
                    if (e.key === 'Enter' && !e.target.tagName.match(/INPUT|TEXTAREA/)) {
                        e.preventDefault();
                        document.getElementById('confirm-cost-sale')?.click();
                    }
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        bootstrap.Modal.getInstance(activeModal).hide();
                    }
                }
                
                // Internal consumption modal shortcuts
                if (modalId === 'internalConsumptionModal') {
                    if (e.key === 'Enter' && !e.target.tagName.match(/INPUT|TEXTAREA/)) {
                        e.preventDefault();
                        document.getElementById('confirm-consumption')?.click();
                    }
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        bootstrap.Modal.getInstance(activeModal).hide();
                    }
                }
                
                // Discount modal shortcuts
                if (modalId === 'discountModal') {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        document.getElementById('confirm-discount')?.click();
                    }
                    if (e.key === 'Escape') {
                        e.preventDefault();
                        bootstrap.Modal.getInstance(activeModal)?.hide();
                    }
                }
                
                // Sale success modal shortcuts (→ P para imprimir, Enter/Esp continuar)
                if (modalId === 'saleSuccessModal') {
                    if (e.key === 'p' || e.key === 'P') {
                        e.preventDefault();
                        document.getElementById('btnPrintTicket')?.click();
                    }
                }
                
                return; // Don't process other shortcuts while modal is open
            }
            
            // ── F-keys & configured shortcuts: SIEMPRE funcionan, sin importar el foco ──
            // Esto va ANTES de la guarda de INPUT para que F1-F12 y atajos configurados
            // se disparen inclusive cuando el cursor está en el buscador.
            const isFKey = /^F\d+$/.test(e.key);
            const isAltNum = e.altKey && e.key >= '1' && e.key <= '9';
            if (isFKey || isAltNum) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                // Lookup in configurable shortcut map
                const keyStr = e.altKey ? `Alt+${e.key}` : e.key;
                const action = shortcutMap[keyStr];
                if (action) {
                    dispatchAction(action);
                }
                return;
            }

            // Don't trigger shortcuts when typing in inputs (except specific keys)
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                // Escape - blur input and clear search
                if (e.key === 'Escape') {
                    e.target.blur();
                    hideSearchResults();
                    if (productSearch) {
                        productSearch.value = '';
                        productSearch.focus();
                    }
                    return;
                }
                // Tab in search - select first result
                if (e.key === 'Tab' && e.target === productSearch && searchResults?.style.display !== 'none') {
                    e.preventDefault();
                    const firstResult = searchResultsList?.querySelector('.search-result-item');
                    if (firstResult) {
                        firstResult.click();
                    }
                    return;
                }
                // Block all other keys from triggering shortcuts while in input
                return;
            }
            
            // Don't trigger shortcuts from select dropdowns
            if (e.target.tagName === 'SELECT') return;
            
            // Global shortcuts (when not in an input) — dynamic from shortcutMap
            // Handle always-on non-configurable keys first
            if (e.key === 'Escape') {
                hideSearchResults();
                if (productSearch) { productSearch.value = ''; productSearch.focus(); }
                return;
            }
            if (e.key === '+' || e.key === '=') {
                e.preventDefault();
                if (cart.items && cart.items.length > 0) {
                    const target = cartFocusIndex >= 0 ? cart.items[cartFocusIndex] : cart.items[cart.items.length - 1];
                    if (target?.product_id) addToCart(target.product_id, 1);
                }
                return;
            }
            if (e.key === '-') {
                e.preventDefault();
                if (cart.items && cart.items.length > 0) {
                    const target = cartFocusIndex >= 0 ? cart.items[cartFocusIndex] : cart.items[cart.items.length - 1];
                    if (target && target.quantity > 1) updateCartItem(target.id, target.quantity - 1);
                    else if (target) removeCartItem(target.id);
                }
                return;
            }
            if (e.key === 'Delete') {
                e.preventDefault();
                if (cart.items && cart.items.length > 0) {
                    const target = cartFocusIndex >= 0 ? cart.items[cartFocusIndex] : cart.items[cart.items.length - 1];
                    if (target) removeCartItem(target.id);
                }
                return;
            }

            // Configurable shortcut lookup (non-F-key, non-Alt+N — already handled above)
            const keyStr = e.key;
            const action = shortcutMap[keyStr];
            if (action) {
                e.preventDefault();
                e.stopPropagation();
                dispatchAction(action);
            }
        });
        
        // Auto-focus search bar after any click outside inputs/selects
        document.addEventListener('click', function(e) {
            if (e.target.closest('.shortcut-key-select, select')) return;
            if (!e.target.matches('input, select, option, button, a, .btn, .quick-btn, .cart-item *, .search-result-item *')) {
                setTimeout(() => {
                    if (productSearch && !document.querySelector('.modal.show') && document.activeElement?.tagName !== 'SELECT') {
                        productSearch.focus();
                    }
                }, 150);
            }
        });
    }
    
    function showShortcutsHelp() {
        // Build dynamic rows from shortcutMap
        const shortcuts = typeof INITIAL_SHORTCUTS !== 'undefined' ? INITIAL_SHORTCUTS : [];
        const configRows = shortcuts.map(sc => {
            const keyHtml = sc.key === 'none'
                ? '<span style="color:#555">—</span>'
                : `<kbd style="background:#222;color:#00d2d3;padding:2px 6px;border-radius:3px;font-family:monospace">${sc.key}</kbd>`;
            return `<tr><td>${keyHtml}</td><td>${sc.label}</td></tr>`;
        }).join('');

        const helpHtml = `
            <div class="modal fade" id="shortcutsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content bg-dark text-white">
                        <div class="modal-header border-secondary">
                            <h5 class="modal-title"><i class="fas fa-keyboard me-2"></i>Atajos de Teclado</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <h6 class="text-muted mb-2">Atajos configurados</h6>
                                    <table class="table table-dark table-sm">
                                        <tbody>${configRows}</tbody>
                                    </table>
                                    <p class="text-muted small mb-0">
                                        <i class="fas fa-cog me-1"></i>
                                        Configurables desde el panel lateral → Atajos
                                    </p>
                                </div>
                                <div class="col-md-6">
                                    <h6 class="text-muted mb-2">Teclas fijas</h6>
                                    <table class="table table-dark table-sm">
                                        <tbody>
                                            <tr class="table-active"><td colspan="2"><strong>Ciclo de Tab</strong></td></tr>
                                            <tr><td><kbd>Tab</kbd></td><td>Búsqueda → Carrito → COBRAR → (vuelve)</td></tr>
                                            <tr><td><kbd>Shift+Tab</kbd></td><td>Navegar hacia atrás</td></tr>
                                            <tr><td><kbd>Tab</kbd> en búsqueda</td><td>Selecciona primer resultado</td></tr>
                                            <tr class="table-active"><td colspan="2"><strong>Navegación carrito</strong></td></tr>
                                            <tr><td><kbd>↑</kbd> <kbd>↓</kbd></td><td>Mover selección al ítem anterior / siguiente</td></tr>
                                            <tr><td><kbd>+</kbd> <kbd>-</kbd></td><td>Aumentar / disminuir cantidad del ítem seleccionado</td></tr>
                                            <tr><td><kbd>Enter</kbd></td><td>Editar cantidad exacta del ítem seleccionado</td></tr>
                                            <tr><td><kbd>Delete</kbd></td><td>Eliminar ítem seleccionado</td></tr>
                                            <tr><td><kbd>Esc</kbd></td><td>Volver al buscador</td></tr>
                                            <tr><td><kbd>Tab</kbd> (último ítem)</td><td>Ir a COBRAR</td></tr>
                                            <tr class="table-active"><td colspan="2"><strong>General</strong></td></tr>
                                            <tr><td><kbd>Enter</kbd></td><td>Agregar producto / confirmar</td></tr>
                                            <tr><td><kbd>↑</kbd> <kbd>↓</kbd></td><td>Navegar resultados de búsqueda</td></tr>
                                            <tr><td><kbd>+</kbd> <kbd>-</kbd></td><td>Cantidad del ítem enfocado (o último si ninguno)</td></tr>
                                            <tr><td><kbd>Alt+1-9</kbd></td><td>Botones de acceso rápido</td></tr>
                                            <tr><td><kbd>P</kbd> (modal éxito)</td><td>Imprimir ticket</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('shortcutsModal')?.remove();
        document.body.insertAdjacentHTML('beforeend', helpHtml);
        const modal = new bootstrap.Modal(document.getElementById('shortcutsModal'));
        modal.show();
    }

    // Expose formatCurrency and showToast for pos-sidebar.js
    window.POS_formatCurrency = (v) => formatCurrency(v);
    window.POS_showToast = (msg, type) => showToast(msg, type);
    window.POS_cart = () => cart;
    window.POS_loadCart = loadCart;
    window.POS_refreshQuickAccessGrid = refreshQuickAccessGrid;
    window.POS_dispatchAction = dispatchAction;

    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function formatCurrency(value) {
        if (value === null || value === undefined) return '$0';
        const number = parseFloat(value);
        if (isNaN(number)) return '$0';
        
        // Argentine format: $1.234 (sin decimales)
        const intPart = Math.round(number).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return '$' + intPart;
    }

    function showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Limit to max 3 visible toasts — remove oldest
        const existing = toastContainer.querySelectorAll('.toast');
        if (existing.length >= 3) {
            existing[0].remove();
        }
        
        const bgClass = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        }[type] || 'bg-info';
        
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast ${bgClass} text-white" role="alert" style="font-size:.85rem;min-width:auto;">
                <div class="toast-body d-flex justify-content-between align-items-center py-1 px-2">
                    <span>${message}</span>
                    <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="toast" style="font-size:.6rem;"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 1500 });
        toast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

})();
