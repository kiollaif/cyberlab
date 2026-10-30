"""Главные задачи новичка проверяем через реальные кнопки и сохранённую SQLite."""

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLabel, QPushButton

from cyberlab.scenarios import USB
from cyberlab.session import LabSession
from cyberlab.storage import HistoryRepository
from cyberlab.ui import MainWindow


@pytest.fixture
def guided_window(qtbot, tmp_path):
    repository = HistoryRepository(tmp_path / "history.sqlite3")
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(LabSession(repository), settings)
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()
    repository.close()


def test_first_launch_explains_goal_and_reaches_first_choice_in_two_clicks(guided_window):
    window = guided_window
    labels = [label.text() for label in window.menu.findChildren(QLabel)]
    assert "CYBERLAB" in labels
    assert "Интерактивный тренажёр кибербезопасности" in labels
    assert any("Вы будете принимать решения" in text for text in labels)
    assert [button.text() for button in window.menu.findChildren(QPushButton)] == [
        "Начать обучение",
        "Продолжить",
        "Мои результаты",
        "Как это работает?",
    ]
    original = window.lab.entries
    window.start_button.click()
    assert window.current_page is window.training
    assert window.scenario_selector.isVisible()
    assert window.lab.entries == original
    window.training_start_button.click()
    assert window.current_page is window.situation
    assert window.situation.findChild(QPushButton, "choice_report").isVisible()
    assert window.lab.entries == original
    assert not window.tutorial.isVisible()  # Знакомство доступно по желанию.


def test_continue_after_browsing_another_topic_and_restart_restores_unread_step(
    qtbot, guided_window
):
    window = guided_window
    window.start_button.click()
    window.training_start_button.click()
    window.situation.findChild(QPushButton, "choice_open_link").click()
    original = window.lab.active
    entries = window.lab.entries
    window.show_menu()
    window.start_button.click()
    window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(USB.id))
    assert window.lab.scenario == USB
    window.show_menu()
    restored = MainWindow(LabSession(window.lab.repository), window.settings)
    qtbot.addWidget(restored)
    restored.show()
    restored.resume_button.click()
    assert restored.lab.active == original
    assert restored.lab.entries == entries
    assert restored.current_page is restored.consequence
    assert restored.scenario_selector.currentData() == "phishing-v1"
    assert "0 → 30" in restored.consequence.risk_change.text()
    restored.close()


def test_results_include_all_topics_and_open_selected_without_changing_snapshots(guided_window):
    window = guided_window
    window.start_button.click()
    window.training_start_button.click()
    window.situation.findChild(QPushButton, "choice_report").click()
    window.consequence.continue_button.click()
    phishing_id = window.lab.session.id
    safe_result = window.lab.active
    window.show_menu()
    window.start_button.click()
    window.scenario_selector.setCurrentIndex(window.scenario_selector.findData(USB.id))
    window.training_start_button.click()
    window.situation.findChild(QPushButton, "choice_connect").click()
    connection = window.lab.repository.connection
    before = connection.execute("SELECT * FROM entries ORDER BY rowid").fetchall()
    window.show_menu()
    window.sessions_button.click()
    assert window.session_list.count() == 2
    assert "USB" in window.session_list.item(0).text()
    assert "В процессе" in window.session_list.item(0).text()
    assert "Завершено" in window.session_list.item(1).text()
    assert window.session_list.item(1).data(Qt.ItemDataRole.UserRole) == phishing_id
    window.session_list.setCurrentRow(1)
    window.open_session_button.click()
    assert window.current_page is window.results
    assert window.lab.active == safe_result
    assert window.scenario_selector.currentData() == "phishing-v1"
    assert connection.execute("SELECT * FROM entries ORDER BY rowid").fetchall() == before
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


def test_empty_results_offer_a_real_first_step(guided_window):
    window = guided_window
    window.sessions_button.click()
    assert window.empty_history.isVisible()
    assert not window.session_list.isVisible()
    assert window.empty_start_button.isVisible()
    window.empty_start_button.click()
    assert window.current_page is window.training


def test_secondary_tools_appear_only_on_request_and_keep_history(guided_window):
    window = guided_window
    window.start_button.click()
    window.training_start_button.click()
    original = window.lab.entries
    navigation = window.navigation
    assert not any(navigation.buttons[name].isVisible() for name in navigation.tool_sections)
    navigation.tools_toggle.click()
    assert all(navigation.buttons[name].isVisible() for name in navigation.tool_sections)
    navigation.buttons["computer"].click()
    assert window.current_page is window.computer
    window.back_button.click()
    assert window.current_page is window.situation
    navigation.buttons["home"].click()
    assert not navigation.tools_toggle.isChecked()
    assert window.lab.entries == original


def test_bad_cross_topic_session_does_not_partly_switch_simulation(guided_window):
    lab = guided_window.lab
    original = lab.scenario, lab.session, lab.active
    with pytest.raises(ValueError):
        lab.open_session(lab.session.id, scenario=USB)
    assert (lab.scenario, lab.session, lab.active) == original
