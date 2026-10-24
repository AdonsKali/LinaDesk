import os
from typing import Optional

from PySide6.QtCore import Qt, QFile
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class SplashScreen(QWidget):
    """
    Загрузочный экран приложения.

    Отвечает только за отображение состояния загрузки.
    Не содержит бизнес-логики и не управляет потоками.
    """

    WIDTH = 600
    HEIGHT = 400
    BOTTOM_HEIGHT = 90

    def __init__(
        self,
        background_image: Optional[str] = None,
        version: str = "v1.0.0",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._background_image = background_image
        self._version = version

        self._setup_window()
        self._setup_ui()

    # ============================================================
    # Setup
    # ============================================================

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowTitle("Lina AI")

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._main_frame = QFrame()
        self._main_frame.setObjectName("main_frame")
        self._main_frame.setFixedSize(
            self.WIDTH,
            self.HEIGHT,
        )

        root_layout.addWidget(self._main_frame)

        self._setup_main_frame()

    def _setup_main_frame(self) -> None:
        layout = QVBoxLayout(self._main_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._setup_art(layout)
        self._setup_bottom(layout)

    # ============================================================
    # Art
    # ============================================================

    def _setup_art(self, parent_layout: QVBoxLayout) -> None:
        art_height = self.HEIGHT - self.BOTTOM_HEIGHT

        self._art_frame = QFrame()
        self._art_frame.setObjectName("art_frame")
        self._art_frame.setFixedSize(
            self.WIDTH,
            art_height,
        )

        parent_layout.addWidget(self._art_frame)

        self._setup_art_background()

    def _setup_art_background(self) -> None:
        if not self._background_image:
            self._setup_gradient_background()
            return

        if not os.path.exists(self._background_image):
            self._setup_gradient_background()
            return

        pixmap = QPixmap(self._background_image)

        if pixmap.isNull():
            self._setup_gradient_background()
            return

        art_height = self.HEIGHT - self.BOTTOM_HEIGHT

        self._art_label = QLabel(self._art_frame)
        self._art_label.setGeometry(
            0,
            0,
            self.WIDTH,
            art_height,
        )

        self._art_label.setPixmap(
            self._scale_and_crop(
                pixmap,
                self.WIDTH,
                art_height,
            )
        )

        self._art_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._art_label.lower()

        # Затемнение поверх изображения
        self._art_overlay = QFrame(self._art_frame)
        self._art_overlay.setGeometry(
            0,
            0,
            self.WIDTH,
            art_height,
        )

        self._art_overlay.setStyleSheet(
            """
            QFrame {
                background: rgba(0, 0, 0, 45);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
            """
        )

        self._art_overlay.raise_()

    def _setup_gradient_background(self) -> None:
        self._art_frame.setStyleSheet(
            """
            QFrame#art_frame {
                background: qlineargradient(
                    x1:0,
                    y1:0,
                    x2:1,
                    y2:1,
                    stop:0 #1a1a2e,
                    stop:0.5 #16213e,
                    stop:1 #0f3460
                );

                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
            }
            """
        )

    @staticmethod
    def _scale_and_crop(
        pixmap: QPixmap,
        width: int,
        height: int,
    ) -> QPixmap:
        """
        Масштабирование изображения в режиме Cover.
        Сохраняет пропорции и обрезает лишнее.
        """

        scaled = pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        x = max(0, (scaled.width() - width) // 2)
        y = max(0, (scaled.height() - height) // 2)

        return scaled.copy(
            x,
            y,
            width,
            height,
        )

    # ============================================================
    # Bottom section
    # ============================================================

    def _setup_bottom(self, parent_layout: QVBoxLayout) -> None:
        self._bottom_frame = QFrame()
        self._bottom_frame.setObjectName("bottom_frame")
        self._bottom_frame.setFixedSize(
            self.WIDTH,
            self.BOTTOM_HEIGHT,
        )

        self._bottom_frame.setStyleSheet(
            """
            QFrame#bottom_frame {
                background: #20293b;

                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;

                border-top: 1px solid rgba(255,255,255,0.05);
            }
            """
        )

        parent_layout.addWidget(self._bottom_frame)

        layout = QVBoxLayout(self._bottom_frame)
        layout.setContentsMargins(
            25,
            12,
            25,
            15,
        )
        layout.setSpacing(8)

        self._setup_status_row(layout)
        self._setup_progress_bar(layout)
        self._setup_version_row(layout)

    # ============================================================
    # Status
    # ============================================================

    def _setup_status_row(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self._status_label = QLabel("Initializing...")
        self._status_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255,255,255,0.7);
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                background: transparent;
            }
            """
        )

        layout.addWidget(self._status_label)
        layout.addStretch()

        self._percent_label = QLabel("0%")
        self._percent_label.setMinimumWidth(40)
        self._percent_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self._percent_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255,255,255,0.7);
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                background: transparent;
            }
            """
        )

        layout.addWidget(self._percent_label)

        parent_layout.addLayout(layout)

    # ============================================================
    # Progress
    # ============================================================

    def _setup_progress_bar(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        self._progress_bar = QProgressBar()

        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)

        self._progress_bar.setStyleSheet(
            """
            QProgressBar {
                background: rgba(255,255,255,0.08);
                border: none;
                border-radius: 4px;
                height: 6px;
            }

            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0,
                    y1:0,
                    x2:1,
                    y2:0,
                    stop:0 #6c8cff,
                    stop:1 #ff6b9d
                );

                border-radius: 4px;
            }
            """
        )

        parent_layout.addWidget(self._progress_bar)

    # ============================================================
    # Version
    # ============================================================

    def _setup_version_row(
        self,
        parent_layout: QVBoxLayout,
    ) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._version_label = QLabel(self._version)
        self._version_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255,255,255,0.45);
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
                font-weight: 500;
            }
            """
        )

        layout.addWidget(self._version_label)
        layout.addStretch()

        self._author_label = QLabel(
            "Lina AI (by AdonsKali)"
        )

        self._author_label.setStyleSheet(
            """
            QLabel {
                color: rgba(255,255,255,0.45);
                font-size: 11px;
                font-family: 'Segoe UI', Arial, sans-serif;
                background: transparent;
                font-weight: 600;
            }
            """
        )

        layout.addWidget(self._author_label)

        parent_layout.addLayout(layout)

    # ============================================================
    # Public API
    # ============================================================

    def set_progress(self, value: int) -> None:
        """Установить прогресс от 0 до 100."""

        value = max(0, min(100, value))

        self._progress_bar.setValue(value)
        self._percent_label.setText(f"{value}%")

    def set_status(self, status: str) -> None:
        """Установить текущий статус загрузки."""

        self._status_label.setText(status)

    def set_progress_and_status(
        self,
        value: int,
        status: str,
    ) -> None:
        """Одновременно обновить прогресс и статус."""

        self.set_progress(value)
        self.set_status(status)

    def set_version(self, version: str) -> None:
        """Установить версию приложения."""

        self._version_label.setText(version)

    def finish(self) -> None:
        """Показать состояние завершения загрузки."""

        self.set_progress_and_status(
            100,
            "Ready!",
        )

    def close_splash(self) -> None:
        """Закрыть splash."""

        self.close()

    # ============================================================
    # Window positioning
    # ============================================================

    def show_centered(self) -> None:
        """Показать splash по центру основного экрана."""

        screen = self.screen()

        if screen is None:
            screen = self.windowHandle().screen() if self.windowHandle() else None

        if screen is None:
            self.show()
            return

        geometry = screen.availableGeometry()

        x = (
            geometry.x()
            + (geometry.width() - self.width()) // 2
        )

        y = (
            geometry.y()
            + (geometry.height() - self.height()) // 2
        )

        self.move(x, y)
        self.show()

    # ============================================================
    # Painting
    # ============================================================

    def paintEvent(self, event) -> None:
        """
        Рисует внешнюю рамку с закругленными углами.
        """

        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        path = QPainterPath()
        path.addRoundedRect(
            self.rect(),
            20,
            20,
        )

        painter.setClipPath(path)

        painter.fillRect(
            self.rect(),
            QColor(0, 0, 0, 0),
        )

        painter.setPen(
            QColor(255, 255, 255, 25)
        )

        painter.drawPath(path)