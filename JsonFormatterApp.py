from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QPlainTextEdit, QTextEdit, QSplitter
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QPalette,
    QFontDatabase, QSyntaxHighlighter, QTextCharFormat, QTextCursor
)

import json
import sys

# ====== 行号编辑器 ======
class LineNumberArea(QWidget):
    """
    显示编辑器左侧行号的 QWidget
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        # 告诉布局管理器行号区域的宽度
        return QtCore.QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        # 代理绘制，由父 CodeEditor 处理
        self.editor.line_number_area_paint_event(event)


# ====== 支持行号的 QPlainTextEdit ======
class CodeEditor(QPlainTextEdit):
    """
    支持行号显示的 QPlainTextEdit
    并实现 placeholder 功能
    """
    def __init__(self, placeholder=""):
        super().__init__()
        self.placeholder = placeholder
        self.textChanged.connect(self.update)  # 内容变化时刷新 placeholder
        self.lineNumberArea = LineNumberArea(self)

        # 绑定信号
        self.blockCountChanged.connect(self.update_line_number_area_width)  # 块数量变化时更新宽度
        self.updateRequest.connect(self.update_line_number_area)  # 滚动/更新时刷新行号
        self.cursorPositionChanged.connect(self.highlight_current_line)  # 光标行高亮

        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)  # 不自动换行

        # 设置暗色背景和字体颜色
        self.setStyleSheet("""
        QPlainTextEdit {
            background-color: #2b2b2b;
            color: #f8f8f2;
            selection-background-color: #555555;
        }
        """)

    # ====== 行号宽度计算 ======
    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        # 设置编辑器左侧边距，为行号留空间
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        # 滚动或更新时刷新行号
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.line_number_area_width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        # 调整编辑器大小时，重新布局行号区域
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    # ====== 绘制行号 ======
    def line_number_area_paint_event(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(40, 40, 40))  # 背景
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

    # ====== 当前行高亮 ======
    def highlight_current_line(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(60, 60, 60)  # 当前行背景色
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    # ====== 绘制 placeholder ======
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.toPlainText() and self.placeholder:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(150, 150, 150))  # 灰色文字
            painter.drawText(self.viewport().rect().adjusted(4, 4, -4, -4),
                             Qt.AlignTop | Qt.AlignLeft,
                             self.placeholder)


# ====== 支持 placeholder 的 QTreeWidget ======
class PlaceholderTreeWidget(QTreeWidget):
    """
    扩展 QTreeWidget，空时显示 placeholder
    """
    def __init__(self, placeholder="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.placeholder = placeholder
        # 数据变化时刷新绘制 placeholder
        self.model().rowsInserted.connect(self.update)
        self.model().rowsRemoved.connect(self.update)
        self.model().modelReset.connect(self.update)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.topLevelItemCount() == 0 and self.placeholder:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(150, 150, 150))  # 灰色文字
            painter.drawText(self.viewport().rect().adjusted(4, 4, -4, -4),
                             Qt.AlignTop | Qt.AlignLeft,
                             self.placeholder)


# ====== JSON 格式化窗口 ======
class JsonFormatterWindow(QWidget):
    windows = []         # 所有窗口实例
    window_count = 0     # 窗口计数，用于区分标题

    def __init__(self):
        super().__init__()
        JsonFormatterWindow.window_count += 1
        self.window_number = JsonFormatterWindow.window_count
        self.setWindowTitle(f"JSON 格式化工具" + (f" {self.window_number}" if self.window_number > 1 else ""))
        self.resize(1200, 700)

        # 使用固定宽度字体
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(15)

        # ====== 输入编辑器 ======
        self.input_edit = CodeEditor(placeholder="原始 JSON")
        self.input_edit.setFont(font)
        self.input_edit.textChanged.connect(self.auto_format_input)  # 自动格式化 JSON

        # ====== 输出树 ======
        self.output_tree = PlaceholderTreeWidget(
            placeholder="JSON 树（折叠/展开）, 选中节点后可展示对应 JSON 结果"
        )
        self.output_tree.setHeaderHidden(True)
        self.output_tree.setFont(font)
        self.output_tree.itemClicked.connect(self.on_tree_item_clicked)

        # ====== 输出文本 ======
        self.output_edit = QTextEdit()
        self.output_edit.setPlaceholderText("JSON 结果（格式化输出）")  # ✅ 原生 placeholder
        # 添加 JSON 高亮器
        self.highlighter = JsonHighlighter(self.output_edit.document())
        self.output_edit.setFont(font)
        self.output_edit.setReadOnly(True)
        palette = self.output_edit.palette()
        palette.setColor(QPalette.PlaceholderText, QColor("#999999"))  # placeholder 灰色
        self.output_edit.setPalette(palette)

        # ====== 三栏布局 ======
        # 左侧：原始 JSON
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(2)
        left_layout.addWidget(self.input_edit)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        # 中间：JSON 树
        middle_layout = QVBoxLayout()
        middle_layout.setContentsMargins(0,0,0,0)
        middle_layout.setSpacing(2)
        middle_layout.addWidget(self.output_tree)
        middle_widget = QWidget()
        middle_widget.setLayout(middle_layout)

        # 右侧：JSON 结果
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(2)
        right_layout.addWidget(self.output_edit)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(right_widget)

        # 设置初始宽度比例：原始 JSON 1/5，JSON 树 2/5，JSON 结果 2/5
        total_width = self.width() if self.width() > 0 else 1200 # 默认宽度
        splitter.setSizes([
            int(total_width * 1 / 5),  # 原始 JSON
            int(total_width * 2 / 5),  # JSON 树
            int(total_width * 2 / 5)  # JSON 结果
        ])

        # 按钮
        btn_format = QPushButton("格式化")
        btn_compress = QPushButton("压缩")
        btn_save = QPushButton("保存")
        btn_copy = QPushButton("复制结果")

        # 绑定按钮事件
        btn_format.clicked.connect(self.format_json)
        btn_compress.clicked.connect(self.compress_json)
        btn_save.clicked.connect(self.save_file)
        btn_copy.clicked.connect(self.copy_result)

        btn_layout = QHBoxLayout()
        for btn in [btn_format, btn_compress, btn_copy, btn_save]:
            font = btn.font()
            font.setBold(True)  # 按钮加粗
            btn.setFont(font)
            btn_layout.addWidget(btn)

        # ====== 主布局 ======
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)  # 左上右下边距，顶部/底部间距缩小
        main_layout.setSpacing(2)  # 垂直间距缩小
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # ====== 菜单栏 ======
        menu_bar = QMenuBar()
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        new_action = file_menu.addAction("新建 JSON 窗口")
        new_action.triggered.connect(JsonFormatterWindow.new_window_static)
        open_action = file_menu.addAction("打开 JSON 文件")
        open_action.triggered.connect(self.open_file)
        main_layout.setMenuBar(menu_bar)

        # 新增帮助菜单
        help_menu = QMenu("帮助", self)
        menu_bar.addMenu(help_menu)
        # 添加“关于 JSON 格式化器”菜单项
        about_action = help_menu.addAction("关于 JSON 格式化器")
        about_action.triggered.connect(self.show_about_dialog)

        # 保存窗口引用
        JsonFormatterWindow.windows.append(self)

    # ====== 核心 JSON 处理逻辑 ======
    def process_json(self, text: str, show_error_dialog=True):
        """
        核心：格式化并渲染 JSON。
        支持字段值为 JSON 字符串的情况。
        :param text: 原始 JSON 文本
        :param show_error_dialog: 是否显示错误弹窗（自动模式下不弹）
        """
        if not text:
            self.output_tree.clear()
            self.output_edit.clear()
            return

        try:
            data = json.loads(text)

            # 递归解析嵌套 JSON 字符串
            def parse_nested(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if isinstance(v, str):
                            try:
                                obj[k] = json.loads(v)
                            except Exception:
                                pass
                        else:
                            parse_nested(v)
                elif isinstance(obj, list):
                    for i, v in enumerate(obj):
                        if isinstance(v, str):
                            try:
                                obj[i] = json.loads(v)
                            except Exception:
                                pass
                        else:
                            parse_nested(v)
                return obj

            data = parse_nested(data)

            # 更新树与右侧结果
            self.populate_tree(data)
            self.output_edit.setPlainText(json.dumps(data, indent=4, ensure_ascii=False))

        except json.JSONDecodeError as e:
            # 自动触发时不提示，只清空结果
            if show_error_dialog:
                QMessageBox.critical(self, "格式化失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")
            else:
                self.output_tree.clear()
                self.output_edit.clear()

    # ====== 自动格式化输入 JSON ======
    def auto_format_input(self):
        """
        自动格式化：实时解析输入（不弹窗提示错误）
        """
        text = self.input_edit.toPlainText().strip()
        self.process_json(text, show_error_dialog=False)

    # ====== 点击“格式化”按钮 ======
    def format_json(self):
        """
        按钮触发格式化：会显示错误提示框
        """
        text = self.input_edit.toPlainText().strip()
        self.process_json(text, show_error_dialog=True)

    # ====== 新建窗口静态方法 ======
    @staticmethod
    def new_window_static():
        win = JsonFormatterWindow()
        win.show()

    # ====== 构建树 ======
    def populate_tree(self, data, parent=None, key_name=None):
        """
        将 JSON 数据转换为 QTreeWidgetItem 树形结构
        """
        if parent is None:
            self.output_tree.clear()
            parent = self.output_tree

        color = QColor("#00FF7F")

        if isinstance(data, dict):
            item = QTreeWidgetItem([key_name] if key_name else "")
            item.setForeground(0, color)  # 设置文字颜色
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
            item.setForeground(0, color)  # 设置文字颜色
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
            item.setForeground(0, color)  # 设置文字颜色
            if parent is self.output_tree:
                parent.addTopLevelItem(item)
            else:
                parent.addChild(item)
            item.setData(0, QtCore.Qt.UserRole, (key_name, data))  # 存 key/value
            item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)

    # ====== 点击树节点显示对应 JSON ======
    def on_tree_item_clicked(self, item, column):
        """
        点击树节点时，在右侧显示对应 JSON，并高亮 key。
        """

        def item_to_json(it):
            """
            递归从树节点生成 JSON 数据。
            """
            child_count = it.childCount()
            # 叶子节点
            if child_count == 0:
                # 叶子节点直接取 UserRole 数据
                data = it.data(0, Qt.UserRole)
                if isinstance(data, tuple) and len(data) == 2:
                    key, value = data
                    return {key: value} if key else value
                else:
                    return data
            # 非叶子节点
            else:
                # 判断是否列表节点
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
            # 生成 JSON 数据
            node_data = item_to_json(item)
            json_text = json.dumps(node_data, indent=4, ensure_ascii=False)
            self.output_edit.setPlainText(json_text)

        except Exception:
            # 万一出错就直接显示文本
            self.output_edit.setPlainText(item.text(0))

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
            QMessageBox.critical(self, "压缩失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")

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
        """
        复制 JSON 结果到剪贴板，并显示提示
        """
        text = self.output_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            tip = QLabel("✅ JSON结果 已复制到剪贴板", self)
            tip.setStyleSheet("""
                background-color: #28a745;  /* 绿色提示 */
                color: white;              
                padding: 12px 20px;        
                border-radius: 8px;        
                font-size: 16pt;           
                font-weight: bold;
            """)
            tip.setAlignment(QtCore.Qt.AlignCenter)
            tip.setWindowFlags(QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint)
            tip.adjustSize()
            # 居中显示在窗口
            tip.move(self.geometry().center() - tip.rect().center())
            tip.show()
            QtCore.QTimer.singleShot(800, tip.close)  # 0.8秒自动关闭

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开 JSON 文件", "", "JSON 文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.input_edit.setPlainText(text)
            except Exception as e:
                QMessageBox.critical(self, "打开失败", str(e))

    def show_about_dialog(self):
        """
        显示关于对话框
        """
        version = "v2.0.2"
        info = f"""
        <h3>JSON 格式化查看器 {version}</h3>
        <p>桌面版 JSON 可视化工具。</p>
        <p>支持 JSON 格式化、压缩、树形展示等功能。</p>
        <p>作者：lawliet</p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("关于 JSON 格式化器")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.formats = {
            "key": self.make_format("#1E90FF"),                 # 键，深天蓝色
            "string": self.make_format("#FFA500"),              # 字符串
            "number": self.make_format("#56b6c2"),              # 数字
            "bool": self.make_format("#e5c07b"),                # 布尔值
            "null": self.make_format("#FF1493"),                # null
            "highlight": self.make_format("#ffffff", bg="#4b5cc4", bold=True)  # 点击高亮
        }

    def make_format(self, color, bg=None, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bg:
            fmt.setBackground(QColor(bg))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    def highlightBlock(self, text):
        import re

        # ---- 1. 匹配 key ----
        for match in re.finditer(r'"(.*?)"\s*:', text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.formats["key"])

        # ---- 2. 匹配字符串 ----
        # 冒号后面跟双引号里的内容，包括日期时间等
        for match in re.finditer(r':\s*"([^"]*)"', text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.formats["string"])

        # ---- 3. 匹配布尔值/Null ----
        # 只匹配不在引号内的 true/false/null
        for match in re.finditer(r':\s*(true|false|null)(?=[,\}\]])', text):
            val = match.group(1)
            fmt = self.formats["null"] if val == "null" else self.formats["bool"]
            self.setFormat(match.start(1), match.end(1) - match.start(1), fmt)

        # ---- 4. 匹配数字 ----
        # 只匹配冒号后跟的纯数字，不匹配带空格或在字符串内的数字
        for match in re.finditer(r':\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?=[,\}\]])', text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.formats["number"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
