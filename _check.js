
// State
let selectedImage = null;
let scannedData = null;

// ========== IMAGE HANDLING ==========

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
        alert('La imagen es demasiado grande. MÃ¡ximo 10MB.');
        return;
    }

    selectedImage = file;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('previewImage').src = e.target.result;
        document.getElementById('previewContainer').style.display = 'block';
        document.getElementById('uploadZone').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function clearImage() {
    selectedImage = null;
    document.getElementById('previewImage').src = '';
    document.getElementById('previewContainer').style.display = 'none';
    document.getElementById('uploadZone').style.display = 'block';
    document.getElementById('cameraInput').value = '';
    document.getElementById('fileInput').value = '';
}

// Drag & drop
const uploadZone = document.getElementById('uploadZone');
if (uploadZone) {
    uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                const dt = new DataTransfer();
                dt.items.add(file);
                document.getElementById('fileInput').files = dt.files;
                handleImageSelect({ target: { files: [file] } });
            }
        }
    });
}

// ========== SCAN ==========

async function scanInvoice() {
    if (!selectedImage) {
        alert('Primero seleccionÃ¡ o sacÃ¡ una foto.');
        return;
    }

    // Show processing
    document.getElementById('previewContainer').style.display = 'none';
    document.getElementById('processingOverlay').style.display = 'block';
    document.getElementById('btnScan').disabled = true;

    let result;
    try {
        const formData = new FormData();
        formData.append('image', selectedImage);

        const response = await fetch(''__DJANGO__'', {
            method: 'POST',
            headers: { 'X-CSRFToken': ''__DJANGO_VAR__'' },
            body: formData,
        });

        result = await response.json();
    } catch (err) {
        alert('Error de conexiÃ³n al servidor: ' + err.message);
        document.getElementById('previewContainer').style.display = 'block';
        document.getElementById('processingOverlay').style.display = 'none';
        document.getElementById('btnScan').disabled = false;
        return;
    }

    document.getElementById('processingOverlay').style.display = 'none';
    document.getElementById('btnScan').disabled = false;

    if (result.success) {
        try {
            scannedData = result.data;
            populateResults(scannedData);
            showStep(2);
        } catch (err) {
            console.error('Error procesando resultados:', err);
            alert('Error procesando los datos del remito: ' + err.message);
            document.getElementById('previewContainer').style.display = 'block';
        }
    } else {
        alert('Error: ' + (result.error || 'No se pudo analizar la imagen'));
        document.getElementById('previewContainer').style.display = 'block';
    }
}

// ========== POPULATE RESULTS ==========

function populateResults(data) {
    // Header fields
    document.getElementById('supplierName').value = data.proveedor || '';
    document.getElementById('invoiceNumber').value = data.numero_comprobante || '';
    document.getElementById('invoiceNotes').value = data.notas || '';

    // Try to match supplier
    const supplierSelect = document.getElementById('supplierSelect');
    if (data.proveedor) {
        const match = Array.from(supplierSelect.options).find(
            o => o.text.toLowerCase().includes(data.proveedor.toLowerCase()) ||
                 data.proveedor.toLowerCase().includes(o.text.toLowerCase())
        );
        if (match) {
            supplierSelect.value = match.value;
            document.getElementById('supplierName').style.display = 'none';
        } else {
            supplierSelect.value = '';
            document.getElementById('supplierName').style.display = 'block';
        }
    }

    // Date
    if (data.fecha) {
        // Convert DD/MM/YYYY to YYYY-MM-DD for input
        const parts = data.fecha.split('/');
        if (parts.length === 3) {
            document.getElementById('invoiceDate').value = `${parts[2]}-${parts[1].padStart(2,'0')}-${parts[0].padStart(2,'0')}`;
        }
    } else {
        document.getElementById('invoiceDate').value = new Date().toISOString().split('T')[0];
    }

    // Payment method
    if (data.metodo_pago) {
        const paymentMap = {
            'efectivo': 'cash', 'cash': 'cash',
            'tarjeta': 'card', 'card': 'card',
            'transferencia': 'transfer', 'transfer': 'transfer',
            'cheque': 'check', 'check': 'check',
        };
        const pm = paymentMap[data.metodo_pago.toLowerCase()];
        if (pm) document.getElementById('paymentMethod').value = pm;
    }

    // IVA
    document.getElementById('invoiceIva').value = data.iva || 0;

    // Products
    const tbody = document.getElementById('productsBody');
    tbody.innerHTML = '';

    if (data.productos && data.productos.length > 0) {
        data.productos.forEach((p, idx) => {
            addProductRowData(p, idx);
        });
    }

    updateTotals();
}

