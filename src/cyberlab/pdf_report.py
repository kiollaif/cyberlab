"""PDF средствами Qt: кириллица, переносы и страницы без стороннего PDF-пакета."""

import html

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMarginsF
from PySide6.QtGui import QFont, QPageSize, QPdfWriter, QTextDocument

from cyberlab.domain import Scenario
from cyberlab.reports import build_report
from cyberlab.storage import HistoryEntry


def build_pdf_report(
    scenario: Scenario, entries: list[HistoryEntry], active: HistoryEntry
) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Не удалось подготовить PDF.")
    writer = QPdfWriter(buffer)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(16, 16, 16, 16))
    writer.setResolution(96)
    writer.setTitle("CYBERLAB — " + scenario.title)
    writer.setCreator("CYBERLAB")
    document = QTextDocument()
    document.setDefaultFont(QFont("DejaVu Sans", 10))
    lines = build_report(scenario, entries, active).splitlines()
    # Данные из сценария и истории экранируются: они не становятся HTML-командами
    # или внешними ссылками. QTextDocument сам создаёт следующие страницы.
    paragraphs = []
    for index, line in enumerate(lines):
        tag = "h1" if index == 0 else "p"
        paragraphs.append(f"<{tag}>{html.escape(line) or '&nbsp;'}</{tag}>")
    document.setHtml(
        '<html><head><meta charset="utf-8"><style>'
        "p { margin: 3px 0; } h1 { font-size: 18pt; color: #15364a; }"
        "</style></head><body>" + "".join(paragraphs) + "</body></html>"
    )
    document.print_(writer)
    del writer  # Закрывает структуру PDF перед чтением буфера.
    buffer.close()
    result = bytes(data)
    if not result.startswith(b"%PDF-") or not result.rstrip().endswith(b"%%EOF"):
        raise OSError("PDF не был завершён. Прежний отчёт не изменён.")
    return result
