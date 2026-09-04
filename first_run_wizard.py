from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)
from ui_controls import MaterialComboBox


class FirstRunWizard(QWizard):
    def __init__(self, parent, default_version, instance, logo_path="",
                 arrow_path="assets/chevron_down.svg", available_versions=None):
        super().__init__(parent)
        self.instance = instance
        self.default_version = default_version
        self.available_versions = available_versions or []
        self.logo_path = logo_path
        self.arrow_path = arrow_path.replace("\\", "/")
        self.up_arrow_path = self.arrow_path.replace("chevron_down", "chevron_up")
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
        self.addPage(self.create_account_page())
        self.addPage(self.create_ready_page())
        self.setStyleSheet(self.stylesheet(self.arrow_path, self.up_arrow_path))

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

        self.name_input = QLineEdit("")
        self.name_input.setPlaceholderText("Es. Survival, Modpack, Creative")
        form.addRow("Nome istanza", self.name_input)

        self.version_combo = MaterialComboBox()
        self.set_available_versions(self.available_versions)
        form.addRow("Versione", self.version_combo)

        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(2, 24)
        self.ram_spinbox.setValue(int(self.instance.get("ram_gb", 4)))
        self.ram_spinbox.setSuffix(" GB")
        form.addRow("Memoria dedicata", self.ram_spinbox)

        layout.addLayout(form)
        layout.addStretch()
        return page

    def create_account_page(self):
        page = QWizardPage()
        page.setTitle("Configura il tuo account")
        page.setSubTitle("Scegli come vuoi accedere a Minecraft.")
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        self.account_tabs = QTabWidget()
        self.account_tabs.setObjectName("OnboardingTabs")

        microsoft_tab = QWidget()
        microsoft_layout = QVBoxLayout(microsoft_tab)
        microsoft_text = QLabel(
            "Accedi con Microsoft per utilizzare i server autenticati e sincronizzare "
            "il tuo profilo Xbox. L'accesso verrà completato dopo la guida."
        )
        microsoft_text.setWordWrap(True)
        microsoft_text.setObjectName("WizardBody")
        microsoft_layout.addWidget(microsoft_text)
        microsoft_layout.addStretch()

        offline_tab = QWidget()
        offline_layout = QVBoxLayout(offline_tab)
        offline_text = QLabel("Gioca subito senza autenticazione Microsoft.")
        offline_text.setObjectName("WizardBody")
        offline_layout.addWidget(offline_text)
        self.offline_username = QLineEdit()
        self.offline_username.setPlaceholderText("Nome giocatore")
        offline_layout.addWidget(self.offline_username)
        offline_layout.addStretch()

        self.account_tabs.addTab(microsoft_tab, "Microsoft")
        self.account_tabs.addTab(offline_tab, "Offline")
        layout.addWidget(self.account_tabs)
        layout.addStretch()
        return page

    def set_available_versions(self, versions, preferred_version=None):
        current_version = self.version_combo.currentData() if self.version_combo.count() else self.default_version
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        seen = set()
        entries = []
        for version in versions:
            version_id = version.get("id", "") if isinstance(version, dict) else str(version)
            version_type = version.get("type", "release") if isinstance(version, dict) else "release"
            if version_id and version_type == "release" and version_id not in seen:
                entries.append(version_id)
                seen.add(version_id)
        if self.default_version not in seen:
            entries.insert(0, self.default_version)
        for version_id in entries:
            self.version_combo.addItem(version_id, version_id)
        target = preferred_version or current_version
        if target not in entries:
            target = self.default_version
        self.version_combo.setCurrentIndex(max(0, self.version_combo.findData(target)))
        self.version_combo.blockSignals(False)

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
        name = self.name_input.text().strip() or "Minecraft"
        self.instance_name = name
        self.instance_version = self.version_combo.currentData() or self.default_version
        self.instance_ram = self.ram_spinbox.value()
        self.profile_mode = "offline" if self.account_tabs.currentIndex() == 1 else "online"
        self.offline_username_value = self.offline_username.text().strip()
        super().accept()

    @staticmethod
    def stylesheet(arrow_path, up_arrow_path="assets/chevron_up.svg"):
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
                min-height: 32px;
                padding: 3px 8px;
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
                width: 22px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(__DOWN_ARROW__);
                width: 10px;
                height: 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
                background: transparent;
            }
            QSpinBox::up-button {
            }
            QSpinBox::down-button {
            }
            QSpinBox::up-arrow {
                image: url(__UP_ARROW__);
                width: 10px;
                height: 6px;
            }
            QSpinBox::down-arrow {
                image: url(__DOWN_ARROW__);
                width: 10px;
                height: 6px;
            }
            QAbstractItemView {
                background: #1b202a;
                color: #f4f7fb;
                selection-background-color: #3578e5;
                selection-color: white;
                outline: none;
            }
            QTabWidget#OnboardingTabs::pane {
                background: #1b202a;
                border: 1px solid #354052;
                border-radius: 7px;
                padding: 8px;
            }
            QTabWidget#OnboardingTabs QTabBar::tab {
                min-width: 92px;
                padding: 6px 12px;
                background: #151a22;
                color: #8e9aae;
                border: 1px solid #354052;
                border-bottom: none;
            }
            QTabWidget#OnboardingTabs QTabBar::tab:selected {
                background: #3578e5;
                color: white;
                border-color: #3578e5;
            }
            QWizard QPushButton {
                min-height: 30px;
                min-width: 70px;
                padding: 5px 12px;
                background: #3578e5;
                color: white;
                border: none;
                border-radius: 7px;
                font-size: 9pt;
                font-weight: 600;
            }
            QWizard QPushButton:hover {
                background: #4f8cff;
            }
            QWizard QPushButton:disabled {
                background: #293140;
                color: #748097;
            }
        """.replace("__DOWN_ARROW__", arrow_path).replace("__UP_ARROW__", up_arrow_path)
