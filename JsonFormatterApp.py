from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QPlainTextEdit, QTextEdit, QSplitter, QLineEdit
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QPalette,
    QFontDatabase, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QShortcut, QKeySequence
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
        # self.setStyleSheet("""
        # QPlainTextEdit {
        #     background-color: #2b2b2b;
        #     color: #f8f8f2;
        #     selection-background-color: #555555;
        # }
        # """)

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
        # 添加右键菜单
        self.output_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output_tree.customContextMenuRequested.connect(self.open_tree_context_menu)

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

        middle_widget.setMinimumWidth(0)  # 允许中间结果树最小宽度为 0
        # 设置初始宽度比例：原始 JSON 3/6，JSON 树 0/6，JSON 结果 3/3
        total_width = self.width() if self.width() > 0 else 1200 # 默认宽度
        splitter.setSizes([
            int(total_width * 3 / 6),  # 原始 JSON
            int(total_width * 0 / 6),  # JSON 树
            int(total_width * 3 / 6)  # JSON 结果
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

        # ===== 搜索框（两栏）=====
        self.search_panels = {
            "input": SearchPanel(self, self.input_edit),
            "output": SearchPanel(self, self.output_edit)
        }

        for p in self.search_panels.values():
            p.hide()

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.open_search)
        QShortcut(QKeySequence("Cmd+F"), self, activated=self.open_search)
        QShortcut(QKeySequence("F3"), self, activated=self.next_match_current)
        QShortcut(QKeySequence("Shift+F3"), self, activated=self.prev_match_current)

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
            self.output_edit.setPlainText("")
            self.highlighter.rehighlight()
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
            json_text = json.dumps(data, indent=4, ensure_ascii=False)
            self.output_edit.setPlainText(json_text)
            self.highlighter.rehighlight()  # 🔹 确保高亮

        except json.JSONDecodeError as e:
            # 自动触发时不提示，只清空结果
            if show_error_dialog:
                QMessageBox.critical(self, "格式化失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")
            else:
                self.output_tree.clear()
                self.output_edit.setPlainText("")
                self.highlighter.rehighlight()

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

        # 设置中间树的文字颜色
        color = QColor("#62b37a")

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
            # 🔹 确保高亮显示
            self.highlighter.rehighlight()

        except Exception:
            # 万一出错就直接显示文本
            self.output_edit.setPlainText(item.text(0))
            self.highlighter.rehighlight()

    # ====== 右键菜单 ======
    def open_tree_context_menu(self, position):
        """
        显示树形控件的右键菜单
        """
        menu = QMenu()
        
        # 获取当前选中的节点
        item = self.output_tree.itemAt(position)
        
        # 只有选中节点时才显示相关选项
        if item:
            expand_action = menu.addAction("展开此节点")
            expand_action.triggered.connect(lambda: item.setExpanded(True))
            
            collapse_action = menu.addAction("折叠此节点")
            collapse_action.triggered.connect(lambda: item.setExpanded(False))
            
            menu.addSeparator()
            
            expand_recursive_action = menu.addAction("递归展开此节点")
            expand_recursive_action.triggered.connect(lambda: self.expand_recursive(item))
            
            collapse_recursive_action = menu.addAction("递归折叠此节点")
            collapse_recursive_action.triggered.connect(lambda: self.collapse_recursive(item))
            
            menu.addSeparator()
            
            collapse_others_action = menu.addAction("折叠其他同级节点")
            collapse_others_action.triggered.connect(lambda: self.collapse_others(item))
            
            menu.addSeparator()

        # 全局选项
        expand_all_action = menu.addAction("展开全部")
        expand_all_action.triggered.connect(self.output_tree.expandAll)
        
        collapse_all_action = menu.addAction("折叠全部")
        collapse_all_action.triggered.connect(self.output_tree.collapseAll)
        
        menu.exec(self.output_tree.viewport().mapToGlobal(position))

    def expand_recursive(self, item):
        """递归展开节点"""
        self.output_tree.expandItem(item)
        for i in range(item.childCount()):
            self.expand_recursive(item.child(i))

    def collapse_recursive(self, item):
        """递归折叠节点"""
        self.output_tree.collapseItem(item)
        for i in range(item.childCount()):
            self.collapse_recursive(item.child(i))

    def collapse_others(self, target_item):
        """
        折叠除了目标节点路径之外的所有节点
        """
        # 1. 获取目标节点的所有祖先（包括自己）
        ancestors = set()
        current = target_item
        while current:
            ancestors.add(current)
            current = current.parent()

        # 2. 遍历并折叠
        # 最简单的方法：先折叠全部，再展开路径
        self.output_tree.collapseAll()

        # 展开路径上的节点
        current = target_item
        while current:
            current.setExpanded(True)
            current = current.parent()

        # 确保目标节点本身是展开的（根据需求，用户可能想看该层级内容）
        target_item.setExpanded(True)

    def compress_json(self):
        """
        压缩 JSON 并更新树与右侧结果
        """
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        try:
            data = json.loads(text)
            compressed = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            # 更新树
            self.populate_tree(json.loads(compressed))
            # 更新右侧文本并高亮
            self.output_edit.setPlainText(compressed)
            self.highlighter.rehighlight()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "压缩失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")

    def save_file(self):
        """
        保存右侧 JSON 结果到文件
        """
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
        version = "v2.0.4"
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

    def current_editor_key(self):
        w = QApplication.focusWidget()

        if w in (self.input_edit, self.input_edit.viewport()):
            return "input"

        if w in (self.output_edit, self.output_edit.viewport()):
            return "output"

        return None

    def open_search(self):
        key = self.current_editor_key()
        if not key:
            return

        panel = self.search_panels[key]
        panel.reposition()
        panel.show()
        panel.raise_()
        panel.search_edit.setFocus()

    def next_match_current(self):
        key = self.current_editor_key()
        if key:
            self.search_panels[key].next_match()

    def prev_match_current(self):
        key = self.current_editor_key()
        if key:
            self.search_panels[key].prev_match()

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


from PySide6.QtWidgets import QWidget, QLineEdit, QLabel, QPushButton, QHBoxLayout
from PySide6.QtGui import QTextCursor

class SearchPanel(QWidget):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.parent = parent
        self.editor = editor
        self.setFixedWidth(320)

        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索")
        # 👉 让 ESC 等同关闭
        self.search_edit.installEventFilter(self)
        self.label = QLabel("0 / 0")
        self.btn_prev = QPushButton("↑")
        self.btn_next = QPushButton("↓")
        self.btn_close = QPushButton("✕")

        layout.addWidget(self.search_edit)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_close)

        # 高亮器
        # self.highlighter = SearchHighlighter(self.editor.document())

        self.matches = []
        self.index = 0

        # 信号
        self.btn_close.clicked.connect(self.hide)
        self.search_edit.textChanged.connect(self.do_search)
        self.search_edit.returnPressed.connect(self.next_match)
        self.btn_next.clicked.connect(self.next_match)
        self.btn_prev.clicked.connect(self.prev_match)

    def reposition(self):
        from PySide6.QtCore import QPoint

        # 定位到 editor viewport 的左上角
        try:
            editor_top_left = self.editor.viewport().mapTo(self.parent, QPoint(0, 0))
        except Exception:
            editor_top_left = self.editor.mapTo(self.parent, QPoint(0, 0))

        # 👉 完全吸附，取消 padding
        x = editor_top_left.x()
        y = editor_top_left.y()

        # 边界检查（避免跑出窗口）
        parent_w = self.parent.width()
        parent_h = self.parent.height()
        panel_w = self.width()
        panel_h = self.height()

        if x + panel_w > parent_w:
            x = parent_w - panel_w
        if y + panel_h > parent_h:
            y = parent_h - panel_h
        if x < 0:
            x = 0
        if y < 0:
            y = 0

        self.move(x, y)

    def do_search(self):
        text = self.search_edit.text()
        self.highlight_search(text)

        self.matches.clear()

        if not text:
            self.label.setText("0 / 0")
            return

        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(0)

        # 查找所有匹配位置
        while True:
            found = doc.find(text, cursor)
            if found.isNull():
                break

            # 使用独立 cursor，避免被 find 内部复用导致高亮错乱
            cursor = QTextCursor(found)

            self.matches.append(cursor.selectionStart())

        self.index = 0
        self.update_label()

        if self.matches:
            self.goto(0)

    def update_label(self):
        if not self.matches:
            self.label.setText("0 / 0")
        else:
            self.label.setText(f"{self.index+1} / {len(self.matches)}")

    def goto(self, idx):
        if not self.matches:
            return

        self.index = idx
        current_pos = self.matches[idx]
        keyword = self.search_edit.text()
        length = len(keyword)
        doc = self.editor.document()
        extra = []

        # 全部匹配（每个 selection 都用 QTextCursor 的拷贝）
        cursor_iter = QTextCursor(doc)
        while True:
            cursor_iter = doc.find(keyword, cursor_iter)
            if cursor_iter.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(cursor_iter)  # <-- 显式拷贝
            fmt_all = QTextCharFormat()
            fmt_all.setBackground(QColor("#00FF00"))  # 普通匹配背景（绿色）
            sel.format = fmt_all
            extra.append(sel)

        # ---------- 在这里加入“整行浅蓝色高亮”（空选区 + FullWidthSelection） ----------
        # 注意：必须在设置所有搜索高亮之前构造或附加该项，以便同时显示
        line_cursor = QTextCursor(doc)
        # 把光标放在 current_pos（但不选中任何字符，保持空选区）
        line_cursor.setPosition(current_pos)
        line_sel = QTextEdit.ExtraSelection()
        line_sel.cursor = QTextCursor(line_cursor)  # 空选区的独立 cursor
        line_fmt = line_sel.format
        # 这就是 VSCode 风格的整行浅蓝（可调整透明度）
        line_fmt.setBackground(QColor(204, 232, 255, 51))  # "#CCE8FF33" 等价
        line_fmt.setProperty(QTextFormat.FullWidthSelection, True)
        line_sel.format = line_fmt
        # 将整行高亮放到 extra 的最前面（视觉上与关键字红色叠加良好）
        extra.insert(0, line_sel)

        # 当前匹配项（显式拷贝 cursor 并使用更醒目的格式）
        cur = QTextCursor(doc)
        cur.setPosition(current_pos)
        cur.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
        sel_cur = QTextEdit.ExtraSelection()
        sel_cur.cursor = QTextCursor(cur)  # <-- 拷贝
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#FF0000"))  # 当前匹配红色背景（关键词区域）
        fmt.setForeground(QColor("#FFFFFF"))  # 白字
        fmt.setFontWeight(QFont.Bold)
        # 不要把 FullWidthSelection 设置成 True —— 否则会覆盖整行蓝色
        sel_cur.format = fmt
        extra.append(sel_cur)

        # 应用 ExtraSelections（包含：整行蓝 + 所有绿 + 当前红）
        self.editor.setExtraSelections(extra)

        # 把文本光标移动到当前匹配的起始位置（但不KeepAnchor，不形成真实选中，这样不会覆盖 ExtraSelection）
        move_cursor = self.editor.textCursor()
        move_cursor.setPosition(current_pos)
        self.editor.setTextCursor(move_cursor)
        self.editor.ensureCursorVisible()

        # 强制刷新（确保视觉更新）
        self.editor.viewport().update()
        self.parent.highlighter.rehighlight()
        self.update_label()

    def next_match(self):
        if not self.matches:
            return
        self.goto((self.index + 1) % len(self.matches))

    def prev_match(self):
        if not self.matches:
            return
        self.goto((self.index - 1) % len(self.matches))

    def highlight_search(self, keyword, current_pos=None):
        """
        高亮搜索：
          - 所有匹配：绿色背景
          - 当前匹配：红色背景 + 白字
          - 当前行整行：浅蓝色背景
        """
        extra = []

        if not keyword:
            if isinstance(self.editor, CodeEditor):
                self.editor.highlight_current_line()
            else:
                self.editor.setExtraSelections([])
            return

        doc = self.editor.document()
        cursor = QTextCursor(doc)

        # 全部匹配（绿色背景）
        while True:
            cursor = doc.find(keyword, cursor)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(cursor)
            fmt_all = QTextCharFormat()
            fmt_all.setBackground(QColor("#00FF00"))  # 绿色背景
            sel.format = fmt_all
            extra.append(sel)

        # 当前匹配红色 + 整行浅蓝
        if current_pos is not None:
            # 当前行浅蓝背景
            line_cursor = QTextCursor(doc)
            line_cursor.setPosition(current_pos)
            line_sel = QTextEdit.ExtraSelection()
            line_sel.cursor = QTextCursor(line_cursor)
            line_fmt = line_sel.format
            line_fmt.setBackground(QColor(204, 232, 255, 51))  # 浅蓝半透明
            line_fmt.setProperty(QTextFormat.FullWidthSelection, True)
            line_sel.format = line_fmt
            extra.insert(0, line_sel)

            # 当前匹配红色背景 + 白字
            keyword_cursor = QTextCursor(doc)
            keyword_cursor.setPosition(current_pos)
            keyword_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(keyword))
            sel_cur = QTextEdit.ExtraSelection()
            sel_cur.cursor = QTextCursor(keyword_cursor)
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#FF0000"))
            fmt.setForeground(QColor("#FFFFFF"))
            fmt.setFontWeight(QFont.Bold)
            sel_cur.format = fmt
            extra.append(sel_cur)

        self.editor.setExtraSelections(extra)
        self.editor.viewport().update()

    # 👉 加上 eventFilter（直接复制即可）
    def eventFilter(self, obj, event):
        if obj == self.search_edit:
            if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.btn_close.click()
                return True
        return super().eventFilter(obj, event)

class SearchHighlighter(QSyntaxHighlighter):
    """
    支持两种高亮：
      - 全部匹配项的 background（默认黄色）
      - 当前选中项的 background（蓝色）
    接收 absolute document position（current_pos），用于把那一项渲染成 current fmt。
    """
    def __init__(self, doc):
        super().__init__(doc)
        self.keyword = ""
        self.fmt = QTextCharFormat()
        self.fmt.setBackground(QColor("#00FF00"))  # 酸橙色背景（全部匹配）
        self.fmt_current = QTextCharFormat()
        self.fmt_current.setForeground(QColor("#FFFFFF"))  # 白色字体
        self.fmt_current.setFontWeight(QFont.Bold)  # 加粗
        self.current_pos = None  # 绝对文档位置（selectionStart）
        self._kw_len = 0

    def set_keyword(self, text):
        self.keyword = text or ""
        self._kw_len = len(self.keyword)
        # reset current pos when keyword changed
        self.current_pos = None
        self.rehighlight()

    def set_current_pos(self, abs_pos):
        """
        abs_pos: 文档中的绝对位置（int），或 None 清除
        """
        self.current_pos = abs_pos
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.keyword:
            return

        # 不要清空已有格式（否则会覆盖 JsonHighlighter 的语法颜色）
        # super().highlightBlock(text) 也不要调用

        start = 0
        while True:
            pos = text.find(self.keyword, start)
            if pos < 0:
                break

            length = len(self.keyword)

            # 叠加背景色（不清除原格式）
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#00FF00"))  # 普通匹配
            self.setFormat(pos, length, fmt)

            # 当前项特殊格式
            abs_start = self.currentBlock().position() + pos
            if self.current_pos is not None and abs_start == self.current_pos:
                fmt2 = QTextCharFormat(fmt)  # 保留背景
                fmt2.setForeground(QColor("#FFFF00"))
                fmt2.setFontWeight(QFont.Bold)
                self.setFormat(pos, length, fmt2)

            start = pos + length



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
