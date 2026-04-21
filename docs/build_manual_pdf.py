"""
Genera docs/Manual-CHE-GOLOSO.pdf a partir de los .md en docs/manual/.
Uso: python docs/build_manual_pdf.py
"""
import os
import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent
MANUAL_DIR = ROOT / 'manual'
OUT_PDF = ROOT / 'Manual-CHE-GOLOSO.pdf'

ORDER = [
    '00-Indice.md',
    '01-Crear-y-modificar-productos.md',
    '02-Compras-y-recepcion.md',
    '03-Vender-por-el-POS.md',
    '04-Caramelera.md',
    '05-Ajustes-de-stock.md',
    '06-Cierre-de-caja.md',
    '07-Reportes.md',
]

CSS = """
@page {
    size: A4;
    margin: 2.2cm 2cm 2cm 2cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        left: 2cm; right: 2cm;
        bottom: 1cm; height: 0.7cm;
    }
}
body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    color: #1a1a2e;
    line-height: 1.5;
}
.cover {
    text-align: center;
    padding-top: 6cm;
}
.cover h1 {
    font-size: 42pt;
    color: #E91E8C;
    margin: 0 0 10pt 0;
    border: 0;
}
.cover .sub {
    font-size: 16pt;
    color: #2D1E5F;
    margin-bottom: 30pt;
}
.cover .meta {
    font-size: 11pt;
    color: #666;
    margin-top: 2cm;
}
h1 {
    color: #E91E8C;
    font-size: 22pt;
    border-bottom: 2pt solid #E91E8C;
    padding-bottom: 4pt;
    margin-top: 0;
    -pdf-keep-with-next: true;
}
h2 {
    color: #2D1E5F;
    font-size: 15pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
    -pdf-keep-with-next: true;
}
h3 {
    color: #2D1E5F;
    font-size: 12pt;
    margin-top: 12pt;
    margin-bottom: 4pt;
    -pdf-keep-with-next: true;
}
p { margin: 4pt 0 8pt 0; }
ul, ol { margin: 4pt 0 10pt 16pt; }
li { margin-bottom: 3pt; }
strong { color: #2D1E5F; }
code {
    font-family: Courier, monospace;
    background: #f4f4f8;
    padding: 1pt 4pt;
    border-radius: 2pt;
    font-size: 10pt;
    color: #c7296b;
}
pre {
    background: #f4f4f8;
    border-left: 3pt solid #E91E8C;
    padding: 8pt 10pt;
    font-family: Courier, monospace;
    font-size: 9.5pt;
    color: #2D1E5F;
    margin: 8pt 0;
    white-space: pre-wrap;
}
hr {
    border: 0;
    border-top: 1pt solid #ddd;
    margin: 14pt 0;
}
a { color: #E91E8C; text-decoration: none; }
.page-break { page-break-before: always; }
.footer {
    text-align: center;
    font-size: 8pt;
    color: #999;
}
.tag-regla {
    background: #fff3e0;
    border-left: 3pt solid #F5D000;
    padding: 6pt 10pt;
    margin: 6pt 0;
    font-size: 10pt;
}
"""


def md_to_html_body(md_text: str) -> str:
    # Bajar todos los headings un nivel para que h1 sea único por sección.
    html = markdown.markdown(
        md_text,
        extensions=['extra', 'sane_lists'],
    )
    return html


def fix_internal_links(html: str) -> str:
    # Los links entre .md no sirven en PDF; los convertimos a texto plano
    # "(ver sección X)" — más útil que un link roto.
    return re.sub(
        r'<a href="(\d+)-[^"]*\.md"[^>]*>([^<]+)</a>',
        r'<strong>\2</strong>',
        html,
    )


def build_html() -> str:
    sections_html = []

    # Portada
    sections_html.append("""
    <div class="cover">
        <h1>CHE GOLOSO</h1>
        <div class="sub">Manual de uso del sistema</div>
        <div class="meta">Guía práctica para el equipo del kiosco<br/>Versión Abril 2026</div>
    </div>
    <div class="page-break"></div>
    """)

    for idx, filename in enumerate(ORDER):
        path = MANUAL_DIR / filename
        md_text = path.read_text(encoding='utf-8')
        html = md_to_html_body(md_text)
        html = fix_internal_links(html)
        sections_html.append(html)
        # Salto de página entre secciones (no después de la última)
        if idx < len(ORDER) - 1:
            sections_html.append('<div class="page-break"></div>')

    body = '\n'.join(sections_html)
    footer = '<div id="footerContent" class="footer">Manual CHE GOLOSO · página <pdf:pagenumber/></div>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>{CSS}</style>
</head>
<body>
    {footer}
    {body}
</body>
</html>
"""


def main() -> int:
    html = build_html()
    with OUT_PDF.open('wb') as f:
        result = pisa.CreatePDF(src=html, dest=f, encoding='utf-8')
    if result.err:
        print(f'ERROR al generar PDF: {result.err}')
        return 1
    print(f'OK PDF generado: {OUT_PDF}')
    print(f'    Tamaño: {OUT_PDF.stat().st_size / 1024:.1f} KB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
