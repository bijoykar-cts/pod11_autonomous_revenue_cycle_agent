from html import unescape
from io import BytesIO
import re
import zipfile
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {"txt", "docx", "pdf"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


class DocumentExtractionError(Exception):
    code = "document_extraction_failed"
    status_code = 400


class UnsupportedDocumentTypeError(DocumentExtractionError):
    code = "unsupported_document_type"
    status_code = 415


class EmptyDocumentTextError(DocumentExtractionError):
    code = "empty_document_text"
    status_code = 422


class DocumentTooLargeError(DocumentExtractionError):
    code = "document_too_large"
    status_code = 413


class PdfParserUnavailableError(DocumentExtractionError):
    code = "pdf_parser_unavailable"
    status_code = 503


def document_type_from_filename(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentTypeError("Unsupported document type")
    return suffix


def extract_document_text(filename: str, content: bytes) -> tuple[str, str]:
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentTooLargeError("Document exceeds maximum upload size")

    document_type = document_type_from_filename(filename)
    if document_type == "txt":
        text = _extract_txt(content)
    elif document_type == "docx":
        text = _extract_docx(content)
    elif document_type == "pdf":
        text = _extract_pdf(content)
    else:
        raise UnsupportedDocumentTypeError("Unsupported document type")

    normalized = _normalize_text(text)
    if not normalized:
        raise EmptyDocumentTextError("No clinical note text found")
    return document_type, normalized


def _extract_txt(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _extract_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise UnsupportedDocumentTypeError("Invalid DOCX document") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise UnsupportedDocumentTypeError("Invalid DOCX document XML") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfParserUnavailableError("PDF parser dependency is unavailable") from exc

    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise DocumentExtractionError("Unable to extract PDF text") from exc


def _normalize_text(text: str) -> str:
    text = unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
