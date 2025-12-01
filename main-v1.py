import sys
import os
import requests
import random
import time
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QStatusBar, QMainWindow)
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- Thư viện Selenium ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# --- CẤU HÌNH ---
API_LOGIN_URL = "https://surfvn.click/api/login.php" 
BASE_SURF_URL = "https://surfvn.click/surf.php"
APP_NAME = "TrafficSurf Surfer"
TOKEN_FILE = "session.dat"

# --- DANH SÁCH USER-AGENT ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-S906N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.119 Mobile Safari/537.36",
]

# --- GIAO DIỆN (STYLESHEET) ---
STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }
#LoginWindow, #SurfWindow { background-color: #2c3e50; }
#LoginWindow QLabel, #SurfWindow QLabel { color: #ecf0f1; font-weight: bold; }
#LoginWindow QLineEdit { background-color: #34495e; color: #ecf0f1; border: 1px solid #2c3e50; border-radius: 5px; padding: 8px; font-size: 11pt; }
#LoginWindow QLineEdit:focus { border: 1px solid #3498db; }
QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 5px; padding: 10px; border: none; font-size: 11pt; }
QPushButton:hover { background-color: #2980b9; }
QPushButton:disabled { background-color: #5b6a78; }
#LoginWindow #TitleLabel, #SurfWindow #TitleLabel { font-size: 16pt; font-weight: bold; color: white; qproperty-alignment: 'AlignCenter'; }
#SurfWindow #StatusLabel { font-size: 10pt; color: #bdc3c7; }
QMessageBox { background-color: #34495e; }
QMessageBox QLabel { color: white; }
QMessageBox QPushButton { background-color: #3498db; color: white; border-radius: 3px; padding: 5px 15px; min-width: 60px; }
"""

# --- LỚP WORKER ĐIỀU KHIỂN SELENIUM (CHẠY NGẦM) ---
class SeleniumWorker(QThread):
    update_status = pyqtSignal(str)

    def __init__(self, api_data):
        super().__init__()
        self.api_data = api_data
        self.running = True
        self.driver = None

    def run(self):
        while self.running:
            try:
                # 1. Lấy thông tin từ dữ liệu API
                api_token = self.api_data.get('api_token')
                allow_proxy = self.api_data.get('allow_proxy', False)
                proxy_string = self.api_data.get('proxy')
                
                # 2. Cấu hình Chrome
                chrome_options = Options()
                user_agent = random.choice(USER_AGENTS)
                chrome_options.add_argument(f"user-agent={user_agent}")
                # chrome_options.add_argument("--headless") # Chạy ẩn nếu muốn
                
                # 3. Cấu hình proxy nếu được phép và có proxy
                if allow_proxy and proxy_string:
                    self.update_status.emit(f"Đang sử dụng proxy: {proxy_string.split(':')[0]}")
                    chrome_options.add_argument(f'--proxy-server={proxy_string}')
                else:
                    self.update_status.emit("Đang lướt web với IP gốc.")

                # 4. Khởi tạo trình duyệt
                self.update_status.emit("Đang khởi tạo trình duyệt...")
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # 5. Truy cập trang surf
                surf_url = f"{BASE_SURF_URL}?api_token={api_token}"
                self.update_status.emit("Đang truy cập trang lướt web...")
                self.driver.get(surf_url)

                # 6. Giữ trình duyệt chạy và theo dõi URL
                self.update_status.emit("Bắt đầu lướt web. Trình duyệt sẽ tự động làm việc.")
                initial_url = self.driver.current_url
                while self.running:
                    time.sleep(5) # Kiểm tra mỗi 5 giây
                    if not self.running: break
                    try:
                        # Nếu URL thay đổi, nghĩa là trang đã chuyển, bắt đầu lại chu trình
                        if self.driver.current_url != initial_url:
                            self.update_status.emit("Website đã được xem xong. Đang lấy website mới...")
                            break # Thoát vòng lặp trong để tạo lại trình duyệt
                    except Exception:
                        # Lỗi có thể xảy ra nếu trình duyệt bị đóng
                        self.update_status.emit("Trình duyệt đã bị đóng. Đang khởi động lại...")
                        break

            except Exception as e:
                self.update_status.emit(f"Lỗi: {str(e)[:100]}. Đang thử lại sau 15 giây.")
                time.sleep(15)
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None

    def stop(self):
        self.running = False
        if self.driver:
            self.driver.quit()
        self.wait()

# --- CỬA SỔ LƯỚT WEB ---
class SurfWindow(QWidget):
    def __init__(self, api_data):
        super().__init__()
        self.api_data = api_data
        self.worker = None
        self.setObjectName("SurfWindow")
        self.init_ui()
        self.start_worker() # Tự động bắt đầu khi cửa sổ mở

    def init_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(500, 250)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(APP_NAME, objectName="TitleLabel")
        username_label = QLabel(f"Xin chào, {self.api_data.get('username', 'user')}!", alignment=Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel("Đang khởi động...", objectName="StatusLabel", alignment=Qt.AlignmentFlag.AlignCenter)
        self.stop_button = QPushButton("Dừng lướt và Thoát")

        layout.addWidget(title_label)
        layout.addWidget(username_label)
        layout.addSpacing(20)
        layout.addWidget(self.status_label)
        layout.addSpacing(20)
        layout.addWidget(self.stop_button)
        
        self.stop_button.clicked.connect(self.close)

    def start_worker(self):
        self.worker = SeleniumWorker(self.api_data)
        self.worker.update_status.connect(self.status_label.setText)
        self.worker.start()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Xác nhận', "Bạn có chắc muốn dừng lướt và thoát?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.worker:
                self.worker.stop()
            event.accept()
        else:
            event.ignore()

# --- CỬA SỔ ĐĂNG NHẬP ---
class LoginWindow(QWidget):
    # ... (Mã nguồn của LoginWindow không thay đổi nhiều, tôi sẽ rút gọn ở đây và dán đầy đủ bên dưới) ...
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
            response = requests.post(API_LOGIN_URL, json={"username": login_id, "password": password}, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("api_token"):
                self.save_token(json.dumps(data)) # Lưu toàn bộ dữ liệu JSON
                self.open_surf_window(data)
            else:
                QMessageBox.critical(self, "Lỗi", data.get("message", "Lỗi không xác định."))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Lỗi Mạng", f"Không thể kết nối đến server: {e}")
        finally:
            self.login_button.setText("Đăng nhập")
            self.login_button.setEnabled(True)
            
    def save_token(self, data_json):
        with open(TOKEN_FILE, "w") as f: f.write(data_json)
            
    def open_surf_window(self, api_data):
        self.surf_window = SurfWindow(api_data)
        self.surf_window.show()
        self.close()

# --- HÀM KHỞI ĐỘNG CHÍNH ---
def load_session_data():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                data_json = f.read().strip()
                if data_json: return json.loads(data_json)
        except (IOError, json.JSONDecodeError):
            return None
    return None

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    
    saved_data = load_session_data()
    # Kiểm tra xem token có hợp lệ không
    if saved_data and saved_data.get("api_token"):
        main_window = SurfWindow(saved_data)
    else:
        main_window = LoginWindow()
        
    main_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
