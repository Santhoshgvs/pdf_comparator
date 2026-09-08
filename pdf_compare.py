"""
PDF Comparison Automation Tool
================================
Compares two PDFs for:
  1. Data/Text differences
  2. Spelling mistakes
  3. Punctuation differences

Generates:
Interactive HTML report
Excel report
Highlighted PDFs
Automated screenshots
Side-by-side comparison images

Author: PDF Comparison Tool
License: Free for all use
"""

import fitz  # PyMuPDF
import difflib
import os
import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple
@dataclass
class ComparisonConfig:
    """Stores all configuration for the comparison."""
    pdf_a_path: str = ""
    pdf_b_path: str = ""
    output_dir: str = "comparison_output"
    generate_screenshots: bool = True
    generate_html_report: bool = True
    generate_pdf_report: bool = True


@dataclass
class Difference:
    """Represents a single difference found between PDFs."""
    page: int
    diff_type: str          # 'added', 'removed', 'changed', 'spelling', 'punctuation'
    text_a: str = ""
    text_b: str = ""
    line_number: int = 0
    position: tuple = ()
    description: str = ""


class PDFTextExtractor:
    """Extracts text from PDF files with position information."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def extract_text_by_page(self) -> dict:
        """Extract text from each page."""
        pages = {}
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            pages[page_num + 1] = {
                "text": page.get_text("text"),
                "words": page.get_text("words"),
            }
        return pages

    def get_page_count(self) -> int:
        """Get total number of pages."""
        return len(self.doc)

    def close(self):
        """Close the PDF document."""
        self.doc.close()


class PDFComparator:
    """Compares two PDFs and finds all differences."""

    def __init__(self, config: ComparisonConfig):
        self.config = config
        self.differences: List[Difference] = []

        # Initialize spell checker
        try:
            from spellchecker import SpellChecker
            self.spell = SpellChecker()
        except ImportError:
            print("⚠️  pyspellchecker not installed. Spelling checks disabled.")
            self.spell = None

    def compare(self) -> List[Difference]:
        """Main comparison method - runs all checks."""
        extractor_a = PDFTextExtractor(self.config.pdf_a_path)
        extractor_b = PDFTextExtractor(self.config.pdf_b_path)

        pages_a = extractor_a.extract_text_by_page()
        pages_b = extractor_b.extract_text_by_page()

        max_pages = max(extractor_a.get_page_count(), extractor_b.get_page_count())

        print(f"   PDF A: {extractor_a.get_page_count()} pages")
        print(f"   PDF B: {extractor_b.get_page_count()} pages")

        for page_num in range(1, max_pages + 1):
            text_a = pages_a.get(page_num, {}).get("text", "")
            text_b = pages_b.get(page_num, {}).get("text", "")

            # 1. Text/data differences
            self._find_text_differences(page_num, text_a, text_b)

            # 2. Spelling differences
            if self.spell:
                self._find_spelling_differences(page_num, text_a, text_b)

            # 3. Punctuation differences
            self._find_punctuation_differences(page_num, text_a, text_b)

        extractor_a.close()
        extractor_b.close()

        return self.differences

    def _find_text_differences(self, page: int, text_a: str, text_b: str):
        """Find line-by-line text differences."""
        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)

        for op, a_start, a_end, b_start, b_end in matcher.get_opcodes():
            if op == 'equal':
                continue
            elif op == 'replace':
                for i, j in zip(range(a_start, a_end), range(b_start, b_end)):
                    self.differences.append(Difference(
                        page=page,
                        diff_type='changed',
                        text_a=lines_a[i] if i < len(lines_a) else "",
                        text_b=lines_b[j] if j < len(lines_b) else "",
                        line_number=i + 1,
                        description=f"Text changed on line {i + 1}"
                    ))
            elif op == 'delete':
                for i in range(a_start, a_end):
                    self.differences.append(Difference(
                        page=page,
                        diff_type='removed',
                        text_a=lines_a[i],
                        text_b="",
                        line_number=i + 1,
                        description=f"Text removed from line {i + 1}"
                    ))
            elif op == 'insert':
                for j in range(b_start, b_end):
                    self.differences.append(Difference(
                        page=page,
                        diff_type='added',
                        text_a="",
                        text_b=lines_b[j],
                        line_number=b_start + 1,
                        description=f"Text added at line {b_start + 1}"
                    ))

    def _find_spelling_differences(self, page: int, text_a: str, text_b: str):
        """Find words that differ due to spelling."""
        words_a = set(re.findall(r'[a-zA-Z]+', text_a))
        words_b = set(re.findall(r'[a-zA-Z]+', text_b))

        only_in_a = words_a - words_b
        only_in_b = words_b - words_a

        misspelled_a = self.spell.unknown(only_in_a)

        for word in misspelled_a:
            candidates = self.spell.candidates(word)
            matching = candidates & words_b if candidates else set()
            self.differences.append(Difference(
                page=page,
                diff_type='spelling',
                text_a=word,
                text_b=", ".join(matching) if matching else "(no match in PDF B)",
                description=f"Possible spelling error in PDF A: '{word}'"
                            + (f" -> corrected to '{', '.join(matching)}' in PDF B" if matching else "")
            ))

        misspelled_b = self.spell.unknown(only_in_b)
        for word in misspelled_b:
            if word not in [d.text_b for d in self.differences if d.diff_type == 'spelling']:
                candidates = self.spell.candidates(word)
                matching = candidates & words_a if candidates else set()
                self.differences.append(Difference(
                    page=page,
                    diff_type='spelling',
                    text_a=", ".join(matching) if matching else "(no match in PDF A)",
                    text_b=word,
                    description=f"Possible spelling error in PDF B: '{word}'"
                ))

    def _find_punctuation_differences(self, page: int, text_a: str, text_b: str):
        """Find punctuation-only differences."""
        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()

        for i, (la, lb) in enumerate(zip(lines_a, lines_b)):
            alpha_a = re.sub(r'[^a-zA-Z0-9\s]', '', la)
            alpha_b = re.sub(r'[^a-zA-Z0-9\s]', '', lb)

            if alpha_a == alpha_b and la != lb:
                punct_a = re.sub(r'[a-zA-Z0-9\s]', '', la)
                punct_b = re.sub(r'[a-zA-Z0-9\s]', '', lb)
                self.differences.append(Difference(
                    page=page,
                    diff_type='punctuation',
                    text_a=la,
                    text_b=lb,
                    line_number=i + 1,
                    description=f"Punctuation difference on line {i + 1}: '{punct_a}' vs '{punct_b}'"
                ))


class PDFHighlighter:
    """Highlights differences directly on PDF pages and saves screenshots."""

    COLOR_MAP = {
        'added': (0.56, 0.93, 0.56),
        'removed': (1.0, 0.71, 0.76),
        'changed': (1.0, 1.0, 0.6),
        'spelling': (1.0, 0.65, 0.0),
        'punctuation': (0.87, 0.63, 0.87),
    }

    def __init__(self, config: ComparisonConfig, differences: List[Difference]):
        self.config = config
        self.differences = differences

    def highlight_and_save(self):
        """Create highlighted copies of both PDFs."""
        os.makedirs(self.config.output_dir, exist_ok=True)

        doc_a = fitz.open(self.config.pdf_a_path)
        doc_b = fitz.open(self.config.pdf_b_path)

        for diff in self.differences:
            page_idx = diff.page - 1

            if diff.text_a and page_idx < len(doc_a):
                self._highlight_text_on_page(doc_a[page_idx], diff.text_a, diff.diff_type)

            if diff.text_b and page_idx < len(doc_b):
                self._highlight_text_on_page(doc_b[page_idx], diff.text_b, diff.diff_type)

        highlighted_a = os.path.join(self.config.output_dir, "highlighted_PDF_A.pdf")
        highlighted_b = os.path.join(self.config.output_dir, "highlighted_PDF_B.pdf")
        doc_a.save(highlighted_a)
        doc_b.save(highlighted_b)

        if self.config.generate_screenshots:
            self._save_page_screenshots(doc_a, "PDF_A")
            self._save_page_screenshots(doc_b, "PDF_B")

        doc_a.close()
        doc_b.close()

        print(f"   ✅ Highlighted PDFs saved")

    def _highlight_text_on_page(self, page, text: str, diff_type: str):
        """Search and highlight text on a page."""
        color = self.COLOR_MAP.get(diff_type, (1, 1, 0))
        text_to_search = text.strip()[:60]

        if not text_to_search:
            return

        areas = page.search_for(text_to_search)
        for rect in areas:
            highlight = page.add_highlight_annot(rect)
            highlight.set_colors(stroke=color)
            highlight.update()

    def _save_page_screenshots(self, doc, prefix: str):
        """Save each page as a PNG screenshot."""
        screenshots_dir = os.path.join(self.config.output_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            output_path = os.path.join(screenshots_dir, f"{prefix}_page_{page_num + 1}.png")
            pix.save(output_path)

        print(f"   📸 Screenshots saved for {prefix}")


class ReportGenerator:
    """Generates a comprehensive HTML comparison report."""

    def __init__(self, config: ComparisonConfig, differences: List[Difference]):
        self.config = config
        self.differences = differences

    def generate_html_report(self) -> str:
        """Create a detailed HTML report."""
        os.makedirs(self.config.output_dir, exist_ok=True)

        counts = self._count_by_type()
        total = len(self.differences)

        # Build the HTML
        html = self._build_html_header()
        html += self._build_summary_cards(counts, total)
        html += self._build_legend()
        html += self._build_filter_bar()
        html += self._build_differences_table()
        html += self._build_screenshot_section()
        html += self._build_javascript()
        html += "</body></html>"

        report_path = os.path.join(self.config.output_dir, "comparison_report.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"   📊 HTML Report saved")
        return report_path

    def _build_html_header(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PDF Comparison Report</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
.header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.summary {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
.summary-card {{ background: white; padding: 15px 25px; border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; min-width: 140px; }}
.summary-card h3 {{ margin: 0; font-size: 2em; }}
.summary-card p {{ margin: 5px 0 0; color: #666; }}
.card-added {{ border-left: 4px solid #90EE90; }}
.card-removed {{ border-left: 4px solid #FFB6C1; }}
.card-changed {{ border-left: 4px solid #FFFF99; }}
.card-spelling {{ border-left: 4px solid #FFA500; }}
.card-punctuation {{ border-left: 4px solid #DDA0DD; }}
.card-total {{ border-left: 4px solid #2c3e50; }}
table {{ width: 100%; border-collapse: collapse; background: white;
    border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
th {{ background: #34495e; color: white; padding: 12px 15px; text-align: left; }}
td {{ padding: 10px 15px; border-bottom: 1px solid #eee; vertical-align: top; }}
tr:hover {{ background: #f8f9fa; }}
.badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold; display: inline-block; }}
.badge-added {{ background: #90EE90; color: #155724; }}
.badge-removed {{ background: #FFB6C1; color: #721c24; }}
.badge-changed {{ background: #FFFF99; color: #856404; }}
.badge-spelling {{ background: #FFA500; color: #fff; }}
.badge-punctuation {{ background: #DDA0DD; color: #4a0e4e; }}
.text-diff {{ font-family: Consolas, monospace; font-size: 0.9em; background: #f8f9fa;
    padding: 5px 8px; border-radius: 4px; display: block; margin: 2px 0;
    white-space: pre-wrap; word-break: break-all; }}
.text-removed {{ background: #ffe0e0; text-decoration: line-through; color: #c0392b; }}
.text-added {{ background: #e0ffe0; color: #27ae60; }}
.filter-bar {{ margin-bottom: 15px; padding: 10px; background: white;
    border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.filter-bar label {{ margin-right: 15px; cursor: pointer; }}
.legend {{ display: flex; gap: 15px; margin: 15px 0; flex-wrap: wrap; }}
.legend-item {{ display: flex; align-items: center; gap: 5px; }}
.legend-color {{ width: 20px; height: 20px; border-radius: 4px; }}
.screenshot-section {{ margin-top: 30px; }}
.screenshot-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
.screenshot-card {{ background: white; padding: 10px; border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.screenshot-card img {{ width: 100%; border: 1px solid #ddd; }}
.screenshot-card h4 {{ margin: 0 0 10px; color: #2c3e50; }}
@media print {{ .filter-bar {{ display: none; }} body {{ background: white; }} }}
</style>
</head>
<body>
<div class="header">
<h1>PDF Comparison Report</h1>
<p><strong>PDF A:</strong> {os.path.basename(self.config.pdf_a_path)}</p>
<p><strong>PDF B:</strong> {os.path.basename(self.config.pdf_b_path)}</p>
<p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
"""

    def _build_summary_cards(self, counts: dict, total: int) -> str:
        return f"""
<div class="summary">
<div class="summary-card card-total"><h3>{total}</h3><p>Total Differences</p></div>
<div class="summary-card card-changed"><h3>{counts.get('changed', 0)}</h3><p>Text Changes</p></div>
<div class="summary-card card-added"><h3>{counts.get('added', 0)}</h3><p>Additions</p></div>
<div class="summary-card card-removed"><h3>{counts.get('removed', 0)}</h3><p>Removals</p></div>
<div class="summary-card card-spelling"><h3>{counts.get('spelling', 0)}</h3><p>Spelling Issues</p></div>
<div class="summary-card card-punctuation"><h3>{counts.get('punctuation', 0)}</h3><p>Punctuation Diffs</p></div>
</div>
"""

    def _build_legend(self) -> str:
        return """
<div class="legend">
<div class="legend-item"><div class="legend-color" style="background:#FFFF99"></div> Changed</div>
<div class="legend-item"><div class="legend-color" style="background:#90EE90"></div> Added</div>
<div class="legend-item"><div class="legend-color" style="background:#FFB6C1"></div> Removed</div>
<div class="legend-item"><div class="legend-color" style="background:#FFA500"></div> Spelling</div>
<div class="legend-item"><div class="legend-color" style="background:#DDA0DD"></div> Punctuation</div>
</div>
"""

    def _build_filter_bar(self) -> str:
        return """
<div class="filter-bar">
<strong>Filter: </strong>
<label><input type="checkbox" checked onchange="filterRows('added', this.checked)"> Additions</label>
<label><input type="checkbox" checked onchange="filterRows('removed', this.checked)"> Removals</label>
<label><input type="checkbox" checked onchange="filterRows('changed', this.checked)"> Changes</label>
<label><input type="checkbox" checked onchange="filterRows('spelling', this.checked)"> Spelling</label>
<label><input type="checkbox" checked onchange="filterRows('punctuation', this.checked)"> Punctuation</label>
</div>
"""

    def _build_differences_table(self) -> str:
        html = """
<table id="diffTable">
<thead><tr>
<th>#</th><th>Page</th><th>Line</th><th>Type</th>
<th>PDF A (Source)</th><th>PDF B (Target)</th><th>Description</th>
</tr></thead><tbody>
"""
        for idx, diff in enumerate(self.differences, 1):
            badge_class = f"badge-{diff.diff_type}"
            text_a_class = "text-removed" if diff.diff_type == 'removed' else ""
            text_b_class = "text-added" if diff.diff_type == 'added' else ""

            if diff.diff_type == 'changed' and diff.text_a and diff.text_b:
                text_a_display = self._inline_diff(diff.text_a, diff.text_b, 'a')
                text_b_display = self._inline_diff(diff.text_a, diff.text_b, 'b')
            else:
                text_a_display = f'<span class="text-diff {text_a_class}">{self._esc(diff.text_a)}</span>'
                text_b_display = f'<span class="text-diff {text_b_class}">{self._esc(diff.text_b)}</span>'

            html += f"""<tr class="diff-row" data-type="{diff.diff_type}">
<td>{idx}</td><td>{diff.page}</td><td>{diff.line_number or '-'}</td>
<td><span class="badge {badge_class}">{diff.diff_type.upper()}</span></td>
<td>{text_a_display}</td><td>{text_b_display}</td>
<td>{self._esc(diff.description)}</td></tr>
"""
        html += "</tbody></table>\n"
        return html

    def _build_screenshot_section(self) -> str:
        screenshots_dir = os.path.join(self.config.output_dir, "screenshots")
        if not os.path.exists(screenshots_dir):
            return ""

        html = '<div class="screenshot-section"><h2>Side-by-Side Page Comparison</h2>'
        a_pages = sorted([f for f in os.listdir(screenshots_dir) if f.startswith("PDF_A_")])
        b_pages = sorted([f for f in os.listdir(screenshots_dir) if f.startswith("PDF_B_")])
        max_pages = max(len(a_pages), len(b_pages))

        html += '<div class="screenshot-grid">'
        for i in range(max_pages):
            if i < len(a_pages):
                html += f'<div class="screenshot-card"><h4>PDF A - Page {i + 1}</h4>'
                html += f'<img src="screenshots/{a_pages[i]}" alt="PDF A Page {i + 1}"></div>'
            if i < len(b_pages):
                html += f'<div class="screenshot-card"><h4>PDF B - Page {i + 1}</h4>'
                html += f'<img src="screenshots/{b_pages[i]}" alt="PDF B Page {i + 1}"></div>'
        html += '</div></div>'
        return html

    def _build_javascript(self) -> str:
        return """
<script>
function filterRows(type, show) {
    document.querySelectorAll(.diff-row[data-type="${type}"]).forEach(row => {
        row.style.display = show ? '' : 'none';
    });
}
document.querySelectorAll('th').forEach((th, index) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
        const tbody = document.querySelector('#diffTable tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isNum = index < 3;
        rows.sort((a, b) => {
            const aV = a.children[index].textContent.trim();
            const bV = b.children[index].textContent.trim();
            return isNum ? parseInt(aV) - parseInt(bV) : aV.localeCompare(bV);
        });
        rows.forEach(r => tbody.appendChild(r));
    });
});
</script>
"""

    def _inline_diff(self, text_a: str, text_b: str, side: str) -> str:
        words_a = text_a.split()
        words_b = text_b.split()
        matcher = difflib.SequenceMatcher(None, words_a, words_b)
        result = []

        for op, a0, a1, b0, b1 in matcher.get_opcodes():
            words = words_a[a0:a1] if side == 'a' else words_b[b0:b1]
            text = ' '.join(words)
            if op == 'equal':
                result.append(self._esc(text))
            elif op == 'replace':
                if side == 'a':
                    result.append(f'<span style="background:#ffcccc;text-decoration:line-through">{self._esc(text)}</span>')
                else:
                    result.append(f'<span style="background:#ccffcc;font-weight:bold">{self._esc(text)}</span>')
            elif op == 'delete' and side == 'a':
                result.append(f'<span style="background:#ffcccc;text-decoration:line-through">{self._esc(text)}</span>')
            elif op == 'insert' and side == 'b':
                result.append(f'<span style="background:#ccffcc;font-weight:bold">{self._esc(text)}</span>')
        return f'<span class="text-diff">{" ".join(result)}</span>'

    def _count_by_type(self) -> dict:
        counts = {}
        for diff in self.differences:
            counts[diff.diff_type] = counts.get(diff.diff_type, 0) + 1
        return counts

    @staticmethod
    def _esc(text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;"))


class ExcelReportGenerator:
    """Generates an Excel report of all differences."""

    def __init__(self, config: ComparisonConfig, differences: List[Difference]):
        self.config = config
        self.differences = differences

    def generate_excel_report(self) -> str:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            print("   ⚠️  openpyxl not installed. Skipping Excel report.")
            print("      Install with: pip install openpyxl")
            return None

        wb = Workbook()

        # Header styling
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
        fills = {
            'added': PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid"),
            'removed': PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid"),
            'changed': PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid"),
            'spelling': PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid"),
            'punctuation': PatternFill(start_color="DDA0DD", end_color="DDA0DD", fill_type="solid"),
        }
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # Summary Sheet
        ws = wb.active
        ws.title = "Summary"
        ws.append(["PDF Comparison Summary"])
        ws['A1'].font = Font(bold=True, size=16)
        ws.append([])
        ws.append(["PDF A:", os.path.basename(self.config.pdf_a_path)])
        ws.append(["PDF B:", os.path.basename(self.config.pdf_b_path)])
        ws.append(["Generated:", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        ws.append(["Total Differences:", len(self.differences)])
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50

        # Details Sheet
        ws2 = wb.create_sheet("All Differences")
        headers = ["#", "Page", "Line", "Type", "PDF A Text", "PDF B Text", "Description"]
        ws2.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws2.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border

        for idx, diff in enumerate(self.differences, 1):
            ws2.append([idx, diff.page, diff.line_number or "",
                        diff.diff_type.upper(), diff.text_a, diff.text_b, diff.description])
            row_num = ws2.max_row
            fill = fills.get(diff.diff_type, PatternFill())
            for col_num in range(1, 8):
                cell = ws2.cell(row=row_num, column=col_num)
                cell.border = thin_border
                if col_num == 4:
                    cell.fill = fill
                cell.alignment = Alignment(wrap_text=True, vertical='top')

        col_widths = [5, 6, 6, 14, 40, 40, 45]
        for i, w in enumerate(col_widths, 1):
            ws2.column_dimensions[chr(64 + i)].width = w

        excel_path = os.path.join(self.config.output_dir, "comparison_report.xlsx")
        wb.save(excel_path)
        print(f"   📊 Excel Report saved")
        return excel_path


# ══════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════
class PDFComparisonTool:
    """Main class that runs the entire comparison pipeline."""

    def __init__(self, pdf_a_path: str, pdf_b_path: str, output_dir: str = "comparison_output"):
        self.config = ComparisonConfig(
            pdf_a_path=pdf_a_path,
            pdf_b_path=pdf_b_path,
            output_dir=output_dir
        )
        if not os.path.exists(pdf_a_path):
            raise FileNotFoundError(f"PDF A not found: {pdf_a_path}")
        if not os.path.exists(pdf_b_path):
            raise FileNotFoundError(f"PDF B not found: {pdf_b_path}")

    def run(self) -> dict:
        """Run the complete comparison pipeline."""
        print("=" * 60)
        print("  PDF COMPARISON TOOL")
        print("=" * 60)
        print(f"  PDF A: {self.config.pdf_a_path}")
        print(f"  PDF B: {self.config.pdf_b_path}")
        print(f"  Output: {self.config.output_dir}")
        print("-" * 60)

        outputs = {}

        # Step 1: Compare
        print("\n Step 1/4: Comparing PDFs...")
        comparator = PDFComparator(self.config)
        differences = comparator.compare()
        print(f"   Found {len(differences)} differences")

        if not differences:
            print("\n  No differences found! The PDFs are identical.")
            return outputs

        counts = {}
        for d in differences:
            counts[d.diff_type] = counts.get(d.diff_type, 0) + 1
        for dtype, count in counts.items():
            print(f"   - {dtype.upper()}: {count}")

        # Step 2: Highlight PDFs + Screenshots
        print("\n Step 2/4: Highlighting differences on PDFs...")
        highlighter = PDFHighlighter(self.config, differences)
        highlighter.highlight_and_save()
        outputs['highlighted_pdf_a'] = os.path.join(self.config.output_dir, "highlighted_PDF_A.pdf")
        outputs['highlighted_pdf_b'] = os.path.join(self.config.output_dir, "highlighted_PDF_B.pdf")

        # Step 3: HTML Report
        print("\n Step 3/4: Generating HTML report...")
        reporter = ReportGenerator(self.config, differences)
        outputs['html_report'] = reporter.generate_html_report()

        # Step 4: Excel Report
        print("\n Step 4/4: Generating Excel report...")
        excel_gen = ExcelReportGenerator(self.config, differences)
        outputs['excel_report'] = excel_gen.generate_excel_report()

        # Final Summary
        print("\n" + "=" * 60)
        print("  COMPARISON COMPLETE!")
        print("=" * 60)
        print(f"\n  All outputs saved to: {os.path.abspath(self.config.output_dir)}/")
        print(f"\n  Output files:")
        print(f"   - comparison_report.html   (open in browser)")
        print(f"   - comparison_report.xlsx   (open in Excel)")
        print(f"   - highlighted_PDF_A.pdf")
        print(f"   - highlighted_PDF_B.pdf")
        print(f"   - screenshots/             (page images)")
        print(f"\n  Total Differences: {len(differences)}")

        return outputs