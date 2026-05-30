from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit,
    QTabWidget, QSpinBox, QDoubleSpinBox, QGridLayout,
    QFormLayout, QApplication, QMessageBox, QTextEdit, QDialog,
    QGroupBox, QCheckBox,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon, QColor
import sys
import sounddevice as sd
from config import config

# Modern QSS Styles
STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Helvetica Neue', 'PingFang SC', 'Arial', sans-serif;
}
QTabWidget::pane {
    border: 1px solid #313244;
    background: #1e1e2e;
    border-radius: 8px;
}
QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}
QLabel {
    font-size: 14px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px;
    color: #cdd6f4;
    selection-background-color: #585b70;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton#StopButton {
    background-color: #f38ba8;
}
QPushButton#StopButton:hover {
    background-color: #eba0ac;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #fab387;
}
"""

class Dashboard(QWidget):
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def closeEvent(self, event):
        """Ensure total program quit when dashboard is closed"""
        self.status_label.setText("Đang dừng...")
        self.on_stop()
        # Force application exit
        QApplication.quit()
        event.accept()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nhận giọng — Bảng điều khiển")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(STYLESHEET)
        
        # Main Layout
        self.layout = QVBoxLayout()
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.layout)
        
        # Header
        header = QLabel("🎙️ Nhận giọng → chữ")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        self.layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        self.init_home_tab()
        self.init_audio_tab()
        self.init_device_manager_tab()
        self.init_transcription_tab()
        self.init_cloud_tab()
        
        # Footer Actions
        footer = QHBoxLayout()
        self.save_btn = QPushButton("Lưu cấu hình")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setStyleSheet("""
            background-color: #a6e3a1; color: #1e1e2e;
        """)
        footer.addStretch()
        footer.addWidget(self.save_btn)
        self.layout.addLayout(footer)

    def init_home_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setStyleSheet("font-size: 18px; color: #a6e3a1;")
        layout.addWidget(self.status_label)
        
        self.start_btn = QPushButton("▶ Bắt đầu")
        self.start_btn.setFixedSize(260, 56)
        self.start_btn.setStyleSheet("font-size: 16px; background-color: #a6e3a1; color: #1e1e2e; border-radius: 10px;")
        self.start_btn.clicked.connect(self.on_start)

        self.stop_btn = QPushButton("⏹ Dừng")
        self.stop_btn.setFixedSize(260, 56)
        self.stop_btn.setStyleSheet("font-size: 16px; background-color: #f38ba8; border-radius: 10px;")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.hide()

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.mode_hint = QLabel()
        self.mode_hint.setTextFormat(Qt.TextFormat.RichText)
        self.mode_hint.setWordWrap(True)
        self.mode_hint.setStyleSheet(
            "color: #6c7086; font-size: 13px; padding: 8px; "
            "background: #313244; border-radius: 8px;"
        )
        self._update_mode_hint()
        layout.addWidget(self.mode_hint)

        quick = QHBoxLayout()
        btn_local = QPushButton("🖥 Local Whisper")
        btn_local.setToolTip("Tab «Nhận giọng» → whisper / mlx")
        btn_local.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        btn_cloud = QPushButton("☁️ Cloud API")
        btn_cloud.setToolTip("Tab «Cloud API» → OpenAI hoặc Gemini")
        btn_cloud.clicked.connect(lambda: self.tabs.setCurrentIndex(4))
        quick.addWidget(btn_local)
        quick.addWidget(btn_cloud)
        layout.addLayout(quick)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🏠 Trang chủ")

    def init_audio_tab(self):
        tab = QWidget()
        layout = QGridLayout() # Use Grid for organized form
        layout.setSpacing(15)
        
        # Device Selection
        bh_hint = QLabel(
            "⚠️ Bắt tiếng YouTube/Zoom: đặt <b>Đầu ra macOS</b> = «Thiết bị Nhiều Đầu ra» "
            "(không chỉ Loa MacBook). Thiết bị vào ở đây = <b>BlackHole 2ch</b>."
        )
        bh_hint.setWordWrap(True)
        bh_hint.setStyleSheet("color: #fab387; font-size: 12px; padding: 4px 0;")
        layout.addWidget(bh_hint, 0, 0, 1, 3)

        layout.addWidget(QLabel("Thiết bị vào:"), 1, 0)
        self.device_combo = QComboBox()
        self.populate_devices()
        layout.addWidget(self.device_combo, 1, 1)
        
        # Refresh Button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(40)
        refresh_btn.clicked.connect(self.populate_devices)
        layout.addWidget(refresh_btn, 1, 2)
        
        # Sample Rate
        layout.addWidget(QLabel("Tần số lấy mẫu:"), 2, 0)
        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(8000, 48000)
        self.sample_rate.setValue(config.sample_rate)
        layout.addWidget(self.sample_rate, 2, 1)

        # Silence Threshold
        layout.addWidget(QLabel("Ngưỡng im lặng:"), 3, 0)
        self.silence_thresh = QDoubleSpinBox()
        self.silence_thresh.setRange(0.001, 1.0)
        self.silence_thresh.setSingleStep(0.001)
        self.silence_thresh.setDecimals(3)
        self.silence_thresh.setValue(config.silence_threshold)
        layout.addWidget(self.silence_thresh, 3, 1)
        
        layout.addWidget(QLabel("Thời gian im lặng (giây):"), 4, 0)
        self.silence_dur = QDoubleSpinBox()
        self.silence_dur.setValue(config.silence_duration)
        layout.addWidget(self.silence_dur, 4, 1)
        
        layout.setRowStretch(5, 1) # Push to top
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🎤 Âm thanh")

    def init_device_manager_tab(self):
        """Audio Device Manager - Create/Manage Multi-Output Devices"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header
        header = QLabel("Quản lý thiết bị âm thanh")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #fab387;")
        layout.addWidget(header)
        
        info = QLabel("Tạo thiết bị Multi-Output để vừa bắt âm hệ thống vừa nghe qua loa")
        info.setStyleSheet("color: #6c7086; font-size: 12px; font-style: italic;")
        layout.addWidget(info)
        
        # Available Devices List
        devices_label = QLabel("Thiết bị ra (loa):")
        layout.addWidget(devices_label)
        
        self.output_devices_list = QComboBox()
        self.output_devices_list.setMinimumHeight(30)
        layout.addWidget(self.output_devices_list)
        
        # Virtual Device List
        virtual_label = QLabel("Thiết bị ảo / BlackHole:")
        layout.addWidget(virtual_label)
        
        self.virtual_devices_list = QComboBox()
        self.virtual_devices_list.setMinimumHeight(30)
        layout.addWidget(self.virtual_devices_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.refresh_devices_btn = QPushButton("🔄 Làm mới danh sách")
        self.refresh_devices_btn.clicked.connect(self.refresh_audio_devices)
        btn_layout.addWidget(self.refresh_devices_btn)
        
        self.create_multi_output_btn = QPushButton("➕ Tạo Multi-Output")
        self.create_multi_output_btn.setStyleSheet("""
            background-color: #a6e3a1; color: #1e1e2e; font-weight: bold;
        """)
        self.create_multi_output_btn.clicked.connect(self.create_multi_output_device)
        btn_layout.addWidget(self.create_multi_output_btn)
        
        layout.addLayout(btn_layout)
        
        # Set as Default Button
        self.set_default_btn = QPushButton("🔊 Đặt làm thiết bị ra mặc định")
        self.set_default_btn.clicked.connect(self.set_default_output_device)
        layout.addWidget(self.set_default_btn)
        
        # Status
        self.device_status = QLabel("Sẵn sàng")
        self.device_status.setStyleSheet("color: #a6e3a1; font-style: italic; padding: 10px;")
        layout.addWidget(self.device_status)
        
        # Help text
        help_text = QLabel(
            "<b>Cách dùng:</b><br>"
            "1. Chọn loa trong danh sách thiết bị ra<br>"
            "2. Chọn BlackHole trong thiết bị ảo<br>"
            "3. Bấm «Tạo Multi-Output»<br>"
            "   • Audio MIDI Setup sẽ mở kèm hướng dẫn<br>"
            "4. Thiết bị mới giúp vừa nghe vừa bắt âm hệ thống!<br>"
            "<br><i>Lưu ý: Có thể cần quyền Trợ năng (Accessibility) để tự động hóa.</i>"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("background-color: #313244; padding: 10px; border-radius: 5px; font-size: 12px;")
        layout.addWidget(help_text)
        
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🔧 Thiết bị")
        
        # Initial population
        self.refresh_audio_devices()

    def refresh_audio_devices(self):
        """Refresh the list of audio devices"""
        try:
            import platform
            if platform.system() != "Darwin":
                self.device_status.setText("⚠️ Quản lý thiết bị chỉ hỗ trợ macOS")
                self.device_status.setStyleSheet("color: #fab387;")
                return
            
            from audio_device_manager import AudioDeviceManager
            manager = AudioDeviceManager()
            
            # Get output devices
            output_devices = manager.get_output_devices()
            self.output_devices_list.clear()
            for device in output_devices:
                self.output_devices_list.addItem(f"{device['name']}", device['id'])
            
            # Get virtual/BlackHole devices
            virtual_devices = manager.get_virtual_devices()
            self.virtual_devices_list.clear()
            if not virtual_devices:
                self.virtual_devices_list.addItem("Chưa tìm thấy BlackHole — hãy cài đặt")
                self.device_status.setText("⚠️ Chưa có BlackHole. Cài: brew install blackhole-2ch")
                self.device_status.setStyleSheet("color: #fab387;")
            else:
                for device in virtual_devices:
                    self.virtual_devices_list.addItem(f"{device['name']}", device['id'])
                self.device_status.setText("✅ Đã tải danh sách thiết bị")
                self.device_status.setStyleSheet("color: #a6e3a1;")
                
        except ImportError:
            self.device_status.setText("⚠️ Cần PyObjC: pip install pyobjc-framework-CoreAudio")
            self.device_status.setStyleSheet("color: #f38ba8;")
        except Exception as e:
            self.device_status.setText(f"❌ Lỗi: {str(e)}")
            self.device_status.setStyleSheet("color: #f38ba8;")
    
    def create_multi_output_device(self):
        """Create a multi-output device combining speakers + BlackHole"""
        try:
            from audio_device_manager import AudioDeviceManager
            manager = AudioDeviceManager()
            
            output_device_id = self.output_devices_list.currentData()
            virtual_device_id = self.virtual_devices_list.currentData()
            
            if not output_device_id or not virtual_device_id:
                self.device_status.setText("⚠️ Hãy chọn cả hai thiết bị")
                self.device_status.setStyleSheet("color: #fab387;")
                return
            
            # Show instruction dialog
            self._show_multi_output_instructions()
            
            # Call the audio device manager to open Audio MIDI Setup
            device_name = f"Phụ đề Multi-Output"
            success = manager.create_multi_output_device(
                device_name,
                [output_device_id, virtual_device_id],
                silent=True  # Suppress console output, show GUI dialog instead
            )
            
            if success:
                self.device_status.setText(f"✅ Đã mở Audio MIDI Setup — làm theo hướng dẫn!")
                self.device_status.setStyleSheet("color: #a6e3a1;")
                # Refresh after user has time to create the device
                QTimer = __import__('PyQt6.QtCore', fromlist=['QTimer']).QTimer
                QTimer.singleShot(3000, self.refresh_audio_devices)
            else:
                self.device_status.setText("❌ Không mở được Audio MIDI Setup")
                self.device_status.setStyleSheet("color: #f38ba8;")
                
        except Exception as e:
            self.device_status.setText(f"❌ Lỗi: {str(e)}")
            self.device_status.setStyleSheet("color: #f38ba8;")
    
    def _show_multi_output_instructions(self):
        """Show a dialog with step-by-step instructions"""
        dialog = QDialog(self)
        dialog.setWindowTitle("🎵 Tạo Multi-Output — Hướng dẫn")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📋 Hướng dẫn từng bước")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa; padding: 10px;")
        layout.addWidget(title)
        
        # Instructions text
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        
        output_device = self.output_devices_list.currentText()
        virtual_device = self.virtual_devices_list.currentText()
        
        instructions_html = f"""
        <div style='font-family: Arial, sans-serif;'>
        <h3 style='color: #fab387;'>✨ Đang mở Audio MIDI Setup...</h3>
        
        <p style='color: #a6adc8;'><b>Làm theo các bước sau:</b></p>
        
        <div style='background: #313244; padding: 12px; border-radius: 6px; margin: 10px 0;'>
        <p style='color: #89b4fa; font-weight: bold;'>👉 Bước 1: Nút dấu cộng</p>
        <p>Trong cửa sổ Audio MIDI Setup, góc <b>dưới bên trái</b>,<br>
        bấm nút <span style='background: #45475a; padding: 2px 8px; border-radius: 3px;'>[+]</span>.</p>
        </div>
        
        <div style='background: #313244; padding: 12px; border-radius: 6px; margin: 10px 0;'>
        <p style='color: #89b4fa; font-weight: bold;'>👉 Bước 2: Tạo Multi-Output</p>
        <p>Chọn mục:<br>
        <span style='color: #a6e3a1; font-weight: bold;'>Create Multi-Output Device</span></p>
        </div>
        
        <div style='background: #313244; padding: 12px; border-radius: 6px; margin: 10px 0;'>
        <p style='color: #89b4fa; font-weight: bold;'>👉 Bước 3: Chọn thiết bị</p>
        <p>Tick các thiết bị:<br>
        ✅ <span style='color: #f9e2af;'>{output_device}</span> (loa của bạn)<br>
        ✅ <span style='color: #f9e2af;'>{virtual_device}</span> (để bắt âm)</p>
        </div>
        
        <div style='background: #313244; padding: 12px; border-radius: 6px; margin: 10px 0;'>
        <p style='color: #89b4fa; font-weight: bold;'>👉 Bước 4: Drift Correction</p>
        <p><b style='color: #f38ba8;'>QUAN TRỌNG:</b> Bỏ tick <b>Drift Correction</b> cho <span style='color: #f9e2af;'>{output_device}</span><br>
        (để vẫn nghe được qua loa)</p>
        </div>
        
        <div style='background: #313244; padding: 12px; border-radius: 6px; margin: 10px 0;'>
        <p style='color: #89b4fa; font-weight: bold;'>👉 Bước 5: Đặt làm đầu ra mặc định</p>
        <p>Vào <b>Cài đặt hệ thống → Âm thanh</b><br>
        Chọn <span style='color: #a6e3a1;'>Multi-Output Device</span> vừa tạo làm thiết bị ra.</p>
        </div>
        
        <hr style='border: 1px solid #45475a; margin: 15px 0;'>
        
        <p style='color: #6c7086; font-style: italic;'>
        💡 Chỉ cần làm một lần; thiết bị giữ sau khi khởi động lại.<br>
        Sau khi cấu hình, bạn vừa nghe bình thường vừa bắt âm cho phụ đề.
        </p>
        </div>
        """
        
        instructions.setHtml(instructions_html)
        layout.addWidget(instructions)
        
        # Close button
        close_btn = QPushButton("✅ Đã hiểu!")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #b4e4b4;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def set_default_output_device(self):
        """Set the selected device as system default output"""
        try:
            from audio_device_manager import AudioDeviceManager
            manager = AudioDeviceManager()
            
            device_id = self.output_devices_list.currentData()
            if not device_id:
                self.device_status.setText("⚠️ Hãy chọn một thiết bị")
                self.device_status.setStyleSheet("color: #fab387;")
                return
            
            device_name = self.output_devices_list.currentText()
            success = manager.set_default_output_device(device_id)
            
            if success:
                self.device_status.setText(f"✅ Đã đặt '{device_name}' làm đầu ra mặc định")
                self.device_status.setStyleSheet("color: #a6e3a1;")
            else:
                self.device_status.setText("❌ Không đặt được thiết bị mặc định")
                self.device_status.setStyleSheet("color: #f38ba8;")
                
        except Exception as e:
            self.device_status.setText(f"❌ Lỗi: {str(e)}")
            self.device_status.setStyleSheet("color: #f38ba8;")

    def _update_mode_hint(self):
        b = config.asr_backend
        if b == "deepgram":
            self.mode_hint.setText(
                "<b>Chế độ:</b> ⚡ Realtime — <span style='color:#89b4fa'>Deepgram streaming</span><br>"
                "Chữ cập nhật liên tục (partial). Cần API key Deepgram."
            )
        elif b in ("openai", "gemini"):
            name = "ChatGPT / OpenAI" if b == "openai" else "Google Gemini"
            self.mode_hint.setText(
                f"<b>Chế độ:</b> ☁️ Cloud — <span style='color:#89b4fa'>{name}</span><br>"
                "Âm thanh máy → API → chữ. Cần API key (tab Cloud API). "
                "Nhanh hơn CPU yếu, có phí theo usage."
            )
        else:
            self.mode_hint.setText(
                "<b>Chế độ:</b> 🖥 Local — Whisper trên máy<br>"
                "Không cần API. Nếu quá chậm → tab <b>Cloud API</b> "
                "hoặc đổi Engine thành <i>openai</i> / <i>gemini</i>."
            )

    def init_transcription_tab(self):
        tab = QWidget()
        layout = QFormLayout()

        engine_hint = QLabel(
            "Realtime: deepgram (WebSocket). Local: whisper / mlx. "
            "Batch cloud: openai / gemini."
        )
        engine_hint.setWordWrap(True)
        engine_hint.setStyleSheet("color: #6c7086; font-size: 12px;")
        layout.addRow(engine_hint)

        self.asr_backend = QComboBox()
        self.asr_backend.addItems(["whisper", "mlx", "deepgram", "openai", "gemini"])
        backends = [self.asr_backend.itemText(i) for i in range(self.asr_backend.count())]
        self.asr_backend.setCurrentText(
            config.asr_backend if config.asr_backend in backends else "whisper"
        )
        self.asr_backend.setToolTip(
            "deepgram: realtime streaming | whisper/mlx: local | openai/gemini: cloud batch"
        )
        self.asr_backend.currentTextChanged.connect(self._on_backend_changed)
        layout.addRow("Engine ASR:", self.asr_backend)

        self.local_asr_group = QGroupBox("Whisper trên máy (local)")
        local_form = QFormLayout()
        self.local_asr_group.setLayout(local_form)

        self.whisper_model = QComboBox()
        self.whisper_model.addItems([
            "distil-small.en",
            "distil-medium.en",
            "tiny.en",
            "base.en",
            "small.en",
            "medium.en",
            "distil-large-v3",
        ])
        self.whisper_model.setCurrentText(config.whisper_model)
        self.whisper_model.setToolTip(
            "Intel Mac / Win CPU: distil-small.en. M-chip: mlx + small.en"
        )
        local_form.addRow("Model Whisper:", self.whisper_model)

        self.device_type = QComboBox()
        self.device_type.addItems(["cpu", "cuda", "mps", "auto"])
        self.device_type.setCurrentText(config.whisper_device)
        local_form.addRow("Thiết bị tính toán:", self.device_type)

        self.compute_type = QComboBox()
        self.compute_type.addItems(["int8", "float16", "float32"])
        self.compute_type.setCurrentText(config.whisper_compute_type)
        local_form.addRow("Lượng tử hóa:", self.compute_type)
        layout.addRow(self.local_asr_group)

        self.source_language = QComboBox()
        self.source_language.setEditable(True)
        self.source_language.addItems(
            ["auto", "en", "zh", "vi", "ja", "ko", "es", "fr", "de", "ru", "ar", "pt", "it"]
        )
        source_lang = config.source_language if config.source_language else "en"
        self.source_language.setCurrentText(source_lang if source_lang else "en")
        layout.addRow("Ngôn ngữ nguồn:", self.source_language)

        self.cloud_partial = QCheckBox("Bật partial khi dùng Cloud (tốn API hơn)")
        self.cloud_partial.setChecked(config.cloud_partial)
        layout.addRow(self.cloud_partial)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "📝 Nhận giọng")
        self._on_backend_changed(self.asr_backend.currentText())

    def _on_backend_changed(self, backend: str):
        is_cloud = backend in ("openai", "gemini", "deepgram")
        self.local_asr_group.setEnabled(not is_cloud)
        self.local_asr_group.setVisible(not is_cloud)
        if hasattr(self, "mode_hint"):
            self._update_mode_hint()

    def init_cloud_tab(self):
        tab = QWidget()
        outer = QVBoxLayout()
        outer.setSpacing(12)

        intro = QLabel(
            "<b>Realtime khuyến nghị:</b> Engine = <b>deepgram</b> (streaming).<br>"
            "OpenAI/Gemini = gửi từng đoạn (chậm, dễ 429). Key Deepgram: console.deepgram.com"
        )
        intro.setWordWrap(True)
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setStyleSheet("color: #a6adc8; font-size: 13px;")
        outer.addWidget(intro)

        dg_box = QGroupBox("Deepgram — Realtime streaming (khuyến nghị)")
        dform = QFormLayout()
        self.deepgram_api_key = QLineEdit()
        self.deepgram_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepgram_api_key.setPlaceholderText("DEEPGRAM_API_KEY hoặc console.deepgram.com")
        if config.deepgram_api_key:
            self.deepgram_api_key.setPlaceholderText("(đã lưu — nhập mới để thay)")
        dform.addRow("API key:", self.deepgram_api_key)
        self.deepgram_model = QComboBox()
        self.deepgram_model.setEditable(True)
        self.deepgram_model.addItems(["nova-3", "nova-2", "nova-2-general"])
        self.deepgram_model.setCurrentText(config.deepgram_model)
        dform.addRow("Model:", self.deepgram_model)
        self.deepgram_language = QComboBox()
        self.deepgram_language.setEditable(True)
        self.deepgram_language.addItems(["en", "en-IN", "en-US", "hi", "ta"])
        self.deepgram_language.setCurrentText(config.deepgram_language)
        dform.addRow("Ngôn ngữ:", self.deepgram_language)
        dg_box.setLayout(dform)
        outer.addWidget(dg_box)

        openai_box = QGroupBox("OpenAI / ChatGPT (Speech-to-Text)")
        oform = QFormLayout()
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key.setPlaceholderText("sk-… hoặc để trống nếu dùng OPENAI_API_KEY")
        if config.openai_api_key:
            self.openai_api_key.setPlaceholderText("(đã lưu — nhập mới để thay)")
        oform.addRow("API key:", self.openai_api_key)

        self.openai_base_url = QLineEdit()
        self.openai_base_url.setText(config.openai_base_url or "")
        self.openai_base_url.setPlaceholderText("https://api.openai.com/v1 (mặc định)")
        oform.addRow("Base URL:", self.openai_base_url)

        self.openai_stt_model = QComboBox()
        self.openai_stt_model.setEditable(True)
        self.openai_stt_model.addItems(
            ["gpt-4o-mini-transcribe", "gpt-4o-transcribe", "whisper-1"]
        )
        self.openai_stt_model.setCurrentText(config.openai_stt_model)
        oform.addRow("Model STT:", self.openai_stt_model)
        openai_box.setLayout(oform)
        outer.addWidget(openai_box)

        gemini_box = QGroupBox("Google Gemini")
        gform = QFormLayout()
        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_api_key.setPlaceholderText("AIza… hoặc GEMINI_API_KEY")
        if config.gemini_api_key:
            self.gemini_api_key.setPlaceholderText("(đã lưu — nhập mới để thay)")
        gform.addRow("API key:", self.gemini_api_key)

        self.gemini_model = QComboBox()
        self.gemini_model.setEditable(True)
        self.gemini_model.addItems(
            [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-3-flash-preview",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
            ]
        )
        self.gemini_model.setCurrentText(config.gemini_model)
        gform.addRow("Model:", self.gemini_model)
        gemini_box.setLayout(gform)
        outer.addWidget(gemini_box)

        test_row = QHBoxLayout()
        self.test_openai_btn = QPushButton("Kiểm tra OpenAI")
        self.test_openai_btn.clicked.connect(lambda: self._test_cloud_api("openai"))
        self.test_gemini_btn = QPushButton("Kiểm tra Gemini")
        self.test_gemini_btn.clicked.connect(lambda: self._test_cloud_api("gemini"))
        self.test_deepgram_btn = QPushButton("Kiểm tra Deepgram")
        self.test_deepgram_btn.clicked.connect(lambda: self._test_cloud_api("deepgram"))
        test_row.addWidget(self.test_deepgram_btn)
        test_row.addWidget(self.test_openai_btn)
        test_row.addWidget(self.test_gemini_btn)
        outer.addLayout(test_row)

        self.cloud_status = QLabel(
            "Key: console.deepgram.com · platform.openai.com · aistudio.google.com"
        )
        self.cloud_status.setWordWrap(True)
        self.cloud_status.setStyleSheet("color: #6c7086; font-size: 12px;")
        outer.addWidget(self.cloud_status)

        outer.addStretch()
        tab.setLayout(outer)
        self.tabs.addTab(tab, "☁️ Cloud API")

    def _test_cloud_api(self, provider: str):
        from config import reload_config

        self.save_config(silent=True)
        reload_config()
        from config import config as cfg

        for btn in (
            getattr(self, "test_deepgram_btn", None),
            self.test_openai_btn,
            self.test_gemini_btn,
        ):
            if btn:
                btn.setEnabled(False)

        if provider == "deepgram":
            key = self.deepgram_api_key.text().strip() or cfg.deepgram_api_key
            if not key:
                self._enable_cloud_test_buttons()
                QMessageBox.warning(
                    self,
                    "Thiếu Deepgram key",
                    "Nhập API key Deepgram.\n\n"
                    "Tab «Nhận giọng» → Engine = deepgram.",
                )
                return
            self.cloud_status.setText("Đang kiểm tra Deepgram WebSocket…")
            worker = CloudTestWorker(
                "deepgram",
                key,
                deepgram_model=self.deepgram_model.currentText(),
            )
        elif provider == "openai":
            key = self.openai_api_key.text().strip() or cfg.openai_api_key
            if not key:
                self._enable_cloud_test_buttons()
                QMessageBox.warning(
                    self,
                    "Thiếu OpenAI key",
                    "Nhập API key OpenAI (sk-…).\n\n"
                    "Tab «Nhận giọng» → Engine phải là openai nếu dùng ChatGPT.",
                )
                return
            self.cloud_status.setText("Đang kiểm tra OpenAI… (10–30 giây)")
            worker = CloudTestWorker(
                "openai", key,
                openai_base_url=self.openai_base_url.text().strip() or None,
                openai_model=self.openai_stt_model.currentText(),
            )
        else:
            key = self.gemini_api_key.text().strip() or cfg.gemini_api_key
            if not key:
                self._enable_cloud_test_buttons()
                QMessageBox.warning(
                    self,
                    "Thiếu Gemini key",
                    "Nhập API key Gemini (AIza…).\n\n"
                    "Tab «Nhận giọng» → Engine phải là gemini nếu dùng Google.",
                )
                return
            self.cloud_status.setText("Đang kiểm tra Gemini… (10–30 giây)")
            worker = CloudTestWorker(
                "gemini", key,
                gemini_model=self.gemini_model.currentText(),
            )

        worker.finished.connect(self._on_cloud_test_done)
        worker.start()
        self._cloud_test_worker = worker

    def _enable_cloud_test_buttons(self):
        for btn in (
            getattr(self, "test_deepgram_btn", None),
            self.test_openai_btn,
            self.test_gemini_btn,
        ):
            if btn:
                btn.setEnabled(True)

    def _on_cloud_test_done(self, ok: bool, message: str):
        self._enable_cloud_test_buttons()
        if ok:
            self.cloud_status.setText(f"✅ {message}")
            self.cloud_status.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            QMessageBox.information(self, "Kiểm tra API — OK", message)
        else:
            self.cloud_status.setText(f"❌ {message}")
            self.cloud_status.setStyleSheet("color: #f38ba8; font-size: 12px;")
            QMessageBox.critical(
                self,
                "Kiểm tra API — lỗi",
                message
                + "\n\nGợi ý: pip install -r requirements.txt",
            )

    def populate_devices(self):
        self.device_combo.clear()
        self.device_combo.addItem("Tự động (mặc định)", "auto")
        
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    name = f"[{i}] {d['name']}"
                    self.device_combo.addItem(name, i) # Store index as data
            
            # Select current
            if config.device_index is not None:
                index = self.device_combo.findData(config.device_index)
                if index >= 0:
                    self.device_combo.setCurrentIndex(index)
        except Exception as e:
            self.device_combo.addItem(f"Lỗi: {e}")

    def save_config(self, silent=False):
        import configparser
        import os
        from config import reload_config

        cp = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        if os.path.exists(config_path):
            cp.read(config_path)

        for section in ("audio", "transcription", "display", "api"):
            if not cp.has_section(section):
                cp.add_section(section)

        idx = self.device_combo.currentData()
        cp.set("audio", "device_index", str(idx) if idx is not None else "auto")
        cp.set("audio", "sample_rate", str(self.sample_rate.value()))
        cp.set("audio", "silence_threshold", str(self.silence_thresh.value()))
        cp.set("audio", "silence_duration", str(self.silence_dur.value()))

        cp.set("transcription", "backend", self.asr_backend.currentText())
        cp.set("transcription", "whisper_model", self.whisper_model.currentText())
        cp.set("transcription", "device", self.device_type.currentText())
        cp.set("transcription", "compute_type", self.compute_type.currentText())
        cp.set("transcription", "source_language", self.source_language.currentText())
        cp.set("transcription", "cloud_partial", str(self.cloud_partial.isChecked()).lower())

        new_openai = self.openai_api_key.text().strip()
        if new_openai:
            cp.set("api", "openai_api_key", new_openai)
        new_gemini = self.gemini_api_key.text().strip()
        if new_gemini:
            cp.set("api", "gemini_api_key", new_gemini)
        cp.set("api", "openai_base_url", self.openai_base_url.text().strip())
        cp.set("api", "openai_stt_model", self.openai_stt_model.currentText())
        cp.set("api", "gemini_model", self.gemini_model.currentText())
        new_dg = self.deepgram_api_key.text().strip()
        if new_dg:
            cp.set("api", "deepgram_api_key", new_dg)
        cp.set("api", "deepgram_model", self.deepgram_model.currentText())
        cp.set("api", "deepgram_language", self.deepgram_language.currentText())
        if self.asr_backend.currentText() == "deepgram":
            cp.set("transcription", "realtime_mode", "true")

        with open(config_path, "w", encoding="utf-8") as f:
            cp.write(f)

        reload_config()
        self._update_mode_hint()
        if not silent:
            self.status_label.setText("Đã lưu cấu hình.")
            QMessageBox.information(
                self,
                "Đã lưu",
                "Đã ghi config.ini.\nBấm «▶ Bắt đầu» trên tab Trang chủ.",
            )

    def _validate_cloud_ready(self) -> bool:
        from config import config as cfg

        if not cfg.is_cloud_asr():
            return True
        provider = cfg.asr_backend
        if provider == "deepgram":
            key = cfg.deepgram_api_key
            name = "Deepgram"
        elif provider == "openai":
            key = cfg.openai_api_key
            name = "OpenAI (sk-…)"
        else:
            key = cfg.gemini_api_key
            name = "Gemini (AIza…)"
        if key:
            return True
        QMessageBox.warning(
            self,
            "Thiếu API key",
            f"Engine đang là «{provider}» nhưng chưa có key {name}.\n\n"
            "1. Tab «☁️ Cloud API» → dán key → Lưu cấu hình\n"
            "2. Hoặc đổi Engine cho khớp key đã nhập",
        )
        self.tabs.setCurrentIndex(4)
        return False

    def on_start(self):
        self.save_config(silent=True)
        from config import config as cfg

        if not self._validate_cloud_ready():
            return

        if cfg.is_streaming_asr():
            self.status_label.setText("Đang mở Deepgram streaming…")
        elif cfg.is_batch_cloud_asr():
            label = "OpenAI" if cfg.asr_backend == "openai" else "Gemini"
            self.status_label.setText(f"Đang kết nối {label}…")
        else:
            self.status_label.setText("Đang tải Whisper…")
        self.status_label.setStyleSheet("font-size: 18px; color: #fab387;")
        self.start_btn.setEnabled(False)
        self.start_btn.setText("Đang tải...")

        self.startup_worker = StartupWorker()
        self.startup_worker.finished.connect(self.on_pipeline_ready)
        self.startup_worker.start()

    def on_pipeline_ready(self, error_msg, pipeline):
        from config import config

        if not pipeline:
            msg = error_msg or "Không khởi tạo được pipeline — xem terminal."
            self.status_label.setText("Khởi tạo thất bại")
            self.status_label.setStyleSheet("font-size: 18px; color: #f38ba8;")
            QMessageBox.critical(self, "Không bắt đầu được", msg)
            self._reset_start_buttons()
            return

        self.pipeline = pipeline

        from large_text_window import LargeTextOverlayWindow
        self.overlay_window = LargeTextOverlayWindow(
            window_width=config.reader_window_width,
            font_size=config.reader_font_size,
            keep_lines=config.reader_keep_lines,
        )
        self.overlay_window.show()
        self.pipeline.signals.update_text.connect(self.overlay_window.update_text)
        if hasattr(self.overlay_window, "stop_requested"):
            self.overlay_window.stop_requested.connect(self.on_stop)

        self.pipeline.start()

        from config import config as cfg
        if cfg.is_streaming_asr():
            mode = "Deepgram realtime"
        elif cfg.is_cloud_asr():
            mode = "Cloud API"
        else:
            mode = "Whisper local"
        self.status_label.setText(f"Đang chạy — {mode}")
        self.status_label.setStyleSheet("font-size: 18px; color: #a6e3a1;")

        self.start_btn.hide()
        self.stop_btn.show()
        self.showMinimized()

    def _reset_start_buttons(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶ Bắt đầu")

    def on_stop(self):
        if hasattr(self, "pipeline") and self.pipeline:
            self.pipeline.stop()
            self.pipeline = None

        if hasattr(self, "overlay_window") and self.overlay_window:
            self.overlay_window.close()
            self.overlay_window = None

        self.status_label.setText("Đã dừng")
        self.stop_btn.hide()
        self._reset_start_buttons()
        self.start_btn.show()
        self.showNormal()


class StartupWorker(QThread):
    finished = pyqtSignal(str, object)  # error_msg, pipeline

    def run(self):
        try:
            from config import reload_config
            reload_config()
            from main import Pipeline
            pipeline = Pipeline()
            self.finished.emit("", pipeline)
        except Exception as e:
            print(f"Startup Error: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit(str(e), None)


class CloudTestWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        provider,
        api_key,
        openai_base_url=None,
        openai_model=None,
        gemini_model=None,
        deepgram_model=None,
    ):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.openai_base_url = openai_base_url
        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.deepgram_model = deepgram_model

    def run(self):
        if self.provider == "deepgram":
            from streaming_asr import test_deepgram_connection

            ok, msg = test_deepgram_connection(
                self.api_key, model=self.deepgram_model or "nova-3"
            )
        else:
            from cloud_asr import test_cloud_connection

            ok, msg = test_cloud_connection(
                self.provider,
                self.api_key,
                openai_base_url=self.openai_base_url,
                openai_model=self.openai_model,
                gemini_model=self.gemini_model,
            )
        self.finished.emit(ok, msg)

if __name__ == "__main__":
    def exception_hook(exctype, value, traceback_obj):
        import traceback
        traceback_str = ''.join(traceback.format_tb(traceback_obj))
        error_msg = f"Unhandled Exception: {value}\n\n{traceback_str}"
        print(error_msg)
        from PyQt6.QtWidgets import QMessageBox
        if QApplication.instance():
            QMessageBox.critical(None, "Lỗi nghiêm trọng", error_msg)
        else:
            # If no app, just print (already done)
            pass
        sys.exit(1)

    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    w = Dashboard()
    w.show()
    sys.exit(app.exec())
