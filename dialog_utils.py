from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import Qt
from custom_window import CustomWindowMixin

class StyledMessageDialog(QDialog, CustomWindowMixin):
    def __init__(self, parent, title, message, msg_type="info", buttons=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(380, 160)
        self.resize(420, 180)

        self.init_custom_frame(title=title, icon=self.windowIcon() if parent is None else parent.windowIcon(), show_maximize=False)

        main_layout = self.content_layout
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("color: #f8fafc; font-size: 10.5pt; line-height: 1.4;")
        main_layout.addWidget(msg_label)

        main_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        if buttons == "yes_no":
            self.no_btn = QPushButton("Annulla")
            self.no_btn.setObjectName("SecondaryButton")
            self.no_btn.setFixedSize(110, 34)
            self.no_btn.clicked.connect(self.reject)
            btn_row.addWidget(self.no_btn)

            self.yes_btn = QPushButton("Conferma")
            self.yes_btn.setObjectName("PrimaryButton")
            self.yes_btn.setFixedSize(110, 34)
            self.yes_btn.clicked.connect(self.accept)
            btn_row.addWidget(self.yes_btn)
        else:
            self.ok_btn = QPushButton("OK")
            self.ok_btn.setObjectName("PrimaryButton")
            self.ok_btn.setFixedSize(110, 34)
            self.ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(self.ok_btn)

        main_layout.addLayout(btn_row)
        self.apply_stylesheet()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #141922;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton#PrimaryButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 9.5pt;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #2563eb;
            }
            QPushButton#SecondaryButton {
                background-color: #1f232d;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                font-weight: 600;
                font-size: 9.5pt;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #2a303e;
                color: white;
            }
        """)

class StyledInputDialog(QDialog, CustomWindowMixin):
    def __init__(self, parent, title, label_text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 180)
        self.resize(440, 200)
        self.text_value = ""

        self.init_custom_frame(title=title, icon=self.windowIcon() if parent is None else parent.windowIcon(), show_maximize=False)

        main_layout = self.content_layout
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        label = QLabel(label_text)
        label.setStyleSheet("color: #f8fafc; font-size: 10pt; font-weight: 600;")
        main_layout.addWidget(label)

        self.line_input = QLineEdit()
        self.line_input.setPlaceholderText("Inserisci qui...")
        self.line_input.setStyleSheet("""
            QLineEdit {
                background-color: #1f232d;
                color: #ffffff;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        main_layout.addWidget(self.line_input)

        main_layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        cancel_btn = QPushButton("Annulla")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setFixedSize(110, 34)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setFixedSize(110, 34)
        ok_btn.clicked.connect(self.on_ok)
        btn_row.addWidget(ok_btn)

        main_layout.addLayout(btn_row)
        self.apply_stylesheet()

    def on_ok(self):
        self.text_value = self.line_input.text()
        self.accept()

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #141922;
                color: #f8fafc;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton#PrimaryButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 9.5pt;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #2563eb;
            }
            QPushButton#SecondaryButton {
                background-color: #1f232d;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                font-weight: 600;
                font-size: 9.5pt;
            }
            QPushButton#SecondaryButton:hover {
                background-color: #2a303e;
                color: white;
            }
        """)

def ask_confirmation(parent, title, message, destructive=False):
    dlg = StyledMessageDialog(parent, title, message, buttons="yes_no")
    if destructive:
        dlg.yes_btn.setText("Elimina")
        dlg.yes_btn.setStyleSheet("""
            QPushButton#PrimaryButton {
                background-color: #dc2626;
            }
            QPushButton#PrimaryButton:hover {
                background-color: #b91c1c;
            }
        """)
    return dlg.exec() == QDialog.DialogCode.Accepted

def show_warning(parent, title, message):
    dlg = StyledMessageDialog(parent, title, message, buttons="ok")
    dlg.exec()

class CustomMessageBox(StyledMessageDialog):
    def __init__(self, title, message, msg_type="info", parent=None):
        super().__init__(parent, title, message, msg_type=msg_type, buttons="ok")
        if msg_type in ("error", "critical"):
            self.ok_btn.setStyleSheet("""
                QPushButton#PrimaryButton {
                    background-color: #dc2626;
                }
                QPushButton#PrimaryButton:hover {
                    background-color: #b91c1c;
                }
            """)

def custom_text_input(parent, title, label_text):
    dlg = StyledInputDialog(parent, title, label_text)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.text_value, True
    return "", False
