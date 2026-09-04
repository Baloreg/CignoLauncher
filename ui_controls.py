from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class MaterialComboBox(QComboBox):
    """Combo box with a compact popup anchored below the field."""

    POPUP_HEIGHT = 220
    MAX_VISIBLE_ITEMS = 8

    def __init__(self, parent=None, fit_popup_to_field=False):
        super().__init__(parent)
        self.fit_popup_to_field = fit_popup_to_field
        self.popup = None
        self.setMinimumHeight(32)
        self.setMaxVisibleItems(self.MAX_VISIBLE_ITEMS)

    def wheelEvent(self, event):
        event.ignore()

    def showPopup(self):
        if self.popup is not None:
            self.hidePopup()

        popup = QFrame(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setObjectName("MaterialComboPopup")
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        list_widget = QListWidget(popup)
        list_widget.setObjectName("MaterialComboPopupList")
        list_widget.setUniformItemSizes(True)
        list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_widget.setAutoScroll(False)
        for index in range(self.count()):
            item = QListWidgetItem(self.itemText(index))
            item.setData(Qt.ItemDataRole.UserRole, index)
            list_widget.addItem(item)
        list_widget.setCurrentRow(self.currentIndex())
        list_widget.itemClicked.connect(self._popup_item_clicked)
        layout.addWidget(list_widget)
        popup.setStyleSheet(self._popup_stylesheet())
        self.popup = popup

        row_height = max(list_widget.sizeHintForRow(0), 28)
        visible_rows = min(max(self.count(), 1), self.MAX_VISIBLE_ITEMS)
        popup_height = min(self.POPUP_HEIGHT, visible_rows * row_height + 2)
        if self.fit_popup_to_field:
            popup_width = self.width()
        else:
            popup_width = max(self.width(), list_widget.sizeHintForColumn(0) + 28)
        popup.setFixedSize(popup_width, popup_height)

        global_below = self.mapToGlobal(QPoint(0, self.height()))
        screen = QApplication.screenAt(global_below)
        if screen is None:
            popup.move(global_below)
            popup.show()
            return
        bounds = screen.availableGeometry()
        popup_x = min(global_below.x(), bounds.right() - popup_width)
        popup_y = min(global_below.y(), bounds.bottom() - popup_height)
        popup.move(max(bounds.left(), popup_x), max(bounds.top(), popup_y))
        popup.show()

    def _popup_item_clicked(self, item):
        self.setCurrentIndex(item.data(Qt.ItemDataRole.UserRole))
        self.hidePopup()

    def hidePopup(self):
        if self.popup is not None:
            popup = self.popup
            self.popup = None
            popup.close()

    @staticmethod
    def _popup_stylesheet():
        return """
            QFrame#MaterialComboPopup {
                background: #1f232d;
                border: 1px solid #4a5a72;
                border-radius: 7px;
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
