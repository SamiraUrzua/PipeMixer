import sys
from PySide6.QtWidgets import QApplication
from pipewire_manager import PipewireManager, PWMonitor
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PipeMixer")

    cache   = PipewireManager()
    monitor = PWMonitor(cache)
    monitor.start()

    window = MainWindow(cache, monitor)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()