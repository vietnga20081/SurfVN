import sys
import os
import requests
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QStatusBar, QMainWindow)
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- CẤU HÌNH ---
API_LOGIN_URL = "https://surfvn.click/api/login.php" 
BASE_SURF_URL = "https://surfvn.click/surf.php"
APP_NAME = "TrafficSurf Surfer"
TOKEN_FILE = "session.dat"

STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }
#LoginWindow { background-color: #2c3e50; }
#LoginWindow QLabel { color: #ecf0f1; font-weight: bold; }
#LoginWindow QLineEdit { background-color: #34495e; color: #ecf0f1; border: 1px solid #2c3e50; border-radius: 5px; padding: 8px; font-size: 11pt; }
#LoginWindow QLineEdit:focus { border: 1px solid #3498db; }
#LoginWindow QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 5px; padding: 10px; border: none; font-size: 11pt; }
#LoginWindow QPushButton:hover { background-color: #2980b9; }
#LoginWindow QPushButton:disabled { background-color: #5b6a78; }
#LoginWindow #TitleLabel { font-size: 16pt; font-weight: bold; color: white; qproperty-alignment: 'AlignCenter'; padding-bottom: 10px; }
#SurfWindow { background-color: #222b35; }
QMainWindow, QStatusBar { background-color: #2c3e50; color: #bdc3c7; font-size: 9pt; }
QStatusBar::item { border: none; }
QMessageBox { background-color: #34495e; }
QMessageBox QLabel { color: white; }
QMessageBox QPushButton { background-color: #3498db; color: white; border-radius: 3px; padding: 5px 15px; min-width: 60px; }
"""

class SurfWindow(QMainWindow):
    def __init__(self, api_token):
        super().__init__()
        self.api_token = api_token
        self.setObjectName("SurfWindow")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1280, 720)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Đang tải trang...")

        surf_url_with_token = f"{BASE_SURF_URL}?api_token={self.api_token}"
        self.browser.setUrl(QUrl(surf_url_with_token))
        self.browser.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, success):
        self.status_bar.showMessage("Đang lướt web tự động..." if success else "Lỗi: Không thể tải trang.")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Xác nhận', "Bạn có chắc muốn thoát?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.surf_window = None
        self.setObjectName("LoginWindow")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Đăng nhập - {APP_NAME}")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(APP_NAME, objectName="TitleLabel")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)

        self.login_input = QLineEdit(placeholderText="Username hoặc Email")
        form_layout.addRow(QLabel("Tài khoản:"), self.login_input)

        self.password_input = QLineEdit(placeholderText="Mật khẩu", echoMode=QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        form_layout.addRow(QLabel("Mật khẩu:"), self.password_input)
        
        layout.addLayout(form_layout)
        layout.addSpacing(20)

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

    def handle_login(self):
        login_id = self.login_input.text().strip()
        password = self.password_input.text().strip()

        if not login_id or not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin.")
            return

        self.login_button.setText("Đang đăng nhập...")
        self.login_button.setEnabled(False)
        QApplication.processEvents()

        try:
            response = requests.post(API_LOGIN_URL, json={"login_identifier": login_id, "password": password}, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and data.get("api_token"):
                self.save_token(data["api_token"])
                self.open_surf_window(data["api_token"])
            else:
                QMessageBox.critical(self, "Lỗi", data.get("message", "Lỗi không xác định."))
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Lỗi Mạng", "Không thể kết nối đến server.")
        finally:
            self.login_button.setText("Đăng nhập")
            self.login_button.setEnabled(True)
            
    def save_token(self, token):
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(token)
        except IOError:
            pass
            
    def open_surf_window(self, api_token):
        self.surf_window = SurfWindow(api_token)
        self.surf_window.show()
        self.close()

def load_token():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token = f.read().strip()
                if token: return token
        except IOError:
            return None
    return None

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    saved_token = load_token()
    main_window = SurfWindow(saved_token) if saved_token else LoginWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
