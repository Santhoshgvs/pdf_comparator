Project Structure:
------------------
pdf_comparator/
│
├── requirements.txt          ← File 1 (dependencies)
├── pdf_compare.py            ← File 2 (main script - ALL the code)
├── run_comparison.py          ← File 3 (simple runner - YOU edit this)
│
├── original.pdf              ← Your first PDF  (you place here)
├── revised.pdf               ← Your second PDF (you place here)
│
└── comparison_output/        ← (auto-created when you run)
    ├── comparison_report.html
    ├── comparison_report.xlsx
    ├── highlighted_PDF_A.pdf
    ├── highlighted_PDF_B.pdf
    ├── screenshots/
    └── side_by_side/

Command to Run:
------------------
python run_comparison.py

Checklist:
------------------
1. Created folder: pdf_comparator/
2. Created file: requirements.txt     (4 lines)
3. Created file: pdf_compare.py       (the big one - paste ALL parts together)
4. Created file: run_comparison.py    (the simple one YOU edit)
5. Ran: pip install -r requirements.txt
6. Placed your 2 PDF files in the folder
7. Edited run_comparison.py with your PDF filenames
8. Ran: python run_comparison.py
9. Report opened in browser.