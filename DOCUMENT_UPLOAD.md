# Document upload (Documentation page)

A professional can upload a Word (.docx), PDF or text (.txt) file instead of retyping it.

- Only the TEXT is read (`services/document_import.py`). The file itself is never stored. The text is placed in the
  normal box so the professional can check and edit it; saving works exactly as before (and the text is anonymised
  before any AI sees it, as always).
- Refused with a clear message: unsupported types (including old .doc), files over 5 MB (also enforced by
  `maxUploadSize` in `.streamlit/config.toml` -- keep the two equal), PDFs over 60 pages, text over about 30,000
  characters, password-protected files, damaged files, empty files, and scanned PDFs (no text layer -- there is no OCR).
- Word files are checked for hidden "zip bombs" before being opened. File names and contents are never logged.
- Libraries added (approved October 2026): `pypdf` (PDF) and `python-docx` (Word; it also brings `lxml`).
  Free, open source, run inside the app, no cost. They are only loaded when a PDF/Word file is opened.
- Tests: `tests/test_document_import.py`.
