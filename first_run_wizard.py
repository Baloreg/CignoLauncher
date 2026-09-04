from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)


class FirstRunWizard(QWizard):
    def __init__(self, parent, default_version, instance, logo_path=""):
        super().__init__(parent)
        self.instance = instance
        self.default_version = default_version
        self.logo_path = logo_path
        self.setWindowTitle("Configura CignoLauncher")
        self.setMinimumSize(520, 430)
        self.resize(620, 480)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
        self.setButtonText(QWizard.WizardButton.NextButton, "Continua")
        self.setButtonText(QWizard.WizardButton.BackButton, "Indietro")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Inizia")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Salta")

        self.addPage(self.create_welcome_page())
        self.addPage(self.create_instance_page())
        self.addPage(self.create_ready_page())
        self.setStyleSheet(self.stylesheet())

    def create_welcome_page(self):
        page = QWizardPage()
        page.setTitle("Benvenuto in CignoLauncher")
        page.setSubTitle("Configura il launcher in pochi secondi.")
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        logo = QLabel()
        pixmap = QPixmap(self.logo_path)
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaledToWidth(280, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        text = QLabel(
            "Gestisci più istanze Minecraft, ognuna con la propria versione, memoria "
            "e cartella salvataggi. Potrai modificare tutto in qualsiasi momento."
        )
        text.setWordWrap(True)
        text.setObjectName("WizardBody")
        layout.addWidget(text)
        layout.addStretch()
        return page

    def create_instance_page(self):
        page = QWizardPage()
        page.setTitle("Prepara la tua istanza")
        page.setSubTitle("Queste impostazioni verranno usate per la prima partita.")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        form.setSpacing(14)

        self.name_input = QLineEdit(self.instance.get("name", "Vanilla Principale"))
        self.name_input.setPlaceholderText("Es. Survival, Modpack, Creative")
        form.addRow("Nome istanza", self.name_input)

        self.version_combo = QComboBox()
        self.version_combo.addItem(self.default_version, self.default_version)
        form.addRow("Versione iniziale", self.version_combo)

        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 24)
        self.ram_spinbox.setValue(int(self.instance.get("ram_gb", 4)))
        self.ram_spinbox.setSuffix(" GB")
        form.addRow("Memoria dedicata", self.ram_spinbox)

        layout.addLayout(form)
        layout.addStretch()
        return page

    def create_ready_page(self):
        page = QWizardPage()
        page.setTitle("Tutto pronto")
        page.setSubTitle("L'istanza è pronta per essere installata o avviata.")
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        summary = QLabel(
            "CignoLauncher aprirà la schermata principale. Da lì potrai aggiungere "
            "altre istanze, accedere con Microsoft o giocare offline."
        )
        summary.setWordWrap(True)
        summary.setObjectName("WizardBody")
        layout.addWidget(summary)
        layout.addStretch()
        return page

    def accept(self):
        name = self.name_input.text().strip() or "Vanilla Principale"
        self.instance_name = name
        self.instance_version = self.version_combo.currentData() or self.default_version
        self.instance_ram = self.ram_spinbox.value()
        super().accept()

    @staticmethod
    def stylesheet():
        return """
            QWizard {
                background: #101318;
                color: #f4f7fb;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QWizardPage {
                background: #101318;
            }
            QLabel {
                background: transparent;
                color: #f4f7fb;
            }
            QWizardPage > QLabel {
                font-size: 10pt;
                color: #8e9aae;
            }
            QLabel#WizardBody {
                color: #b4bfd0;
                font-size: 11pt;
                line-height: 1.4;
            }
            QLineEdit, QComboBox, QSpinBox {
                min-height: 38px;
                padding: 5px 10px;
                background: #1b202a;
                color: #f4f7fb;
                border: 1px solid #354052;
                border-radius: 7px;
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 2px solid #4f8cff;
            }
            QComboBox::drop-down {
                width: 30px;
                border: none;
                border-left: 1px solid #354052;
            }
            QAbstractItemView {
                background: #1b202a;
                color: #f4f7fb;
                selection-background-color: #3578e5;
                selection-color: white;
                outline: none;
            }
            QWizard QPushButton {
                min-height: 34px;
                min-width: 90px;
                padding: 6px 16px;
                background: #3578e5;
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
            }
            QWizard QPushButton:hover {
                background: #4f8cff;
            }
            QWizard QPushButton:disabled {
                background: #293140;
                color: #748097;
            }
        """
