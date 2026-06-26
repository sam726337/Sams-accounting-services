THEME = {
    "bg": "#f4f7fb",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "line": "#d9e2ec",
    "text": "#101828",
    "muted": "#667085",
    "primary": "#0f766e",
    "primary_dark": "#115e59",
    "sidebar": "#0b1220",
}

STYLESHEET = """
QWidget#shell,
QWidget#workspace,
QWidget#startupWindow {
    background: #f4f7fb;
    color: #101828;
    font-family: Segoe UI;
}

QScrollArea#workspaceScroll {
    background: #f4f7fb;
}

QFrame#sidebar {
    background: #0b1220;
}

QPushButton#hamburgerButton {
    background: #ffffff;
    border: 1px solid rgba(15, 118, 110, 0.22);
    border-radius: 8px;
    padding: 0;
}

QPushButton#hamburgerButton:hover {
    background: #effaf8;
    border-color: rgba(15, 118, 110, 0.45);
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
    background: #162033;
    color: #ffffff;
}

QPushButton#navActive {
    background: #123f3d;
    color: #ffffff;
    font-weight: 700;
}

QFrame#userCard {
    background: #111c2f;
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
QFrame#activityPanel,
QFrame#recoPanel,
QFrame#insightCard,
QFrame#stepperPanel,
QFrame#detailPanel,
QFrame#startupCard {
    background: #ffffff;
    border: 1px solid #d9e0ea;
    border-radius: 8px;
}

QFrame#startupHero {
    background: #0b1220;
    border-radius: 8px;
}

QFrame#hero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #effaf8);
}

QFrame#insightCard {
    background: #fbfdff;
}

QLabel#pageTitle {
    color: #101828;
    font-size: 22px;
    font-weight: 700;
}

QLabel#startupTitle {
    color: #101828;
    font-size: 24px;
    font-weight: 800;
}

QLabel#startupTitleLight {
    color: #ffffff;
    font-size: 26px;
    font-weight: 800;
}

QLabel#startupSubtitle,
QLabel#startupBody {
    color: #667085;
    font-size: 13px;
}

QLabel#startupBodyLight {
    color: #d0d5dd;
    font-size: 14px;
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

QLabel#insightValue {
    color: #101828;
    font-size: 15px;
    font-weight: 800;
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
QLabel#connectorStatusError,
QLabel#statusIdle,
QLabel#statusOk,
QLabel#statusWarning,
QLabel#statusError,
QLabel#statusInfo {
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#connectorStatusIdle,
QLabel#statusIdle,
QLabel#statusInfo {
    background: #f1f5f9;
    color: #475467;
}

QLabel#connectorStatusOk,
QLabel#statusOk {
    background: #ecfdf3;
    color: #067647;
}

QLabel#statusWarning {
    background: #fffaeb;
    color: #b54708;
}

QLabel#connectorStatusError,
QLabel#statusError {
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

QPushButton#primaryButton:disabled,
QPushButton#secondaryButton:disabled {
    background: #eef2f6;
    color: #98a2b3;
    border: 1px solid #d9e0ea;
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

QPushButton#filterButton,
QPushButton#filterActive {
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 7px 11px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#filterButton {
    background: #ffffff;
    color: #475467;
}

QPushButton#filterButton:hover {
    background: #f8fafc;
    color: #101828;
}

QPushButton#filterActive {
    background: #e6f6f3;
    color: #0f766e;
    border-color: rgba(15, 118, 110, 0.28);
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

QListWidget#fileList {
    background: #f8fafc;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 6px;
    color: #101828;
    font-size: 12px;
}

QListWidget#fileList::item {
    padding: 7px;
    border-radius: 5px;
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

QTableWidget#resultTable {
    border: 0;
    background: #ffffff;
    color: #101828;
    gridline-color: transparent;
    selection-background-color: transparent;
    font-size: 12px;
}

QFrame#stepActive,
QFrame#stepDone,
QFrame#stepIdle {
    border-radius: 7px;
    border: 1px solid #d9e0ea;
}

QFrame#stepActive {
    background: #e6f6f3;
    border-color: rgba(15, 118, 110, 0.42);
}

QFrame#stepDone {
    background: #ecfdf3;
    border-color: rgba(6, 118, 71, 0.26);
}

QFrame#stepIdle {
    background: #f8fafc;
}

QLabel#stepNumber {
    min-width: 22px;
    min-height: 22px;
    border-radius: 11px;
    background: #0f766e;
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
}

QLabel#stepLabel {
    color: #344054;
    font-size: 12px;
    font-weight: 800;
}

QLabel#detailTitle {
    color: #101828;
    font-size: 16px;
    font-weight: 800;
}

QLabel#detailValue {
    color: #101828;
    font-size: 12px;
    font-weight: 700;
}

QLabel#toastInfo {
    background: #effaf8;
    color: #115e59;
    border: 1px solid rgba(15, 118, 110, 0.18);
    border-radius: 7px;
    padding: 9px 11px;
    font-size: 12px;
    font-weight: 700;
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
