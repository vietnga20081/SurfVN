import sys
import os
import json
import random
import time
import requests

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QCheckBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ======================= CONFIG =========================
API_LOGIN_URL = "https://surfvn.click/api/login.php"
BASE_SURF_URL = "https://surfvn.click/surf.php"
APP_NAME = "TrafficSurf"

TOKEN_FILE = "session.dat"
PROXY_SESSION_FILE = "proxy.dat"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
]


# ======================= UTILITIES =========================

def build_proxy(proxy_creds: dict):
    """Trả về dict proxy cho requests nếu user/pass tồn tại."""
    if not proxy_creds.get("username") or not proxy_creds.get("password"):
        return None

    user = requests.utils.quote(proxy_creds["username"])
    pwd = requests.utils.quote(proxy_creds["password"])

    pac_proxy = f"http://{user}:{pwd}@127.0.0.1"  # Fake entry → Windows sẽ override bằng PAC system
    return {"http": pac_proxy, "https": pac_proxy}


def save_proxy_session(proxy_data: dict):
    with open(PROXY_SESSION_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(proxy_data))


def load_proxy_session():
    if os.path.exists(PROXY_SESSION_FILE):
        try:
            return json.loads(open(PROXY_SESSION_FILE, "r").read().strip())
        except:
            return {}
    return {}


def check_proxy_required(proxy_creds=None):
    """Kiểm tra môi trường có yêu cầu proxy không."""
    try:
        r = requests.get("https://www.google.com/generate_204", timeout=5, proxies=build_proxy(proxy_creds))
        return False  # truy cập OK → không cần proxy
    except requests.exceptions.ProxyError:
        return True
    except requests.exceptions.RequestException:
        return True

    return False


# ======================= PROXY LOGIN DIALOG =========================

class ProxyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.result_data = {}

        self.setWindowTitle("Proxy Authentication Required")
        self.setFixedSize(400, 220)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel("Máy chủ yêu cầu đăng nhập Proxy.\nVui lòng nhập thông tin để kết nối mạng:")
        label.setWordWrap(True)
        layout.addWidget(label)

        form = QFormLayout()

        self.user = QLineEdit()
        self.user.setPlaceholderText("Proxy Username")
        form.addRow("Username:", self.user)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Proxy Password")
        form.addRow("Password:", self.password)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accepted_action)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def accepted_action(self):
        if not self.user.text().strip() or not self.password.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ Username và Password Proxy.")
            return

        self.result_data = {
            "username": self.user.text().strip(),
            "password": self.password.text().strip()
        }

        save_proxy_session(self.result_data)
        self.accept()

    def get_result(self):
        return self.result_data


# ======================= SELENIUM WORKER =========================
class SeleniumWorker(QThread):
    update = pyqtSignal(str)

    def __init__(self, api_data, proxy_creds=None):
        super().__init__()
        self.api_data = api_data
        self.proxy_creds = proxy_creds or {}
        self.running = True
        self.driver = None

    def run(self):
        while self.running:
            try:
                chrome_options = Options()
                chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

                chrome_options.add_argument("--proxy-server=system")
                chrome_options.add_argument("--proxy-auto-detect")

                chrome_options.add_argument("--disable-blink-features=AutomationControlled")

                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)

                url = f"{BASE_SURF_URL}?api_token={self.api_data.get('api_token')}"
                self.update.emit("Đang truy cập website...")
                self.driver.get(url)

                while self.running:
                    time.sleep(5)

            except Exception as e:
                self.update.emit(f"Lỗi: {str(e)[:80]}, thử lại sau 10 giây...")
                time.sleep(10)
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None

    def stop(self):
        self.running = False
        if self.driver:
            self.driver.quit()


# ======================= MAIN WINDOWS =========================

class SurfWindow(QWidget):
    def __init__(self, api_data, proxy_creds):
        super().__init__()
        self.worker = None
        self.api_data = api_data
        self.proxy_creds = proxy_creds

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(400, 220)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Xin chào, {api_data.get('username')}!", alignment=Qt.AlignmentFlag.AlignCenter))

        self.status = QLabel("Đang khởi động...", alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        stop_btn = QPushButton("Dừng và Thoát")
        stop_btn.clicked.connect(self.close)
        layout.addWidget(stop_btn)

        self.start()

    def start(self):
        self.worker = SeleniumWorker(self.api_data, self.proxy_creds)
        self.worker.update.connect(self.status.setText)
        self.worker.start()

    def closeEvent(self, e):
        if self.worker:
            self.worker.stop()
        e.accept()


class LoginWindow(QWidget):
    def __init__(self, proxy_creds):
        super().__init__()
        self.proxy_creds = proxy_creds

        self.setWindowTitle(f"Đăng nhập - {APP_NAME}")
        self.setFixedSize(350, 220)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.user = QLineEdit()
        self.passw = QLineEdit()
        self.passw.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Username:", self.user)
        form.addRow("Password:", self.passw)
        layout.addLayout(form)

        self.btn = QPushButton("Đăng nhập")
        self.btn.clicked.connect(self.handle_login)
        layout.addWidget(self.btn)

    def handle_login(self):
        if not self.user.text() or not self.passw.text():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ")
            return

        self.btn.setText("Đang đăng nhập...")
        self.btn.setDisabled(True)

        proxies = build_proxy(self.proxy_creds)

        try:
            r = requests.post(API_LOGIN_URL, json={
                "username": self.user.text(),
                "password": self.passw.text()
            }, proxies=proxies, timeout=10)

            data = r.json()

            if data.get("success"):
                open(TOKEN_FILE, "w").write(json.dumps(data))
                self.open_surf(data)
            else:
                QMessageBox.critical(self, "Đăng nhập thất bại", data.get("message"))

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))

        self.btn.setText("Đăng nhập")
        self.btn.setDisabled(False)

    def open_surf(self, data):
        self.surf = SurfWindow(data, self.proxy_creds)
        self.surf.show()
        self.close()


# ======================= APP ENTRY =========================

def main():
    app = QApplication(sys.argv)

    proxy_creds = load_proxy_session()

    if check_proxy_required(proxy_creds):
        dialog = ProxyDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        proxy_creds = dialog.get_result()

    saved = None
    if os.path.exists(TOKEN_FILE):
        saved = json.loads(open(TOKEN_FILE).read())

    if saved and saved.get("api_token"):
        win = SurfWindow(saved, proxy_creds)
    else:
        win = LoginWindow(proxy_creds)

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
