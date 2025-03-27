import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtNetwork import QTcpSocket

class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Control")
        self.setGeometry(700, 100, 400, 400)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Text edit for commands
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        # Execute button
        self.execute_button = QPushButton("Execute")
        self.execute_button.clicked.connect(self.send_commands)
        layout.addWidget(self.execute_button)

        # Get Dimensions button
        self.get_dimensions_button = QPushButton("Get Dimensions")
        self.get_dimensions_button.clicked.connect(self.get_dimensions)
        layout.addWidget(self.get_dimensions_button)

        # Get Position button
        self.get_position_button = QPushButton("Get Position")
        self.get_position_button.clicked.connect(self.get_position)
        layout.addWidget(self.get_position_button)

    def send_commands(self):
        commands = self.text_edit.toPlainText()
        socket = QTcpSocket(self)
        socket.connectToHost("127.0.0.1", 12345)
        if socket.waitForConnected(1000):
            socket.write(commands.encode())
            socket.waitForBytesWritten()
            socket.disconnectFromHost()
        else:
            print("Failed to connect to server")

    def get_dimensions(self):
        socket = QTcpSocket(self)
        socket.connectToHost("127.0.0.1", 12345)
        if socket.waitForConnected(1000):
            socket.write("GET_DIMENSIONS\n".encode())
            if socket.waitForReadyRead(1000):
                response = socket.readLine().data().decode().strip()
                QMessageBox.information(self, "Dimensions", f"Grid Dimensions: {response}")
            else:
                print("No response for GET_DIMENSIONS")
            socket.disconnectFromHost()
        else:
            print("Failed to connect to server")

    def get_position(self):
        socket = QTcpSocket(self)
        socket.connectToHost("127.0.0.1", 12345)
        if socket.waitForConnected(1000):
            socket.write("GET_POSITION\n".encode())
            if socket.waitForReadyRead(1000):
                response = socket.readLine().data().decode().strip()
                parts = response.split()
                if len(parts) == 3:
                    x, y, dir_deg = parts
                    dir_text = {0: "Up", 90: "Right", 180: "Down", 270: "Left"}.get(int(dir_deg), str(dir_deg))
                    msg = f"Position: ({x}, {y}), Facing: {dir_text}"
                    QMessageBox.information(self, "Position", msg)
                else:
                    print("Invalid response for GET_POSITION")
            else:
                print("No response for GET_POSITION")
            socket.disconnectFromHost()
        else:
            print("Failed to connect to server")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ClientWindow()
    window.show()
    sys.exit(app.exec_())