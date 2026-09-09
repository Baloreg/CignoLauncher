from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMainWindow, QDialog, QWizard, QGraphicsDropShadowEffect, QApplication
from PyQt6.QtCore import Qt, QPoint, QSize, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QColor

class CustomTitleBar(QWidget):
    def __init__(self, parent_window, title="CignoLauncher", icon=None, show_maximize=True):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.dragging = False
        self.drag_position = QPoint()
        self.show_maximize = show_maximize

        self.setFixedHeight(36)
        self.setObjectName("CustomTitleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)

        # Calculate right buttons total width for perfect symmetry
        # (minimize 32px + maximize 32px + close 32px + spacings 3*4px = 108px)
        right_buttons_width = 108 if self.show_maximize else 72

        left_dummy = QWidget()
        left_dummy.setFixedWidth(right_buttons_width)
        layout.addWidget(left_dummy)

        center_widget = QWidget()
        center_widget.setObjectName("TitleCenterWidget")
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Window Icon
        self.icon_label = QLabel()
        if icon and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(QSize(18, 18)))
        center_layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        center_layout.addWidget(self.title_label)

        layout.addWidget(center_widget, 1)

        right_widget = QWidget()
        right_widget.setObjectName("TitleRightWidget")
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Minimize Button
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("TitleBarButton")
        self.min_btn.setToolTip("Minimizza")
        self.min_btn.clicked.connect(self.on_minimize)
        right_layout.addWidget(self.min_btn)

        # Maximize Button
        if self.show_maximize:
            self.max_btn = QPushButton("🗖")
            self.max_btn.setObjectName("TitleBarButton")
            self.max_btn.setToolTip("Massimizza")
            self.max_btn.clicked.connect(self.on_maximize_restore)
            right_layout.addWidget(self.max_btn)
        else:
            self.max_btn = None

        # Close Button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("TitleBarCloseButton")
        self.close_btn.setToolTip("Chiudi")
        self.close_btn.clicked.connect(self.on_close)
        right_layout.addWidget(self.close_btn)

        layout.addWidget(right_widget)

        self.setStyleSheet("""
            QWidget#CustomTitleBar {
                background: transparent;
                border: none;
            }
            QLabel#TitleLabel {
                color: #f8fafc;
                font-weight: 600;
                font-size: 9.5pt;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton#TitleBarButton, QPushButton#TitleBarCloseButton {
                background-color: transparent;
                border: none;
                color: #94a3b8;
                font-size: 10pt;
                min-width: 32px;
                min-height: 32px;
                max-width: 32px;
                max-height: 32px;
                border-radius: 4px;
            }
            QPushButton#TitleBarButton:hover {
                background-color: #273244;
                color: #f8fafc;
            }
            QPushButton#TitleBarCloseButton:hover {
                background-color: #e81123;
                color: white;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.parent_window:
                local_pos = self.parent_window.mapFromGlobal(event.globalPosition().toPoint())
                edge = self.parent_window.get_resize_edge(local_pos)
                if edge:
                    self.parent_window.resizing_edge = edge
                    self.parent_window.drag_pos = event.globalPosition().toPoint()
                    self.parent_window.window_geom = self.parent_window.geometry()
                    event.accept()
                    return

                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and self.parent_window:
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.max_btn:
            self.on_maximize_restore()

    def on_minimize(self):
        if self.parent_window:
            self.parent_window.showMinimized()

    def on_maximize_restore(self):
        if self.parent_window and self.max_btn:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.max_btn.setText("🗖")
            else:
                self.parent_window.showMaximized()
                self.max_btn.setText("🗗")

    def on_close(self):
        if self.parent_window:
            self.parent_window.close()


class CustomWindowMixin:
    """Mixin per aggiungere cornice personalizzata e title bar alle finestre PyQt."""
    BORDER_MARGIN = 6
    TOP = 1
    BOTTOM = 2
    LEFT = 4
    RIGHT = 8

    def init_custom_frame(self, title="CignoLauncher", icon=None, show_maximize=True):
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)

        app = QApplication.instance()
        if app:
            app.installEventFilter(self)

        # Outer container with border and rounded corners
        self.outer_widget = QWidget(self)
        self.outer_widget.setObjectName("OuterContainer")
        self.outer_widget.setMouseTracking(True)
        self.outer_widget.setStyleSheet("""
            QWidget#OuterContainer {
                background-color: #141922;
                border: 1px solid #273244;
                border-radius: 8px;
            }
        """)
        
        self.outer_layout = QVBoxLayout(self.outer_widget)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(self, title=title, icon=icon, show_maximize=show_maximize)
        self.outer_layout.addWidget(self.title_bar)

        # Content container
        self.content_container = QWidget()
        self.content_container.setObjectName("ContentContainer")
        self.content_container.setMouseTracking(True)
        self.content_container.setStyleSheet("""
            QWidget#ContentContainer {
                background: transparent;
                border: none;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.outer_layout.addWidget(self.content_container)

        if isinstance(self, QMainWindow):
            QMainWindow.setCentralWidget(self, self.outer_widget)
        else:
            base_layout = QVBoxLayout(self)
            base_layout.setContentsMargins(0, 0, 0, 0)
            base_layout.addWidget(self.outer_widget)

        self.set_styled_background_recursive(self)

        self.resizing_edge = None
        self.drag_pos = QPoint()
        self.window_geom = None

    def set_styled_background_recursive(self, widget):
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        for child in widget.findChildren(QWidget):
            child.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def eventFilter(self, obj, event):
        if not isinstance(obj, QWidget) or obj.window() != self:
            return False

        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
                local_pos = self.mapFromGlobal(global_pos)
                edge = self.get_resize_edge(local_pos)
                if edge:
                    self.resizing_edge = edge
                    self.drag_pos = global_pos
                    self.window_geom = self.geometry()
                    return True
        elif event.type() == QEvent.Type.MouseMove:
            global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
            if self.resizing_edge and not self.isMaximized():
                diff = global_pos - self.drag_pos
                geom = self.window_geom
                x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
                min_w, min_h = self.minimumWidth(), self.minimumHeight()

                dx, dy = diff.x(), diff.y()

                if self.resizing_edge & self.LEFT:
                    new_w = max(min_w, w - dx)
                    if new_w > min_w:
                        x += dx
                        w = new_w
                if self.resizing_edge & self.RIGHT:
                    w = max(min_w, w + dx)
                if self.resizing_edge & self.TOP:
                    new_h = max(min_h, h - dy)
                    if new_h > min_h:
                        y += dy
                        h = new_h
                if self.resizing_edge & self.BOTTOM:
                    h = max(min_h, h + dy)

                self.setGeometry(x, y, w, h)
                return True

            local_pos = self.mapFromGlobal(global_pos)
            edge = self.get_resize_edge(local_pos)
            if edge:
                self.update_cursor_shape(local_pos)
                return True
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if self.resizing_edge:
                self.resizing_edge = None
                self.setCursor(Qt.CursorShape.ArrowCursor)

        return super().eventFilter(obj, event) if hasattr(super(), 'eventFilter') else False

    def get_resize_edge(self, pos):
        if self.isMaximized():
            return 0
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self.BORDER_MARGIN

        left = x < m
        right = x >= w - m
        top = y < m
        bottom = y >= h - m

        edge = 0
        if top: edge |= self.TOP
        if bottom: edge |= self.BOTTOM
        if left: edge |= self.LEFT
        if right: edge |= self.RIGHT
        return edge

    def update_cursor_shape(self, pos):
        if self.isMaximized():
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        edge = self.get_resize_edge(pos)
        if not edge:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if (edge == (self.TOP | self.LEFT)) or (edge == (self.BOTTOM | self.RIGHT)):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (edge == (self.TOP | self.RIGHT)) or (edge == (self.BOTTOM | self.LEFT)):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif (edge & self.TOP) or (edge & self.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif (edge & self.LEFT) or (edge & self.RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'title_label'):
            self.title_bar.title_label.setText(title)

    def setWindowIcon(self, icon):
        super().setWindowIcon(icon)
        if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'icon_label') and icon:
            self.title_bar.icon_label.setPixmap(icon.pixmap(QSize(18, 18)))
