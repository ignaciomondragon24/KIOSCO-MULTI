/**
 * CHE GOLOSO - Sign Generator Page Logic
 * Product search, auto-fill, items management, and print triggering.
 */

class SignGenerator {
    constructor(config) {
        this.config = config;
        this.items = [];
        this.renderer = new SignRenderer();
        this._init();
    }

    _init() {
        this._setupSearch();
        this._setupPrintControls();
        this._setupNestingListeners();
        this._updateItemsUI();
        this._updateNestingInfo();
        this._updatePreview();

        const btnRefresh = document.getElementById('btnRefreshPreview');
        if (btnRefresh) btnRefresh.addEventListener('click', () => this._updatePreview());
    }

    /* ----------------------------------------------------------
       PRODUCT SEARCH
       ---------------------------------------------------------- */
    _setupSearch() {
        const input = document.getElementById('productSearch');
        const results = document.getElementById('searchResults');
        let timeout = null;

        input.addEventListener('input', () => {
            clearTimeout(timeout);
            const q = input.value.trim();
            if (q.length < 2) { results.innerHTML = ''; results.style.display = 'none'; return; }

            timeout = setTimeout(() => this._search(q), 300);
        });

        // Close results on outside click
        document.addEventListener('click', e => {
            if (!e.target.closest('#productSearch') && !e.target.closest('#searchResults')) {
                results.style.display = 'none';
            }
        });
    }

    async _search(query) {
        const results = document.getElementById('searchResults');
        try {
            const resp = await fetch(`/stocks/api/search/?q=${encodeURIComponent(query)}`);
            const data = await resp.json();
            const products = data.products || [];

            if (products.length === 0) {
                results.innerHTML = '<div class="search-result-item text-muted">No se encontraron productos</div>';
            } else {
                results.innerHTML = products.map(p => `
                    <div class="search-result-item" data-id="${p.id}">
                        <div class="d-flex justify-content-between">
                            <strong>${this._escapeHtml(p.name)}</strong>
                            <span class="text-primary fw-bold">${this._formatPrice(p.sale_price)}</span>
                        </div>
                        <small class="text-muted">${p.barcode || ''} ${p.sku ? '| ' + p.sku : ''}</small>
                    </div>
                `).join('');

                results.querySelectorAll('.search-result-item[data-id]').forEach(el => {
                    el.addEventListener('click', () => {
                        const id = el.dataset.id;
                        this.addProduct(id);
                        results.style.display = 'none';
                        document.getElementById('productSearch').value = '';
                    });
                });
            }
            results.style.display = 'block';
        } catch (err) {
            console.error('Search error:', err);
        }
    }

    /* ----------------------------------------------------------
       ADD PRODUCT
       ---------------------------------------------------------- */
    async addProduct(productId) {
        try {
            const resp = await fetch(
                `${this.config.productDataUrl}?product_id=${productId}&sign_type=${this.config.signType}`
            );
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            this.items.push({
                id: Date.now(),
                product_id: data.product_id,
                product_name: data.product_name,
                data: data.data,
                copies: 1,
            });

            this._updateItemsUI();
            this._updatePreview();
        } catch (err) {
            console.error('Error adding product:', err);
            alert('Error al agregar producto: ' + err.message);
        }
    }

    /* ----------------------------------------------------------
       ITEMS MANAGEMENT
       ---------------------------------------------------------- */
    removeItem(itemId) {
        this.items = this.items.filter(i => i.id !== itemId);
        this._updateItemsUI();
        this._updatePreview();
    }

    setCopies(itemId, copies) {
        const item = this.items.find(i => i.id === itemId);
        if (item) {
            item.copies = Math.max(1, parseInt(copies) || 1);
            this._updateItemsUI();
            this._updatePreview();
        }
    }

    editItemData(itemId, key, value) {
        const item = this.items.find(i => i.id === itemId);
        if (item && item.data) {
            item.data[key] = value;
            this._updatePreview();
        }
    }

