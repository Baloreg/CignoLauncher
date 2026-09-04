from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QListView


class NoWheelListView(QListView):
    def wheelEvent(self, event):
        event.ignore()


class MaterialComboBox(QComboBox):
    """Combo box with a compact popup anchored below the field."""

    POPUP_HEIGHT = 220
    MAX_VISIBLE_ITEMS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(32)
        self.setMaxVisibleItems(self.MAX_VISIBLE_ITEMS)
        view = NoWheelListView()
        view.setUniformItemSizes(True)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setView(view)

    def wheelEvent(self, event):
        event.ignore()

    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        row_height = max(self.view().sizeHintForRow(0), 28)
        visible_rows = min(max(self.count(), 1), self.MAX_VISIBLE_ITEMS)
        popup_height = min(self.POPUP_HEIGHT, visible_rows * row_height + 4)
        popup_width = max(self.width(), self.view().sizeHintForColumn(0) + 28)
        popup.setFixedSize(popup_width, popup_height)

        global_below = self.mapToGlobal(QPoint(0, self.height()))
        screen = QApplication.screenAt(global_below)
        if screen is None:
            popup.move(global_below)
            return
        bounds = screen.availableGeometry()
        popup_x = min(global_below.x(), bounds.right() - popup_width)
        popup_y = min(global_below.y(), bounds.bottom() - popup_height)
        popup.move(max(bounds.left(), popup_x), max(bounds.top(), popup_y))
