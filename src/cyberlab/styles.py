"""Графитовая тема: один акцент, компактные элементы и спокойная иерархия."""

STYLESHEET = """
QWidget { background: #19191d; color: #dedee3; font-family: "Segoe UI", "Inter", sans-serif;
          font-size: 13px; }
QMainWindow, QWidget#root, QWidget#workspace { background: #19191d; }
QWidget#sidebar { background: #141417; border-right: 1px solid #28282d; }
QLabel { background: transparent; border: none; }
QLabel#brand { color: #ececf0; font-size: 14px; font-weight: 650; letter-spacing: 2px; }
QLabel#sidebarCaption { color: #777780; font-size: 11px; }
QLabel#eyebrow { color: #85858f; font-size: 11px; letter-spacing: 1px; }
QLabel#heading { color: #dcdce2; font-size: 14px; font-weight: 600; }
QLabel#storyTitle { color: #eeeeF2; font-size: 24px; font-weight: 600; }
QLabel#muted, QLabel#badge { color: #92929d; font-size: 12px; }
QLabel#caption { color: #777782; font-size: 11px; }
QLabel#metricValue { color: #e7e7ed; font-size: 18px; font-weight: 600; }
QLabel#buttonTitle { background: transparent; color: #dedee3; font-size: 13px; font-weight: 500; }
QLabel#buttonHint { background: transparent; color: #858590; font-size: 12px; }
QLabel#choiceNumber { color: #73737f; font-size: 12px; }
QLabel#choiceArrow { color: #777782; font-size: 16px; }
QLabel:disabled { color: #62626d; }
QWidget#topbar { border-bottom: 1px solid #29292f; }
QLabel#breadcrumb { color: #90909c; font-size: 12px; }
QFrame#panel { border: none; background: transparent; }
QFrame#scenarioRow { border-top: 1px solid #303037; border-bottom: 1px solid #303037; }
QFrame#comparisonColumn { background: #1e1e23; border: none; border-radius: 5px; }
QFrame#resultRow { border: none; border-bottom: 1px solid #2b2b31; }
QPushButton { background: #25252c; border: 1px solid #36363f; border-radius: 5px;
              padding: 0; text-align: left; }
QPushButton:hover { background: #2d2d35; border-color: #45454f; }
QPushButton:focus-visible { border: 1px solid #a6a4d9; }
QPushButton[role="primary"] { background: #aaa8df; border: 1px solid #aaa8df; }
QLabel#buttonTitle[primary="true"] { color: #17161f; }
QLabel#buttonTitle:disabled { color: #63636d; }
QPushButton[role="primary"]:hover { background: #bab8eb; border-color: #bab8eb; }
QPushButton[role="link"] { background: transparent; border: 1px solid transparent; }
QPushButton[role="link"]:hover { background: #232329; }
QPushButton[role="decision"] { background: transparent; border: none;
                              border-bottom: 1px solid #303037; border-radius: 0; }
QPushButton[role="decision"]:hover { background: #222228; }
QPushButton[role="decision"]:focus { background: #26252f; border-bottom-color: #aaa8df; }
QPushButton[role="nav"] { background: transparent; border: none; color: #9999a5;
                         padding: 7px 10px; font-size: 13px; border-radius: 5px; }
QPushButton[role="nav"]:hover { background: #202025; color: #d9d9e1; }
QPushButton[role="nav"]:checked { background: #282731; color: #e0def9; }
QPushButton:disabled { background: transparent; color: #63636d; border-color: #2b2b31; }
QProgressBar { background: #303037; border: none; border-radius: 1px; }
QProgressBar::chunk { background: #aaa8df; border-radius: 1px; }
QCheckBox { color: #a3a3ae; spacing: 7px; font-size: 12px; padding: 2px 0; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #62626f; border-radius: 3px; }
QCheckBox::indicator:checked { background: #aaa8df; border-color: #aaa8df; }
QTreeWidget, QListWidget, QTextEdit { background: #1b1b20; border: none; padding: 4px; }
QTreeWidget::item, QListWidget::item { padding: 7px 8px; border-bottom: 1px solid #25252c; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #2b2a37; color: #e5e2ff; }
QPlainTextEdit { background: #1f1f25; color: #dedee3; border: 1px solid #35353e;
                 border-radius: 5px; padding: 9px; selection-background-color: #4e4c6a; }
QPlainTextEdit:focus { border-color: #77758f; }
QPlainTextEdit[role="answer"] { background: transparent; border: none; padding: 0; }
QTabWidget::pane { border: none; border-top: 1px solid #303037; }
QTabBar::tab { background: transparent; color: #90909d; padding: 9px 12px;
               border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #e2e0f5; border-bottom-color: #aaa8df; }
QComboBox { background: #24242b; padding: 7px 10px; border: 1px solid #373740;
            border-radius: 4px; font-size: 12px; }
QComboBox QAbstractItemView { background: #24242b; selection-background-color: #3b394f; }
QHeaderView::section { background: #222227; color: #898995; padding: 6px; border: none; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: #3b3b44; min-height: 28px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QToolTip { background: #292930; color: #dedee3; border: 1px solid #41414b; padding: 5px; }
"""
