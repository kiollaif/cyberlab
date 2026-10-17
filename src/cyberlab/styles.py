"""Цвета, размеры и оформление Qt. Не содержит правил симуляции."""

STYLESHEET = """
QWidget { background: #101922; color: #e1eaf0; font-size: 16px; }
QMainWindow, QWidget#root { background: #0b1119; }
QFrame#panel { border: 1px solid #293746; border-radius: 10px; }
QFrame#metric { background: #15212d; border: 1px solid #293746; border-radius: 8px; }
QLabel { background: transparent; }
QLabel#brand { color: #60e2bd; font-size: 26px; font-weight: 800; letter-spacing: 3px; }
QLabel#heading { font-size: 17px; font-weight: 700; }
QLabel#storyTitle { font-size: 26px; font-weight: 700; }
QLabel#muted { color: #9aafbe; }
QLabel#badge { color: #60e2bd; background: #16372f; border-radius: 6px; padding: 8px; }
QLabel#metricValue { color: #60e2bd; font-size: 20px; font-weight: 700; }
QLabel#buttonTitle { font-weight: 600; }
QLabel#buttonHint { color: #b6c9d4; font-size: 14px; }
QPushButton { background: #203141; border: 1px solid #3a5163; border-radius: 7px;
              padding: 9px 13px; text-align: left; }
QPushButton:hover { background: #29475a; border-color: #60e2bd; }
QPushButton:focus { border: 2px solid #60e2bd; }
QPushButton[role="choice"] { background: #18382f; border-color: #2b6e58; }
QPushButton[role="primary"] { background: #164737; border: 1px solid #60e2bd; }
QPushButton[role="primary"]:hover { background: #225d49; }
QFrame[rating="risk"] { border-left: 4px solid #efac77; }
QFrame[rating="helpful"] { border-left: 4px solid #60e2bd; }
QProgressBar { background: #243443; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #60e2bd; border-radius: 3px; }
QCheckBox { padding: 10px 0; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #9aafbe; }
QCheckBox::indicator:checked { background: #60e2bd; border: 2px solid #e1eaf0; }
QPushButton:disabled { color: #71818c; }
QTreeWidget, QListWidget, QTextEdit { background: #101922; border: 1px solid #293746;
                                  border-radius: 6px; padding: 5px; }
QTreeWidget::item, QListWidget::item { padding: 7px 3px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #25483f; color: #c8ffec; }
QTabWidget::pane { border: 1px solid #293746; border-radius: 6px; }
QTabBar::tab { background: #15212d; padding: 8px; border-bottom: 2px solid #293746; }
QTabBar::tab:selected { color: #60e2bd; border-bottom-color: #60e2bd; }
QComboBox { background: #1b2a36; padding: 7px; border: 1px solid #3a5163; border-radius: 5px; }
QComboBox QAbstractItemView { background: #1b2a36; selection-background-color: #25483f; }
QTableWidget { background: #101922; border: none; gridline-color: #293746; }
QHeaderView::section { background: #1b2a36; color: #9aafbe; padding: 6px; border: none; }
QSplitter::handle { background: #0b1119; width: 8px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #101922; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #3a5163; min-height: 24px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #203141; color: #e1eaf0; border: 1px solid #60e2bd; }
"""
