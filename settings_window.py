from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout,
                             QFormLayout, QPushButton, QComboBox, QDoubleSpinBox, QMessageBox, QSpinBox)
from PyQt6.QtCore import Qt
import configparser
import os
from config import config

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cài đặt")
        self.setFixedSize(400, 300)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(config.api_key if config.api_key != "dummy-key-for-local" else "")
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Khóa API OpenAI:", self.api_key_input)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setText(config.api_base_url if config.api_base_url else "")
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1")
        form_layout.addRow("URL gốc API:", self.base_url_input)
        
        self.model_input = QComboBox()
        self.model_input.setEditable(True)
        initial_models = [config.model] if config.model else ["gpt-3.5-turbo"]
        self.model_input.addItems(initial_models)
        self.model_input.setCurrentText(config.model)
        
        model_row = QWidget()
        model_row_layout = QHBoxLayout(model_row)
        model_row_layout.setContentsMargins(0,0,0,0)
        model_row_layout.addWidget(self.model_input)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Tải danh sách model từ máy chủ")
        self.refresh_btn.setFixedWidth(30)
        self.refresh_btn.clicked.connect(self.fetch_models)
        model_row_layout.addWidget(self.refresh_btn)
        
        form_layout.addRow("Model dịch:", model_row)
        
        self.threads_input = QSpinBox()
        self.threads_input.setRange(1, 16)
        self.threads_input.setValue(config.translation_threads)
        self.threads_input.setSuffix(" luồng")
        self.threads_input.setToolTip("Số yêu cầu dịch đồng thời (tăng nếu nói nhanh)")
        form_layout.addRow("Luồng dịch:", self.threads_input)
        
        self.backend_input = QComboBox()
        self.backend_input.addItems(["whisper", "mlx", "funasr"])
        self.backend_input.setCurrentText(config.asr_backend)
        self.backend_input.setToolTip("ASR: whisper (CPU/CUDA), mlx (Apple Silicon), funasr (Alibaba)")
        form_layout.addRow("Engine ASR:", self.backend_input)
        
        self.whisper_input = QComboBox()
        self.whisper_input.addItems(["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v3", "turbo"])
        self.whisper_input.setCurrentText(config.whisper_model)
        form_layout.addRow("Model Whisper:", self.whisper_input)
        
        self.funasr_input = QComboBox()
        self.funasr_input.setEditable(True)
        self.funasr_input.addItems([
            "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
            "iic/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8404-online",
            "iic/speech_UniASR_asr_2pass-en-16k-common-vocab1080-tensorflow1-online",
            "iic/SenseVoiceSmall",
            "FunAudioLLM/SenseVoiceSmall",
            "FunAudioLLM/Fun-ASR-Nano-2512",
            "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
        ])
        self.funasr_input.setCurrentText(config.funasr_model)
        self.funasr_input.setToolTip("Tên model FunASR (chỉ khi backend=funasr)")
        form_layout.addRow("Model FunASR:", self.funasr_input)
        
        self.step_size_input = QDoubleSpinBox()
        self.step_size_input.setRange(0.1, 2.0)
        self.step_size_input.setSingleStep(0.1)
        self.step_size_input.setValue(config.streaming_step_size)
        form_layout.addRow("Bước stream (giây):", self.step_size_input)
        
        self.silence_dur_input = QDoubleSpinBox()
        self.silence_dur_input.setRange(0.2, 5.0)
        self.silence_dur_input.setSingleStep(0.1)
        self.silence_dur_input.setValue(config.silence_duration)
        self.silence_dur_input.setSuffix(" giây")
        form_layout.addRow("Im lặng VAD (giây):", self.silence_dur_input)

        self.max_phrase_input = QSpinBox()
        self.max_phrase_input.setRange(5, 600)
        self.max_phrase_input.setSingleStep(5)
        self.max_phrase_input.setValue(int(config.max_phrase_duration))
        self.max_phrase_input.setSuffix(" giây")
        form_layout.addRow("Cụm từ tối đa (giây):", self.max_phrase_input)
        
        layout.addLayout(form_layout)
        
        self.save_btn = QPushButton("Lưu & khởi động lại")
        self.save_btn.clicked.connect(self.save_config)
        self.save_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.save_btn)
        
        self.setLayout(layout)
        
    def fetch_models(self):
        from openai import OpenAI
        
        api_key = self.api_key_input.text() or "dummy"
        base_url = self.base_url_input.text()
        
        if not base_url:
            QMessageBox.warning(self, "Thiếu URL", "Hãy nhập URL gốc API trước.")
            return

        self.refresh_btn.setEnabled(False)
        self.model_input.clear()
        self.model_input.addItem("Đang tải...")
        
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            models_response = client.models.list(timeout=5.0) 
            model_ids = sorted([m.id for m in models_response.data])
            
            self.model_input.clear()
            self.model_input.addItems(model_ids)
            
            current = config.model
            if current in model_ids:
                self.model_input.setCurrentText(current)
            elif model_ids:
                self.model_input.setCurrentIndex(0)
                
            QMessageBox.information(self, "Thành công", f"Tìm thấy {len(model_ids)} model.")
            
        except Exception as e:
            self.model_input.clear()
            self.model_input.addItem(config.model)
            QMessageBox.critical(self, "Lỗi", f"Không tải được model: {str(e)}")
            
        self.refresh_btn.setEnabled(True)
        
    def save_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        parser = configparser.ConfigParser()
        parser.read(config_path)
        
        if not parser.has_section("api"): parser.add_section("api")
        if not parser.has_section("translation"): parser.add_section("translation")
        if not parser.has_section("transcription"): parser.add_section("transcription")
        if not parser.has_section("audio"): parser.add_section("audio")
        
        parser.set("api", "api_key", self.api_key_input.text() or "")
        parser.set("api", "base_url", self.base_url_input.text() or "")
        parser.set("translation", "model", self.model_input.currentText())
        parser.set("translation", "threads", str(self.threads_input.value()))
        parser.set("transcription", "backend", self.backend_input.currentText())
        parser.set("transcription", "whisper_model", self.whisper_input.currentText())
        parser.set("transcription", "funasr_model", self.funasr_input.currentText())
        parser.set("audio", "streaming_step_size", str(self.step_size_input.value()))
        parser.set("audio", "max_phrase_duration", str(self.max_phrase_input.value()))
        parser.set("audio", "silence_duration", str(self.silence_dur_input.value()))
        
        try:
            with open(config_path, 'w') as f:
                parser.write(f)
            QMessageBox.information(self, "Đã lưu", "Đã lưu cấu hình! Ứng dụng sẽ tự khởi động lại.")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không lưu được cấu hình: {e}")
