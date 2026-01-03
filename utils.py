import shelve
import unicodedata
from fpdf import FPDF # type: ignore

def generate_pdf(content, filename):
    """
    Generates a PDF file from text content.
    """
    # Normalize content to handle unicode characters incompatible with latin-1/ascii
    content = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore').decode('ascii')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.multi_cell(0, 10, content)
    pdf.output(filename, 'F')
    return pdf

def load_chat_history():
    """
    Loads chat history from a local shelve database.
    """
    with shelve.open("chat_history") as db:
        return db.get("messages", [])

def save_chat_history(messages):
    """
    Saves chat history to a local shelve database.
    """
    with shelve.open("chat_history") as db:
        db["messages"] = messages