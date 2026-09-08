"""
==============================================
  PDF COMPARISON - SIMPLE RUNNER
==============================================

HOW TO USE:
  1. Place your two PDF files in this folder
  2. Change the file names below
  3. Run this script

That's it!
"""

from pdf_compare import PDFComparisonTool

# ╔══════════════════════════════════════════╗
# ║  CHANGE THESE TO YOUR PDF FILE NAMES     ║
# ╚══════════════════════════════════════════╝

PDF_FILE_1 = "Original_file.pdf"      # <-- Your first PDF
PDF_FILE_2 = "Revised_file.pdf"       # <-- Your second PDF
OUTPUT_FOLDER = "comparison_output"  # <-- Where results go

# ──────────────────────────────────────────
# Don't change anything below this line
# ──────────────────────────────────────────

if __name__ == "__main__":
    try:
        tool = PDFComparisonTool(
            pdf_a_path=PDF_FILE_1,
            pdf_b_path=PDF_FILE_2,
            output_dir=OUTPUT_FOLDER
        )
        results = tool.run()

        # Auto-open the HTML report in your browser
        import webbrowser
        import os
        report_path = os.path.join(OUTPUT_FOLDER, "comparison_report.html")
        if os.path.exists(report_path):
            print(f"\n  Opening report in browser...")
            webbrowser.open('file://' + os.path.abspath(report_path))

    except FileNotFoundError as e:
        print(f"\n  ERROR: {e}")
        print(f"\n  Make sure your PDF files are in the same folder as this script.")
        print(f"  Current folder: {os.getcwd()}")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        raise