    _updateItemsUI() {
        const list = document.getElementById('itemsList');
        const counter = document.getElementById('itemCount');
        const btnPrint = document.getElementById('btnPrint');
        const emptyMsg = document.getElementById('emptyMessage');

        const totalCopies = this.items.reduce((s, i) => s + (i.copies || 1), 0);
        if (counter) counter.textContent = `${this.items.length} producto(s), ${totalCopies} cartel(es)`;

        if (btnPrint) btnPrint.disabled = this.items.length === 0;
        if (emptyMsg) emptyMsg.style.display = this.items.length === 0 ? '' : 'none';

        if (this.items.length === 0) {
            list.innerHTML = '';
            return;
        }

        list.innerHTML = this.items.map(item => `
            <div class="item-row p-2 mb-2 rounded" style="background:#f0f0f5; border:1px solid #dee2e6;">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <strong style="color:#212529;">${this._escapeHtml(item.product_name)}</strong>
                    <button class="btn btn-sm btn-outline-danger" onclick="generator.removeItem(${item.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <label class="small mb-0" style="color:#555;">Copias:</label>
                    <input type="number" class="form-control form-control-sm" style="width:70px"
                        value="${item.copies}" min="1" max="100"
                        onchange="generator.setCopies(${item.id}, this.value)">
                    <button class="btn btn-sm btn-outline-primary ms-auto"
                        onclick="generator.toggleItemEdit(${item.id})" title="Editar datos">
                        <i class="fas fa-pen"></i>
                    </button>
                </div>
                <div id="edit-${item.id}" class="item-edit mt-2" style="display:none;">
                    ${this._renderDataFields(item)}
                </div>
            </div>
        `).join('');
    }

    _renderDataFields(item) {
        if (!item.data) return '';
        return Object.entries(item.data).map(([key, val]) => `
            <div class="input-group input-group-sm mb-1">
                <span class="input-group-text" style="font-size:0.75rem;">${key}</span>
                <input type="text" class="form-control" value="${this._escapeHtml(String(val))}"
                    onchange="generator.editItemData(${item.id}, '${key}', this.value)">
            </div>
        `).join('');
    }

    toggleItemEdit(itemId) {
        const el = document.getElementById(`edit-${itemId}`);
        if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }

    /* ----------------------------------------------------------
       NESTING INFO & PREVIEW
       ---------------------------------------------------------- */
    _getPrintSettings() {
        const paperSize = document.getElementById('paperSize')?.value || 'A4';
        const margin = parseInt(document.getElementById('printMargin')?.value) || 5;
        const gap = parseInt(document.getElementById('printGap')?.value) || 2;
        return { paperSize, margin, gap };
    }

    _calcGrid(paperSize, margin, gap) {
        const PAPER = { A4: {w:210,h:297}, A3: {w:297,h:420}, letter: {w:216,h:279} };
        const paper = PAPER[paperSize] || PAPER.A4;
        const pw = paper.w - 2 * margin;
        const ph = paper.h - 2 * margin;
        const sw = this.config.widthMM;
        const sh = this.config.heightMM;

        const cols = Math.floor((pw + gap) / (sw + gap));
        const rows = Math.floor((ph + gap) / (sh + gap));
        return { cols, rows, perPage: cols * rows, paper };
    }

