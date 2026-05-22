"""Overlay chỉ hiển thị văn bản nhận giọng — chữ lớn, chạy theo khi nói."""

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QFrame,
    QPushButton, QHBoxLayout, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

from overlay_window import ResizeHandle
import time
import os

try:
    from AppKit import NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorStationary
    import objc
    from ctypes import c_void_p
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class LargeTextOverlayWindow(QWidget):
    """Cửa sổ phụ đề chữ to — transcript cập nhật theo giọng nói."""

    stop_requested = pyqtSignal()

    def __init__(self, window_width=900, font_size=32, keep_lines=30):
        super().__init__()
        self.window_width = window_width
        self.font_size = font_size
        self.keep_lines = keep_lines
        self.chunk_text = {}
        self._last_chunk_id = None
        self._committed_ids = set()

        screen = QApplication.primaryScreen().availableGeometry()
        self.window_height = int(screen.height() * 0.85)

        self.initUI()
        self.oldPos = self.pos()

    def showEvent(self, event):
        super().showEvent(event)
        if HAS_APPKIT:
            self._set_all_spaces()

    def _set_all_spaces(self):
        try:
            win_id = int(self.winId())
            ns_view = objc.objc_object(c_void_p=c_void_p(win_id))
            ns_window = ns_view.window()
            ns_window.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
            )
        except Exception:
            pass

    def initUI(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.setLayout(layout)

        panel = QFrame()
        panel.setStyleSheet("background-color: rgba(0, 0, 0, 200); border-radius: 10px;")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 6)
        panel_layout.setSpacing(6)

        title = QLabel("🎤 Đang nghe (tiếng Anh)")
        title.setStyleSheet("color: #89b4fa; font-size: 13px; font-weight: bold; margin: 0;")
        panel_layout.addWidget(title)

        hist_title = QLabel("Lịch sử")
        hist_title.setStyleSheet("color: #6c7086; font-size: 11px; margin: 0;")
        panel_layout.addWidget(hist_title)

        self.history = QTextEdit()
        self.history.setReadOnly(True)
        hist_font = QFont()
        hist_font.setPointSize(max(13, self.font_size - 14))
        self.history.setFont(hist_font)
        self.history.setStyleSheet(
            "QTextEdit { color: #a6adc8; background: rgba(30,30,46,160); "
            "border: none; border-radius: 6px; padding: 4px 6px; }"
        )
        self.history.setMinimumHeight(200)
        panel_layout.addWidget(self.history, stretch=3)

        live_title = QLabel("Đang nói")
        live_title.setStyleSheet("color: #6c7086; font-size: 11px; margin: 0;")
        panel_layout.addWidget(live_title)

        self.live_label = QLabel("…")
        self.live_label.setWordWrap(True)
        self.live_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        live_font = QFont()
        live_font.setPointSize(self.font_size)
        live_font.setBold(True)
        self.live_label.setFont(live_font)
        self.live_label.setStyleSheet(
            "color: #ffffff; background: rgba(49,50,68,200); "
            "border-radius: 6px; padding: 6px 8px; margin: 0;"
        )
        self.live_label.setMinimumHeight(48)
        panel_layout.addWidget(self.live_label, stretch=2)

        layout.addWidget(panel, stretch=1)

        bar = QHBoxLayout()
        self.save_btn = QPushButton("💾 Lưu")
        self.save_btn.setFixedWidth(80)
        self.save_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,60); color: white; "
            "border-radius: 6px; padding: 6px; }"
            "QPushButton:hover { background: rgba(255,255,255,120); }"
        )
        self.save_btn.clicked.connect(self._save_transcript)
        bar.addWidget(self.save_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setToolTip("Dừng")
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setStyleSheet(
            "QPushButton { background: rgba(243,139,168,180); color: white; "
            "border-radius: 16px; font-size: 14px; border: none; }"
        )
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        bar.addWidget(self.stop_btn)
        bar.addStretch()
        bar.addWidget(ResizeHandle(self))
        layout.addLayout(bar)

        self.resize(self.window_width, self.window_height)
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.window_width) // 2
        y = screen.y() + 40
        self.move(x, y)
        self.setMouseTracking(True)
        self.is_moving = False

    def _commit_chunk(self, chunk_id):
        if chunk_id in self._committed_ids or chunk_id not in self.chunk_text:
            return
        text = self.chunk_text[chunk_id].strip()
        if not text:
            return
        self._committed_ids.add(chunk_id)
        ts = time.strftime("%H:%M:%S")
        self.history.append(
            f"<p style='margin:2px 0;line-height:1.3'>"
            f"<span style='color:#6c7086'>[{ts}]</span> {text}</p>"
        )
        self._trim_body()
        sb = self.history.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _trim_body(self):
        doc = self.history.document()
        if doc.blockCount() <= self.keep_lines * 2:
            return
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        for _ in range(doc.blockCount() - self.keep_lines):
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def update_text(self, chunk_id, original_text, translated_text=""):
        if not original_text or not original_text.strip():
            return

        text = original_text.strip()

        if self._last_chunk_id is not None and chunk_id != self._last_chunk_id:
            self._commit_chunk(self._last_chunk_id)

        self.chunk_text[chunk_id] = text
        self._last_chunk_id = chunk_id
        self.live_label.setText(text)

    def _save_transcript(self):
        if self._last_chunk_id is not None:
            self._commit_chunk(self._last_chunk_id)
        if not self.chunk_text:
            return
        os.makedirs("transcripts", exist_ok=True)
        path = f"transcripts/voice_text_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        lines = [self.chunk_text[k] for k in sorted(self.chunk_text.keys())]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Nhận giọng — lưu lúc {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                for line in lines:
                    f.write(line + "\n")
            orig = self.save_btn.text()
            self.save_btn.setText("Đã lưu!")
            QTimer.singleShot(2000, lambda: self.save_btn.setText(orig))
        except Exception as e:
            print(f"[LargeText] Lỗi lưu: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_moving = True
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.is_moving:
            delta = event.globalPosition().toPoint() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.is_moving = False

    def closeEvent(self, event):
        if self._last_chunk_id is not None:
            self._commit_chunk(self._last_chunk_id)
        super().closeEvent(event)
