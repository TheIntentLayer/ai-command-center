#!/usr/bin/env python3
"""
md_to_pdf.py - Convert markdown files to high-quality PDFs.

Renders Mermaid diagrams as images via Playwright + Mermaid JS.
Uses weasyprint with Google Fonts (Inter) for clean, readable output.

Usage:
    python3 system/scripts/md_to_pdf.py <input.md> [output.pdf]
    
    If output.pdf is omitted, writes to same directory as input with .pdf extension.

Dependencies (install once):
    pip install weasyprint markdown playwright --break-system-packages
    python3 -m playwright install chromium

Examples:
    python3 system/scripts/md_to_pdf.py workstream-1/document.md
    python3 system/scripts/md_to_pdf.py workstream-1/report.md workstream-1/report.pdf
"""

import re
import sys
import os
import base64
import tempfile
import markdown
from pathlib import Path

def render_mermaid_diagrams(md_text, output_dir):
    """Extract mermaid blocks, render as PNGs via mermaid.ink API, return modified markdown."""
    import urllib.request
    
    mermaid_pattern = re.compile(r'```mermaid\n(.*?)```', re.DOTALL)
    matches = list(mermaid_pattern.finditer(md_text))
    
    if not matches:
        return md_text, []
    
    print(f"  Found {len(matches)} Mermaid diagram(s). Rendering via mermaid.ink...")
    
    image_paths = []
    result = md_text
    
    for i, match in enumerate(reversed(matches)):  # reverse to preserve offsets
        diagram_code = match.group(1).strip()
        img_filename = f"mermaid-{len(matches) - 1 - i}.png"
        img_path = os.path.join(output_dir, img_filename)
        
        try:
            # Base64 encode the diagram for the mermaid.ink API
            encoded = base64.urlsafe_b64encode(diagram_code.encode('utf-8')).decode('utf-8')
            url = f"https://mermaid.ink/img/{encoded}?type=png&bgColor=white"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            
            with open(img_path, 'wb') as f:
                f.write(resp.read())
            
            # Verify it's actually an image
            with open(img_path, 'rb') as f:
                header = f.read(4)
            
            if header[:4] == b'\x89PNG':
                print(f"    Diagram {len(matches) - i}/{len(matches)} rendered: {img_filename}")
                image_paths.append(img_path)
                
                abs_path = os.path.abspath(img_path)
                img_tag = f'<div class="diagram-rendered"><img src="file://{abs_path}" alt="Diagram" /></div>'
                result = result[:match.start()] + img_tag + result[match.end():]
            else:
                print(f"    Diagram {len(matches) - i}/{len(matches)} FAILED: not a valid PNG")
                
        except Exception as e:
            print(f"    Diagram {len(matches) - i}/{len(matches)} FAILED: {e}")
    
    return result, image_paths


def md_to_pdf(input_path, output_path=None):
    """Convert a markdown file to a high-quality PDF."""
    
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)
    
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".pdf"
    output_path = os.path.abspath(output_path)
    
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    
    # Read markdown
    with open(input_path, "r") as f:
        md_content = f.read()
    
    # Render mermaid diagrams
    with tempfile.TemporaryDirectory() as tmpdir:
        md_content, image_paths = render_mermaid_diagrams(md_content, tmpdir)
        
        # Convert markdown to HTML
        html_body = markdown.markdown(
            md_content,
            extensions=['extra', 'smarty', 'toc'],
            output_format='html5'
        )
        
        # Get document title from first H1
        title_match = re.search(r'<h1>(.*?)</h1>', html_body)
        doc_title = title_match.group(1) if title_match else "Document"
        
        # Full HTML with styling
        html_full = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{doc_title}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

@page {{
    size: letter;
    margin: 0.9in 0.9in 1.1in 0.9in;
    @bottom-center {{
        content: counter(page);
        font-family: 'Inter', sans-serif;
        font-size: 8.5pt;
        color: #999;
    }}
}}

body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #111;
    max-width: 100%;
    -webkit-font-smoothing: antialiased;
}}

/* === HEADINGS === */

h1 {{
    font-size: 24pt;
    font-weight: 900;
    color: #0a0a0a;
    margin-top: 0;
    margin-bottom: 6pt;
    line-height: 1.15;
    border-bottom: 3px solid #e94560;
    padding-bottom: 10pt;
}}

h2 {{
    font-size: 15pt;
    font-weight: 700;
    color: #0a0a0a;
    margin-top: 26pt;
    margin-bottom: 8pt;
    border-bottom: 1px solid #ddd;
    padding-bottom: 5pt;
    page-break-after: avoid;
}}

h3 {{
    font-size: 12pt;
    font-weight: 600;
    color: #1a1a1a;
    margin-top: 18pt;
    margin-bottom: 6pt;
    page-break-after: avoid;
}}

/* === BODY TEXT === */

p {{
    margin-bottom: 9pt;
    color: #111;
    orphans: 3;
    widows: 3;
}}

strong {{
    color: #0a0a0a;
    font-weight: 700;
}}

em {{
    font-style: italic;
}}

/* === STRUCTURE === */

hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 22pt 0;
}}

blockquote {{
    border-left: 3px solid #e94560;
    margin: 14pt 0;
    padding: 8pt 14pt;
    background: #fdf2f4;
    color: #222;
    font-style: italic;
    font-size: 10pt;
}}

blockquote p {{
    margin-bottom: 4pt;
    color: #222;
}}

ul, ol {{
    margin-bottom: 9pt;
    padding-left: 22pt;
    color: #111;
}}

li {{
    margin-bottom: 4pt;
    color: #111;
}}

/* === DIAGRAMS === */

.diagram-rendered {{
    text-align: center;
    margin: 16pt 0;
    page-break-inside: avoid;
}}

.diagram-rendered img {{
    max-width: 100%;
    height: auto;
}}

/* Fallback for text-based diagram boxes */
.diagram-box {{
    background: #f0f4f8;
    border: 1.5px solid #0f3460;
    border-radius: 5px;
    padding: 12pt 16pt;
    margin: 14pt 0;
    page-break-inside: avoid;
}}

.diagram-box .diagram-title {{
    font-size: 10.5pt;
    font-weight: 700;
    color: #0f3460;
    margin-bottom: 6pt;
}}

.diagram-box p {{
    font-size: 9.5pt;
    line-height: 1.5;
    margin-bottom: 3pt;
    color: #222;
}}

/* === CODE === */

code {{
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
    font-size: 9pt;
    background: #f5f5f5;
    padding: 1.5pt 4pt;
    border-radius: 3px;
    color: #111;
}}

pre {{
    background: #f5f5f5;
    padding: 10pt;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 8.5pt;
    line-height: 1.4;
    color: #111;
    border: 1px solid #e0e0e0;
    page-break-inside: avoid;
}}

pre code {{
    background: none;
    padding: 0;
}}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
        
        # Generate PDF
        from weasyprint import HTML
        HTML(string=html_full).write_pdf(output_path)
    
    # Report
    try:
        from pypdf import PdfReader
        reader = PdfReader(output_path)
        page_count = len(reader.pages)
    except ImportError:
        page_count = "unknown"
    
    file_size = os.path.getsize(output_path)
    size_mb = file_size / (1024 * 1024)
    
    print(f"\nDone.")
    print(f"  Pages: {page_count}")
    print(f"  Size:  {size_mb:.1f} MB")
    print(f"  File:  {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_pdf.py <input.md> [output.pdf]")
        print("  If output.pdf is omitted, writes to same directory with .pdf extension.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    md_to_pdf(input_file, output_file)
