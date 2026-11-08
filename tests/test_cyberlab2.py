"""Пользовательский путь 2.0, локальная справка, схема и настоящий PDF."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QFileDialog, QPushButton

from cyberlab.glossary import TERMS
from cyberlab.pdf_report import build_pdf_report
from cyberlab.scenarios import DOWNLOAD, MESSAGE, SCENARIOS
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def cyberlab2(qtbot, tmp_path):
    repository = HistoryRepository(tmp_path / "history.sqlite3")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(LabSession(repository), settings)
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.show()
    yield window
    qtbot.waitUntil(lambda: not window.ai_mentor.busy)
    window.close()
    repository.close()


def choose(window, choice):
    window.situation.findChild(QPushButton, "choice_" + choice).click()
    assert window.current_page is window.consequence
    window.consequence.continue_button.click()


def test_catalog_metadata_and_optional_lesson_preserve_selected_topic(cyberlab2):
    window = cyberlab2
    window.start_button.click()
    assert window.training.lesson_offer.isVisible()
    assert window.scenario_selector.count() == 6
    for scenario in SCENARIOS:
        window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(scenario.id))
        assert scenario.difficulty in window.training.objectives.text()
        assert all(
            objective in window.training.objectives.text() for objective in scenario.objectives
        )
    original = window.lab.entries
    window.training.lesson_offer.click()
    assert window.current_page is window.tutorial
    assert "фишинг" in window.tutorial.title.text().lower()
    for _ in range(4):
        window.tutorial.next_button.click()
    window.tutorial.finish_button.click()
    assert window.current_page is window.training
    assert window.lab.scenario == DOWNLOAD and window.lab.entries == original
    assert not window.training.lesson_offer.isVisible()
    window.back_button.click()
    assert window.current_page is window.menu
    window.start_button.click()
    assert window.current_page is window.training
    window.training_start_button.click()
    assert window.current_page is window.situation
    assert "отключите" in window.situation.source_body.text()


@pytest.mark.parametrize(
    "scenario,route,safe_action",
    [
        (MESSAGE, ("open_link", "submit", "ignore"), "delete"),
        (DOWNLOAD, ("download", "run", "ignore"), "official"),
    ],
)
def test_new_scenario_ui_rewind_interactive_map_and_real_assessment(
    qtbot, cyberlab2, scenario, route, safe_action
):
    window = cyberlab2
    window.start_button.click()
    window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(scenario.id))
    window.training_start_button.click()
    root = window.lab.active.id
    for action in route:
        window.situation.findChild(QPushButton, "choice_" + action).click()
        if action == "download":
            assert window.lab.active.state.program_downloaded
            assert "Учебная загрузка" in window.computer.browser_heading.text()
            assert window.computer.file_list.count() == 3
        before = window.lab.entries
        diagram = window.consequence.causality
        window.pages[window.consequence].ensureWidgetVisible(diagram)
        qtbot.mouseClick(
            diagram, Qt.MouseButton.LeftButton, pos=diagram.node_rect(0).center().toPoint()
        )
        assert window.consequence.event.text() == diagram.items[0]
        qtbot.keyClick(diagram, Qt.Key.Key_Right)
        assert window.consequence.event.text() == window.lab.active.choice_title
        assert window.lab.entries == before
        window.consequence.continue_button.click()
    assert window.current_page is window.results
    assert window.results.assessment.risky == 3
    assert window.results.assessment.score == 0
    assert len(window.results.assessment.mistakes) == 3
    assert window.results.risk_chart.values[-1] >= 95
    window.results.risk_chart._select(1)
    assert window.results.assessment.decisions[0].title in window.results.point_detail.text()
    window._go_to(root)
    assert window.computer.file_list.count() == 2
    choose(window, safe_action)
    assert window.results.assessment.score == 100
    assert window.results.assessment.safe == 1
    window.show_menu()
    window.sessions_button.click()
    assert window.session_list.count() == 2  # Оба итога одной тренировки, не только последний.
    assert set(window.saved_sessions.chart.values) == {0, 100}
    window.saved_sessions.chart._select(0)
    window.open_session_button.click()
    assert window.lab.active.state.risk >= 95


def test_pdf_export_reads_cyrillic_and_contains_only_selected_path(
    cyberlab2, tmp_path, monkeypatch
):
    window = cyberlab2
    window.start_button.click()
    window.training_start_button.click()
    root = window.lab.active.id
    for action in ("open_link", "submit", "ignore"):
        choose(window, action)
    window._go_to(root)
    choose(window, "report")
    destination = tmp_path / "Мой учебный отчёт.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination), "Документ PDF (*.pdf)")
    )
    before = window.lab.entries
    window.results.pdf_button.click()
    assert destination.read_bytes().startswith(b"%PDF-")
    doc = QPdfDocument()
    assert doc.load(str(destination)) == QPdfDocument.Error.None_
    text = "\n".join(doc.getAllText(i).text() for i in range(doc.pageCount()))
    assert "Безопасных решений: 1" in text and "Оценка решений: 100/100" in text
    assert "Отправить учебный пароль" not in text
    assert window.lab.entries == before and "сохранён" in window.results.export_status.text()
    doc.close()


def test_pdf_long_report_has_final_recommendation_and_multiple_pages(qtbot, tmp_path):
    repository = HistoryRepository(":memory:")
    try:
        lab = LabSession(repository, DOWNLOAD)
        for action in ("inspect", "download", "run", "ignore"):
            lab.choose(action)
        data = build_pdf_report(DOWNLOAD, lab.entries, lab.active)
        path = tmp_path / "long.pdf"
        path.write_bytes(data)
        doc = QPdfDocument()
        assert doc.load(str(path)) == QPdfDocument.Error.None_
        text = "\n".join(doc.getAllText(i).text() for i in range(doc.pageCount()))
        assert doc.pageCount() >= 2
        assert "Ошибки и рекомендации" in text
        assert "Реальные пароли, файлы и устройства не" in text
        assert "0 → 0 → 25 → 80 → 100" in text
        doc.close()
    finally:
        repository.close()


def test_glossary_is_offline_and_does_not_change_the_simulation(cyberlab2, monkeypatch):
    window = cyberlab2
    window.start_button.click()
    window.training_start_button.click()
    before = window.lab.entries
    window._open_ai()
    panel = window.ai_mentor
    monkeypatch.setattr(
        panel.client, "answer", lambda *a: pytest.fail("Справка не должна вызывать API")
    )
    for term, explanation in TERMS.items():
        index = panel.term_selector.findText(term)
        panel.term_selector.setCurrentIndex(index)
        panel.term_selector.activated.emit(index)
        assert panel.answer.toPlainText() == explanation
        assert "офлайн" in panel.mode.text() and not panel.busy
    assert window.lab.entries == before


def test_cancel_and_failed_pdf_export_keep_history_and_existing_file(
    cyberlab2, tmp_path, monkeypatch
):
    window = cyberlab2
    window.start_button.click()
    window.training_start_button.click()
    choose(window, "report")
    before = window.lab.entries
    old_file = tmp_path / "existing.pdf"
    old_file.write_bytes(b"Existing report")
    window.results.export_status.setText("Отчёт сохранён.")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    window.results.pdf_button.click()
    assert not window.results.export_status.text()
    assert old_file.read_bytes() == b"Existing report" and window.lab.entries == before
    errors = []
    monkeypatch.setattr("cyberlab.ui.show_error", lambda *a: errors.append(a))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path), ""))
    window.results.pdf_button.click()
    assert errors and not window.results.export_status.text()
    assert window.lab.entries == before and old_file.read_bytes() == b"Existing report"


def test_error_dialog_has_plain_explanation_and_optional_technical_details(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from cyberlab.ui_helpers import show_error

    observed = []
    monkeypatch.setattr(
        QMessageBox,
        "exec",
        lambda dialog: observed.append((dialog.text(), dialog.detailedText())),
    )
    show_error(None, "Не удалось сохранить отчёт", OSError("test disk write failed"))
    assert "Проверьте доступ к папке" in observed[0][0]
    assert "test disk write failed" not in observed[0][0]
    assert observed[0][1] == "test disk write failed"
