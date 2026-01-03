import shelve
import unicodedata
import os

# Try importing FPDF, but don't crash if it's missing
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

def generate_pdf(content, filename):
    """
    Generates a PDF file from text content.
    """
    if FPDF is None:
        # Fallback if library is missing
        return None

    try:
        # Normalize content to handle unicode characters incompatible with latin-1/ascii
        content = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore').decode('ascii')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.multi_cell(0, 10, content)
        pdf.output(filename, 'F')
        return pdf
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

def load_chat_history():
    """
    Loads chat history safely.
    """
    try:
        with shelve.open("chat_history") as db:
            return db.get("messages", [])
    except Exception:
        # Return empty list if file is corrupt or unreadable
        return []

def save_chat_history(messages):
    """
    Saves chat history safely.
    """
    try:
        with shelve.open("chat_history") as db:
            db["messages"] = messages
    except Exception:
        pass