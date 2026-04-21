/**
 * CHE GOLOSO - Print Nesting Manager
 * Optimizes placement of multiple signs on a single paper sheet.
 */

class SignPrintManager {
    constructor(config) {
        this.signWidthMM = config.signWidthMM;
        this.signHeightMM = config.signHeightMM;
        this.layout = config.layout;
        this.items = config.items || [];
        this.paperSize = config.paperSize || 'A4';
        this.margin = config.margin || 5;
        this.gap = config.gap || 2;
    }

    static PAPER_SIZES = {
        A4: { width: 210, height: 297 },
        A3: { width: 297, height: 420 },
        letter: { width: 216, height: 279 },
    };

    /**
     * Calculate how many signs fit on one page.
     */
    calculateGrid() {
        const paper = SignPrintManager.PAPER_SIZES[this.paperSize] || SignPrintManager.PAPER_SIZES.A4;
        const pw = paper.width - 2 * this.margin;
        const ph = paper.height - 2 * this.margin;
        const sw = this.signWidthMM;
        const sh = this.signHeightMM;
        const gap = this.gap;

        const cols = Math.floor((pw + gap) / (sw + gap));
        const rows = Math.floor((ph + gap) / (sh + gap));
        return { cols, rows, total: cols * rows };
    }

    /**
     * Generate all pages as arrays of items.
     */
    generatePages() {
        const grid = this.calculateGrid();
        if (grid.total === 0) return [];

        // Expand items by copies
        const expanded = [];
        this.items.forEach(item => {
            const copies = Math.max(1, item.copies || 1);
            for (let i = 0; i < copies; i++) {
                expanded.push(item.data);
            }
        });

        const pages = [];
        for (let i = 0; i < expanded.length; i += grid.total) {
            pages.push(expanded.slice(i, i + grid.total));
        }
        return pages;
    }

    /**
     * Open print window with all pages rendered.
     * Stores data in localStorage and opens print_preview.html
     */
    openPrintWindow(printUrl) {
        const printData = {
            layout: this.layout,
            items: this.items,
            widthMM: this.signWidthMM,
            heightMM: this.signHeightMM,
            paperSize: this.paperSize,
            margin: this.margin,
            gap: this.gap,
        };

        localStorage.setItem('signagePrintData', JSON.stringify(printData));
        window.open(printUrl, '_blank');
    }
}
