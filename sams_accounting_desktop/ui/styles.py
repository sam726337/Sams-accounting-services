STYLESHEET = """
QWidget#shell,
QWidget#workspace {
    background: #eef2f6;
    color: #101828;
    font-family: Segoe UI;
}

QScrollArea#workspaceScroll {
    background: #eef2f6;
}

QFrame#sidebar {
    background: #101828;
}

QLabel#brandTitle {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}

QLabel#brandDetail,
QLabel#userPlan {
    color: #98a2b3;
    font-size: 11px;
}

QPushButton#navItem,
QPushButton#navActive {
    border: 0;
    border-radius: 7px;
    color: #d0d5dd;
    background: transparent;
    text-align: left;
    padding: 7px 12px;
    font-size: 13px;
}

QPushButton#navItem:hover {
    background: #1d2939;
    color: #ffffff;
}

QPushButton#navActive {
    background: #184e4a;
    color: #ffffff;
    font-weight: 700;
}

QFrame#userCard {
    background: #172033;
    border-radius: 8px;
}

QLabel#userName {
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}

QFrame#topbar,
QFrame#hero,
QFrame#kpiCard,
QFrame#moduleCard,
QFrame#sidePanel,
QFrame#activityPanel {
    background: #ffffff;
    border: 1px solid #d9e0ea;
    border-radius: 8px;
}

QLabel#pageTitle {
    color: #101828;
    font-size: 22px;
    font-weight: 700;
}

QLabel#pageSubtitle,
QLabel#heroBody,
QLabel#cardBody,
QLabel#smallText,
QLabel.smallText {
    color: #667085;
    font-size: 12px;
}

QLabel#eyebrow {
    color: #0f766e;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}

QLabel#heroTitle {
    color: #101828;
    font-size: 20px;
    font-weight: 700;
}

QLabel#mutedLabel,
QLabel#stateText {
    color: #667085;
    font-size: 11px;
}

QLabel#kpiValue {
    color: #101828;
    font-size: 22px;
    font-weight: 700;
}

QLabel#cardTitle {
    color: #101828;
    font-size: 16px;
    font-weight: 700;
}

QLabel#sectionTitle {
    color: #101828;
    font-size: 15px;
    font-weight: 700;
}

QLabel#badge {
    background: #eef8f7;
    color: #115e59;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 700;
}

QLabel#healthValue {
    color: #101828;
    font-size: 12px;
    font-weight: 700;
}

QLabel#connectorStatusIdle,
QLabel#connectorStatusOk,
QLabel#connectorStatusError {
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#connectorStatusIdle {
    background: #f1f5f9;
    color: #475467;
}

QLabel#connectorStatusOk {
    background: #ecfdf3;
    color: #067647;
}

QLabel#connectorStatusError {
    background: #fef3f2;
    color: #b42318;
}

QLineEdit#searchBox {
    background: #f8fafc;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 9px 12px;
    color: #101828;
}

QPushButton#primaryButton {
    background: #0f766e;
    color: #ffffff;
    border: 0;
    border-radius: 7px;
    padding: 9px 15px;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background: #115e59;
}

QPushButton#secondaryButton {
    background: #f7f9fc;
    color: #101828;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton#secondaryButton:hover {
    background: #edf2f7;
}

QProgressBar#healthProgress {
    height: 8px;
    background: #edf2f7;
    border: 0;
    border-radius: 4px;
}

QProgressBar#healthProgress::chunk {
    background: #0f766e;
    border-radius: 4px;
}

QListWidget#ledgerList {
    background: #f8fafc;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 6px;
    color: #101828;
    font-size: 12px;
}

QListWidget#ledgerList::item {
    padding: 7px;
    border-radius: 5px;
}

QListWidget#ledgerList::item:selected {
    background: #d9f3ef;
    color: #101828;
}

QPlainTextEdit#connectorLog {
    background: #101828;
    color: #d0d5dd;
    border: 0;
    border-radius: 7px;
    padding: 9px;
    font-family: Consolas;
    font-size: 11px;
}

QTableWidget#activityTable {
    border: 0;
    background: #ffffff;
    color: #101828;
    gridline-color: transparent;
    selection-background-color: transparent;
    font-size: 12px;
}

QHeaderView::section {
    background: #f8fafc;
    color: #475467;
    border: 0;
    border-bottom: 1px solid #d9e0ea;
    padding: 8px;
    font-weight: 700;
}
"""