function addProductRowData(p, idx) {
    const tbody = document.getElementById('productsBody');
    const tr = document.createElement('tr');
    tr.dataset.index = idx;

    const qty = p.cantidad || 0;
    const price = p.precio_unitario || 0;
    const total = p.precio_total || (qty * price);
    const barcode = p.codigo_barras || '';

    tr.innerHTML = `
        <td class="text-center">
            <i class="fas fa-spinner fa-spin text-muted match-icon" title="Buscando..."></i>
            <button type="button" class="btn btn-sm btn-outline-warning btn-create-product mt-1" 
                    style="display:none; font-size:0.7rem; padding:1px 5px;" 
                    onclick="openCreateProductModal(this.closest('tr'))" title="Crear producto">
                <i class="fas fa-plus"></i>
            </button>
        </td>
        <td class="edit-cell">
            <input type="text" class="fw-bold" value="${escapeHtml(p.nombre || '')}" 
                   data-field="nombre" title="Nombre del producto">
            ${barcode ? `<br><small class="text-muted"><i class="fas fa-barcode me-1"></i>${escapeHtml(barcode)}</small>` : ''}
        </td>
        <td class="edit-cell text-center">
            <input type="number" value="${qty}" min="0" data-field="cantidad" 
                   onchange="recalcRow(this)">
        </td>
        <td class="edit-cell text-end">
            <input type="number" value="${price}" min="0" step="0.01" data-field="precio_unitario" 
                   onchange="recalcRow(this)">
        </td>
        <td class="edit-cell text-end">
            <input type="number" value="${total.toFixed(2)}" min="0" step="0.01" data-field="precio_total"
                   onchange="updateTotals()">
        </td>
        <td>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('tr').remove(); updateTotals();">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;

    // Store barcode as data attribute
    tr.dataset.barcode = barcode || '';

    tbody.appendChild(tr);

    // Check if product exists in DB
    checkProductMatch(tr, p.nombre, barcode);
}

function addProductRow() {
    const tbody = document.getElementById('productsBody');
    const idx = tbody.children.length;
    addProductRowData({
        nombre: '',
        cantidad: 1,
        precio_unitario: 0,
        precio_total: 0,
        codigo_barras: '',
    }, idx);
}

async function checkProductMatch(tr, nombre, barcode) {
    const icon = tr.querySelector('.match-icon');
    try {
        const q = barcode || nombre;
        const response = await fetch(`'__DJANGO__'?q=${encodeURIComponent(q)}`);
        const result = await response.json();

        if (result.results && result.results.length > 0) {
            const matched = result.results[0];
            tr.dataset.productId = matched.id;
            icon.className = 'fas fa-check-circle match-found match-icon';
            icon.title = `Encontrado: ${matched.name}`;
            // Hide create button if exists
            const createBtn = tr.querySelector('.btn-create-product');
            if (createBtn) createBtn.style.display = 'none';
        } else {
            tr.dataset.productId = '';
            icon.className = 'fas fa-exclamation-circle match-not-found match-icon';
            icon.title = 'Producto no encontrado en el sistema';
            // Show create button
            const createBtn = tr.querySelector('.btn-create-product');
            if (createBtn) createBtn.style.display = '';
        }
    } catch {
        icon.className = 'fas fa-question-circle text-muted match-icon';
        icon.title = 'No se pudo verificar';
    }
}

function recalcRow(input) {
    const tr = input.closest('tr');
    const qty = parseFloat(tr.querySelector('[data-field="cantidad"]').value) || 0;
    const price = parseFloat(tr.querySelector('[data-field="precio_unitario"]').value) || 0;
    tr.querySelector('[data-field="precio_total"]').value = (qty * price).toFixed(2);
    updateTotals();
}

function updateTotals() {
    const rows = document.querySelectorAll('#productsBody tr');
    let subtotal = 0;

    rows.forEach(tr => {
        const total = parseFloat(tr.querySelector('[data-field="precio_total"]').value) || 0;
        subtotal += total;
    });

    const iva = parseFloat(document.getElementById('invoiceIva').value) || 0;
    const total = subtotal + iva;

    document.getElementById('summarySubtotal').textContent = fmtMoney(subtotal);
    document.getElementById('summaryTotal').textContent = fmtMoney(total);
}

// ========== CONFIRM ==========

async function confirmInvoice() {
    const rows = document.querySelectorAll('#productsBody tr');
    if (rows.length === 0) {
        alert('No hay productos para confirmar.');
        return;
    }

    const productos = [];
    let notLinkedCount = 0;
    rows.forEach(tr => {
        const nombre = tr.querySelector('[data-field="nombre"]').value.trim();
        const cantidad = parseInt(tr.querySelector('[data-field="cantidad"]').value) || 0;
        const precio_unitario = parseFloat(tr.querySelector('[data-field="precio_unitario"]').value) || 0;
        const precio_total = parseFloat(tr.querySelector('[data-field="precio_total"]').value) || 0;
        const product_id = tr.dataset.productId || null;
        const codigo_barras = tr.dataset.barcode || '';

        if (nombre && cantidad > 0) {
            if (!product_id) notLinkedCount += 1;
            productos.push({ nombre, cantidad, precio_unitario, precio_total, product_id, codigo_barras });
        }
    });

    if (productos.length === 0) {
        alert('No hay productos vÃ¡lidos. CompletÃ¡ nombre y cantidad.');
        return;
    }

    if (notLinkedCount > 0) {
        const proceed = confirm(`Hay ${notLinkedCount} producto(s) sin vincular a un producto del sistema. Se van a omitir en la compra/stock. Â¿QuerÃ©s continuar?`);
        if (!proceed) {
            return;
        }
    }

    const iva = parseFloat(document.getElementById('invoiceIva').value) || 0;
    let subtotal = 0;
    productos.forEach(p => subtotal += p.precio_total);

    const supplierSelect = document.getElementById('supplierSelect');
    const dateInput = document.getElementById('invoiceDate');

    const payload = {
        supplier_id: supplierSelect.value || null,
        supplier_name: document.getElementById('supplierName').value.trim(),
        numero_comprobante: document.getElementById('invoiceNumber').value.trim(),
        fecha: dateInput.value,
        productos: productos,
        subtotal: subtotal,
        iva: iva,
        total: subtotal + iva,
        metodo_pago: document.getElementById('paymentMethod').value,
        notas: document.getElementById('invoiceNotes').value.trim(),
        registrar_gasto: document.getElementById('chkRegisterExpense').checked,
        actualizar_stock: document.getElementById('chkUpdateStock').checked,
    };

    const btnConfirm = document.getElementById('btnConfirm');
    if (btnConfirm) {
        btnConfirm.disabled = true;
        btnConfirm.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Guardando...';
    }

    try {
        const response = await fetch(''__DJANGO__'', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': ''__DJANGO_VAR__'',
            },
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (result.success) {
            showSuccess(result);
        } else {
            alert('Error: ' + (result.error || 'No se pudo guardar'));
        }
    } catch (err) {
        alert('Error de conexiÃ³n: ' + err.message);
    } finally {
        const btnC = document.getElementById('btnConfirm');
        if (btnC) {
            btnC.disabled = false;
            btnC.innerHTML = '<i class="fas fa-check me-2"></i>Confirmar y Guardar';
        }
    }
}

function showSuccess(result) {
    showStep(3);

    let html = `
        <p class="lead">
            Compra <strong>${escapeHtml(result.order_number)}</strong> registrada
        </p>
        <div class="row justify-content-center g-3 mb-3" style="max-width: 600px; margin: 0 auto;">
            <div class="col-4">
                <div class="p-3 bg-light rounded">
                    <div class="fs-3 fw-bold text-primary">${result.items_created}</div>
                    <small class="text-muted">Productos</small>
                </div>
            </div>
            <div class="col-4">
                <div class="p-3 bg-light rounded">
                    <div class="fs-3 fw-bold text-success">${result.stock_updated}</div>
                    <small class="text-muted">Stock actualizado</small>
                </div>
            </div>
            <div class="col-4">
                <div class="p-3 bg-light rounded">
                    <div class="fs-3 fw-bold">${result.expense_id ? 'âœ“' : 'â€”'}</div>
                    <small class="text-muted">Gasto registrado</small>
                </div>
            </div>
        </div>
    `;
    const successEl = document.getElementById('successDetails');
    if (successEl) successEl.innerHTML = html;

    // Show not found products
    if (result.products_not_found && result.products_not_found.length > 0) {
        const warn = document.getElementById('notFoundWarning');
        if (warn) warn.classList.remove('d-none');
        const list = document.getElementById('notFoundList');
        if (list) {
            list.innerHTML = result.products_not_found.map(p =>
                `<li><strong>${escapeHtml(p.nombre)}</strong> (${p.cantidad} u. Ã— $${p.precio.toFixed(2)})</li>`
            ).join('');
        }
    }
}

// ========== NAVIGATION ==========

function showStep(step) {
    // Update step indicators
    for (let i = 1; i <= 3; i++) {
        const el = document.getElementById('step' + i);
        if (el) {
            el.classList.remove('active', 'completed');
            if (i < step) el.classList.add('completed');
            if (i === step) el.classList.add('active');
        }
    }

    // Show/hide sections
    const sections = {
        'uploadSection': step === 1,
        'resultsSection': step === 2,
        'successSection': step === 3,
    };
    for (const [id, show] of Object.entries(sections)) {
        const el = document.getElementById(id);
        if (el) el.style.display = show ? 'block' : 'none';
    }
}

function resetAll() {
    clearImage();
    scannedData = null;
    const body = document.getElementById('productsBody');
    if (body) body.innerHTML = '';
    const warn = document.getElementById('notFoundWarning');
    if (warn) warn.classList.add('d-none');
    const list = document.getElementById('notFoundList');
    if (list) list.innerHTML = '';
    showStep(1);
}

function toggleNewSupplier() {
    const sel = document.getElementById('supplierSelect');
    document.getElementById('supplierName').style.display = sel.value ? 'none' : 'block';
}

// ========== CREATE PRODUCT ==========

let activeCreateRow = null;
let lastEditedPriceField = 'margin'; // 'margin' o 'sale'

function openCreateProductModal(tr) {
    activeCreateRow = tr;
    const nombre = tr.querySelector('[data-field="nombre"]').value.trim();
    lastEditedPriceField = 'margin';
    const precio = parseFloat(tr.querySelector('[data-field="precio_unitario"]').value) || 0;
    const barcode = tr.dataset.barcode || '';

    // Reset bÃºsqueda existente
    const searchInp = document.getElementById('cpSearchExisting');
    const searchRes = document.getElementById('cpSearchResults');
    if (searchInp) { searchInp.value = nombre; }  // precarga con el nombre detectado
    if (searchRes) { searchRes.style.display = 'none'; searchRes.innerHTML = ''; }

    document.getElementById('cpName').value = nombre;
    document.getElementById('cpBarcode').value = barcode;
    document.getElementById('cpPurchasePrice').value = precio;
    const cpErr = document.getElementById('cpError');
    if (cpErr) cpErr.classList.add('d-none');

    // Set margin from category if selected, else default 30
    const margin = parseFloat(document.getElementById('cpMargin').value) || 30;
    document.getElementById('cpMargin').value = margin;
    calcSaleFromMargin();

    const modal = new bootstrap.Modal(document.getElementById('createProductModal'));
    modal.show();

    // Auto-buscar con el nombre pre-cargado
    if (nombre.length >= 2) searchExistingProducts(nombre);
}

function calcSaleFromMargin() {
    const cost = parseFloat(document.getElementById('cpPurchasePrice').value) || 0;
    const margin = parseFloat(document.getElementById('cpMargin').value) || 0;
    const sale = cost * (1 + margin / 100);
    document.getElementById('cpSalePrice').value = sale > 0 ? sale.toFixed(2) : '0.00';
}

function calcMarginFromSale() {
    const cost = parseFloat(document.getElementById('cpPurchasePrice').value) || 0;
    const sale = parseFloat(document.getElementById('cpSalePrice').value) || 0;
    if (cost > 0 && sale > 0) {
        const margin = ((sale - cost) / cost) * 100;
        document.getElementById('cpMargin').value = margin.toFixed(2);
    }
}

// Alias de compatibilidad para llamadas existentes
function calcSalePrice() { calcSaleFromMargin(); }

// Cambio de categorÃ­a: aplica margen por defecto de categorÃ­a
document.getElementById('cpCategory').addEventListener('change', function() {
    const opt = this.options[this.selectedIndex];
    if (opt && opt.dataset.margin) {
        document.getElementById('cpMargin').value = opt.dataset.margin;
        lastEditedPriceField = 'margin';
        calcSaleFromMargin();
    }
});

// Si el usuario edita margen, recalculamos precio de venta
document.getElementById('cpMargin').addEventListener('input', function() {
    lastEditedPriceField = 'margin';
    calcSaleFromMargin();
});

// Si el usuario edita precio de venta, recalculamos margen
document.getElementById('cpSalePrice').addEventListener('input', function() {
    lastEditedPriceField = 'sale';
    calcMarginFromSale();
});

// Al cambiar costo, mantenemos la direcciÃ³n del Ãºltimo campo editado
document.getElementById('cpPurchasePrice').addEventListener('input', function() {
    if (lastEditedPriceField === 'sale') {
        calcMarginFromSale();
    } else {
        calcSaleFromMargin();
    }
});

function showModalError(msg) {
    const errorDiv = document.getElementById('cpError');
    if (errorDiv) {
        errorDiv.textContent = msg;
        errorDiv.classList.remove('d-none');
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    // TambiÃ©n toast visible para que no pase desapercibido
    const toast = document.createElement('div');
    toast.className = 'alert alert-danger position-fixed bottom-0 end-0 m-3 shadow';
    toast.style.zIndex = '99999';
    toast.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${escapeHtml(msg)}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

async function createProductFromScan() {
    const name = document.getElementById('cpName').value.trim();
    const category_id = document.getElementById('cpCategory').value || null;
    const purchase_price = parseFloat(document.getElementById('cpPurchasePrice').value) || 0;
    let sale_price = parseFloat(document.getElementById('cpSalePrice').value) || 0;
    const barcode = document.getElementById('cpBarcode').value.trim() || null;
    const errorDiv = document.getElementById('cpError');
    if (errorDiv) errorDiv.classList.add('d-none');

    if (!name) {
        showModalError('El nombre del producto es obligatorio.');
        return;
    }

    // Si sale_price es 0 pero hay precio de compra, calcular automÃ¡ticamente
    if (sale_price <= 0 && purchase_price > 0) {
        const margin = parseFloat(document.getElementById('cpMargin').value) || 30;
        sale_price = parseFloat((purchase_price * (1 + margin / 100)).toFixed(2));
        document.getElementById('cpSalePrice').value = sale_price.toFixed(2);
    }

    if (sale_price <= 0) {
        showModalError('IngresÃ¡ el precio de venta (debe ser mayor a 0).');
        return;
    }

    if (!activeCreateRow) {
        showModalError('No se pudo identificar la fila. CerrÃ¡ y abrÃ­ el modal nuevamente.');
        return;
    }

    const btn = document.getElementById('btnCreateProduct');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creando...';

    try {
        const csrfToken = getCsrfToken();
        const response = await fetch(''__DJANGO__'', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ name, category_id, purchase_price, sale_price, barcode }),
        });

        const rawText = await response.text();
        let result;
        try {
            result = JSON.parse(rawText);
        } catch {
            result = {
                success: false,
                error: response.ok
                    ? 'Respuesta invÃ¡lida del servidor al crear producto.'
                    : `Error HTTP ${response.status} al crear producto.`,
            };
        }

        if (!response.ok && !result.success) {
            errorDiv.textContent = result.error || `No se pudo crear el producto (HTTP ${response.status}).`;
            errorDiv.classList.remove('d-none');
            return;
        }

        if (result.success) {
            // Update the row with the new product
            if (activeCreateRow) {
                activeCreateRow.dataset.productId = String(result.product_id);
                const icon = activeCreateRow.querySelector('.match-icon');
                if (icon) {
                    icon.className = 'fas fa-check-circle match-found match-icon';
                    icon.title = `${result.already_existed ? 'Vinculado' : 'Creado'}: ${result.product_name}`;
                }
                const createBtn = activeCreateRow.querySelector('.btn-create-product');
                if (createBtn) createBtn.style.display = 'none';
                if (barcode) activeCreateRow.dataset.barcode = barcode;
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('createProductModal'));
            if (modal) modal.hide();

            // Brief success feedback
            const toast = document.createElement('div');
            toast.className = 'alert alert-success position-fixed bottom-0 end-0 m-3 shadow';
            toast.style.zIndex = '9999';
            toast.innerHTML = `<i class="fas fa-check me-2"></i>${escapeHtml(result.message)}`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        } else {
            errorDiv.textContent = result.error || 'Error al crear el producto.';
            errorDiv.classList.remove('d-none');
        }
    } catch (err) {
        errorDiv.textContent = 'Error de conexiÃ³n: ' + err.message;
        errorDiv.classList.remove('d-none');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check me-1"></i>Crear y Vincular';
    }
}

// ========== BUSCAR PRODUCTO EXISTENTE ==========

let _searchDebounceTimer = null;

function searchExistingProducts(query) {
    const resultsEl = document.getElementById('cpSearchResults');
    if (!resultsEl) return;
    if (!query || query.length < 2) {
        resultsEl.style.display = 'none';
        resultsEl.innerHTML = '';
        return;
    }
    fetch(`'__DJANGO__'?q=${encodeURIComponent(query)}`, {
        credentials: 'same-origin',
    })
    .then(r => r.json())
    .then(data => {
        if (data.results && data.results.length > 0) {
            resultsEl.innerHTML = data.results.map(p =>
                `<a href="#" class="list-group-item list-group-item-action py-2 px-3"
                    onclick="event.preventDefault(); linkProductToRow(${p.id}, ${JSON.stringify(p.name)})">
                    <i class="fas fa-box me-2 text-muted"></i><strong>${escapeHtml(p.name)}</strong>
                    ${p.barcode ? `<small class="text-muted ms-2"><i class="fas fa-barcode me-1"></i>${escapeHtml(p.barcode)}</small>` : ''}
                </a>`
            ).join('');
            resultsEl.style.display = 'block';
        } else {
            resultsEl.innerHTML = '<div class="list-group-item text-muted small py-2"><i class="fas fa-info-circle me-1"></i>No se encontraron productos</div>';
            resultsEl.style.display = 'block';
        }
    })
    .catch(() => { resultsEl.style.display = 'none'; });
}

// El script corre al final del body, el DOM ya estÃ¡ cargado â€” no necesita DOMContentLoaded
(function attachSearchListener() {
    const searchInput = document.getElementById('cpSearchExisting');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(_searchDebounceTimer);
            const q = this.value.trim();
            _searchDebounceTimer = setTimeout(() => searchExistingProducts(q), 300);
        });
    }
})();

function linkProductToRow(productId, productName) {
    if (!activeCreateRow) return;
    activeCreateRow.dataset.productId = String(productId);
    const icon = activeCreateRow.querySelector('.match-icon');
    if (icon) {
        icon.className = 'fas fa-check-circle match-found match-icon';
        icon.title = `Vinculado: ${productName}`;
    }
    const createBtn = activeCreateRow.querySelector('.btn-create-product');
    if (createBtn) createBtn.style.display = 'none';

    const modal = bootstrap.Modal.getInstance(document.getElementById('createProductModal'));
    if (modal) modal.hide();

    const toast = document.createElement('div');
    toast.className = 'alert alert-success position-fixed bottom-0 end-0 m-3 shadow';
    toast.style.zIndex = '9999';
    toast.innerHTML = `<i class="fas fa-link me-2"></i>Vinculado a: <strong>${escapeHtml(productName)}</strong>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ========== HELPERS ==========

function getCsrfToken() {
    const tokenFromTemplate = ''__DJANGO_VAR__'';
    if (tokenFromTemplate && tokenFromTemplate !== 'NOTPROVIDED') {
        return tokenFromTemplate;
    }

    const cookie = document.cookie
        .split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='));

    return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
}

function fmtMoney(v) {
    const parts = v.toFixed(2).split('.');
    const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return '$' + intPart + ',' + parts[1];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Init
showStep(1);

