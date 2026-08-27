THEME = {
    "bg": "#f4f7fb",
    "surface": "#ffffff",
    "surface_soft": "#f8fafc",
    "line": "#d9e2ec",
    "text": "#101828",
    "muted": "#475467",
    "primary": "#0f766e",
    "primary_dark": "#115e59",
    "sidebar": "#0b1220",
}

STYLESHEET = """
QWidget#shell,
QWidget#workspace,
QWidget#startupWindow {
    background: #f6f8fb;
    color: #101828;
    font-family: Segoe UI;
}

QScrollArea#workspaceScroll {
    background: #f6f8fb;
}

QFrame#topNav,
QFrame#sidebar {
    background: #0b1220;
}

QFrame#topNav {
    border-bottom: 1px solid #1f2937;
}

QWidget#navStrip {
    background: transparent;
}

QLabel#brandTitle {
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}

QLabel#brandDetail,
QLabel#userPlan {
    color: #b3bdcc;
    font-size: 12px;
}

QPushButton#navItem,
QPushButton#navActive {
    border: 0;
    border-radius: 7px;
    color: #d0d5dd;
    background: transparent;
    text-align: center;
    padding: 7px 10px;
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

QPushButton#tallyStatusChecking,
QPushButton#tallyStatusConnected,
QPushButton#tallyStatusDisconnected {
    border-radius: 7px;
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 700;
    text-align: center;
}

QPushButton#tallyStatusChecking {
    background: #1f2937;
    color: #d0d5dd;
    border: 1px solid #344054;
}

QPushButton#tallyStatusChecking:hover {
    background: #263244;
}

QPushButton#tallyStatusConnected {
    background: #063f34;
    color: #d1fae5;
    border: 1px solid rgba(20, 184, 166, 0.55);
}

QPushButton#tallyStatusConnected:hover {
    background: #075646;
}

QPushButton#tallyStatusDisconnected {
    background: #3f1515;
    color: #fee2e2;
    border: 1px solid rgba(248, 113, 113, 0.5);
}

QPushButton#tallyStatusDisconnected:hover {
    background: #561c1c;
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
QFrame#choiceCard,
QFrame#formPanel,
QFrame#previewPanel,
QFrame#salesProgressPanel,
QFrame#startupCard {
    background: #ffffff;
    border: 1px solid #e3e8ef;
    border-radius: 12px;
}

QFrame#choiceCard {
    background: #fbfdff;
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
    font-weight: 800;
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

QLabel#startupMeta {
    color: #667085;
    font-size: 11px;
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
    color: #475467;
    font-size: 13px;
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
QLabel#stateText,
QLabel#formLabel {
    color: #475467;
    font-size: 12px;
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
    font-weight: 800;
}

QLabel#choiceTitle {
    color: #101828;
    font-size: 24px;
    font-weight: 800;
}

QLabel#choiceBody {
    color: #667085;
    font-size: 14px;
}

QLabel#sectionTitle {
    color: #101828;
    font-size: 15px;
    font-weight: 700;
}

QLabel#progressTitle {
    color: #101828;
    font-size: 12px;
    font-weight: 800;
}

QLabel#badge {
    background: #eef6f5;
    color: #115e59;
    border-radius: 12px;
    padding: 5px 10px;
    font-size: 10px;
    font-weight: 800;
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

QComboBox#masterCombo {
    background: #f8fafc;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 8px 10px;
    color: #101828;
}

QComboBox#masterCombo QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 4px;
    color: #101828;
    selection-background-color: #d9f3ef;
    selection-color: #101828;
}

QDateEdit#dateInput,
QSpinBox#numberInput {
    background: #f8fafc;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    padding: 8px 10px;
    color: #101828;
}

QDateEdit#dateInput:focus,
QSpinBox#numberInput:focus,
QLineEdit#searchBox:focus,
QComboBox#masterCombo:focus {
    border-color: rgba(15, 118, 110, 0.55);
}

QPushButton#primaryButton {
    background: #0f766e;
    color: #ffffff;
    border: 0;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 800;
}

QPushButton#cardButton {
    background: transparent;
    color: #0f766e;
    border: 1px solid #b8d8d4;
    border-radius: 8px;
    padding: 8px 13px;
    font-weight: 800;
    text-align: center;
}

QPushButton#cardButton:hover {
    background: #eef8f6;
    border-color: #0f766e;
}

QPushButton#primaryButton:hover {
    background: #115e59;
}

QPushButton#secondaryButton {
    background: #f7f9fc;
    color: #101828;
    border: 1px solid #d9e0ea;
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
}

QPushButton#secondaryButton:hover {
    background: #edf2f7;
}

QPushButton#primaryButton:disabled,
QPushButton#primaryButton:disabled:hover,
QPushButton#secondaryButton:disabled,
QPushButton#secondaryButton:disabled:hover {
    background: #eef2f6;
    color: #98a2b3;
    border: 1px solid #d9e0ea;
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

QProgressBar#salesImportProgress {
    height: 18px;
    background: #e8eef5;
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    color: #101828;
    font-size: 10px;
    font-weight: 800;
    text-align: center;
}

QProgressBar#salesImportProgress::chunk {
    background: #0f766e;
    border-radius: 6px;
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

QTextBrowser#legalDocument {
    background: #ffffff;
    color: #344054;
    border: 1px solid #d9e0ea;
    border-radius: 8px;
    padding: 14px;
    font-family: Segoe UI;
    font-size: 13px;
}

QCheckBox#consentCheckbox {
    color: #344054;
    spacing: 9px;
    font-size: 12px;
}

QTableWidget#activityTable {
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    background: #ffffff;
    color: #101828;
    gridline-color: transparent;
    selection-background-color: transparent;
    font-size: 13px;
}

QTableWidget#resultTable {
    border: 0;
    background: #ffffff;
    color: #101828;
    gridline-color: transparent;
    selection-background-color: transparent;
    font-size: 13px;
}

QTableWidget#salesTable {
    border: 1px solid #d9e0ea;
    border-radius: 7px;
    background: #ffffff;
    color: #101828;
    gridline-color: transparent;
    selection-background-color: #d9f3ef;
    selection-color: #101828;
    font-size: 12px;
}

QTableWidget#salesTable::item {
    padding: 7px;
}

QTableWidget#activityTable::item:alternate,
QTableWidget#resultTable::item:alternate,
QTableWidget#salesTable::item:alternate {
    background: #f8fafc;
}

QScrollBar:vertical {
    background: #f1f5f9;
    width: 11px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #c5ced8;
    border-radius: 5px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #98a2b3;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
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
    padding: 9px 8px;
    font-weight: 700;
}

QTableWidget::item {
    padding: 7px;
}
"""
