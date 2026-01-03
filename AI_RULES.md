# AI Rules & Guidelines

This document outlines the technical stack and development rules for the Automated Course Content Generator (ACCG) application.

## Tech Stack

- **Language**: Python 3.x
- **Web Framework**: [Streamlit](https://streamlit.io/) - Used for the entire UI and application logic.
- **AI Model Integration**: [OpenAI Python Client](https://github.com/openai/openai-python) - Interfaces with GPT-3.5/4 models.
- **PDF Generation**: [FPDF](https://pyfpdf.readthedocs.io/) - Used to generate downloadable course PDFs.
- **Environment Management**: [python-dotenv](https://pypi.org/project/python-dotenv/) - For loading environment variables (API keys).
- **Data Persistence**: `shelve` (Python Standard Library) - Used for storing chat history locally.
- **Data Interchange**: JSON - Used for parsing structured responses from the LLM.

## Development Rules

1.  **UI Development**:
    *   All user interface elements must be built using **Streamlit** components (`st.write`, `st.columns`, `st.button`, etc.).
    *   Do not use React, Vue, or other frontend frameworks.
    *   Use `st.session_state` to manage state across re-runs.

2.  **AI Integration**:
    *   Use the `openai` library for all LLM interactions.
    *   Ensure API keys are loaded securely from environment variables using `os.getenv("OPENAI_API_KEY")`.

3.  **Prompt Management**:
    *   Store large prompt templates in the `prompts/` directory as Python variables.
    *   Import these prompts into `app.py` rather than hardcoding them in the main logic.

4.  **File Generation**:
    *   Use `fpdf` for generating PDF documents.
    *   Ensure text content is normalized (e.g., using `unicodedata`) before writing to PDF to handle encoding issues.

5.  **Code Structure**:
    *   Keep the main application logic in `app.py`.
    *   Utility functions (like `generate_pdf`) should be defined clearly, preferably at the top of the file or in a separate utility module if they grow too large.