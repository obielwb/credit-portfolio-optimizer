

from __future__ import annotations


def _sanitize_pdf_text(value: str) -> str:

    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def build_text_pdf(lines: list[str]) -> bytes:


    page_lines = [line for line in lines if line is not None]
    if not page_lines:
        page_lines = ["Report"]

    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
        "/BaseFont /Helvetica >> /F2 << /Type /Font /Subtype /Type1 "
        "/BaseFont /Helvetica-Bold >> >> >> /Contents 4 0 R >>",
    ]

    stream_lines = [
        "BT",
        "/F2 16 Tf",
        "50 790 Td",
        f"({_sanitize_pdf_text(page_lines[0])}) Tj",
        "/F1 10 Tf",
    ]
    for index, line in enumerate(page_lines[1:], start=1):
        stream_lines.append(f"0 -{28 if index == 1 else 16} Td")
        stream_lines.append(f"({_sanitize_pdf_text(line)}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines)
    objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n{obj}\nendobj\n"

    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    )
    return pdf.encode("latin-1", errors="replace")


__all__ = ["build_text_pdf"]
