"""Графитовая тема с холодным синим акцентом и бирюзовой шкалой."""

STYLESHEET = """
QWidget { background: #0e131b; color: #dce7f2; font-family: "Segoe UI", "Inter", sans-serif;
          font-size: 14px; }
QMainWindow, QWidget#root, QWidget#workspace { background: #0e131b; }
QWidget#sidebar, QWidget#sidebarContent { background: #090e15; }
QWidget#sidebar { border-right: 1px solid #28282d; }
QLabel { background: transparent; border: none; }
QLabel#brand { color: #ececf0; font-size: 14px; font-weight: 650; letter-spacing: 2px; }
QLabel#sidebarCaption { color: #777780; font-size: 11px; }
QLabel#eyebrow { color: #85858f; font-size: 11px; letter-spacing: 1px; }
QLabel#heading { color: #dcdce2; font-size: 14px; font-weight: 600; }
QLabel#storyTitle { color: #eef7ff; font-size: 26px; font-weight: 600; }
QLabel#welcomeBrand { color: #f1f0f5; font-size: 38px; font-weight: 650; letter-spacing: 3px; }
QLabel#welcomeSubtitle { color: #dedce9; font-size: 20px; font-weight: 500; }
QLabel#welcomeDescription { color: #b3b3bf; font-size: 15px; }
QLabel#muted, QLabel#badge { color: #aaaab6; font-size: 13px; }
QLabel#caption { color: #9797a3; font-size: 12px; }
QLabel#metricValue { color: #e7e7ed; font-size: 18px; font-weight: 600; }
QLabel#buttonTitle { background: transparent; color: #dce7f2; font-size: 15px; font-weight: 500; }
QLabel#buttonHint { background: transparent; color: #aaaab6; font-size: 13px; }
QLabel#choiceNumber { color: #73737f; font-size: 12px; }
QLabel#choiceArrow { color: #777782; font-size: 16px; }
QLabel:disabled { color: #62626d; }
QWidget#topbar { border-bottom: 1px solid #29292f; }
QLabel#breadcrumb { color: #90909c; font-size: 12px; }
QFrame#sourcePreview { background: #121f2d; border: 1px solid #263b4c; border-radius: 6px; }
QFrame#panel { border: none; background: transparent; }
QFrame#scenarioRow { border-top: 1px solid #29394a; border-bottom: 1px solid #29394a; }
QFrame#comparisonColumn { background: #131d29; border: none; border-radius: 5px; }
QFrame#resultRow { border: none; border-bottom: 1px solid #2b2b31; }
QPushButton { background: #192430; border: 1px solid #314152; border-radius: 5px;
              padding: 6px 11px; text-align: left; }
QPushButton:hover { background: #223344; border-color: #45454f; }
QPushButton:focus { border-color: #55cbd4; }
QPushButton[size="welcome"] { font-size: 15px; padding: 9px 18px; }
QPushButton[role="primary"] { background: #66b9e9; color: #07131d; border: 1px solid #66b9e9; }
QLabel#buttonTitle:disabled { color: #63636d; }
QPushButton[role="primary"]:hover { background: #83cdf7; border-color: #83cdf7; }
QPushButton[role="link"] { background: transparent; border: 1px solid transparent; }
QPushButton[role="link"]:hover { background: #232329; }
QPushButton[role="decision"] { background: transparent; border: none;
                              border-bottom: 1px solid #29394a; border-radius: 0; padding: 0; }
QPushButton[role="decision"]:hover { background: #162333; }
QPushButton[role="decision"]:focus { background: #1a3547; border-bottom-color: #66b9e9; }
QPushButton[role="nav"] { background: transparent; border: none; color: #9999a5;
                         padding: 7px 10px; font-size: 13px; border-radius: 5px; }
QPushButton[role="nav"]:hover { background: #202025; color: #d9d9e1; }
QPushButton[role="nav"]:checked { background: #182d40; color: #d7efff; }
QPushButton:disabled { background: transparent; color: #63636d; border-color: #2b2b31; }
QProgressBar { background: #29394a; border: none; border-radius: 1px; }
QProgressBar::chunk { background: #66b9e9; border-radius: 1px; }
QProgressBar#riskMeter::chunk { background: #55cbd4; }
QProgressBar#riskMeter[critical="true"]::chunk { background: #ed8b8b; }
QCheckBox { color: #a3a3ae; spacing: 7px; font-size: 12px; padding: 2px 0; }
QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #62626f; border-radius: 3px; }
QCheckBox::indicator:checked { background: #66b9e9; border-color: #66b9e9; }
QTreeWidget, QListWidget, QTextEdit { background: #111b26; border: none; padding: 4px; }
QTreeWidget::item, QListWidget::item { padding: 7px 8px; border-bottom: 1px solid #192430; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #1c3d52; color: #d7f1ff; }
QPlainTextEdit { background: #14212e; color: #dce7f2; border: 1px solid #35353e;
                 border-radius: 5px; padding: 9px; selection-background-color: #4e4c6a; }
QPlainTextEdit:focus { border-color: #77758f; }
QPlainTextEdit[role="answer"] { background: transparent; border: none; padding: 0; }
QTabWidget::pane { border: none; border-top: 1px solid #29394a; }
QTabBar::tab { background: transparent; color: #90909d; padding: 9px 12px;
               border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #e2e0f5; border-bottom-color: #66b9e9; }
QComboBox { background: #172433; padding: 7px 10px; border: 1px solid #373740;
            border-radius: 4px; font-size: 12px; }
QComboBox QAbstractItemView { background: #172433; selection-background-color: #25455e; }
QHeaderView::section { background: #222227; color: #898995; padding: 6px; border: none; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: #3b3b44; min-height: 28px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QToolTip { background: #292930; color: #dce7f2; border: 1px solid #41414b; padding: 5px; }
"""
