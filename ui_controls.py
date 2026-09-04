from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QMenu,
)


class MaterialComboBox(QComboBox):
    """Combo box with a compact popup anchored below the field."""

    POPUP_HEIGHT = 220
    MAX_VISIBLE_ITEMS = 8

    def __init__(self, parent=None, fit_popup_to_field=False):
        super().__init__(parent)
        self.fit_popup_to_field = fit_popup_to_field
        self.popup_menu = None
        self.setMinimumHeight(32)
        self.setMaxVisibleItems(self.MAX_VISIBLE_ITEMS)

    def wheelEvent(self, event):
        event.ignore()

    def showPopup(self):
        if self.popup_menu is not None:
            self.hidePopup()

        popup = QMenu(self)
        popup.setObjectName("MaterialComboPopup")
        popup.setStyleSheet(self._popup_stylesheet())
        for index in range(self.count()):
            action = popup.addAction(self.itemText(index))
            action.setData(index)
            action.setCheckable(True)
            action.setChecked(index == self.currentIndex())
        popup.triggered.connect(self._menu_action_triggered)
        self.popup_menu = popup

        row_height = 30
        visible_rows = min(max(self.count(), 1), self.MAX_VISIBLE_ITEMS)
        popup_height = min(self.POPUP_HEIGHT, visible_rows * row_height + 2)
        if self.fit_popup_to_field:
            popup_width = self.width()
        else:
            popup_width = max(self.width(), min(self.width() + 120, 360))
        popup.setFixedWidth(popup_width)
        popup.setMaximumHeight(popup_height)

        global_below = self.mapToGlobal(QPoint(0, self.height()))
        screen = QApplication.screenAt(global_below)
        if screen is None:
            popup.move(global_below)
            popup.popup(global_below)
            return
        bounds = screen.availableGeometry()
        popup_x = min(global_below.x(), bounds.right() - popup_width)
        popup_y = min(global_below.y(), bounds.bottom() - popup_height)
        popup.move(max(bounds.left(), popup_x), max(bounds.top(), popup_y))
        popup.popup(QPoint(max(bounds.left(), popup_x), max(bounds.top(), popup_y)))

    def _menu_action_triggered(self, action):
        index = action.data()
        self.hidePopup()
        self.setCurrentIndex(index)

    def hidePopup(self):
        if self.popup_menu is not None:
            self.popup_menu.hide()
            self.popup_menu = None

    @staticmethod
    def _popup_stylesheet():
        return """
            QMenu#MaterialComboPopup {
                background: #1f232d;
                color: #f4f7fb;
                border: 1px solid #4a5a72;
                border-radius: 7px;
                padding: 4px;
            }
            QMenu#MaterialComboPopup::item {
                min-height: 28px;
                padding: 5px 8px;
                border-radius: 4px;
            }
            QMenu#MaterialComboPopup::item:selected {
                background: #2e405c;
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
