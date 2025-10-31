from PySide6 import QtCore
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QPlainTextEdit, QTextEdit, QSplitter
)
from PySide6.QtGui import QFont, QColor, QPainter, QTextFormat
import json
import sys

# ====== 行号编辑器 ======
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

# ====== JSON 格式化窗口 ======
class JsonFormatterWindow(QWidget):
    windows = []
    window_count = 0

    def __init__(self):
        super().__init__()
        JsonFormatterWindow.window_count += 1
        self.window_number = JsonFormatterWindow.window_count
        self.setWindowTitle(f"JSON 格式化工具" + (f" {self.window_number}" if self.window_number > 1 else ""))
        self.resize(1200, 700)

        font = QFont("Consolas", 15)

        # 输入编辑器
        self.input_edit = CodeEditor()
        self.input_edit.setFont(font)

        # 用户输入json后自动进行格式化
        self.input_edit.textChanged.connect(self.auto_format_input)

        # 输出树
        self.output_tree = QTreeWidget()
        self.output_tree.setHeaderHidden(True)
        self.output_tree.setFont(font)
        self.output_tree.itemClicked.connect(self.on_tree_item_clicked)

        # 输出文本
        self.output_edit = QTextEdit()
        self.output_edit.setFont(font)
        self.output_edit.setReadOnly(True)

        # 标签
        label_input = QLabel("原始 JSON")
        label_tree = QLabel("JSON 树（折叠/展开）")
        label_output = QLabel("JSON 结果（可复制）")
        for lbl in [label_input, label_tree, label_output]:
            lbl.setAlignment(QtCore.Qt.AlignCenter)

        # 三栏 splitter
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(2)
        left_layout.addWidget(label_input)
        left_layout.addWidget(self.input_edit)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        middle_layout = QVBoxLayout()
        middle_layout.setContentsMargins(0,0,0,0)
        middle_layout.setSpacing(2)
        middle_layout.addWidget(label_tree)
        middle_layout.addWidget(self.output_tree)
        middle_widget = QWidget()
        middle_widget.setLayout(middle_layout)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(2)
        right_layout.addWidget(label_output)
        right_layout.addWidget(self.output_edit)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0,1)
        splitter.setStretchFactor(1,1)
        splitter.setStretchFactor(2,1)

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
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # 菜单栏
        menu_bar = QMenuBar()
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        new_action = file_menu.addAction("新建 JSON 窗口")
        new_action.triggered.connect(JsonFormatterWindow.new_window_static)
        open_action = file_menu.addAction("打开 JSON 文件")
        open_action.triggered.connect(self.open_file)
        main_layout.setMenuBar(menu_bar)

        JsonFormatterWindow.windows.append(self)

    def auto_format_input(self):
        """
        当原始 JSON 编辑器内容变化时，自动格式化
        """
        text = self.input_edit.toPlainText().strip()
        if not text:
            self.output_tree.clear()
            self.output_edit.clear()
            return
        try:
            data = json.loads(text)
            # 更新树和右侧结果区域
            self.populate_tree(data)
            self.output_edit.setPlainText(json.dumps(data, indent=4, ensure_ascii=False))
        except json.JSONDecodeError:
            # JSON 不完整或非法，不更新
            pass

    @staticmethod
    def new_window_static():
        win = JsonFormatterWindow()
        win.show()

    # ====== 构建树 ======
    def populate_tree(self, data, parent=None, key_name=None):
        if parent is None:
            self.output_tree.clear()
            parent = self.output_tree

        if isinstance(data, dict):
            item = QTreeWidgetItem([key_name] if key_name else "")
            if parent is self.output_tree:
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)
            item.setExpanded(True)
            item.setData(0, QtCore.Qt.UserRole, data)  # 存储完整数据
            for k, v in data.items():
                self.populate_tree(v, item, k)

        elif isinstance(data, list):
            item = QTreeWidgetItem([key_name] if key_name else "")
            if parent is self.output_tree:
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)
            item.setExpanded(True)
            item.setData(0, QtCore.Qt.UserRole, data)  # 存储完整数据
            for i, v in enumerate(data):
                self.populate_tree(v, item, f"[{i}]")

        else:
            text = f"{key_name}: {data}" if key_name else str(data)
            item = QTreeWidgetItem([text])
            if parent is self.output_tree:
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)
            item.setData(0, QtCore.Qt.UserRole, (key_name, data))  # 存 key/value
            item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)

    # ====== 点击树节点显示正确 JSON ======
    def on_tree_item_clicked(self, item, column):
        def item_to_json(it):
            child_count = it.childCount()
            # 叶子节点
            if child_count == 0:
                data = it.data(0, QtCore.Qt.UserRole)
                if isinstance(data, tuple) and len(data) == 2:
                    key, value = data
                    return {key: value} if key else value
                else:
                    return data
            # 非叶子节点
            else:
                is_list = all(it.child(i).text(0).startswith('[') for i in range(child_count))
                if is_list:
                    return [item_to_json(it.child(i)) for i in range(child_count)]
                else:
                    result = {}
                    for i in range(child_count):
                        child = it.child(i)
                        key = child.text(0).split(":", 1)[0] if ":" in child.text(0) else child.text(0)
                        value = item_to_json(child)
                        # 如果 value 已经是 dict 包裹，则展开
                        if isinstance(value, dict) and len(value) == 1 and list(value.keys())[0] == key:
                            value = list(value.values())[0]
                        result[key] = value
                    return result

            try:
                node_data = item_to_json(item)
                self.output_edit.setPlainText(json.dumps(node_data, indent=4, ensure_ascii=False))
            except Exception:
                self.output_edit.setPlainText(item.text(0))

        try:
            node_data = item_to_json(item)
            self.output_edit.setPlainText(json.dumps(node_data, indent=4, ensure_ascii=False))
        except Exception:
            self.output_edit.setPlainText(item.text(0))

    # ====== 功能实现 ======
    def format_json(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        try:
            data = json.loads(text)
            self.populate_tree(data)
            self.output_edit.setPlainText(json.dumps(data, indent=4, ensure_ascii=False))
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
            self.populate_tree(json.loads(compressed))
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

            # 自动消失提示
            tip = QLabel("✅ JSON结果 已复制到剪贴板", self)
            tip.setStyleSheet("""
                background-color: #28a745;  /* 鲜绿色背景 */
                color: white;              /* 白色文字 */
                padding: 12px 20px;        /* 较大内边距 */
                border-radius: 8px;        /* 圆角 */
                font-size: 16pt;           /* 大字体 */
                font-weight: bold;
            """)
            tip.setAlignment(QtCore.Qt.AlignCenter)
            tip.setWindowFlags(QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
            tip.adjustSize()
            # 居中显示在窗口
            tip.move(self.geometry().center() - tip.rect().center())
            tip.show()

            # 1.5秒后自动关闭
            QtCore.QTimer.singleShot(800, tip.close)

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开 JSON 文件", "", "JSON 文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.input_edit.setPlainText(text)
            except Exception as e:
                QMessageBox.critical(self, "打开失败", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
