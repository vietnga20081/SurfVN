import sys
import os
import requests
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QStatusBar, QFrame)
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView

# --- CẤU HÌNH ---
APP_NAME = "SurfVN - Traffic Exchange"
TOKEN_FILE = "session.dat"
API_LOGIN_URL = "http://surfvn.click/api/login.php" # << THAY ĐỔI URL NÀY
SURF_URL_TEMPLATE = "http://surfvn.click/surf.php?api_token={}" # << THAY ĐỔI URL NÀY

# --- STYLESHEET (QSS) CHO GIAO DIỆN HIỆN ĐẠI ---
STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}

/* Cửa sổ Đăng nhập */
#LoginWindow {
    background-color: #2c3e50; /* Nền xanh đậm */
}
#LoginWindow QLabel {
    color: #ecf0f1; /* Chữ trắng mờ */
    font-weight: bold;
}
#LoginWindow QLineEdit {
    background-color: #34495e; /* Nền input đậm hơn */
    color: #ecf0f1;
    border: 1px solid #2c3e50;
    border-radius: 5px;
    padding: 8px;
}
#LoginWindow QLineEdit:focus {
    border: 1px solid #3498db; /* Viền xanh khi focus */
}
#LoginWindow QPushButton {
    background-color: #3498db; /* Nút màu xanh dương */
    color: white;
    font-weight: bold;
    border-radius: 5px;
    padding: 10px;
    border: none;
}
#LoginWindow QPushButton:hover {
    background-color: #2980b9; /* Màu đậm hơn khi di chuột */
}
#LoginWindow QPushButton:disabled {
    background-color: #5b6a78;
}
#LoginWindow #TitleLabel {
    font-size: 16pt;
    font-weight: bold;
    color: white;
    qproperty-alignment: 'AlignCenter';
    padding-bottom: 10px;
}

/* Cửa sổ Lướt web */
#SurfWindow {
    background-color: #222b35;
}
QStatusBar {
    background-color: #2c3e50;
    color: #bdc3c7;
    font-size: 9pt;
}
QStatusBar::item {
    border: none;
}
"""

class SurfWindow(QWidget):
    def __init__(self, api_token):
        super().__init__()
        self.api_token = api_token
        self.setObjectName("SurfWindow") # Đặt ID để áp dụng style
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1280, 720)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        self.status_bar = QStatusBar()
        self.status_label = QLabel("Đang tải trang lướt web...")
        self.status_bar.addWidget(self.status_label, 1) # Tham số 1 để co giãn
        layout.addWidget(self.status_bar)

        surf_url = SURF_URL_TEMPLATE.format(self.api_token)
        self.browser.setUrl(QUrl(surf_url))
        self.browser.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, success):
        status_text = "Đã tải xong. Quá trình lướt web đang tự động..." if success else "Lỗi: Không thể tải trang lướt web."
        self.status_label.setText(status_text)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Xác nhận thoát', 
                                     "Bạn có chắc muốn đóng ứng dụng không?", 
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
        self.setObjectName("LoginWindow") # Đặt ID để áp dụng style
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Đăng nhập - {APP_NAME}")
        self.setFixedSize(400, 250) # Kích thước cố định cho đẹp

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30) # Thêm padding
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("TitleLabel")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Username hoặc Email")
        form_layout.addRow(QLabel("Tài khoản:"), self.login_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mật khẩu")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow(QLabel("Mật khẩu:"), self.password_input)
        
        layout.addLayout(form_layout)
        layout.addSpacing(20)

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

    def handle_login(self):
        # ... (logic xử lý đăng nhập giữ nguyên như trước) ...
        login_identifier = self.login_input.text().strip()
        password = self.password_input.text().strip()
        if not login_identifier or not password:
            QMessageBox.warning(self, "Thông tin trống", "Vui lòng nhập đầy đủ thông tin đăng nhập.")
            return
        self.login_button.setText("Đang đăng nhập...")
        self.login_button.setEnabled(False)
        QApplication.processEvents()
        try:
            response = requests.post(API_LOGIN_URL, json={"login_identifier": login_identifier, "password": password}, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                self.save_token(data.get("api_token"))
                self.open_surf_window(data.get("api_token"))
            else:
                QMessageBox.critical(self, "Đăng nhập thất bại", data.get("message", "Lỗi không xác định."))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Lỗi Mạng", f"Không thể kết nối đến server.\nLỗi: {e}")
        finally:
            self.login_button.setText("Đăng nhập")
            self.login_button.setEnabled(True)
            
    def save_token(self, token):
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(token)
        except IOError:
            print(f"Warning: Could not save token to {TOKEN_FILE}")
            
    def open_surf_window(self, api_token):
        self.surf_window = SurfWindow(api_token)
        self.surf_window.show()
        self.close()

def load_token():
    # ... (hàm load token giữ nguyên) ...
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return f.read().strip()
        except IOError: return None
    return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET) # <-- ÁP DỤNG STYLESHEET CHO TOÀN BỘ ỨNG DỤNG
    
    saved_token = load_token()
    
    if saved_token:
        main_window = SurfWindow(saved_token)
    else:
        main_window = LoginWindow()
        
    main_window.show()
    sys.exit(app.exec())
