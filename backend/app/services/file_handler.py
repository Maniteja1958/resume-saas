from io import BytesIO
from fastapi import UploadFile


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    filename = (filename or "").lower()

    if filename.endswith(".pdf"):
        return _parse_pdf(content)
    if filename.endswith(".docx"):
        return _parse_docx(content)

    return content.decode("utf-8", errors="ignore")


async def read_upload(upload: UploadFile) -> tuple[bytes, str, str]:
    content = await upload.read()
    filename = upload.filename or "resume.txt"
    text = extract_text_from_bytes(content, filename)
    return content, filename, text


def _parse_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)
    except Exception as exc:
        return f"[PDF parse failed: {exc}]"


def _parse_docx(content: bytes) -> str:
    try:
        import docx

        doc = docx.Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        return f"[DOCX parse failed: {exc}]"
