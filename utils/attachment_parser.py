# utils/attachment_parser.py

import io
import pdfplumber
from docx import Document


def parse_pdf(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def parse_docx(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


_PARSERS = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
}


def parse_attachment(mime_type: str, data: bytes):
    parser = _PARSERS.get(mime_type)
    if parser:
        return parser(data)
    return None
