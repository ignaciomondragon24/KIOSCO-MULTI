/**
 * CHE GOLOSO - Sign Renderer
 * Renders sign templates with product data and text auto-scaling.
 * Used by: designer preview, generate preview, print preview.
 */

class SignRenderer {
    constructor(options = {}) {
        this.pxPerMM = options.pxPerMM || 3.78; // 96dpi
    }

    /**
     * Render a sign into a container element.
     * @param {HTMLElement} container - Target container
     * @param {Object} layout - Template layout JSON
     * @param {Object} data - Variable data (key→value)
     * @param {number} widthMM - Sign width in mm
     * @param {number} heightMM - Sign height in mm
     * @param {number} scale - Display scale factor (1 = actual size at screen DPI)
     */
    render(container, layout, data, widthMM, heightMM, scale = 1) {
        const px = this.pxPerMM * scale;
        const signEl = document.createElement('div');
        signEl.style.position = 'relative';
        signEl.style.width = (widthMM * px) + 'px';
        signEl.style.height = (heightMM * px) + 'px';
        signEl.style.background = layout.background_color || '#FFFFFF';
        signEl.style.overflow = 'hidden';
        signEl.style.fontFamily = 'Arial, sans-serif';

        if (layout.border_width && layout.border_width > 0) {
            signEl.style.border = (layout.border_width * px) + 'px solid ' + (layout.border_color || '#333');
        }

        const elements = layout.elements || [];
        // Sort by zIndex
        const sorted = [...elements].sort((a, b) => (a.zIndex || 0) - (b.zIndex || 0));

        sorted.forEach(el => {
            const div = document.createElement('div');
            div.style.position = 'absolute';
            div.style.left = (el.x * px) + 'px';
            div.style.top = (el.y * px) + 'px';
            div.style.width = (el.width * px) + 'px';
            div.style.height = (el.height * px) + 'px';
            div.style.overflow = 'hidden';
            div.style.boxSizing = 'border-box';

            if (el.type === 'text' || el.type === 'variable') {
                this._renderTextElement(div, el, data, px, scale);
            } else if (el.type === 'shape') {
                this._renderShapeElement(div, el, px);
            } else if (el.type === 'line') {
                this._renderLineElement(div, el, px);
            } else if (el.type === 'image') {
                this._renderImageElement(div, el, px);
            }

            signEl.appendChild(div);
        });

        container.appendChild(signEl);
        // Auto-scale text after DOM insertion
        this._applyAutoScale(signEl, scale);
    }

    _renderTextElement(div, el, data, px, scale) {
        let text = '';
        if (el.type === 'variable') {
            text = data[el.variable] || '';
        } else {
            text = el.content || '';
        }

        div.style.display = 'flex';
        div.style.alignItems = el.verticalAlign === 'top' ? 'flex-start' :
                               el.verticalAlign === 'bottom' ? 'flex-end' : 'center';
        div.style.justifyContent = el.textAlign === 'left' ? 'flex-start' :
                                   el.textAlign === 'right' ? 'flex-end' : 'center';

        if (el.backgroundColor && el.backgroundColor !== 'transparent') {
            div.style.backgroundColor = el.backgroundColor;
        }

        const span = document.createElement('span');
        span.style.display = 'block';
        span.style.width = '100%';
        span.style.fontFamily = el.fontFamily || 'Arial';
        span.style.fontWeight = el.fontWeight || 'normal';
        span.style.fontStyle = el.fontStyle || 'normal';
        span.style.textDecoration = el.textDecoration || 'none';
        span.style.color = el.color || '#000000';
        span.style.textAlign = el.textAlign || 'center';
        span.style.lineHeight = '1.15';
        span.style.wordBreak = 'break-word';
        span.textContent = text;

        const fontSize = (el.fontSize || 14) * scale;
        span.style.fontSize = fontSize + 'pt';

        if (el.autoScale) {
            span.dataset.autoScale = '1';
            span.dataset.maxFontSize = String(el.fontSize || 14);
            span.dataset.minFontSize = String(el.minFontSize || 6);
            span.dataset.scale = String(scale);
        }

        div.appendChild(span);
    }

