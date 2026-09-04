from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QIcon


DIALOG_STYLE = """
    QMessageBox {
        background: #12161e;
        color: #edf3fb;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    QLabel {
        color: #edf3fb;
        font-size: 10pt;
    }
    QPushButton {
        min-width: 82px;
        min-height: 30px;
        padding: 5px 14px;
        background: #273244;
        color: #dce7f5;
        border: 1px solid #40516b;
        border-radius: 6px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #34445d;
        border-color: #5f83b4;
    }
    QPushButton#DestructiveButton {
        background: #7f2930;
        color: #fff1f2;
        border-color: #b34a53;
    }
    QPushButton#DestructiveButton:hover {
        background: #a53640;
    }
"""


def ask_confirmation(parent, title, message, destructive=False):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setIcon(QMessageBox.Icon.Warning if destructive else QMessageBox.Icon.Question)
    dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    dialog.setDefaultButton(QMessageBox.StandardButton.No)
    dialog.setStyleSheet(DIALOG_STYLE)
    yes_button = dialog.button(QMessageBox.StandardButton.Yes)
    no_button = dialog.button(QMessageBox.StandardButton.No)
    yes_button.setText("Elimina" if destructive else "Conferma")
    no_button.setText("Annulla")
    if destructive:
        yes_button.setObjectName("DestructiveButton")
    for button in (yes_button, no_button):
        button.setIcon(QIcon())
    return dialog.exec() == QMessageBox.StandardButton.Yes


def show_warning(parent, title, message):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    dialog.setIcon(QMessageBox.Icon.Warning)
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    dialog.setStyleSheet(DIALOG_STYLE)
    dialog.exec()
