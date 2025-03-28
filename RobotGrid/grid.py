import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPen, QBrush, QColor, QPalette, QPixmap, QPainter
from PyQt5.QtNetwork import QTcpServer, QHostAddress

class Robot:
    def __init__(self):
        self.x = 7  # Start at center of 15x15 grid (0 to 14)
        self.y = 7
        self.direction = 0  # 0=north (up), 90=east (right), 180=south (down), 270=west (left)

    def move_forward(self, n):
        if self.direction == 0:    self.y -= n  # Up
        elif self.direction == 90:  self.x += n  # Right
        elif self.direction == 180: self.y += n  # Down
        elif self.direction == 270: self.x -= n  # Left
        self.wrap_position()

    def move_backward(self, n):
        if self.direction == 0:    self.y += n
        elif self.direction == 90:  self.x -= n
        elif self.direction == 180: self.y -= n
        elif self.direction == 270: self.x += n
        self.wrap_position()

    def turn_left(self):
        self.direction = (self.direction - 90) % 360

    def turn_right(self):
        self.direction = (self.direction + 90) % 360

    def center(self):
        self.x = 7
        self.y = 7

    def wrap_position(self):
        self.x = self.x % 15
        self.y = self.y % 15

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Display")
        self.setGeometry(100, 100, 620, 650)  # Fits 600x600 scene + controls

        # Dark mode palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        self.setPalette(palette)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Graphics view and scene
        self.view = QGraphicsView()
        self.scene = QGraphicsScene(0, 0, 600, 600)  # 15x15 grid, 40 units/cell
        self.scene.setBackgroundBrush(QBrush(QColor(25, 25, 25)))
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        # Draw 15x15 grid
        pen = QPen(Qt.white)
        for i in range(0, 601, 40):
            self.scene.addLine(i, 0, i, 600, pen)
            self.scene.addLine(0, i, 600, i, pen)

        # Initialize robot with icon
        self.robot = Robot()
        self.robot_item = QGraphicsPixmapItem()
        self.scene.addItem(self.robot_item)

        # Load robot image
        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "robot.jpg")
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Error: {image_path} not found, using default image")
            pixmap = QPixmap(40, 40)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(Qt.blue))
            painter.drawEllipse(0, 0, 40, 40)
            painter.end()
            self.robot_item.setPixmap(pixmap)
            self.robot_item.setTransformOriginPoint(20, 20)
        else:
            pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.robot_item.setPixmap(pixmap)
            self.robot_item.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)

        # Set initial position and rotation
        w = self.robot_item.pixmap().width()
        h = self.robot_item.pixmap().height()
        pos_x = self.robot.x * 40 + 20 - w / 2
        pos_y = self.robot.y * 40 + 20 - h / 2
        self.robot_item.setPos(pos_x, pos_y)
        self.robot_item.setRotation(self.robot.direction)

        # Center button
        self.center_button = QPushButton("Center Robot")
        self.center_button.clicked.connect(self.on_center_clicked)
        layout.addWidget(self.center_button)

        # Status label
        direction_text = {0: "Up", 90: "Right", 180: "Down", 270: "Left"}[self.robot.direction]
        self.status_label = QLabel(f"Grid: 15x15 | Position: ({self.robot.x}, {self.robot.y}), Facing: {direction_text}")
        layout.addWidget(self.status_label)

        # TCP server
        self.server = QTcpServer(self)
        if not self.server.listen(QHostAddress("127.0.0.1"), 12345):
            print("Failed to start server")
            sys.exit(1)
        self.server.newConnection.connect(self.handle_connection)

        # Command queue and timer
        self.command_queue = []
        self.timer = QTimer(self)
        self.timer.setInterval(500)  # 500ms delay between commands
        self.timer.timeout.connect(self.process_next_command)

    def update_robot(self):
        if not self.robot_item.pixmap().isNull():
            w = self.robot_item.pixmap().width()
            h = self.robot_item.pixmap().height()
            pos_x = self.robot.x * 40 + 20 - w / 2
            pos_y = self.robot.y * 40 + 20 - h / 2
            self.robot_item.setPos(pos_x, pos_y)
            self.robot_item.setRotation(self.robot.direction)

            # Update status label
            direction_text = {0: "Up", 90: "Right", 180: "Down", 270: "Left"}[self.robot.direction]
            self.status_label.setText(f"Grid: 15x15 | Position: ({self.robot.x}, {self.robot.y}), Facing: {direction_text}")

    def on_center_clicked(self):
        self.robot.center()
        self.update_robot()

    def handle_connection(self):
        client_socket = self.server.nextPendingConnection()
        client_socket.waitForReadyRead()
        data = client_socket.readAll().data().decode()
        commands = [cmd.strip() for cmd in data.splitlines() if cmd.strip()]
        for command in commands:
            if command.upper() == "GET_DIMENSIONS":
                client_socket.write("15 15\n".encode())
            elif command.upper() == "GET_POSITION":
                response = f"{self.robot.x} {self.robot.y} {self.robot.direction}\n"
                client_socket.write(response.encode())
            else:
                # Process as action command
                parts = command.split()
                if not parts:
                    continue
                cmd = parts[0].upper()
                if cmd == "TURN" and len(parts) == 2:
                    dir = parts[1].upper()
                    if dir == "LEFT":
                        self.command_queue.append("TURN LEFT")
                    elif dir == "RIGHT":
                        self.command_queue.append("TURN RIGHT")
                    else:
                        print(f"Invalid turn direction: {dir}")
                elif cmd in ["FORWARD", "BACKWARD"] and len(parts) == 2:
                    try:
                        steps = int(parts[1])
                        action = "FORWARD 1" if cmd == "FORWARD" else "BACKWARD 1"
                        self.command_queue.extend([action] * steps)
                    except ValueError:
                        print(f"Invalid steps for {cmd}: {parts[1]}")
                else:
                    print(f"Unknown command: {command}")
                client_socket.write("OK\n".encode())  # Acknowledge action command
        if self.command_queue and not self.timer.isActive():
            self.timer.start()
        client_socket.disconnectFromHost()

    def process_next_command(self):
        if self.command_queue:
            command = self.command_queue.pop(0)
            self.process_command(command)
        else:
            self.timer.stop()

    def process_command(self, command):
        if command == "TURN LEFT":
            self.robot.turn_left()
        elif command == "TURN RIGHT":
            self.robot.turn_right()
        elif command == "FORWARD 1":
            self.robot.move_forward(1)
        elif command == "BACKWARD 1":
            self.robot.move_backward(1)
        else:
            print(f"Unknown command in queue: {command}")
        self.update_robot()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())