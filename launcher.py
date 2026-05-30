import sys
import os
import subprocess
import configparser
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QProgressBar, QMessageBox, QPushButton)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

class DependencyInstaller(QThread):
    progress = pyqtSignal(str) # Log message
    finished = pyqtSignal(bool) # Success/Fail

    def run(self):
        self.progress.emit("Đang kiểm tra thư viện...")
        
        required_packages = []
        try:
            with open("requirements.txt", "r") as f:
                required_packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            self.progress.emit("Không tìm thấy requirements.txt — bỏ qua.")
            self.finished.emit(True)
            return

        self.progress.emit("Đang cài/kiểm tra qua pip...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.progress.emit(output.strip())
            
            rc = process.poll()
            if rc == 0:
                self.progress.emit("Đã cài thư viện thành công.")
                self.finished.emit(True)
            else:
                stderr = process.stderr.read()
                self.progress.emit(f"Lỗi: {stderr}")
                self.finished.emit(False)
                
        except Exception as e:
            self.progress.emit(f"Không chạy được pip: {e}")
            self.finished.emit(False)

class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nhận giọng — Khởi động")
        self.setFixedSize(400, 200)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)
        
        self.label = QLabel("Đang khởi tạo ứng dụng...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(self.label)
        
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 0)
        self.layout.addWidget(self.pbar)
        
        self.log_label = QLabel("Đang kiểm tra môi trường...")
        self.log_label.setStyleSheet("color: #666; font-size: 12px;")
        self.log_label.setWordWrap(True)
        self.layout.addWidget(self.log_label)
        
        self.start_btn = QPushButton("Mở ứng dụng")
        self.start_btn.setStyleSheet("""
            background-color: #3498db; color: white; padding: 10px; font-weight: bold; border-radius: 5px;
        """)
        self.start_btn.clicked.connect(self.launch_main_app)
        self.start_btn.hide()
        self.layout.addWidget(self.start_btn)

        QTimer.singleShot(500, self.start_check)

    def start_check(self):
        self.installer = DependencyInstaller()
        self.installer.progress.connect(self.update_log)
        self.installer.finished.connect(self.on_install_finished)
        self.installer.start()

    def update_log(self, message):
        self.log_label.setText(message)

    def on_install_finished(self, success):
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        
        if success:
            self.log_label.setText("Sẵn sàng!")
            self.start_btn.show()
            self.label.setText("Khởi tạo xong")
            QTimer.singleShot(800, self.launch_main_app)
            
        else:
            self.label.setText("Khởi tạo thất bại")
            self.log_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Lỗi", "Không cài được thư viện.\nXem chi tiết trong terminal.")

    def launch_main_app(self):
        self.close()
        try:
            import dashboard
            self.dash = dashboard.Dashboard()
            self.dash.show()
        except Exception as e:
            import traceback
            error_msg = f"Không mở được bảng điều khiển:\n{str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            QMessageBox.critical(self, "Lỗi", error_msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    launcher = LauncherWindow()
    launcher.show()
    
    sys.exit(app.exec())
