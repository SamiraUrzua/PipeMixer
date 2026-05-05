from PySide6.QtWidgets import QApplication


DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QFrame#card {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
}

QFrame#toolbar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
}

QFrame#panel_header {
    background-color: transparent;
}

QLabel#panel_title {
    color: #cdd6f4;
    font-size: 15px;
    font-weight: bold;
}

QLabel#section_title {
    color: #6c7086;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
}

QPushButton:hover {
    background-color: #585b70;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton:checked {
    background-color: #89b4fa;
    color: #1e1e2e;
}

QPushButton:checked:hover {
    background-color: #74c7ec;
}

QPushButton#remove_btn {
    background-color: transparent;
    color: #6c7086;
    font-size: 14px;
    padding: 0px;
}

QPushButton#remove_btn:hover {
    color: #f38ba8;
    background-color: transparent;
}

QPushButton#add_btn {
    background-color: #45475a;
    color: #89b4fa;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 4px 10px;
    font-weight: bold;
}

QPushButton#add_btn:hover {
    background-color: #585b70;
    color: #cdd6f4;
}

QPushButton#toggle_btn {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 5px 8px;
    min-width: 38px;
}

QPushButton#toggle_btn:checked {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
}

QPushButton#toggle_btn:hover {
    background-color: #585b70;
}

QPushButton#toggle_btn:checked:hover {
    background-color: #74c7ec;
}

QPushButton#mute_btn {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 5px 12px;
}

QPushButton#mute_btn:checked {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
}

QPushButton#mute_btn:hover {
    background-color: #585b70;
}

QPushButton#mute_btn:checked:hover {
    background-color: #eba0ac;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
    border-bottom: 1px solid #313244;
    padding: 2px 4px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #313244;
}

QMenu {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #313244;
}

QPushButton#flat_btn {
    background-color: transparent;
    color: #cdd6f4;
    padding: 2px 8px;
    font-weight: 500;
}

QPushButton#flat_btn:hover {
    color: #89b4fa;
    background-color: transparent;
}

QPushButton#restart_btn {
    background-color: #313244;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 12px;
}

QPushButton#restart_btn:hover {
    background-color: #45475a;
    color: #cdd6f4;
}

QSlider {
    background: transparent;
}

QSlider::groove:horizontal {
    height: 4px;
    background: #45475a;
    border-radius: 2px;
    border: none;
}

QSlider::handle:horizontal {
    background: #89b4fa;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: none;
}

QSlider::handle:horizontal:hover {
    background: #cdd6f4;
}

QSlider::sub-page:horizontal {
    background: #89b4fa;
    border-radius: 2px;
    border: none;
}

QSlider:disabled::groove:horizontal {
    background: #313244;
}

QCheckBox {
    color: #a6adc8;
    spacing: 6px;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #585b70;
    background: #1e1e2e;
}

QCheckBox::indicator:checked {
    background: #89b4fa;
    border-color: #89b4fa;
}

QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

QLabel {
    background: transparent;
}

QLabel#available {
    color: #cdd6f4;
}

QLabel#unavailable {
    color: #f38ba8;
}

QLineEdit {
    background-color: #1e1e2e;
    color: #cdd6f4;
    border: 1px solid #89b4fa;
    border-radius: 4px;
    padding: 2px 6px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}

QDialog {
    background-color: #1e1e2e;
}

QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    color: #cdd6f4;
    outline: none;
}

QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}

QListWidget::item:hover:!selected {
    background-color: #313244;
}

QDialogButtonBox QPushButton {
    min-width: 70px;
}

QFrame#route_row {
    background-color: #25253a;
    border-radius: 6px;
    border: 1px solid #45475a;
}

QFrame#separator {
    color: #313244;
    background-color: #313244;
    border: none;
    max-height: 1px;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyleSheet(DARK_THEME)