    _setupNestingListeners() {
        ['paperSize', 'printMargin', 'printGap'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => {
                this._updateNestingInfo();
                this._updatePreview();
            });
        });
    }

    _updateNestingInfo() {
        const info = document.getElementById('nestingInfo');
        if (!info) return;

        const { paperSize, margin, gap } = this._getPrintSettings();
        const grid = this._calcGrid(paperSize, margin, gap);

        if (grid.perPage === 0) {
            info.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-triangle me-1"></i>El cartel no entra en esta hoja.</span>';
            return;
        }

        const totalCopies = this.items.reduce((s, i) => s + (i.copies || 1), 0);
        const totalPages = totalCopies > 0 ? Math.ceil(totalCopies / grid.perPage) : 0;

        info.innerHTML = `
            <div class="d-flex align-items-center gap-2 flex-wrap">
                <span><i class="fas fa-th me-1"></i><strong>${grid.cols} × ${grid.rows} = ${grid.perPage}</strong> carteles/hoja</span>
                ${totalCopies > 0 ? `<span class="text-primary">| <strong>${totalPages}</strong> hoja(s) para ${totalCopies} cartel(es)</span>` : ''}
            </div>`;
    }

    _updatePreview() {
        const container = document.getElementById('previewArea');
        if (!container) return;

        const { paperSize, margin, gap } = this._getPrintSettings();
        const grid = this._calcGrid(paperSize, margin, gap);
        this._updateNestingInfo();

        if (grid.perPage === 0) {
            container.innerHTML = '<p class="text-danger text-center py-3">El cartel no entra en esta hoja</p>';
            return;
        }

        const paper = grid.paper;
        const sw = this.config.widthMM;
        const sh = this.config.heightMM;

        // Collect product data (expand by copies)
        const allSigns = [];
        this.items.forEach(item => {
            for (let c = 0; c < (item.copies || 1); c++) {
                allSigns.push(item.data);
            }
        });
        const totalCopies = allSigns.length;
        const totalPages = totalCopies > 0 ? Math.ceil(totalCopies / grid.perPage) : 0;

        // Scale paper to fit preview area — use parent's width as fallback
        const containerW = container.clientWidth || container.parentElement?.clientWidth || 500;
        const maxW = containerW - 20;
        const paperWPx = paper.w * 3.78;
        const paperHPx = paper.h * 3.78;
        const scale = Math.min(maxW / paperWPx, 500 / paperHPx, 1);
        const px = 3.78 * scale;

        // Clear AFTER measuring width
        container.innerHTML = '';

        // --- Build ONE representative page showing ALL grid positions filled ---
        const pageDiv = document.createElement('div');
        pageDiv.style.cssText = `position:relative;background:white;border:1px solid #ccc;margin:0 auto 8px;box-shadow:0 2px 10px rgba(0,0,0,0.15);overflow:hidden;`;
        pageDiv.style.width = (paper.w * px) + 'px';
        pageDiv.style.height = (paper.h * px) + 'px';

        for (let i = 0; i < grid.perPage; i++) {
            const row = Math.floor(i / grid.cols);
            const col = i % grid.cols;
            const x = margin + col * (sw + gap);
            const y = margin + row * (sh + gap);

            const slot = document.createElement('div');
            slot.style.cssText = `position:absolute;left:${x * px}px;top:${y * px}px;width:${sw * px}px;height:${sh * px}px;overflow:hidden;border:1px solid #e0e0e0;box-sizing:border-box;`;

            if (allSigns.length > 0) {
                // Cycle through products to fill ALL slots on the page
                const signData = allSigns[i % allSigns.length];
                try {
                    this.renderer.render(slot, this.config.layout, signData, sw, sh, scale);
                } catch (err) {
                    console.error('Error rendering sign slot', i, err);
                    slot.style.background = '#fff3f3';
                    slot.innerHTML = '<span style="color:red;font-size:10px;">Error</span>';
                }
            } else {
                // No products yet — show empty placeholder
                slot.style.border = '1px dashed #ccc';
                slot.style.display = 'flex';
                slot.style.alignItems = 'center';
                slot.style.justifyContent = 'center';
                slot.innerHTML = `<span style="color:#ccc;font-size:${Math.max(8, 10 * scale)}px;"><i class="fas fa-plus"></i></span>`;
            }

            pageDiv.appendChild(slot);
        }

        container.appendChild(pageDiv);

        // Info summary below the page
        const summary = document.createElement('div');
        summary.className = 'text-center small mt-2';
        if (totalCopies > 0) {
            summary.innerHTML = `<span class="text-muted">Entran <strong>${grid.perPage}</strong> carteles por hoja.</span> ` +
                `<span class="text-primary">Con <strong>${totalCopies}</strong> copia(s) necesitás <strong>${totalPages}</strong> hoja(s).</span>`;
        } else {
            summary.innerHTML = `<span class="text-muted">Entran <strong>${grid.perPage}</strong> carteles por hoja. Agregá productos para verlos.</span>`;
        }
        container.appendChild(summary);
    }

    /* ----------------------------------------------------------
       PRINT
       ---------------------------------------------------------- */
    _setupPrintControls() {
        const btnPrint = document.getElementById('btnPrint');
        if (btnPrint) {
            btnPrint.addEventListener('click', () => this.print());
        }
    }

    print() {
        if (this.items.length === 0) {
            alert('Agregá al menos un producto antes de imprimir.');
            return;
        }

        const { paperSize, margin, gap } = this._getPrintSettings();

        const manager = new SignPrintManager({
            signWidthMM: this.config.widthMM,
            signHeightMM: this.config.heightMM,
            layout: this.config.layout,
            items: this.items,
            paperSize: paperSize,
            margin: margin,
            gap: gap,
        });

        manager.openPrintWindow(this.config.printUrl);
    }

    /* ----------------------------------------------------------
       UTILS
       ---------------------------------------------------------- */
    _formatPrice(value) {
        const num = parseFloat(value) || 0;
        return '$' + num.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}


/* ============================================================
   INITIALIZATION
   ============================================================ */
(function() {
    function init() {
        if (typeof GENERATE_CONFIG !== 'undefined') {
            window.generator = new SignGenerator(GENERATE_CONFIG);
        }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
