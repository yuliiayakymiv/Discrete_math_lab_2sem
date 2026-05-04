import os
import sys

# Makes imports work when this file is placed in the project root folder.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from algorithms.arithmetic_coding import arithmetic_compress, arithmetic_decompress
from algorithms.deflate import deflate_compress_bytes, deflate_decompress_bytes
from algorithms.huffman import huffman_compress, huffman_decompress
from algorithms.lz77 import lz77_compress, lz77_decompress
from algorithms.lzma import compress as lzma_compress, decompress as lzma_decompress
from algorithms.lzw_alg import lzw_compress, lzw_decompress
from algorithms.run_length_encoding import rle_compress, rle_decompress
from algorithms.burrows_wheeler_transform import bwt_compress, bwt_decompress


ALGORITHMS: dict[str, dict] = {
    "Huffman": {
        "compress": huffman_compress,
        "decompress": huffman_decompress,
        "description": "Prefix-free entropy coding. Good for text and binary data.",
        "extensions": [".txt", ".csv", ".json", ".bin", ".jpg", ".bmp", ".wav"],
    },
    "LZW": {
        "compress": lzw_compress,
        "decompress": lzw_decompress,
        "description": "Dictionary compression. Best for repetitive text-like files.",
        "extensions": [".txt", ".csv", ".json", ".bin"],
    },
    "LZ77": {
        "compress": lz77_compress,
        "decompress": lz77_decompress,
        "description": "Sliding-window compression. Good for repeated fragments.",
        "extensions": [".txt", ".csv", ".json", ".bin", ".tiff"],
    },
    "LZMA": {
        "compress": lzma_compress,
        "decompress": lzma_decompress,
        "description": "High compression ratio, but slower than simple algorithms.",
        "extensions": [".txt", ".csv", ".json", ".bin"],
    },
    "Deflate": {
        "compress": deflate_compress_bytes,
        "decompress": deflate_decompress_bytes,
        "description": "LZ77 + Huffman. Similar idea to ZIP/gzip/PNG.",
        "extensions": [".txt", ".csv", ".json", ".bin", ".jpg", ".bmp", ".wav"],
    },
    "RLE": {
        "compress": rle_compress,
        "decompress": rle_decompress,
        "description": "Run-length encoding. Best only when many equal bytes repeat.",
        "extensions": [".txt", ".bin", ".bmp", ".tiff"],
    },
    "BWT": {
        "compress": bwt_compress,
        "decompress": bwt_decompress,
        "description": "Burrows-Wheeler transform. Works well for text data.",
        "extensions": [".txt", ".csv", ".json", ".bin"],
    },
    "Arithmetic": {
        "compress": arithmetic_compress,
        "decompress": arithmetic_decompress,
        "description": "Entropy coding. Can get close to theoretical limit.",
        "extensions": [".txt", ".csv", ".json", ".bin"],
    },
}


class CompressionWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, mode: str, algorithm_name: str, input_path: str, output_folder: str):
        super().__init__()
        self.mode = mode
        self.algorithm_name = algorithm_name
        self.input_path = input_path
        self.output_folder = output_folder

    def _make_output_path(self) -> str:
        base_name = os.path.basename(self.input_path)
        name, ext = os.path.splitext(base_name)
        safe_alg = self.algorithm_name.lower().replace(" ", "_")

        if self.mode == "compress":
            filename = f"{name}_{safe_alg}_compressed.bin"
        else:
            filename = f"{name}_{safe_alg}_decompressed{ext if ext != '.bin' else '.out'}"

        path = os.path.join(self.output_folder, filename)
        counter = 1
        root, extension = os.path.splitext(path)
        while os.path.exists(path):
            path = f"{root}_{counter}{extension}"
            counter += 1
        return path

    def run(self):
        try:
            meta = ALGORITHMS[self.algorithm_name]
            with open(self.input_path, "rb") as file:
                data = file.read()

            if self.mode == "compress":
                result = meta["compress"](data)
            else:
                result = meta["decompress"](data)

            os.makedirs(self.output_folder, exist_ok=True)
            output_path = self._make_output_path()
            with open(output_path, "wb") as file:
                file.write(result)

            self.finished.emit(True, output_path)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class DropZone(QFrame):
    file_dropped = pyqtSignal(str)

    IDLE_STYLE = """
        QFrame {
            border: 3px dashed #ff00ff;
            border-radius: 0px;
            background-color: #e8f7ff;
        }
    """
    HOVER_STYLE = """
        QFrame {
            border: 3px dashed #00ffff;
            border-radius: 0px;
            background-color: #ffffcc;
        }
    """

    def __init__(self, mode_text: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet(self.IDLE_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel("💾")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 36px; border: none; background: transparent;")

        self.text_label = QLabel(mode_text)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet(
            "font-size: 14px; color: #000080; font-weight: bold; border: none; background: transparent;"
        )

        self.file_name_label = QLabel("")
        self.file_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_name_label.setStyleSheet(
            "font-size: 13px; color: #cc0000; font-weight: bold; border: none; background: transparent;"
        )

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.file_name_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.HOVER_STYLE)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.IDLE_STYLE)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self.IDLE_STYLE)
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(self, "Choose file")
        if path:
            self.file_dropped.emit(path)

    def set_file(self, path: str):
        self.icon_label.setText("✅")
        self.file_name_label.setText(os.path.basename(path))

    def reset(self):
        self.icon_label.setText("💾")
        self.file_name_label.setText("")


class RatioBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ratio = 0.0
        self._orig = 0
        self._comp = 0
        self.setMinimumHeight(45)
        self.setVisible(False)

    def set_ratio(self, original: int, compressed: int):
        self.ratio = compressed / original if original > 0 else 0.0
        self._orig = original
        self._comp = compressed
        self.setVisible(True)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.setBrush(QColor("#000080"))
        painter.setPen(QColor("#ffffff"))
        painter.drawRect(0, 6, w - 1, h - 12)

        fill_w = min(int(w * self.ratio), w)
        painter.setBrush(QColor("#00ff00") if self.ratio < 1 else QColor("#ff4040"))
        painter.drawRect(1, 7, max(fill_w - 2, 0), h - 14)

        percent = round(self.ratio * 100, 1)
        text = f"{round(self._orig / 1024, 2)} KB  ->  {round(self._comp / 1024, 2)} KB  ({percent}%)"
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class ModeTab(QWidget):
    def __init__(self, mode: str, parent_window):
        super().__init__()
        self.mode = mode
        self.parent_window = parent_window
        self.selected_file: str | None = None
        self.selected_size = 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        text = "CLICK OR DROP FILE TO COMPRESS" if self.mode == "compress" else "CLICK OR DROP .BIN FILE TO DECOMPRESS"
        self.drop_zone = DropZone(text)
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self.drop_zone)

        row = QHBoxLayout()
        label = QLabel("ALGORITHM:")
        label.setFixedWidth(120)
        label.setStyleSheet("font-weight: bold; color: #000080;")
        self.alg_box = QComboBox()
        self.alg_box.addItems(list(ALGORITHMS.keys()))
        self.alg_box.currentTextChanged.connect(self._on_alg_changed)
        row.addWidget(label)
        row.addWidget(self.alg_box, 1)
        layout.addLayout(row)

        self.alg_desc = QLabel("")
        self.alg_desc.setWordWrap(True)
        self.alg_desc.setStyleSheet("color: #660066; font-weight: bold;")
        layout.addWidget(self.alg_desc)

        self.ext_hint = QLabel("")
        self.ext_hint.setStyleSheet("color: #000080;")
        layout.addWidget(self.ext_hint)

        folder_row = QHBoxLayout()
        folder_label = QLabel("SAVE TO:")
        folder_label.setFixedWidth(120)
        folder_label.setStyleSheet("font-weight: bold; color: #000080;")
        self.output_folder = QLineEdit(os.getcwd())
        self.output_folder.setReadOnly(True)
        self.choose_folder_btn = QPushButton("Browse...")
        self.choose_folder_btn.clicked.connect(self._choose_output_folder)
        folder_row.addWidget(folder_label)
        folder_row.addWidget(self.output_folder, 1)
        folder_row.addWidget(self.choose_folder_btn)
        layout.addLayout(folder_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.action_btn = QPushButton("COMPRESS NOW" if self.mode == "compress" else "DECOMPRESS NOW")
        self.action_btn.setMinimumHeight(48)
        self.action_btn.clicked.connect(self._start)
        layout.addWidget(self.action_btn)

        self.ratio_bar = RatioBar()
        layout.addWidget(self.ratio_bar)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #cc0000; font-weight: bold;")
        layout.addWidget(self.status)

        layout.addStretch()
        self._on_alg_changed(self.alg_box.currentText())

    def _on_alg_changed(self, name: str):
        meta = ALGORITHMS.get(name, {})
        self.alg_desc.setText("INFO: " + meta.get("description", ""))
        self.ext_hint.setText("SUPPORTED: " + "  ".join(meta.get("extensions", [])))

    def _on_file_selected(self, path: str):
        if not os.path.isfile(path):
            QMessageBox.warning(self, "File not found", "Selected path is not a file.")
            return

        if self.mode == "decompress" and os.path.splitext(path)[1].lower() != ".bin":
            answer = QMessageBox.question(
                self,
                "Not a .bin file",
                "This does not look like a compressed .bin file. Try anyway?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self.selected_file = path
        self.selected_size = os.path.getsize(path)
        self.drop_zone.set_file(path)
        self.ratio_bar.setVisible(False)
        self.status.setText(f"READY: {os.path.basename(path)} ({round(self.selected_size / 1024, 2)} KB)")

    def _choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_folder.text())
        if folder:
            self.output_folder.setText(folder)

    def _start(self):
        if not self.selected_file:
            QMessageBox.warning(self, "No file", "Choose a file first.")
            return

        folder = self.output_folder.text().strip()
        if not folder:
            QMessageBox.warning(self, "No output folder", "Choose where to save the output file.")
            return

        algorithm = self.alg_box.currentText()
        ext = os.path.splitext(self.selected_file)[1].lower()
        allowed = ALGORITHMS[algorithm]["extensions"]

        if self.mode == "compress" and ext not in allowed:
            QMessageBox.warning(
                self,
                "Wrong file type",
                f"{algorithm} does not support {ext}.\nAllowed: {', '.join(allowed)}",
            )
            return

        self.parent_window.run_worker(self, self.mode, algorithm, self.selected_file, folder)

    def set_busy(self, busy: bool):
        self.progress.setVisible(busy)
        self.action_btn.setEnabled(not busy)
        self.alg_box.setEnabled(not busy)
        self.choose_folder_btn.setEnabled(not busy)

    def reset(self):
        self.selected_file = None
        self.selected_size = 0
        self.drop_zone.reset()
        self.ratio_bar.setVisible(False)
        self.status.setText("")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(QSize(860, 700))
        self.setWindowTitle("Codec MEOW")
        self.worker: CompressionWorker | None = None
        self.active_tab: ModeTab | None = None
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet("""
            QWidget {
                background-color: #c0c0c0;
                color: #000000;
                font-family: 'MS Sans Serif', 'Tahoma', sans-serif;
                font-size: 12px;
            }
            QLabel#title {
                color: #ffff00;
                background-color: #000080;
                font-size: 30px;
                font-weight: bold;
                padding: 10px;
                border: 3px outset #ffffff;
            }
            QTabWidget::pane {
                border: 3px outset #ffffff;
                background: #dcdcdc;
            }
            QTabBar::tab {
                background: #b0b0b0;
                color: #000080;
                padding: 8px 24px;
                border: 2px outset #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #ffffcc;
                color: #cc0000;
            }
            QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 3px outset #ffffff;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffffcc;
                color: #000080;
            }
            QPushButton:pressed {
                border: 3px inset #ffffff;
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                color: #777777;
                background-color: #aaaaaa;
            }
            QComboBox, QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 2px inset #ffffff;
                padding: 6px;
            }
            QProgressBar {
                border: 2px inset #ffffff;
                background: #ffffff;
                min-height: 16px;
            }
            QProgressBar::chunk {
                background-color: #000080;
            }
        """)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        title = QLabel("Codec MEOW")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # subtitle = QLabel("separate tabs · custom output folder")
        # subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # subtitle.setStyleSheet("color: #000080; font-weight: bold;")
        # layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.compress_tab = ModeTab("compress", self)
        self.decompress_tab = ModeTab("decompress", self)
        self.tabs.addTab(self.compress_tab, "COMPRESSION")
        self.tabs.addTab(self.decompress_tab, "DECOMPRESSION")
        layout.addWidget(self.tabs, 1)

        footer = QLabel("Dream Team © 2026")
        #footer = QLabel("Huffman | LZW | LZ77 | LZMA | Deflate | RLE | BWT | Arithmetic")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #660066; font-weight: bold;")
        layout.addWidget(footer)

    def run_worker(self, tab: ModeTab, mode: str, algorithm: str, input_path: str, output_folder: str):
        self.active_tab = tab
        tab.set_busy(True)
        tab.status.setText(("COMPRESSING" if mode == "compress" else "DECOMPRESSING") + f" WITH {algorithm}...")

        self.worker = CompressionWorker(mode, algorithm, input_path, output_folder)
        self.worker.finished.connect(lambda ok, msg: self._worker_done(tab, mode, algorithm, ok, msg))
        self.worker.start()

    def _worker_done(self, tab: ModeTab, mode: str, algorithm: str, success: bool, message: str):
        tab.set_busy(False)

        if not success:
            QMessageBox.warning(self, "Operation failed", message or "Unknown error.")
            tab.status.setText("ERROR. OPERATION FAILED.")
            return

        if mode == "compress" and os.path.exists(message):
            compressed_size = os.path.getsize(message)
            tab.ratio_bar.set_ratio(tab.selected_size, compressed_size)

        tab.status.setText(f"DONE. SAVED TO: {message}")
        QMessageBox.information(self, "Done", f"Saved to:\n{message}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