    _renderShapeElement(div, el, px) {
        div.style.backgroundColor = el.backgroundColor || '#E91E8C';
        if (el.borderWidth && el.borderWidth > 0) {
            div.style.border = (el.borderWidth * px) + 'px solid ' + (el.borderColor || '#000');
        }
        if (el.borderRadius) {
            div.style.borderRadius = (el.borderRadius * px) + 'px';
        }
        if (el.opacity !== undefined && el.opacity !== 1) {
            div.style.opacity = el.opacity;
        }
    }

    _renderImageElement(div, el, px) {
        const img = document.createElement('img');
        img.src = el.src || '';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        div.appendChild(img);
    }

    _renderLineElement(div, el, px) {
        div.style.backgroundColor = 'transparent';
        const lineW = (el.lineWidth || 1) * px;
        div.style.borderTop = lineW + 'px ' + (el.lineStyle || 'solid') + ' ' + (el.lineColor || '#000');
        div.style.height = lineW + 'px';
    }

    /**
     * Apply auto-scaling to all marked text spans after DOM insertion.
     * Uses binary search for speed, then fine-tunes. Checks both axes.
     */
    _applyAutoScale(container, scale) {
        container.querySelectorAll('[data-auto-scale="1"]').forEach(span => {
            const maxSize = parseFloat(span.dataset.maxFontSize) * scale;
            const minSize = parseFloat(span.dataset.minFontSize) * scale;
            const parent = span.parentElement;
            const containerW = parent.clientWidth;
            const containerH = parent.clientHeight;

            if (!span.textContent.trim() || containerW <= 0) return;

            // Helper: does text fit at given pt size?
            const fits = (sz) => {
                span.style.fontSize = sz + 'pt';
                return span.scrollWidth <= containerW + 1 && span.scrollHeight <= containerH + 1;
            };

            // Quick check: if max fits, done
            if (fits(maxSize)) return;

            // Binary search down to ~0.5pt precision
            let lo = minSize, hi = maxSize;
            while (hi - lo > 0.5) {
                const mid = (lo + hi) / 2;
                if (fits(mid)) { lo = mid; } else { hi = mid; }
            }
            // Fine-tune: step down from lo in 0.25pt steps
            let size = lo;
            while (size > minSize && !fits(size)) {
                size -= 0.25;
            }
            span.style.fontSize = Math.max(size, minSize) + 'pt';
        });
    }

    /**
     * Get sample data for a sign type (for previews).
     */
    getSampleData(signType) {
        const SAMPLES = {
            simple: {
                nombre_producto: 'GALLETAS DE ARROZ GALLO',
                gramaje: '120g',
                precio_unitario: '$1.290',
            },
            promo: {
                nombre_producto: 'TURRON MISKY',
                precio_unitario: '$180',
                cantidad_promo: '3',
                precio_promo: '$500',
                etiqueta_promo: 'PROMO!!',
            },
            bulk: {
                nombre_producto: 'CARAMELOS ARCOR SURTIDOS',
                precio_total: '$11.500',
                tipo_empaque: 'CAJA',
                contenido_empaque: 'X 30U.',
            },
            weight: {
                nombre_producto: 'ALMENDRAS PELADAS PREMIUM',
                precio_100g: '$3.200',
                precio_250g: '$7.350',
                precio_1kg: '$29.400',
            },
        };
        return SAMPLES[signType] || SAMPLES.simple;
    }

    /**
     * Format a number as Argentine currency.
     */
    static formatCurrency(value) {
        const num = parseFloat(value);
        if (isNaN(num)) return value;
        const intPart = Math.round(num);
        return '$' + intPart.toLocaleString('es-AR');
    }
}

// Export
if (typeof window !== 'undefined') {
    window.SignRenderer = SignRenderer;
}
