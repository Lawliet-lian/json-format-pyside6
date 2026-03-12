from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QPlainTextEdit, QTextEdit, QSplitter, QLineEdit,
    QToolButton, QSizePolicy, QTreeWidgetItemIterator,
    QInputDialog, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QPalette,
    QFontDatabase, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QShortcut, QKeySequence, QTextDocument
)

import json
import sys

# ====== 主题配置 ======
THEMES = {
    "light": {
        "window_bg": "#FFFFFF",
        "text_color": "#000000",
        "input_bg": "#FFFFFF",
        "tree_bg": "#FFFFFF",
        "output_bg": "#FFFFFF",
        "header_bg": "#f0f0f0",
        "header_border": "#dcdcdc",
        "header_text": "#000000",
        "btn_bg": "transparent",
        "btn_hover": "#e0e0e0",
        "btn_text": "#000000",
        "splitter_handle": "#dcdcdc",
        "placeholder": "#969696",
        "line_num_bg": "#f0f0f0",
        "line_num_text": "#808080",
        "current_line": "#e8e8e8",
        "selection_bg": "#a5d6a7",
        "border_color": "#dcdcdc",
        "highlight": {
            "key": "#D500F9",       # 鲜艳紫
            "string": "#00C853",    # 鲜艳绿
            "number": "#FF0000",    # 红色
            "bool": "#FF1493",      # 深粉
            "null": "#FFD700",      # 金色
            "highlight_bg": "#4b5cc4",
            "highlight_fg": "#ffffff",
            "search_match": "#00FF00",
            "search_current": "#FF0000" # 红色
        },
        "scrollbar_handle": "#c1c1c1",
        "scrollbar_handle_hover": "#a8a8a8",
        "scrollbar_bg": "#f0f0f0"
    },
    "dark": {
        "window_bg": "#2b2b2b",
        "text_color": "#dcdcdc",
        "input_bg": "#1e1e1e",
        "tree_bg": "#1e1e1e",
        "output_bg": "#1e1e1e",
        "header_bg": "#333333",
        "header_border": "#444444",
        "header_text": "#dcdcdc",
        "btn_bg": "transparent",
        "btn_hover": "#444444",
        "btn_text": "#dcdcdc",
        "splitter_handle": "#444444",
        "placeholder": "#666666",
        "line_num_bg": "#2d2d2d",
        "line_num_text": "#858585",
        "current_line": "#2d2d30",
        "selection_bg": "#264f78",
        "border_color": "#3e3e42",
        "highlight": {
            "key": "#40C4FF",       # 亮青
            "string": "#69F0AE",    # 荧光绿
            "number": "#FF8C00",    # 深橙色
            "bool": "#FF1493",      # 鲜艳粉
            "null": "#FF1744",      # 鲜艳红
            "highlight_bg": "#264f78",
            "highlight_fg": "#ffffff",
            "search_match": "#6A7B50",
            "search_current": "#FF0000" # 红色
        },
        "scrollbar_handle": "#424242",
        "scrollbar_handle_hover": "#4f4f4f",
        "scrollbar_bg": "#2d2d2d"
    }
}

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
        self.theme = THEMES["light"]  # 默认主题
        self.textChanged.connect(self.update)  # 内容变化时刷新 placeholder
        self.lineNumberArea = LineNumberArea(self)
        
        self.search_extra_selections = []  # 存储搜索高亮

        # 绑定信号
        self.blockCountChanged.connect(self.update_line_number_area_width)  # 块数量变化时更新宽度
        self.updateRequest.connect(self.update_line_number_area)  # 滚动/更新时刷新行号
        self.cursorPositionChanged.connect(self.highlight_current_line)  # 光标行高亮

        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)  # 不自动换行

    def set_theme(self, theme_config):
        self.theme = theme_config
        self.highlight_current_line()
        self.update()  # 触发重绘（包括 placeholder）
        self.lineNumberArea.update() # 触发重绘行号
        
        # 更新自身样式
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['text_color']};
                selection-background-color: {self.theme['selection_bg']};
                border: 1px solid {self.theme['border_color']};
                border-radius: 4px;
            }}
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
        # 背景色
        bg_color = QColor(self.theme["line_num_bg"])
        painter.fillRect(event.rect(), bg_color)
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        # 行号文字颜色
        text_color = QColor(self.theme["line_num_text"])
        painter.setPen(text_color)
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
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
            # 当前行背景色
            lineColor = QColor(self.theme["current_line"])
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        
        # 叠加搜索高亮
        extraSelections.extend(self.search_extra_selections)
        self.setExtraSelections(extraSelections)

    def set_search_selections(self, selections):
        """
        设置搜索高亮选区，并触发重绘
        """
        self.search_extra_selections = selections
        self.highlight_current_line()

    # ====== 绘制 placeholder ======
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.toPlainText() and self.placeholder:
            painter = QPainter(self.viewport())
            # placeholder 颜色
            painter.setPen(QColor(self.theme["placeholder"]))
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
        self.theme = THEMES["light"]
        # 数据变化时刷新绘制 placeholder
        self.model().rowsInserted.connect(self.refresh_placeholder)
        self.model().rowsRemoved.connect(self.refresh_placeholder)
        self.model().modelReset.connect(self.refresh_placeholder)

    def refresh_placeholder(self, *args):
        """刷新 placeholder 显示"""
        self.viewport().update()

    def set_theme(self, theme_config):
        self.theme = theme_config
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {self.theme['tree_bg']};
                color: {self.theme['text_color']};
                border: 1px solid {self.theme['border_color']};
                border-radius: 4px;
            }}
            QHeaderView::section {{
                background-color: {self.theme['header_bg']};
                color: {self.theme['header_text']};
                border: 1px solid {self.theme['header_border']};
            }}
        """)
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.topLevelItemCount() == 0 and self.placeholder:
            painter = QPainter(self.viewport())
            # placeholder 颜色
            painter.setPen(QColor(self.theme["placeholder"]))
            painter.drawText(self.viewport().rect().adjusted(4, 4, -4, -4),
                             Qt.AlignTop | Qt.AlignLeft,
                             self.placeholder)

# ====== 可折叠面板 ======
class CollapsiblePanel(QWidget):
    """
    包含标题栏和折叠按钮的容器组件
    """
    def __init__(self, title="", content_widget=None, expanded_text="❮", collapsed_text="❯", parent=None):
        super().__init__(parent)
        self.content_widget = content_widget
        self.is_expanded = True
        self.expanded_text = expanded_text
        self.collapsed_text = collapsed_text
        self.theme = THEMES["light"]
        
        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        
        # 标题栏
        self.header = QWidget()
        self.header.setFixedHeight(26) # 缩小高度
        
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0) # 0边距，极致压缩
        self.header_layout.setSpacing(0)
        self.header.setLayout(self.header_layout)
        
        # 标题文本
        self.title_label = QLabel(title)
        self.title_label.setContentsMargins(5, 0, 0, 0) # 标题左边距
        font = self.title_label.font()
        font.setBold(True)
        font.setPointSize(12) # 稍微减小字体
        self.title_label.setFont(font)
        
        # 折叠/展开按钮
        self.toggle_btn = QToolButton()
        self.toggle_btn.setText(self.expanded_text)
        self.toggle_btn.setFixedSize(16, 26) # 宽度极窄，高度填满header
        font = self.toggle_btn.font()
        font.setPointSize(10) # 缩小箭头符号
        self.toggle_btn.setFont(font)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setCursor(Qt.PointingHandCursor) # 鼠标手型
        self.toggle_btn.clicked.connect(self.toggle)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.toggle_btn)
        
        self.main_layout.addWidget(self.header)
        
        if self.content_widget:
            self.main_layout.addWidget(self.content_widget)

    def set_theme(self, theme_config):
        self.theme = theme_config
        self.header.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme['header_bg']}; 
                border-bottom: 1px solid {self.theme['header_border']};
            }}
        """)
        self.title_label.setStyleSheet(f"color: {self.theme['header_text']}; border: none;")
        
        self.toggle_btn.setStyleSheet(f"""
            QToolButton {{ 
                border: none; 
                background: transparent; 
                color: {self.theme['btn_text']};
                font-weight: bold; 
            }}
            QToolButton:hover {{ 
                background-color: {self.theme['btn_hover']}; 
                border-radius: 3px; 
            }}
        """)

    def toggle(self):
        self.set_expanded(not self.is_expanded)

    def set_expanded(self, expanded):
        self.is_expanded = expanded
        self.toggle_btn.setChecked(expanded)
        
        if self.is_expanded:
            if self.content_widget:
                self.content_widget.show()
            self.title_label.show()
            self.setMaximumWidth(16777215) # QWIDGETSIZE_MAX
            self.toggle_btn.setText(self.expanded_text)
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            # 恢复 header 样式
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {self.theme['header_bg']}; 
                    border-bottom: 1px solid {self.theme['header_border']};
                }}
            """)
        else:
            if self.content_widget:
                self.content_widget.hide()
            self.title_label.hide()
            self.setMaximumWidth(16) # 收缩后的宽度，极致压缩
            self.toggle_btn.setText(self.collapsed_text)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            # 收缩时隐藏 header 背景，使其看起来更像一条线
            self.header.setStyleSheet(f"""
                QWidget {{
                    background-color: {self.theme['header_bg']}; 
                    border-bottom: none;
                }}
            """)


# ====== 可双击修改的标题标签 ======
class EditableTitleLabel(QLabel):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setToolTip("双击修改标题")
        self.setCursor(Qt.PointingHandCursor)
        # 稍微增加一点样式，使其看起来像标题
        self.setStyleSheet("padding: 2px;")

    def mouseDoubleClickEvent(self, event):
        new_title, ok = QInputDialog.getText(self, "修改标题", "请输入新标题:", text=self.text())
        if ok and new_title:
            self.setText(new_title)
            # 通知所在的顶层窗口更新标题
            if self.window():
                self.window().setWindowTitle(new_title)


# ====== 搜索高亮代理 ======
class SearchHighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.keyword = ""
        self.theme = THEMES["light"]
        self.current_item = None
        self.current_match_index = -1

    def set_search_config(self, keyword, theme):
        self.keyword = keyword
        self.theme = theme
        self.current_item = None
        self.current_match_index = -1
        
    def set_current_match(self, item, match_index):
        self.current_item = item
        self.current_match_index = match_index
        
    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        style = options.widget.style() if options.widget else QApplication.style()
        
        # 1. 绘制背景和选区状态（不带文字）
        original_text = options.text
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter, options.widget)
        options.text = original_text # 恢复 text

        # 2. 绘制高亮文字
        text = original_text
        if not text:
            return

        import html
        
        # 获取当前 item (用于判断是否是当前匹配项)
        current_item_widget = None
        tree_widget = None
        
        if options.widget and isinstance(options.widget, QTreeWidget):
             tree_widget = options.widget
        elif self.parent() and isinstance(self.parent(), QTreeWidget):
             tree_widget = self.parent()
             
        if tree_widget:
             current_item_widget = tree_widget.itemFromIndex(index)

        # 准备 HTML
        html_content = html.escape(text)

        if self.keyword:
            import re
            try:
                # 在原始文本中查找匹配
                pattern = re.compile(re.escape(self.keyword), re.IGNORECASE)
                matches = list(pattern.finditer(text))
                
                if matches:
                    html_parts = []
                    last_end = 0
                    
                    # 获取颜色
                    # 普通匹配颜色
                    color_match = self.theme.get('highlight', {}).get('search_match', '#00FF00')
                    # 当前聚焦匹配颜色
                    color_current = self.theme.get('highlight', {}).get('search_current', '#008000')
                    
                    if isinstance(color_match, QColor): color_match = color_match.name()
                    if isinstance(color_current, QColor): color_current = color_current.name()

                    is_target_item = (current_item_widget == self.current_item)

                    for i, match in enumerate(matches):
                        # 添加匹配前的文本 (转义)
                        html_parts.append(html.escape(text[last_end:match.start()]))
                        
                        # 确定当前匹配的背景色
                        bg_color = color_match
                        if is_target_item and i == self.current_match_index:
                            bg_color = color_current
                        
                        # 添加匹配文本 (转义 + span)
                        matched_str = html.escape(match.group(0))
                        html_parts.append(f'<span style="background-color: {bg_color}; color: black;">{matched_str}</span>')
                        
                        last_end = match.end()
                    
                    # 添加剩余文本
                    html_parts.append(html.escape(text[last_end:]))
                    html_content = "".join(html_parts)
                    
            except Exception:
                pass

        painter.save()
        
        # 获取文本绘制区域
        text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, options, options.widget)
        
        # 使用 QTextDocument 渲染 HTML
        doc = QTextDocument()
        doc.setDefaultFont(options.font)
        doc.setDocumentMargin(0) 
        
        # 确定文字颜色
        if options.state & QStyle.State_Selected:
            text_color = options.palette.color(QPalette.HighlightedText).name()
        else:
            text_color = options.palette.color(QPalette.Text).name()
            
        doc.setTextWidth(text_rect.width())
        # white-space: pre 保持空格
        doc.setHtml(f'<div style="color: {text_color}; white-space: pre;">{html_content}</div>')
        
        # 垂直居中调整
        doc_height = doc.size().height()
        offset_y = (text_rect.height() - doc_height) / 2
        
        painter.translate(text_rect.topLeft())
        painter.translate(0, offset_y)
        painter.setClipRect(0, 0, text_rect.width(), text_rect.height())
        
        doc.drawContents(painter)
        painter.restore()


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
        # 设置搜索高亮代理
        self.search_delegate = SearchHighlightDelegate(self.output_tree)
        self.output_tree.setItemDelegate(self.search_delegate)
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
        self.left_panel = CollapsiblePanel("原始 JSON", self.input_edit, expanded_text="❮", collapsed_text="❯")
        
        # 中间：JSON 树
        self.middle_panel = CollapsiblePanel("JSON 树", self.output_tree, expanded_text="❯", collapsed_text="❮")
        # 默认收缩中间树
        self.middle_panel.set_expanded(False)

        # 右侧：JSON 结果
        self.right_panel = CollapsiblePanel("JSON 结果", self.output_edit, expanded_text="❯", collapsed_text="❮")

        self.splitter = QSplitter()
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.middle_panel)
        self.splitter.addWidget(self.right_panel)

        # 设置初始宽度比例：原始 JSON 1/2，JSON 树 16 (收缩状态)，JSON 结果 1/2
        total_width = self.width() if self.width() > 0 else 1200 # 默认宽度
        self.splitter.setSizes([
            int(total_width * 1 / 2),  # 原始 JSON
            16,                        # JSON 树 (因为收缩了，给个极小宽度)
            int(total_width * 1 / 2)   # JSON 结果
        ])

        # 按钮
        self.btn_format = QPushButton("格式化")
        self.btn_compress = QPushButton("压缩")
        self.btn_save = QPushButton("保存")
        self.btn_copy = QPushButton("复制结果")

        # 布局切换按钮
        self.btn_layout_source_result = QPushButton("原始+结果")
        self.btn_layout_source_tree = QPushButton("原始+树")
        self.btn_layout_all = QPushButton("三栏布局")
        self.btn_layout_tree_result = QPushButton("树+结果")

        # 绑定按钮事件
        self.btn_format.clicked.connect(self.format_json)
        self.btn_compress.clicked.connect(self.compress_json)
        self.btn_save.clicked.connect(self.save_file)
        self.btn_copy.clicked.connect(self.copy_result)

        # 绑定布局切换事件
        self.btn_layout_source_result.clicked.connect(lambda: self.switch_layout(True, False, True))
        self.btn_layout_source_tree.clicked.connect(lambda: self.switch_layout(True, True, False))
        self.btn_layout_all.clicked.connect(lambda: self.switch_layout(True, True, True))
        self.btn_layout_tree_result.clicked.connect(lambda: self.switch_layout(False, True, True))

        # 标题 Label (可双击修改)
        title_text = f"JSON 格式化工具" + (f" {self.window_number}" if self.window_number > 1 else "")
        self.title_label = EditableTitleLabel(title_text, self)
        font = self.title_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setContentsMargins(5, 0, 0, 0)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.title_label)
        
        # 增加一点间距，但不要用 stretch 把按钮顶到最右边
        btn_layout.addSpacing(255)

        # 功能按钮组
        for btn in [self.btn_format, self.btn_compress, self.btn_copy, self.btn_save]:
            font = btn.font()
            font.setBold(True)  # 按钮加粗
            btn.setFont(font)
            # 设置固定宽度（加宽）
            btn.setFixedWidth(100) 
            btn_layout.addWidget(btn)

        # 添加分割线或间距
        btn_layout.addSpacing(20)

        # 中间加弹簧，把后面的布局按钮顶到最右边
        btn_layout.addStretch()

        # 布局切换按钮组
        for btn in [self.btn_layout_source_result, self.btn_layout_source_tree, 
                    self.btn_layout_all, self.btn_layout_tree_result]:
            font = btn.font()
            # font.setBold(True) # 布局按钮是否加粗可选，这里保持一致性也可以加粗
            btn.setFont(font)
            btn_layout.addWidget(btn)
        
        # ====== 主布局 ======
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(2, 2, 2, 2)  # 左上右下边距，顶部/底部间距缩小
        main_layout.setSpacing(2)  # 垂直间距缩小
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        # ====== 菜单栏 ======
        menu_bar = QMenuBar()
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        new_action = file_menu.addAction("新建 JSON 窗口")
        new_action.triggered.connect(JsonFormatterWindow.new_window_static)
        open_action = file_menu.addAction("打开 JSON 文件")
        open_action.triggered.connect(self.open_file)
        
        # 视图菜单 - 主题切换
        view_menu = QMenu("视图", self)
        menu_bar.addMenu(view_menu)
        
        self.theme_menu = QMenu("主题", self)
        view_menu.addMenu(self.theme_menu)
        
        self.action_auto = self.theme_menu.addAction("跟随系统")
        self.action_light = self.theme_menu.addAction("明亮模式")
        self.action_dark = self.theme_menu.addAction("暗黑模式")
        
        self.action_auto.setCheckable(True)
        self.action_light.setCheckable(True)
        self.action_dark.setCheckable(True)
        
        self.action_auto.setChecked(True) # 默认跟随系统
        
        self.action_auto.triggered.connect(lambda: self.switch_theme_mode("auto"))
        self.action_light.triggered.connect(lambda: self.switch_theme_mode("light"))
        self.action_dark.triggered.connect(lambda: self.switch_theme_mode("dark"))
        
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
            "output": SearchPanel(self, self.output_edit),
            "tree": TreeSearchPanel(self, self.output_tree)
        }

        for p in self.search_panels.values():
            p.hide()

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.open_search)
        QShortcut(QKeySequence("Cmd+F"), self, activated=self.open_search)
        QShortcut(QKeySequence("F3"), self, activated=self.next_match_current)
        QShortcut(QKeySequence("Shift+F3"), self, activated=self.prev_match_current)

        # 保存窗口引用
        JsonFormatterWindow.windows.append(self)
        
        # 初始化主题
        self.current_theme_mode = "auto"
        self._is_applying_theme = False
        self.apply_theme()

    def switch_theme_mode(self, mode):
        self.current_theme_mode = mode
        
        # 更新菜单选中状态
        self.action_auto.setChecked(mode == "auto")
        self.action_light.setChecked(mode == "light")
        self.action_dark.setChecked(mode == "dark")
        
        self.apply_theme()

    def detect_system_theme(self):
        """
        检测系统主题
        返回 "dark" 或 "light"
        """
        # 简单检测：通过窗口背景色亮度判断
        # 注意：在某些系统上这可能不准确，但在 PySide6 中通常有效
        palette = QApplication.palette()
        bg_color = palette.color(QPalette.Window)
        # 计算亮度 (YIQ formula)
        brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
        return "dark" if brightness < 128 else "light"

    def changeEvent(self, event):
        """
        监听系统主题变化
        """
        if event.type() == QtCore.QEvent.PaletteChange:
            if self.current_theme_mode == "auto" and not self._is_applying_theme:
                # 只有当不在应用主题时才尝试重新应用
                self.apply_theme()
        super().changeEvent(event)

    def apply_theme(self):
        """
        应用当前主题
        """
        if self._is_applying_theme:
            return
            
        self._is_applying_theme = True
        try:
            mode = self.current_theme_mode
            if mode == "auto":
                mode = self.detect_system_theme()
                
            theme = THEMES.get(mode, THEMES["light"])
            self.current_theme_data = theme # 保存当前主题数据供其他地方使用
            
            # 1. 设置窗口背景
            # 全局滚动条样式
            scrollbar_style = f"""
                QScrollBar:vertical {{
                    border: none;
                    background: {theme.get('scrollbar_bg', '#f0f0f0')};
                    width: 12px;
                    margin: 0px 0px 0px 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: {theme.get('scrollbar_handle', '#c1c1c1')};
                    min-height: 20px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {theme.get('scrollbar_handle_hover', '#a8a8a8')};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    border: none;
                    background: none;
                    height: 0px;
                }}
                QScrollBar:horizontal {{
                    border: none;
                    background: {theme.get('scrollbar_bg', '#f0f0f0')};
                    height: 12px;
                    margin: 0px 0px 0px 0px;
                }}
                QScrollBar::handle:horizontal {{
                    background: {theme.get('scrollbar_handle', '#c1c1c1')};
                    min-width: 20px;
                    border-radius: 6px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background: {theme.get('scrollbar_handle_hover', '#a8a8a8')};
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    border: none;
                    background: none;
                    width: 0px;
                }}
            """
            
            self.setStyleSheet(f"background-color: {theme['window_bg']}; color: {theme['text_color']}; {scrollbar_style}")
            
            # 2. 设置输入框主题
            self.input_edit.set_theme(theme)
            
            # 3. 设置树控件主题
            self.output_tree.set_theme(theme)
            
            # 4. 设置输出框主题
            # 输出框是普通 QTextEdit，手动设置样式
            self.output_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {theme['output_bg']};
                    color: {theme['text_color']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 4px;
                }}
            """)
            # 更新 placeholder 颜色
            palette = self.output_edit.palette()
            palette.setColor(QPalette.PlaceholderText, QColor(theme['placeholder']))
            self.output_edit.setPalette(palette)
            
            # 更新高亮器颜色
            self.highlighter.set_theme(theme)
            
            # 5. 设置可折叠面板主题
            self.left_panel.set_theme(theme)
            self.middle_panel.set_theme(theme)
            self.right_panel.set_theme(theme)
            
            # 6. 设置 Splitter Handle 颜色
            handle_color = theme['splitter_handle']
            handle_hover = theme.get('btn_hover', '#cccccc')
            self.splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {handle_color};
                    border: 1px solid transparent;
                }}
                QSplitter::handle:hover {{
                    background-color: {handle_hover};
                }}
                QSplitter::handle:pressed {{
                    background-color: {theme['header_border']};
                }}
            """)
            
            # 8. 更新搜索面板主题
            for panel in self.search_panels.values():
                panel.set_theme(theme)
            
            # 7. 更新按钮样式
            for btn in [self.btn_format, self.btn_compress, self.btn_save, self.btn_copy,
                        self.btn_layout_source_result, self.btn_layout_source_tree, 
                        self.btn_layout_all, self.btn_layout_tree_result]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme['input_bg']};
                        color: {theme['text_color']};
                        border: 1px solid {theme['border_color']};
                        border-radius: 4px;
                        padding: 5px 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme['btn_hover']};
                    }}
                    QPushButton:pressed {{
                        background-color: {theme['header_border']};
                    }}
                """)
        finally:
            self._is_applying_theme = False

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
            # 自动触发 或 手动触发
            # 尝试查找并提取混合内容中的 JSON
            extracted_json, start_idx, end_idx = self.extract_json_from_text(text)
            if extracted_json:
                try:
                    # 解析提取出的 JSON
                    data = json.loads(extracted_json)
                    
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
                    
                    # 更新树
                    self.populate_tree(data)
                    
                    # 格式化 JSON
                    formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
                    
                    # 拼接到原文中（保留前后非 JSON 内容）
                    prefix = text[:start_idx]
                    suffix = text[end_idx:]
                    
                    # 构造错误提示信息
                    error_msg = f"// ⚠️ 解析警告：第 {e.lineno} 行解析错误，原因：{e.msg}\n"
                    
                    final_text = f"{error_msg}{prefix}{formatted_json}{suffix}"
                    
                    self.output_edit.setPlainText(final_text)
                    self.highlighter.rehighlight()
                    
                    # 弹出警告提示（如果是自动触发，就不弹窗干扰了，改用状态栏或其他方式提示更好）
                    if show_error_dialog:
                        msg_info = (f"虽然提取并格式化了其中的 JSON 内容，\n"
                                    f"但输入的文本包含非 JSON 字符，请检查原始数据。\n\n"
                                    f"原始解析错误:\n{e.msg}\n行: {e.lineno}, 列: {e.colno}")
                        QMessageBox.warning(self, "JSON 格式有误", msg_info)
                    else:
                        pass
                    return

                except Exception as inner_e:
                    pass # 提取后的解析还是失败，继续显示原来的错误

            # 只有在手动触发时，才弹出错误对话框
            if show_error_dialog:
                QMessageBox.critical(self, "格式化失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")
            else:
                self.output_tree.clear()
                self.output_edit.setPlainText("")
                self.highlighter.rehighlight()

    def extract_json_from_text(self, text):
        """
        尝试从文本中提取第一个有效的 JSON 对象或数组
        返回: (json_str, start_index, end_index)
        """
        text = text.strip()
        
        # 1. 寻找第一个 { 或 [
        start_idx = -1
        for i, char in enumerate(text):
            if char in '{[':
                start_idx = i
                break
                
        if start_idx == -1:
            return None, -1, -1
            
        # 2. 从 start_idx 开始匹配括号
        stack = []
        in_string = False
        escape = False
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if in_string:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char in '{[':
                    stack.append(char)
                elif char in '}]':
                    if not stack:
                        # 只有右括号没有左括号，说明匹配失败（可能是多余的符号）
                        continue 
                    
                    last = stack[-1]
                    if (char == '}' and last == '{') or (char == ']' and last == '['):
                        stack.pop()
                        # 如果栈空了，说明找到了一个完整的闭合 JSON 对象
                        if not stack:
                            # 截取候选 JSON
                            candidate = text[start_idx : i+1]
                            # 尝试验证解析
                            try:
                                json.loads(candidate)
                                return candidate, start_idx, i+1
                            except:
                                # 解析失败，继续寻找（可能只是碰巧匹配了括号但内容不对）
                                pass
        
        return None, -1, -1

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

    def switch_layout(self, show_left, show_mid, show_right):
        """
        切换布局模式
        :param show_left: 是否显示原始 JSON
        :param show_mid: 是否显示 JSON 树
        :param show_right: 是否显示 JSON 结果
        """
        # 1. 设置面板展开/折叠状态
        self.left_panel.set_expanded(show_left)
        self.middle_panel.set_expanded(show_mid)
        self.right_panel.set_expanded(show_right)
        
        # 2. 计算并设置 splitter 比例
        # 统计需要显示的面板数量
        visible_count = sum([show_left, show_mid, show_right])
        if visible_count == 0:
            return

        total_width = self.splitter.width()
        # 预留给折叠面板的宽度 (16px per collapsed panel)
        collapsed_width = 16
        
        sizes = []
        
        # 辅助函数：根据状态返回应该设置的宽度
        def get_width(is_visible):
            if is_visible:
                # 减去所有折叠面板占用的宽度后，平分剩余空间
                collapsed_count = 3 - visible_count
                net_width = total_width - (collapsed_count * collapsed_width)
                return max(0, net_width // visible_count)
            else:
                return collapsed_width

        sizes.append(get_width(show_left))
        sizes.append(get_width(show_mid))
        sizes.append(get_width(show_right))
        
        self.splitter.setSizes(sizes)

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
            
        if w in (self.output_tree, self.output_tree.viewport()):
            return "tree"

        return None

    def open_search(self):
        key = self.current_editor_key()
        
        # 如果没有焦点，优先尝试输入框，其次输出框
        if not key:
            if self.left_panel.is_expanded:
                key = "input"
                self.input_edit.setFocus()
            elif self.middle_panel.is_expanded:
                key = "tree"
                self.output_tree.setFocus()
            elif self.right_panel.is_expanded:
                key = "output"
                self.output_edit.setFocus()
            else:
                # 都折叠了？强制展开输入框
                key = "input"
                self.left_panel.set_expanded(True)
                self.input_edit.setFocus()
        
        # 确保目标面板是展开的
        if key == "input" and not self.left_panel.is_expanded:
             self.left_panel.set_expanded(True)
        elif key == "tree" and not self.middle_panel.is_expanded:
             self.middle_panel.set_expanded(True)
        elif key == "output" and not self.right_panel.is_expanded:
             self.right_panel.set_expanded(True)

        panel = self.search_panels[key]
        panel.reposition()
        panel.show()
        panel.raise_()
        panel.search_edit.setFocus()
        panel.search_edit.selectAll()

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
        self.theme = THEMES["light"]
        self.update_formats()

    def set_theme(self, theme_config):
        self.theme = theme_config
        self.update_formats()
        self.rehighlight()

    def update_formats(self):
        colors = self.theme["highlight"]
        self.formats = {
            "key": self.make_format(colors["key"]),
            "string": self.make_format(colors["string"]),
            "number": self.make_format(colors["number"]),
            "bool": self.make_format(colors["bool"]),
            "null": self.make_format(colors["null"]),
            "highlight": self.make_format(colors["highlight_fg"], bg=colors["highlight_bg"], bold=True)
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
        self.theme = THEMES["light"]

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
        self.btn_close.clicked.connect(self.close_search)
        self.search_edit.textChanged.connect(self.do_search)
        self.search_edit.returnPressed.connect(self.next_match)
        self.btn_next.clicked.connect(self.next_match)
        self.btn_prev.clicked.connect(self.prev_match)

    def close_search(self):
        self.search_edit.clear()
        self.hide()

    def set_theme(self, theme_config):
        self.theme = theme_config
        # 设置面板样式
        self.setStyleSheet(f"""
            SearchPanel {{
                background-color: {self.theme['header_bg']};
                border: 1px solid {self.theme['header_border']};
                border-radius: 4px;
            }}
            QLabel {{
                color: {self.theme['text_color']};
            }}
            QLineEdit {{
                background-color: {self.theme['input_bg']};
                color: {self.theme['text_color']};
                border: 1px solid {self.theme['border_color']};
                border-radius: 2px;
                padding: 2px;
            }}
            QPushButton {{
                background-color: {self.theme['btn_bg']};
                color: {self.theme['btn_text']};
                border: none;
                border-radius: 2px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['btn_hover']};
            }}
        """)
        
        # 重新触发搜索高亮以更新颜色
        if self.search_edit.text():
            self.highlight_search(self.search_edit.text())

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
            fmt_all.setBackground(QColor(self.theme['highlight']['search_match']))  # 主题色
            sel.format = fmt_all
            extra.append(sel)

        # ---------- 在这里加入“整行浅蓝色高亮”（空选区 + FullWidthSelection） ----------
        # 注意：必须在设置所有搜索高亮之前构造或附加该项，以便同时显示
        # 如果是 CodeEditor，它自己会处理当前行高亮，这里不需要添加
        if not isinstance(self.editor, CodeEditor):
            line_cursor = QTextCursor(doc)
            # 把光标放在 current_pos（但不选中任何字符，保持空选区）
            line_cursor.setPosition(current_pos)
            line_sel = QTextEdit.ExtraSelection()
            line_sel.cursor = QTextCursor(line_cursor)  # 空选区的独立 cursor
            line_fmt = line_sel.format
            # 使用主题中的当前行颜色
            line_fmt.setBackground(QColor(self.theme['current_line']))  
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
        fmt.setBackground(QColor(self.theme['highlight']['search_current']))  # 主题色
        fmt.setForeground(QColor(self.theme['highlight']['highlight_fg']))  # 主题色
        fmt.setFontWeight(QFont.Bold)
        # 不要把 FullWidthSelection 设置成 True —— 否则会覆盖整行蓝色
        sel_cur.format = fmt
        extra.append(sel_cur)

        # 应用 ExtraSelections（包含：整行蓝 + 所有绿 + 当前红）
        if isinstance(self.editor, CodeEditor):
            self.editor.set_search_selections(extra)
        else:
            self.editor.setExtraSelections(extra)

        # 把文本光标移动到当前匹配的起始位置（但不KeepAnchor，不形成真实选中，这样不会覆盖 ExtraSelection）
        move_cursor = self.editor.textCursor()
        move_cursor.setPosition(current_pos)
        self.editor.setTextCursor(move_cursor)
        self.editor.ensureCursorVisible()

        # 强制刷新（确保视觉更新）
        self.editor.viewport().update()
        # 尝试调用 parent 的 highlighter 刷新，如果有的话
        if hasattr(self.parent, 'highlighter'):
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
          - 所有匹配：主题配置 search_match
          - 当前匹配：主题配置 search_current
          - 当前行整行：主题配置 current_line
        """
        extra = []

        if not keyword:
            if isinstance(self.editor, CodeEditor):
                self.editor.set_search_selections([])
            else:
                self.editor.setExtraSelections([])
            return

        doc = self.editor.document()
        cursor = QTextCursor(doc)

        # 全部匹配
        while True:
            cursor = doc.find(keyword, cursor)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.cursor = QTextCursor(cursor)
            fmt_all = QTextCharFormat()
            fmt_all.setBackground(QColor(self.theme['highlight']['search_match']))
            sel.format = fmt_all
            extra.append(sel)

        # 当前匹配红色 + 整行浅蓝
        if current_pos is not None:
            # 当前行浅蓝背景 (CodeEditor 自动处理，非 CodeEditor 手动添加)
            if not isinstance(self.editor, CodeEditor):
                line_cursor = QTextCursor(doc)
                line_cursor.setPosition(current_pos)
                line_sel = QTextEdit.ExtraSelection()
                line_sel.cursor = QTextCursor(line_cursor)
                line_fmt = line_sel.format
                line_fmt.setBackground(QColor(self.theme['current_line']))
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
            fmt.setBackground(QColor(self.theme['highlight']['search_current']))
            fmt.setForeground(QColor(self.theme['highlight']['highlight_fg']))
            fmt.setFontWeight(QFont.Bold)
            sel_cur.format = fmt
            extra.append(sel_cur)

        if isinstance(self.editor, CodeEditor):
            self.editor.set_search_selections(extra)
        else:
            self.editor.setExtraSelections(extra)
        self.editor.viewport().update()

    # 👉 加上 eventFilter（直接复制即可）
    def eventFilter(self, obj, event):
        if obj == self.search_edit:
            if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Escape:
                self.btn_close.click()
                return True
        return super().eventFilter(obj, event)






class TreeSearchPanel(SearchPanel):
    """
    针对 QTreeWidget 的搜索面板
    """
    def __init__(self, parent, editor):
        super().__init__(parent, editor)
        self.tree_matches = []  # 存储匹配的 (QTreeWidgetItem, match_index)

    def do_search(self):
        text = self.search_edit.text()
        
        # 触发高亮 (设置全局 keyword)
        self.highlight_search(text)
        
        self.tree_matches.clear()
        
        # 记得清除之前的高亮（如果有的话）
        self.index = 0
        
        if not text:
            self.label.setText("0 / 0")
            return

        import re
        try:
            pattern = re.compile(re.escape(text), re.IGNORECASE)
            
            # 遍历树的所有节点
            iterator = QTreeWidgetItemIterator(self.editor)
            while iterator.value():
                item = iterator.value()
                item_text = item.text(0)
                
                # 查找该节点内的所有匹配
                matches = list(pattern.finditer(item_text))
                for i in range(len(matches)):
                    self.tree_matches.append((item, i))
                    
                iterator += 1
        except Exception:
            pass

        self.update_label()

        if self.tree_matches:
            self.goto(0)

    def update_label(self):
        if not self.tree_matches:
            self.label.setText("0 / 0")
        else:
            self.label.setText(f"{self.index+1} / {len(self.tree_matches)}")

    def goto(self, idx):
        if not self.tree_matches:
            return
            
        # 防止越界
        if idx < 0 or idx >= len(self.tree_matches):
            return

        self.index = idx
        item, match_index = self.tree_matches[idx]

        # 1. 确保父节点全部展开
        parent = item.parent()
        while parent:
            parent.setExpanded(True)
            parent = parent.parent()

        # 2. 选中并滚动到该节点
        self.editor.setCurrentItem(item)
        self.editor.scrollToItem(item)
        
        # 3. 设置当前聚焦的匹配项
        delegate = self.editor.itemDelegate()
        if hasattr(delegate, 'set_current_match'):
            delegate.set_current_match(item, match_index)
            self.editor.viewport().update()
        
        self.update_label()

    def next_match(self):
        if not self.tree_matches:
            return
        self.goto((self.index + 1) % len(self.tree_matches))

    def prev_match(self):
        if not self.tree_matches:
            return
        self.goto((self.index - 1) % len(self.tree_matches))

    def highlight_search(self, keyword, current_pos=None):
        # 树控件文本内的高亮
        delegate = self.editor.itemDelegate()
        if hasattr(delegate, 'set_search_config'):
            delegate.set_search_config(keyword, self.theme)
            self.editor.viewport().update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
