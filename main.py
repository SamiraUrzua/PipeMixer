import sys
from PySide6.QtWidgets import QApplication
from pipewire_manager import PipewireManager, PWMonitor
from main_window import MainWindow
from theme import apply_theme
from version import __version__


def main():
    app = QApplication(sys.argv)
    
    app.setApplicationName(f"PipeMixer v{__version__}")
    apply_theme(app)

    cache   = PipewireManager()
    monitor = PWMonitor(cache)
    monitor.start()

    window = MainWindow(cache, monitor)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()