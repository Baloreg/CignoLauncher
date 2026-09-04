from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication, QComboBox, QFrame, QListWidget, QListWidgetItem, QVBoxLayout


class MaterialComboBox(QComboBox):
    """Combo box with a compact popup anchored below the field."""

    POPUP_HEIGHT = 220
    MAX_VISIBLE_ITEMS = 8

    def __init__(self, parent=None, fit_popup_to_field=False, popup_row_height=28):
        super().__init__(parent)
        self.fit_popup_to_field = fit_popup_to_field
        self.popup_row_height = popup_row_height
        self.popup = None
        self.popup_list = None
        self.setMinimumHeight(32)
        self.setMaxVisibleItems(self.MAX_VISIBLE_ITEMS)

    def wheelEvent(self, event):
        event.ignore()

    def showPopup(self):
        if self.popup is not None:
            self.hidePopup()

        if self.popup is None:
            popup = QFrame(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            popup.setObjectName("MaterialComboPopup")
            popup.destroyed.connect(self._popup_destroyed)
            layout = QVBoxLayout(popup)
            layout.setContentsMargins(1, 1, 1, 1)
            self.popup_list = QListWidget(popup)
            self.popup_list.setObjectName("MaterialComboPopupList")
            self.popup_list.setUniformItemSizes(True)
            self.popup_list.setIconSize(QSize(20, 20))
            self.popup_list.setTextElideMode(Qt.TextElideMode.ElideRight)
            self.popup_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.popup_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.popup_list.setAutoScroll(False)
            self.popup_list.itemClicked.connect(self._popup_item_clicked)
            layout.addWidget(self.popup_list)
            popup.setStyleSheet(self._popup_stylesheet())
            self.popup = popup
        else:
            popup = self.popup
        self.popup_list.clear()
        for index in range(self.count()):
            item = QListWidgetItem(self.itemIcon(index), self.itemText(index))
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.popup_list.addItem(item)
        self.popup_list.setCurrentRow(self.currentIndex())

        row_height = max(self.popup_list.sizeHintForRow(0), self.popup_row_height)
        visible_rows = min(max(self.count(), 1), self.MAX_VISIBLE_ITEMS)
        popup_height = min(self.POPUP_HEIGHT, visible_rows * row_height + 2)
        if self.fit_popup_to_field:
            popup_width = self.width()
        else:
            popup_width = max(self.width(), min(self.width() + 120, 360))

        global_below = self.mapToGlobal(QPoint(0, self.height()))
        screen = QApplication.screenAt(global_below)
        if screen is None:
            popup.setFixedSize(popup_width, popup_height)
            popup.move(global_below)
            popup.show()
            return
        bounds = screen.availableGeometry()
        popup_height = min(popup_height, max(1, bounds.bottom() - global_below.y()))
        popup_x = min(max(bounds.left(), global_below.x()), bounds.right() - popup_width)
        popup_position = QPoint(popup_x, global_below.y())
        popup.setFixedSize(popup_width, popup_height)
        popup.move(popup_position)
        popup.show()

    def _popup_item_clicked(self, item):
        index = item.data(Qt.ItemDataRole.UserRole)
        self.hidePopup()
        self.setCurrentIndex(index)

    def hidePopup(self):
        popup = self.popup
        if popup is not None and not sip.isdeleted(popup):
            popup.hide()
        elif popup is not None:
            self.popup = None

    def _popup_destroyed(self):
        self.popup = None

    @staticmethod
    def _popup_stylesheet():
        return """
            QFrame#MaterialComboPopup {
                background: #1f232d;
                color: #f4f7fb;
                border: 1px solid #4a5a72;
                border-radius: 7px;
                padding: 4px;
            }
            QListWidget#MaterialComboPopupList {
                background: #1f232d;
                color: #f4f7fb;
                border: none;
                outline: none;
                padding: 3px;
            }
            QListWidget#MaterialComboPopupList::item {
                min-height: 28px;
                padding: 5px 8px;
                border-radius: 4px;
            }
            QListWidget#MaterialComboPopupList::item:hover {
                background: #2e405c;
            }
            QListWidget#MaterialComboPopupList::item:selected {
                background: #3578e5;
                color: white;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 3px 1px 3px 0;
            }
            QScrollBar::handle:vertical {
                background: #64748b;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """
