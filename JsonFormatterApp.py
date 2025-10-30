from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QFileDialog, QMessageBox, QLabel, QTextEdit, QMenuBar, QMenu
)
from PySide6.QtGui import QFont, QColor, QPainter, QTextFormat
import json
import sys

# ====== 行号边栏 ======
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QtCore.QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


# ====== 支持行号的 QPlainTextEdit ======
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.setStyleSheet("""
        QPlainTextEdit {
            background-color: #2b2b2b;
            color: #f8f8f2;
            selection-background-color: #555555;
        }
        """)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.line_number_area_width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(40, 40, 40))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(200, 200, 200))
                painter.drawText(0, top, self.lineNumberArea.width() - 2, self.fontMetrics().height(),
                                 QtCore.Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlight_current_line(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(60, 60, 60)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)


# ====== 单个 JSON 窗口 ======
class JsonFormatterWindow(QWidget):
    windows = []  # 全局管理所有窗口引用

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON 格式化工具")
        self.resize(1000, 600)

        # 输入输出
        self.input_edit = CodeEditor()
        self.output_edit = CodeEditor()
        self.output_edit.setReadOnly(True)
        font = QFont("Consolas", 15)
        self.input_edit.setFont(font)
        self.output_edit.setFont(font)

        # 标签
        label_input = QLabel("原始 JSON")
        label_output = QLabel("结果 JSON")
        label_input.setAlignment(QtCore.Qt.AlignCenter)
        label_output.setAlignment(QtCore.Qt.AlignCenter)

        # 左右布局
        text_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        left_layout.addWidget(label_input)
        left_layout.addWidget(self.input_edit)
        right_layout.addWidget(label_output)
        right_layout.addWidget(self.output_edit)
        text_layout.addLayout(left_layout, 1)
        text_layout.addLayout(right_layout, 1)

        # 按钮
        btn_format = QPushButton("格式化")
        btn_compress = QPushButton("压缩")
        btn_save = QPushButton("保存")
        btn_copy = QPushButton("复制结果")
        btn_format.clicked.connect(self.format_json)
        btn_compress.clicked.connect(self.compress_json)
        btn_save.clicked.connect(self.save_file)
        btn_copy.clicked.connect(self.copy_result)
        btn_layout = QHBoxLayout()
        for btn in [btn_format, btn_compress, btn_copy, btn_save]:
            btn_layout.addWidget(btn)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(btn_layout)
        main_layout.addLayout(text_layout)
        self.setLayout(main_layout)

        # 添加到全局窗口管理
        JsonFormatterWindow.windows.append(self)

        # 菜单栏（mac 顶部显示）
        menu_bar = QMenuBar()
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        new_action = file_menu.addAction("新建 JSON 窗口")
        new_action.triggered.connect(JsonFormatterWindow.new_window_static)
        main_layout.setMenuBar(menu_bar)

    # 静态方法新建窗口
    @staticmethod
    def new_window_static():
        win = JsonFormatterWindow()
        win.show()

    # 功能实现
    def format_json(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        try:
            data = json.loads(text)
            formatted = json.dumps(data, indent=4, ensure_ascii=False)
            self.output_edit.setPlainText(formatted)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "格式化失败",
                                 f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")

    def compress_json(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        try:
            data = json.loads(text)
            compressed = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            self.output_edit.setPlainText(compressed)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "压缩失败",
                                 f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")

    def save_file(self):
        text = self.output_edit.toPlainText().strip()
        if not text:
            return
        file_name, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "JSON 文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(text)
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))

    def copy_result(self):
        text = self.output_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "复制成功", "结果 JSON 已复制到剪贴板")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
