# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Streamlit entrypoint and page layout orchestration.
- `components/`
  - `upload_step.py`: Upload UI, example-PDF loaders, multi-step analysis flow and results table/CSV.
  - `sidebar.py`: Legacy sidebar (currently unused in `app.py`).
- `services/`
  - `pdf_service.py`: PDF page numbering, image conversion, page extraction utilities.
  - `gemini_service.py`: Prompting, batch analysis, page relevance, validation, and final summary via Gemini.
- `utils/session_state.py`: Initializes and manages Streamlit `st.session_state` keys.
- `Filereference/`: Sample PDFs and user-provided assets.
- `requirements.txt`, `packages.txt`: Python and OS dependencies (e.g., Poppler for `pdf2image`).

## Build, Test, and Development Commands
- Create env and install deps:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install --upgrade pip && pip install -r requirements.txt`
- OS deps for PDF images: install Poppler (e.g., `brew install poppler` on macOS, `apt-get install poppler-utils` on Debian/Ubuntu; see `packages.txt`).
- Run locally: `streamlit run app.py`
- Python: 3.12+ recommended (3.13 supported; pandas pinned to avoid source builds).

## Coding Style & Naming Conventions
- Python with 4-space indentation and type hints where helpful.
- `snake_case` for files, functions, and variables; `PascalCase` for classes.
- Keep UI text user-facing and concise; prefer `st.*` logging over prints.
- Small, focused functions; docstrings for non-trivial logic.

## Testing Guidelines
- No formal test suite yet; perform manual smoke tests:
  - Click each example PDF button (구본명/윤덕철) and verify load and preview.
  - Upload a custom PDF; confirm 3-step progress, results table, and CSV download.
  - Validate Unicode filenames in `Filereference/` load correctly.

## Commit & Pull Request Guidelines
- Use Conventional Commits: e.g., `feat(upload): add example PDF buttons`,
  `fix(upload): normalize Hangul filenames`, `chore(ui): remove sidebar`.
- PRs should include: purpose/summary, screenshots of UI changes, affected files in `Filereference/`, and any config notes.

## Security & Configuration Tips
- Configure Gemini via `.env` or Streamlit secrets: `GEMINI_API_KEY` (see `config.py`). Do not commit secrets.
- `Filereference/` contains user data; avoid committing sensitive documents. Hangul filenames may be stored as NFC/NFD—loading uses normalization, but keep descriptive, stable names.
