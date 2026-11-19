from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QMenuBar, QMenu,
    QPlainTextEdit, QTextEdit, QSplitter, QLineEdit,
    QToolButton, QSizePolicy,
    QInputDialog, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QFrame
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QPalette,
    QFontDatabase, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QKeySequence, QTextDocument, QIcon, QPixmap, QPen, QPainterPath, QAction
)

import html
import json
import re
import sys
from string_format_app import FormatterWindow
from timestamp_converter_app import TimestampConverterWindow
# 多窗口管理器：统一维护稳定 UUID 索引、「窗口」菜单与多选激活语义
from window_manager import WindowManager

# ====== 主题配置 ======
THEMES = {
    "light": {
        "window_bg": "#F0F2F6",
        "text_color": "#242A38",
        "input_bg": "#FFFFFF",
        "tree_bg": "#FFFFFF",
        "header_bg": "#F8F9FC",
        "header_border": "#E5E9F0",
        "header_text": "#343D50",
        "btn_bg": "#FFFFFF",
        "btn_hover": "#EBEEF6",
        "btn_text": "#354057",
        "accent": "#4B47CB",
        "accent_hover": "#3E3AB5",
        "accent_soft": "#E9E8FB",
        "on_accent": "#FFFFFF",
        "placeholder": "#69758A",
        "line_num_bg": "#F7F8FC",
        "line_num_text": "#68748C",
        "current_line": "#F0F2FD",
        "selection_bg": "#DCE0FF",
        "border_color": "#DCE2EC",
        "tree_value": "#56637B",
        "warning_bg": "#FFF4DB",
        "warning_text": "#794A10",
        "highlight": {
            "key": "#5543B0",
            "string": "#08765D",
            "number": "#A04E1A",
            "bool": "#963F79",
            "null": "#963F79",
            "search_match": "#F9D99B",
            "search_current": "#4B47CB",
            "highlight_fg": "#FFFFFF",
        },
        "scrollbar_handle": "#C2CAD8",
        "scrollbar_handle_hover": "#9EA9BC",
    },
    "dark": {
        "window_bg": "#2b2b2b",
        "text_color": "#dcdcdc",
        "input_bg": "#1e1e1e",
        "tree_bg": "#1e1e1e",
        "header_bg": "#333333",
        "header_border": "#444444",
        "header_text": "#dcdcdc",
        "btn_bg": "#1e1e1e",
        "btn_hover": "#444444",
        "btn_text": "#dcdcdc",
        "accent": "#264f78",
        "accent_hover": "#315f8c",
        "accent_soft": "#2d2d30",
        "on_accent": "#ffffff",
        "placeholder": "#666666",
        "line_num_bg": "#2d2d2d",
        "line_num_text": "#858585",
        "current_line": "#2d2d30",
        "selection_bg": "#264f78",
        "border_color": "#3e3e42",
        "tree_value": "#62b37a",
        "warning_bg": "#333333",
        "warning_text": "#dcdcdc",
        "highlight": {
            "key": "#40C4FF",
            "string": "#69F0AE",
            "number": "#FF8C00",
            "bool": "#FF1493",
            "null": "#FF1744",
            "search_match": "#6A7B50",
            "search_current": "#FF0000",
            "highlight_fg": "#ffffff",
        },
        "scrollbar_handle": "#424242",
        "scrollbar_handle_hover": "#4f4f4f",
    },
}


def toolbar_icon(name, color):
    pixmap = QPixmap(32, 32)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    if name == "search":
        painter.drawEllipse(QtCore.QRectF(2.8, 2.8, 7.8, 7.8))
        painter.drawLine(QtCore.QPointF(9.5, 9.5), QtCore.QPointF(13.4, 13.4))
    else:
        path = QPainterPath(QtCore.QPointF(10.0, 2.3))
        path.lineTo(13.7, 6.0)
        path.lineTo(11.6, 6.4)
        path.lineTo(9.3, 8.7)
        path.lineTo(8.9, 11.6)
        path.lineTo(4.4, 7.1)
        path.lineTo(7.3, 6.7)
        path.lineTo(9.6, 4.4)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QtCore.QPointF(6.6, 9.4), QtCore.QPointF(2.8, 13.2))
    painter.end()
    return QIcon(pixmap)


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

    def mousePressEvent(self, event):
        self.editor.line_number_area_mouse_press_event(event)


# ====== 支持行号的 QPlainTextEdit ======
class CodeEditor(QPlainTextEdit):
    """
    支持行号显示的 QPlainTextEdit
    并实现 placeholder 功能
    """
    LINE_NUMBER_PADDING = 12
    FOLD_CONTROL_WIDTH = 8

    def __init__(self, placeholder=""):
        super().__init__()
        self.placeholder = placeholder
        self.theme = THEMES["light"]  # 默认主题
        self.textChanged.connect(self.update)  # 内容变化时刷新 placeholder
        self.lineNumberArea = LineNumberArea(self)
        
        self.search_extra_selections = []  # 存储搜索高亮
        self.folding_enabled = False
        self.fold_regions = {}
        self.folded_starts = set()
        self.skip_map = {}  # 优化：用于在绘制行号时快速跳过大量隐藏块
        self.shared_line_number_digits = 1

        # 绑定信号
        self.blockCountChanged.connect(self.update_line_number_area_width)  # 块数量变化时更新宽度
        self.updateRequest.connect(self.update_line_number_area)  # 滚动/更新时刷新行号
        self.cursorPositionChanged.connect(self.highlight_current_line)  # 光标行高亮
        self.textChanged.connect(self.rebuild_fold_regions)

        self.update_line_number_area_width()
        self.highlight_current_line()
        self.setLineWrapMode(QPlainTextEdit.NoWrap)  # 不自动换行
        self.document().setDocumentMargin(9)

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
                border: none;
            }}
        """)

    # ====== 行号宽度计算 ======
    def line_number_area_width(self):
        digits = max(self.shared_line_number_digits, len(str(self.blockCount())))
        return self.LINE_NUMBER_PADDING + self.fontMetrics().horizontalAdvance("9") * digits

    def set_shared_line_number_digits(self, digits):
        self.shared_line_number_digits = digits
        self.update_line_number_area_width()

    def update_line_number_area_width(self):
        width = self.line_number_area_width()
        if self.viewportMargins().left() != width:
            self.setViewportMargins(width, 0, 0, 0)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(cr.left(), cr.top(), width, cr.height())

    def update_line_number_area(self, rect, dy):
        # 滚动或更新时刷新行号
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.line_number_area_width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_line_number_area_width()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.FontChange:
            self.update_line_number_area_width()

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
        painter.setRenderHint(QPainter.Antialiasing)
        gutter_width = self.lineNumberArea.width()
        number_x = self.LINE_NUMBER_PADDING - self.FOLD_CONTROL_WIDTH
        number_col_width = gutter_width - self.LINE_NUMBER_PADDING
        line_height = self.fontMetrics().height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible():
                if bottom >= event.rect().top():
                    number = str(blockNumber + 1)
                    painter.drawText(number_x, top, number_col_width, line_height, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, number)
                    if self.folding_enabled and blockNumber in self.fold_regions:
                        x = gutter_width - self.FOLD_CONTROL_WIDTH / 2
                        y = top + line_height / 2
                        arrow = QPainterPath()
                        if blockNumber in self.folded_starts:
                            arrow.moveTo(x - 2, y - 3)
                            arrow.lineTo(x + 2, y)
                            arrow.lineTo(x - 2, y + 3)
                        else:
                            arrow.moveTo(x - 3, y - 2)
                            arrow.lineTo(x + 3, y - 2)
                            arrow.lineTo(x, y + 2)
                        arrow.closeSubpath()
                        painter.fillPath(arrow, text_color)
                
                # 只有可见块才更新 top 和 bottom
                top = bottom
                bottom = top + round(self.blockBoundingRect(block).height())
                block = block.next()
                blockNumber += 1
            else:
                # 快速跳过隐藏块
                if blockNumber in self.skip_map:
                    jump_to = self.skip_map[blockNumber]
                    block = self.document().findBlockByNumber(jump_to)
                    blockNumber = jump_to
                else:
                    block = block.next()
                    blockNumber += 1

    def line_number_area_mouse_press_event(self, event):
        if not self.folding_enabled:
            return
        if event.button() != Qt.LeftButton:
            return
        fold_start_x = self.lineNumberArea.width() - self.FOLD_CONTROL_WIDTH
        if event.position().x() < fold_start_x or event.position().x() > self.lineNumberArea.width():
            return
        block_number = self.block_number_at_y(event.position().y())
        if block_number is None:
            return
        if block_number in self.fold_regions:
            self.toggle_fold(block_number)

    def block_number_at_y(self, y):
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid():
            if block.isVisible():
                if top <= y <= bottom:
                    return block_number
                if top > y:
                    return None
                top = bottom
                bottom = top + round(self.blockBoundingRect(block).height())
                block = block.next()
                block_number += 1
            else:
                if block_number in self.skip_map:
                    jump_to = self.skip_map[block_number]
                    block = self.document().findBlockByNumber(jump_to)
                    block_number = jump_to
                else:
                    block = block.next()
                    block_number += 1
        return None

    def enable_json_folding(self, enabled=True):
        if not enabled:
            self.expand_all_folds()
            self.fold_regions.clear()
        self.folding_enabled = enabled
        self.rebuild_fold_regions()
        self.lineNumberArea.update()

    def rebuild_fold_regions(self):
        if not self.folding_enabled:
            return
        fold_regions = {}
        stack = []
        block = self.document().firstBlock()
        while block.isValid():
            line = block.text()
            block_num = block.blockNumber()
            in_string = False
            escape = False
            for ch in line:
                if in_string:
                    if escape:
                        escape = False
                    elif ch == '\\':
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch in '{[':
                        stack.append((ch, block_num))
                    elif ch in '}]':
                        expected = '{' if ch == '}' else '['
                        if stack and stack[-1][0] == expected:
                            _, start = stack.pop()
                            if block_num > start + 1:
                                fold_regions[start] = max(fold_regions.get(start, start), block_num)
            block = block.next()
        self.fold_regions = fold_regions
        self.folded_starts = {s for s in self.folded_starts if s in self.fold_regions}
        self.apply_fold_visibility()

    def toggle_fold(self, start_block_number):
        if start_block_number not in self.fold_regions:
            return
            
        if start_block_number in self.folded_starts:
            self.folded_starts.remove(start_block_number)
        else:
            self.folded_starts.add(start_block_number)
            # 如果当前光标在被折叠的区域内，则将光标移出到折叠节点起始行
            cursor_block = self.textCursor().blockNumber()
            end_block = self.fold_regions.get(start_block_number, start_block_number)
            if start_block_number < cursor_block <= end_block:
                cursor = self.textCursor()
                start_block = self.document().findBlockByNumber(start_block_number)
                cursor.setPosition(start_block.position())
                self.setTextCursor(cursor)
                
        self.apply_fold_visibility()
        
        # 折叠/展开后，尝试恢复滚动条位置，或者确保当前操作的块仍然可见
        # 我们优先确保被点击折叠的这一行在视口内
        start_block = self.document().findBlockByNumber(start_block_number)
        if start_block.isValid():
            # 将光标移动到被折叠/展开的块
            cursor = self.textCursor()
            cursor.setPosition(start_block.position())
            self.setTextCursor(cursor)
            # 强制确保光标所在的这一行在视口内可见
            # 因为我们在 apply_fold_visibility 中做了布局的强制刷新
            # 我们需要在这里通过定时器稍微延迟一下，确保布局刷新完成后再滚动
            QtCore.QTimer.singleShot(0, self.ensureCursorVisible)

    def apply_fold_visibility(self):
        if not self.folding_enabled or not (self.folded_starts or self.skip_map):
            return
        blocks_to_hide = set()
        self.skip_map.clear()

        for start in sorted(self.folded_starts):
            if start in blocks_to_hide:
                continue
            end = self.fold_regions[start]
            self.skip_map[start + 1] = end
            blocks_to_hide.update(range(start + 1, end))

        block = self.document().firstBlock()
        dirty = False
        while block.isValid():
            b_num = block.blockNumber()
            should_hide = b_num in blocks_to_hide
            
            if block.isVisible() == should_hide:
                block.setVisible(not should_hide)
                # 只对可见性发生变化的块标记 dirty
                self.document().markContentsDirty(block.position(), block.length())
                dirty = True
                
            block = block.next()
            
        if dirty:
            # 强制更新文档布局
            self.document().documentLayout().requestUpdate()
            
            # 黑科技：通过切换换行模式强制重新计算滚动条和视口
            wrap_mode = self.lineWrapMode()
            self.setLineWrapMode(QPlainTextEdit.WidgetWidth if wrap_mode == QPlainTextEdit.NoWrap else QPlainTextEdit.NoWrap)
            self.setLineWrapMode(wrap_mode)
            
            self.viewport().update()
            self.lineNumberArea.update()

    def expand_folds_for_position(self, position):
        if not self.folding_enabled:
            return
        block = self.document().findBlock(position)
        if not block.isValid():
            return
        block_number = block.blockNumber()
        changed = False
        for start in list(self.folded_starts):
            end = self.fold_regions.get(start)
            if end is not None and start < block_number <= end:
                self.folded_starts.remove(start)
                changed = True
        if changed:
            self.apply_fold_visibility()

    def expand_all_folds(self):
        if not self.folding_enabled:
            return
        if not self.folded_starts:
            return
        self.folded_starts.clear()
        self.apply_fold_visibility()

    # ====== 当前行高亮 ======
    def highlight_current_line(self):
        extraSelections = []
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

    def set_search_selections(self, selections, cursor=None):
        self.search_extra_selections = selections
        position_changed = cursor is not None and cursor.position() != self.textCursor().position()
        if cursor is not None:
            self.setTextCursor(cursor)
        # 光标移动时，cursorPositionChanged 已经刷新高亮。
        if not position_changed:
            self.highlight_current_line()

    # ====== 绘制 placeholder ======
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.document().isEmpty() and self.placeholder:
            painter = QPainter(self.viewport())
            # placeholder 颜色
            painter.setPen(QColor(self.theme["placeholder"]))
            painter.drawText(self.viewport().rect().adjusted(9, 9, -9, -9),
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

    def mousePressEvent(self, event):
        self.editor.line_number_area_mouse_press_event(event)

# ====== 支持 placeholder 的 QTreeWidget ======
class PlaceholderTreeWidget(QTreeWidget):
    """
    扩展 QTreeWidget，空时显示 placeholder
    """
    def __init__(self, placeholder="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.placeholder = placeholder
        self.theme = THEMES["light"]
        self.setUniformRowHeights(True)
        self.itemExpanded.connect(self.load_children)
        # 数据变化时刷新绘制 placeholder
        self.model().rowsInserted.connect(self.refresh_placeholder)
        self.model().rowsRemoved.connect(self.refresh_placeholder)
        self.model().modelReset.connect(self.refresh_placeholder)

    def set_json(self, data, lazy=False):
        self.clear()
        root = self.make_item(None, data)
        self.addTopLevelItem(root)
        if not lazy:
            self.expand_subtree(root)

    @staticmethod
    def child_entries(value):
        if isinstance(value, dict):
            return iter(value.items())
        if isinstance(value, list):
            return ((f"[{index}]", child) for index, child in enumerate(value))
        return iter(())

    @staticmethod
    def node_label(key, value):
        if isinstance(value, (dict, list)):
            if key is not None:
                return key
            return "对象" if isinstance(value, dict) else "数组"
        display = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return f"{key}: {display}" if key is not None else display

    def make_item(self, key, value):
        item = QTreeWidgetItem([self.node_label(key, value)])
        item.json_key = key
        item.json_value = value
        item.has_unloaded_children = isinstance(value, (dict, list)) and bool(value)
        if item.has_unloaded_children:
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        return item

    def load_children(self, item):
        if item.has_unloaded_children:
            item.has_unloaded_children = False
            item.addChildren([self.make_item(key, value) for key, value in self.child_entries(item.json_value)])
            item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicatorWhenChildless)

    def expand_subtree(self, item):
        self.load_children(item)
        if not item.childCount():
            return
        item.setExpanded(True)
        for index in range(item.childCount()):
            self.expand_subtree(item.child(index))

    def expandAll(self):
        root = self.topLevelItem(0)
        if root is not None:
            self.expand_subtree(root)

    def iter_labels(self):
        root = self.topLevelItem(0)
        if root is None:
            return

        # Iterators keep the traversal in tree order without constructing widget items.
        stack = [iter([(None, root.json_value)])]
        path_indices = [-1]
        while stack:
            entry = next(stack[-1], None)
            if entry is None:
                stack.pop()
                path_indices.pop()
                continue
            key, value = entry
            path_indices[-1] += 1
            yield tuple(path_indices[1:]), self.node_label(key, value)
            if isinstance(value, (dict, list)) and value:
                stack.append(self.child_entries(value))
                path_indices.append(-1)

    def reveal_path(self, path):
        item = self.topLevelItem(0)
        for index in path:
            self.load_children(item)
            item.setExpanded(True)
            item = item.child(index)
        return item

    def refresh_placeholder(self, *args):
        """刷新 placeholder 显示"""
        self.viewport().update()

    def set_theme(self, theme_config):
        self.theme = theme_config
        self.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.theme['tree_bg']};
                color: {self.theme['text_color']};
                border: none;
                padding: 5px 4px;
                show-decoration-selected: 1;
            }}
            QTreeWidget::item {{ min-height: 25px; }}
            QTreeWidget::item:hover {{ background: {self.theme['header_bg']}; }}
            QTreeWidget::item:selected {{
                background: {self.theme['selection_bg']};
                color: {self.theme['text_color']};
            }}
        """)
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.topLevelItemCount() == 0 and self.placeholder:
            painter = QPainter(self.viewport())
            # placeholder 颜色
            painter.setPen(QColor(self.theme["placeholder"]))
            painter.drawText(self.viewport().rect().adjusted(9, 9, -9, -9),
                             Qt.AlignTop | Qt.AlignLeft,
                             self.placeholder)

# ====== 可折叠面板 ======
class CollapsiblePanel(QFrame):
    expanded_changed = QtCore.Signal(bool)
    COLLAPSED_WIDTH = 1

    def __init__(self, title, compact_title, content_widget, expanded_text="‹", parent=None):
        super().__init__(parent)
        self.setObjectName("workspacePanel")
        self.content_widget = content_widget
        self.is_expanded = True
        self.compact_title = compact_title
        self.collapse_arrow = expanded_text
        self.search_widget = None
        self.search_was_visible = False

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = QWidget()
        self.header.setObjectName("panelHeader")
        self.header.setFixedHeight(39)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(11, 0, 5, 0)
        header_layout.setSpacing(2)

        self.leading_controls = QHBoxLayout()
        self.leading_controls.setSpacing(2)
        header_layout.addLayout(self.leading_controls)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("panelTitle")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.search_btn = QToolButton()
        self.search_btn.setFixedSize(27, 27)
        self.search_btn.setToolTip(f"搜索{title}")
        self.search_btn.setAccessibleName(self.search_btn.toolTip())
        self.search_btn.setCursor(Qt.PointingHandCursor)
        header_layout.addWidget(self.search_btn)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("panelToggle")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.update_toggle_button()
        self.trailing_controls = QHBoxLayout()
        self.trailing_controls.setSpacing(2)
        self.trailing_controls.addWidget(self.toggle_btn)
        header_layout.addLayout(self.trailing_controls)

        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_widget, 1)
        self.set_expanded(True)

    def add_search_widget(self, widget):
        self.search_widget = widget
        self.main_layout.insertWidget(1, widget)
        widget.hide()

    def set_theme(self, theme):
        self.search_btn.setIcon(toolbar_icon("search", theme["btn_text"]))

    def update_toggle_button(self, restore=False, destination=None):
        button = self.toggle_btn
        if restore:
            text, label, width = "恢复布局", "恢复默认三栏布局", 64
        elif destination is not None:
            text = f"‹ {self.compact_title}" if destination == "left" else f"{self.compact_title} ›"
            label, width = f"展开{self.title_label.text()}", 52
        else:
            text, label, width = self.collapse_arrow, f"折叠{self.title_label.text()}", 23

        button.setFixedSize(width, 27)
        button.setText(text)
        button.setToolTip(label)
        button.setAccessibleName(label)
        labeled = restore or destination is not None
        if button.property("labeled") != labeled:
            button.setProperty("labeled", labeled)
            button.style().unpolish(button)
            button.style().polish(button)

    def mousePressEvent(self, event):
        if not self.is_expanded and event.button() == Qt.LeftButton:
            self.set_expanded(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def set_expanded(self, expanded):
        if self.search_widget is not None and self.is_expanded != expanded:
            if not expanded:
                self.search_was_visible = not self.search_widget.isHidden()
            self.search_widget.setVisible(expanded and self.search_was_visible)
        self.is_expanded = expanded
        self.header.setVisible(expanded)
        self.content_widget.setVisible(expanded)
        self.setToolTip("" if expanded else f"展开{self.title_label.text()}")
        self.setCursor(Qt.ArrowCursor if expanded else Qt.PointingHandCursor)
        self.setMaximumWidth(16777215 if expanded else self.COLLAPSED_WIDTH)
        self.setMinimumWidth(0 if expanded else self.COLLAPSED_WIDTH)
        self.setSizePolicy(QSizePolicy.Preferred if expanded else QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setProperty("collapsed", not expanded)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        self.expanded_changed.emit(expanded)

# ====== 可双击修改的标题标签 ======
class EditableTitleLabel(QLabel):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setToolTip("双击修改标题")
        self.setCursor(Qt.PointingHandCursor)

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
        self.pattern = None
        self.theme = THEMES["light"]
        self.current_item = None
        self.current_match_index = -1
        self._doc = QTextDocument()
        self._doc.setDocumentMargin(0)

    def set_theme(self, theme):
        self.theme = theme

    def set_search_config(self, keyword, theme):
        self.pattern = re.compile(re.escape(keyword), re.IGNORECASE) if keyword else None
        self.set_theme(theme)
        self.set_current_match(None, -1)

    def set_current_match(self, item, match_index):
        self.current_item = item
        self.current_match_index = match_index

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        text = options.text
        item = self.parent().itemFromIndex(index)
        key = item.json_key
        is_scalar = not isinstance(item.json_value, (dict, list))
        value_start = len(key) + 2 if is_scalar and key is not None else len(text)
        matches = list(self.pattern.finditer(text)) if self.pattern else []
        if not matches and value_start == len(text):
            super().paint(painter, option, index)
            return

        style = options.widget.style() if options.widget else QApplication.style()
        text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, options, options.widget)
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter, options.widget)

        def text_segment(start, end):
            key_text = html.escape(text[start:min(end, value_start)])
            value = html.escape(text[max(start, value_start):end])
            return f'{key_text}<span style="color:{self.theme["tree_value"]}">{value}</span>' if value else key_text

        parts = []
        end = 0
        colors = self.theme["highlight"]
        for index, match in enumerate(matches):
            parts.append(text_segment(end, match.start()))
            current = item == self.current_item and index == self.current_match_index
            background = colors["search_current"] if current else colors["search_match"]
            foreground = colors["highlight_fg"] if current else self.theme["text_color"]
            matched_text = html.escape(match.group())
            parts.append(f'<span style="background:{background};color:{foreground}">{matched_text}</span>')
            end = match.end()
        parts.append(text_segment(end, len(text)))

        painter.save()
        self._doc.setDefaultFont(options.font)
        self._doc.setTextWidth(text_rect.width())
        content = "".join(parts)
        self._doc.setHtml(f'<div style="color:{self.theme["text_color"]};white-space:pre">{content}</div>')
        painter.translate(text_rect.topLeft())
        painter.setClipRect(0, 0, text_rect.width(), text_rect.height())
        painter.translate(0, (text_rect.height() - self._doc.size().height()) / 2)
        self._doc.drawContents(painter)
        painter.restore()


# ====== JSON 格式化窗口 ======
class JsonFormatterWindow(QWidget):
    window_count = 0     # 窗口计数，用于区分标题
    SETTINGS_ORG = "lawliet"
    SETTINGS_APP = "json-format-pyside6"
    SETTINGS_GROUP = "json_formatter_window_layout"
    DEFAULT_WINDOW_WIDTH = 1200
    DEFAULT_WINDOW_HEIGHT = 700

    def __init__(self):
        super().__init__()
        JsonFormatterWindow.window_count += 1
        self.window_number = JsonFormatterWindow.window_count
        self.setWindowTitle(f"JSON 工具" + (f" {self.window_number}" if self.window_number > 1 else ""))
        self.resize(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)

        # 使用固定宽度字体
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        if sys.platform == "darwin":
            font.setFamily("Menlo")
        font.setPointSize(15)

        # ====== 输入编辑器 ======
        self.input_edit = CodeEditor(placeholder="原始 JSON")
        self.input_edit.setFont(font)
        self.format_timer = QtCore.QTimer(self)
        self.format_timer.setSingleShot(True)
        self.format_timer.setInterval(150)
        self.format_timer.timeout.connect(self.auto_format_input)
        self.input_edit.textChanged.connect(self.format_timer.start)

        # ====== 输出树 ======
        self.output_tree = PlaceholderTreeWidget(
            placeholder="选中节点查看对应 JSON"
        )
        self.output_tree.setHeaderHidden(True)
        tree_font = self.output_tree.font()
        tree_font.setPointSize(font.pointSize())
        self.output_tree.setFont(tree_font)
        self.output_tree.itemClicked.connect(self.on_tree_item_clicked)
        # 设置搜索高亮代理
        self.search_delegate = SearchHighlightDelegate(self.output_tree)
        self.output_tree.setItemDelegate(self.search_delegate)
        # 添加右键菜单
        self.output_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output_tree.customContextMenuRequested.connect(self.open_tree_context_menu)

        # ====== 输出文本 ======
        self.output_edit = CodeEditor(placeholder="格式化结果将显示在这里")
        # 添加 JSON 高亮器
        self.highlighter = JsonHighlighter(self.output_edit.document())
        self.output_edit.setFont(font)
        self.output_edit.setReadOnly(True)
        self.output_edit.enable_json_folding(True)
        self.input_edit.blockCountChanged.connect(self.sync_line_number_digits)
        self.output_edit.blockCountChanged.connect(self.sync_line_number_digits)
        self.sync_line_number_digits()
        palette = self.output_edit.palette()
        palette.setColor(QPalette.PlaceholderText, QColor("#999999"))  # placeholder 灰色
        self.output_edit.setPalette(palette)

        self.left_panel = CollapsiblePanel("原始 JSON", "原始", self.input_edit)
        self.middle_panel = CollapsiblePanel("JSON 树", "树", self.output_tree, expanded_text="›")
        self.right_panel = CollapsiblePanel("格式化结果", "结果", self.output_edit, expanded_text="›")
        self.workspace_panels = (self.left_panel, self.middle_panel, self.right_panel)

        self.splitter = QSplitter()
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)
        for panel in self.workspace_panels:
            self.splitter.addWidget(panel)
        self.splitter.setSizes(self.default_splitter_sizes())

        self.btn_format = QPushButton("格式化")
        self.btn_format.setObjectName("primaryAction")
        self.btn_compress = QPushButton("压缩")
        self.btn_loose_parse = QPushButton("宽松解析")
        self.btn_copy = QPushButton("复制结果")
        self.copy_feedback = QtCore.QTimer(self)
        self.copy_feedback.setSingleShot(True)
        self.copy_feedback.timeout.connect(lambda: self.btn_copy.setText("复制结果"))
        self.btn_save = QPushButton("保存")

        self.btn_format.clicked.connect(self.format_json)
        self.btn_compress.clicked.connect(self.compress_json)
        self.btn_loose_parse.clicked.connect(self.loose_parse_json)
        self.btn_copy.clicked.connect(self.copy_result)
        self.btn_save.clicked.connect(self.save_file)

        self.is_pinned = False
        self.btn_pin_window = QToolButton()
        self.btn_pin_window.setFixedSize(34, 32)
        self.btn_pin_window.setCheckable(True)
        self.btn_pin_window.setCursor(Qt.PointingHandCursor)
        self.btn_pin_window.setToolTip("置顶窗口")
        self.btn_pin_window.setAccessibleName("置顶窗口")
        self.btn_pin_window.toggled.connect(self.toggle_window_pin)

        self.btn_layout = QToolButton()
        self.btn_layout.setObjectName("layoutMenuButton")
        self.btn_layout.setText("布局")
        self.btn_layout.setToolTip("切换三栏布局")
        self.btn_layout.setCursor(Qt.PointingHandCursor)
        self.btn_layout.setPopupMode(QToolButton.InstantPopup)
        layout_menu = QMenu(self.btn_layout)
        for label, panels in (
            ("原始 JSON + 结果", (True, False, True)),
            ("原始 JSON + JSON 树", (True, True, False)),
            ("JSON 树 + 结果", (False, True, True)),
        ):
            layout_menu.addAction(label, lambda states=panels: self.switch_layout(*states))
        layout_menu.addSeparator()
        layout_menu.addAction("恢复默认三栏布局", self.restore_default_layout)
        self.btn_layout.setMenu(layout_menu)

        self.title_label = EditableTitleLabel(self.windowTitle(), self)
        self.title_label.setObjectName("workspaceTitle")
        self.title_label.setMaximumWidth(180)
        self.title_label.setMinimumWidth(96)
        self.title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        toolbar = QFrame()
        toolbar.setObjectName("workspaceToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(17, 0, 15, 0)
        toolbar_layout.setSpacing(7)
        toolbar.setFixedHeight(40)
        toolbar_layout.addWidget(self.title_label)
        toolbar_layout.addSpacing(12)
        for button in (self.btn_format, self.btn_compress, self.btn_loose_parse):
            button.setCursor(Qt.PointingHandCursor)
            toolbar_layout.addWidget(button)
        toolbar_layout.addStretch()
        for button in (self.btn_copy, self.btn_save, self.btn_layout, self.btn_pin_window):
            button.setCursor(Qt.PointingHandCursor)
            toolbar_layout.addWidget(button)

        self.parse_warning = QLabel()
        self.parse_warning.setObjectName("parseWarning")
        self.parse_warning.setWordWrap(True)
        self.parse_warning.hide()
        self.right_panel.main_layout.insertWidget(1, self.parse_warning)
        self.right_panel.expanded_changed.connect(
            lambda expanded: self.parse_warning.setVisible(expanded and bool(self.parse_warning.text()))
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.splitter, 1)

        # 使用延迟保存，避免在拖动 splitter 或连续调整窗口大小时频繁写入配置。
        self.layout_save_timer = QtCore.QTimer(self)
        self.layout_save_timer.setSingleShot(True)
        self.layout_save_timer.timeout.connect(self.save_layout_state)
        self.splitter.splitterMoved.connect(self.schedule_layout_save)
        for panel in self.workspace_panels:
            panel.expanded_changed.connect(self.update_splitter_handles)
            panel.toggle_btn.clicked.connect(lambda checked=False, current=panel: self.toggle_workspace_panel(current))
        for index in range(1, self.splitter.count()):
            self.splitter.handle(index).installEventFilter(self)

        # 在事件循环启动后恢复上次布局。
        # 这样可以确保 splitter 已经有了有效宽度，恢复比例时更稳定。
        QtCore.QTimer.singleShot(0, self.restore_layout_state)

        # ====== 菜单栏 ======
        menu_bar = QMenuBar()
        file_menu = QMenu("文件", self)
        menu_bar.addMenu(file_menu)
        file_menu.addAction(self.new_json_window_action())
        file_menu.addAction("打开字符串格式化窗口", QKeySequence("Ctrl+Alt+S"), self.open_string_formatter_window)
        file_menu.addAction("打开时间戳转换窗口", QKeySequence("Ctrl+Alt+T"), self.open_timestamp_converter_window)
        file_menu.addSeparator()
        file_menu.addAction("打开 JSON 文件", QKeySequence(QKeySequence.StandardKey.Open), self.open_file)
        file_menu.addAction("保存结果", QKeySequence(QKeySequence.StandardKey.Save), self.save_file)
        file_menu.addAction("收起当前窗口", QKeySequence("Ctrl+W"), self.close)
        file_menu.addSeparator()
        # 退出应用时真正销毁所有窗口。
        quit_action = file_menu.addAction("退出")
        quit_action.setMenuRole(QAction.QuitRole)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))  # macOS 上自动映射为 Cmd+Q
        quit_action.triggered.connect(JsonFormatterWindow.quit_app)

        json_menu = QMenu("JSON", self)
        menu_bar.addMenu(json_menu)
        json_menu.addAction("格式化", QKeySequence("Ctrl+Shift+F"), self.format_json)
        json_menu.addAction("压缩", QKeySequence("Ctrl+Shift+M"), self.compress_json)
        json_menu.addAction("宽松解析", QKeySequence("Ctrl+Shift+R"), self.loose_parse_json)
        json_menu.addAction("复制结果", QKeySequence("Ctrl+Shift+C"), self.copy_result)
        json_menu.addSeparator()
        json_menu.addAction("查找", QKeySequence(QKeySequence.StandardKey.Find), lambda: self.open_search())
        next_match_action = json_menu.addAction("查找下一处", self.next_match_current)
        next_match_action.setShortcuts([QKeySequence("Ctrl+G"), QKeySequence("F3")])
        prev_match_action = json_menu.addAction("查找上一处", self.prev_match_current)
        prev_match_action.setShortcuts([QKeySequence("Ctrl+Shift+G"), QKeySequence("Shift+F3")])

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
        # 添加“关于 JSON 工具”菜单项
        about_action = help_menu.addAction("关于 JSON 工具")
        about_action.triggered.connect(self.show_about_dialog)

        # ====== 窗口菜单（多窗口设计第三节：菜单名称固定为「窗口」）======
        # 菜单内容 = 窗口管理器中注册的全部窗口；
        # ✓ 表示窗口当前可见，允许多个窗口同时 ✓（多选语义，非单选）。
        self.window_menu = QMenu("窗口", self)
        menu_bar.addMenu(self.window_menu)

        # ===== 搜索框（两栏）=====
        self.search_panels = {
            "input": SearchPanel(self.left_panel, self.input_edit),
            "output": SearchPanel(self.right_panel, self.output_edit),
            "tree": TreeSearchPanel(self.middle_panel, self.output_tree)
        }

        # 将搜索面板添加到对应的折叠面板中
        self.left_panel.add_search_widget(self.search_panels["input"])
        self.right_panel.add_search_widget(self.search_panels["output"])
        for key, panel in (("input", self.left_panel), ("tree", self.middle_panel), ("output", self.right_panel)):
            panel.search_btn.clicked.connect(lambda checked=False, target=key: self.open_search(target))
        self.middle_panel.add_search_widget(self.search_panels["tree"])

        # 将当前窗口登记到全局窗口管理器：
        # 1. 分配稳定 UUID（不再使用 id(window)）
        # 2. 登记本窗口的「窗口」菜单，由管理器统一重建 ✓ 列表
        manager = WindowManager.instance()
        manager.register_window_menu(self.window_menu)
        manager.register(self, title=self.windowTitle(), kind="json")
        
        # 初始化主题
        self.current_theme_mode = "auto"
        self._is_applying_theme = False
        self.apply_theme()

    def sync_line_number_digits(self):
        digits = len(str(max(self.input_edit.blockCount(), self.output_edit.blockCount())))
        self.input_edit.set_shared_line_number_digits(digits)
        self.output_edit.set_shared_line_number_digits(digits)

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
            if getattr(self, "current_theme_mode", None) == "auto" and not self._is_applying_theme:
                # 只有当不在应用主题时才尝试重新应用
                self.apply_theme()
        super().changeEvent(event)

    def toggle_window_pin(self, pinned):
        """
        切换窗口是否保持在桌面最前层显示。

        这里直接切换 Qt.WindowStaysOnTopHint。
        Qt 在修改顶层窗口 flag 后，通常需要重新 show 一次，
        才能让新的窗口层级立即生效。
        """
        self.is_pinned = pinned
        self.btn_pin_window.setToolTip("取消置顶" if pinned else "置顶窗口")
        self.btn_pin_window.setAccessibleName(self.btn_pin_window.toolTip())
        self.update_pin_icon()

        # 记录当前几何信息，避免在重新应用窗口 flag 后出现位置偏移。
        current_geometry = self.geometry()

        # 只调整“始终置顶”这一项，不改动其他窗口标志。
        self.setWindowFlag(Qt.WindowStaysOnTopHint, pinned)

        # 重新显示窗口，让新的窗口层级立即生效。
        self.show()
        self.setGeometry(current_geometry)
        self.raise_()
        self.activateWindow()

    def apply_theme(self):
        if self._is_applying_theme:
            return

        self._is_applying_theme = True
        try:
            mode = self.detect_system_theme() if self.current_theme_mode == "auto" else self.current_theme_mode
            theme = THEMES[mode]
            self.current_theme_data = theme
            self.setObjectName("jsonWorkspace")
            self.setStyleSheet(f"""
                QWidget#jsonWorkspace {{ background: {theme['window_bg']}; }}
                QLabel {{ color: {theme['text_color']}; }}
                QFrame#workspaceToolbar {{
                    background: {theme['header_bg']};
                    border-bottom: 1px solid {theme['border_color']};
                }}
                QLabel#workspaceTitle {{ font-size: 18px; font-weight: 700; }}
                QFrame#workspacePanel {{
                    background: {theme['input_bg']};
                    border: none;
                }}
                QWidget#panelHeader {{
                    background: {theme['header_bg']};
                    border-bottom: 1px solid {theme['header_border']};
                }}
                QLabel#panelTitle {{ color: {theme['header_text']}; font-weight: 600; }}
                QFrame#workspaceToolbar QPushButton, QFrame#workspaceToolbar QToolButton {{
                    background: {theme['btn_bg']};
                    color: {theme['btn_text']};
                    border: 1px solid {theme['border_color']};
                    border-radius: 6px;
                    min-height: 30px;
                    padding: 0px 11px;
                }}
                QFrame#workspaceToolbar QToolButton {{ padding: 0px; }}
                QFrame#workspaceToolbar QToolButton::menu-indicator {{
                    subcontrol-origin: padding;
                    subcontrol-position: center right;
                    right: 7px;
                }}
                QFrame#workspaceToolbar QToolButton#layoutMenuButton {{ padding: 0px 21px 0px 10px; }}
                QFrame#workspaceToolbar QPushButton:hover, QFrame#workspaceToolbar QToolButton:hover {{
                    background: {theme['btn_hover']};
                }}
                QFrame#workspaceToolbar QToolButton:checked {{
                    background: {theme['accent_soft']};
                    border-color: {theme['accent']};
                }}
                QFrame#workspaceToolbar QPushButton:focus, QFrame#workspaceToolbar QToolButton:focus {{
                    border-color: {theme['accent']};
                }}
                QFrame#workspaceToolbar QPushButton#primaryAction {{
                    background: {theme['accent']};
                    color: {theme['on_accent']};
                    border: 1px solid {theme['accent']};
                    font-weight: 600;
                    padding: 0px 15px;
                }}
                QFrame#workspaceToolbar QPushButton#primaryAction:hover,
                QFrame#workspaceToolbar QPushButton#primaryAction:pressed {{
                    background: {theme['accent_hover']};
                    border-color: {theme['accent_hover']};
                }}
                QFrame#workspaceToolbar QPushButton#primaryAction:focus {{
                    border-color: {theme['on_accent']};
                }}
                QWidget#panelHeader QToolButton {{
                    background: transparent;
                    color: {theme['btn_text']};
                    border: 1px solid transparent;
                    border-radius: 5px;
                }}
                QWidget#panelHeader QToolButton:hover {{ background: {theme['btn_hover']}; }}
                QWidget#panelHeader QToolButton:focus {{ border-color: {theme['accent']}; }}
                QToolButton#panelToggle {{ font-size: 19px; }}
                QToolButton#panelToggle[labeled="true"] {{ font-size: 12px; }}
                QLabel#parseWarning {{
                    background: {theme['warning_bg']};
                    color: {theme['warning_text']};
                    padding: 7px 10px;
                }}
                QMenuBar, QMenu {{
                    background: {theme['header_bg']};
                    color: {theme['text_color']};
                }}
                QMenu {{ border: 1px solid {theme['border_color']}; padding: 4px; }}
                QMenu::item {{ padding: 5px 22px 5px 12px; }}
                QMenu::item:selected, QMenuBar::item:selected {{ background: {theme['accent_soft']}; }}
                QMenu::separator {{ height: 1px; background: {theme['header_border']}; margin: 4px; }}
                QSplitter::handle {{ background: {theme['header_border']}; }}
                QSplitter::handle:hover, QSplitter::handle:pressed {{ background: {theme['accent']}; }}
                QFrame#workspacePanel[collapsed="true"] {{ background: {theme['header_border']}; }}
                QFrame#workspacePanel[collapsed="true"]:hover {{ background: {theme['accent']}; }}
                QScrollBar:vertical {{ width: 10px; background: transparent; }}
                QScrollBar:horizontal {{ height: 10px; background: transparent; }}
                QScrollBar::handle {{
                    background: {theme['scrollbar_handle']};
                    min-width: 25px;
                    min-height: 25px;
                    border: 2px solid {theme['input_bg']};
                    border-radius: 5px;
                }}
                QScrollBar::handle:hover {{ background: {theme['scrollbar_handle_hover']}; }}
                QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
                QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
            """)

            self.input_edit.set_theme(theme)
            self.output_edit.set_theme(theme)
            self.output_tree.set_theme(theme)
            self.search_delegate.set_theme(theme)
            self.highlighter.set_theme(theme)
            self.update_pin_icon()
            for panel in (self.left_panel, self.middle_panel, self.right_panel):
                panel.set_theme(theme)
            for panel in self.search_panels.values():
                panel.set_theme(theme)
        finally:
            self._is_applying_theme = False

    def update_pin_icon(self):
        theme = self.current_theme_data
        color = theme["accent"] if self.is_pinned else theme["btn_text"]
        self.btn_pin_window.setIcon(toolbar_icon("pin", color))

    # ====== 核心 JSON 处理逻辑 ======
    def parse_nested_json_value(self, value):
        if not isinstance(value, str):
            return value
        candidate = value.strip()
        if len(candidate) >= 2 and candidate[0] == '`' and candidate[-1] == '`':
            candidate = candidate[1:-1].strip()
        attempts = [candidate]
        if '\\"' in candidate:
            attempts.append(candidate.replace('\\"', '"'))
        for attempt in attempts:
            current = attempt
            for _ in range(3):
                try:
                    parsed = json.loads(current)
                except Exception:
                    break
                if isinstance(parsed, str):
                    next_current = parsed.strip()
                    if next_current == current:
                        return parsed
                    current = next_current
                    continue
                return parsed
        return value

    def parse_nested_json_object(self, obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                parsed_v = self.parse_nested_json_value(v)
                obj[k] = parsed_v
                if isinstance(parsed_v, (dict, list)):
                    self.parse_nested_json_object(parsed_v)
        elif isinstance(obj, list):
            for i, v in enumerate(list(obj)):
                parsed_v = self.parse_nested_json_value(v)
                obj[i] = parsed_v
                if isinstance(parsed_v, (dict, list)):
                    self.parse_nested_json_object(parsed_v)
        return obj

    def set_json_result(self, text, data=None, warning=""):
        if text:
            # 小文档保持默认展开，大文档在展开节点时创建对应的子项。
            self.output_tree.set_json(data, lazy=len(text) >= 100_000)
        else:
            self.output_tree.clear()
        self.output_edit.setPlainText(text)
        self.search_panels["tree"].do_search()
        self.parse_warning.setText(warning)
        self.parse_warning.setVisible(bool(warning) and self.right_panel.is_expanded)

    def process_json(self, text: str, show_error_dialog=True, expand_nested=False):
        """格式化 JSON，或从混合文本中提取第一个有效的对象或数组。"""
        if not text:
            self.set_json_result("")
            return

        warning = ""
        warning_details = ""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            extracted = self.extract_json_from_text(text)
            if extracted is None:
                self.set_json_result("")
                if show_error_dialog:
                    QMessageBox.critical(
                        self, "格式化失败", f"{error.msg}\n行: {error.lineno}, 列: {error.colno}"
                    )
                return
            data = extracted
            warning = "已提取首个有效 JSON，结果仅包含提取的内容。"
            warning_details = f"原始解析错误: {error.msg}（第 {error.lineno} 行，第 {error.colno} 列）"

        if expand_nested:
            data = self.parse_nested_json_object(data)

        self.set_json_result(json.dumps(data, indent=4, ensure_ascii=False), data, warning)
        if warning and show_error_dialog:
            QMessageBox.warning(self, "输入包含非 JSON 内容", f"{warning}\n{warning_details}")

    def extract_json_from_text(self, text):
        """返回混合文本中的第一个有效 JSON 对象或数组。"""
        decoder = json.JSONDecoder()
        for match in re.finditer(r"[{\[]", text):
            try:
                data, _ = decoder.raw_decode(text, match.start())
                return data
            except (json.JSONDecodeError, RecursionError):
                continue
        return None

    # ====== 自动格式化输入 JSON ======
    def auto_format_input(self):
        """
        自动格式化：实时解析输入（不弹窗提示错误）
        """
        self.format_timer.stop()
        text = self.input_edit.toPlainText().strip()
        self.process_json(text, show_error_dialog=False)

    # ====== 点击“格式化”按钮 ======
    def format_json(self):
        """
        按钮触发格式化：会显示错误提示框
        """
        self.format_timer.stop()
        text = self.input_edit.toPlainText().strip()
        self.process_json(text, show_error_dialog=True)

    def normalize_loose_json_text(self, text: str) -> str:
        normalized = text.strip()
        fence_pattern = r'^\s*```(?:json)?\s*([\s\S]*?)\s*```\s*$'
        fence_match = re.match(fence_pattern, normalized, flags=re.IGNORECASE)
        if fence_match:
            normalized = fence_match.group(1)

        normalized = normalized.replace('\u00a0', ' ')
        normalized = re.sub(r'\\\s*$', '', normalized)

        if re.match(r'^\s*[\{\[]\\"', normalized):
            normalized = re.sub(r'(?<!\\)\\"', '"', normalized)

        normalized = re.sub(
            r'`([^`\\]*(?:\\.[^`\\]*)*)`',
            lambda m: json.dumps(m.group(1), ensure_ascii=False),
            normalized
        )

        # 仅在“宽松解析”链路中兜底修复字符串里的非法单反斜杠。
        # 例如业务文本里的 "\新版"、"\11CM" 在标准 JSON 中都属于非法转义，
        # 这里将它们修复为 "\\新版"、"\\11CM"，以便后续 json.loads 可以接受。
        normalized = self.escape_invalid_backslashes_in_strings(normalized)

        previous = None
        while previous != normalized:
            previous = normalized
            normalized = re.sub(r',(\s*[}\]])', r'\1', normalized)

        return normalized

    def escape_invalid_backslashes_in_strings(self, text: str) -> str:
        """
        仅用于“宽松解析”按钮对应的预处理阶段。

        处理目标：
        - 只扫描 JSON 双引号字符串内部的内容；
        - 如果遇到反斜杠后面不是合法 JSON 转义字符，
          就把这个单反斜杠补成双反斜杠；
        - 已经合法的转义（如 \\n、\\t、\\"、\\\\、\\u4E2D）保持不变。

        这样可以兼容业务文本中常见的路径分隔、规格分段等写法，
        同时避免影响普通“格式化”按钮的严格 JSON 解析行为。
        """
        result = []
        in_string = False
        index = 0
        valid_escape_chars = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't'}

        while index < len(text):
            char = text[index]

            if not in_string:
                result.append(char)
                if char == '"':
                    in_string = True
                index += 1
                continue

            if char == '"':
                result.append(char)
                in_string = False
                index += 1
                continue

            if char != '\\':
                result.append(char)
                index += 1
                continue

            # 字符串内遇到反斜杠时，先判断它是否构成合法 JSON 转义。
            next_index = index + 1
            if next_index >= len(text):
                # 末尾孤立反斜杠无法组成合法转义，补成字面量反斜杠。
                result.append('\\\\')
                index += 1
                continue

            next_char = text[next_index]
            if next_char in valid_escape_chars:
                result.append(char)
                result.append(next_char)
                index += 2
                continue

            if next_char == 'u':
                # \u 后面必须紧跟 4 位十六进制字符，否则也视为非法转义并转义反斜杠本身。
                unicode_digits = text[next_index + 1: next_index + 5]
                if len(unicode_digits) == 4 and re.fullmatch(r'[0-9a-fA-F]{4}', unicode_digits):
                    result.append(char)
                    result.append(next_char)
                    result.append(unicode_digits)
                    index += 6
                    continue

            # 这里说明是非法转义，例如 \版、\1、\x。
            # 只把当前反斜杠补成双反斜杠，后面的字符按原样继续处理。
            result.append('\\\\')
            index += 1

        return ''.join(result)

    def complete_json_structure(self, text: str) -> str:
        stack = []
        in_string = False
        escape = False
        for ch in text:
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch in '{[':
                    stack.append(ch)
                elif ch in '}]' and stack:
                    top = stack[-1]
                    if (top == '{' and ch == '}') or (top == '[' and ch == ']'):
                        stack.pop()
        completed = text
        if in_string:
            if completed.endswith('\\'):
                completed = re.sub(r'\\+$', '', completed)
            completed += '"'
        for token in reversed(stack):
            completed += '}' if token == '{' else ']'
        return completed

    def try_repair_loose_json_text(self, text: str) -> str:
        candidate = text
        for _ in range(3):
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError as e:
                if "Unterminated string" in e.msg or "Expecting ',' delimiter" in e.msg:
                    repaired = self.complete_json_structure(candidate)
                    if repaired == candidate:
                        break
                    candidate = repaired
                    continue
                break
        return candidate

    def loose_parse_json(self):
        self.format_timer.stop()
        text = self.input_edit.toPlainText().strip()
        normalized = self.normalize_loose_json_text(text)
        normalized = self.try_repair_loose_json_text(normalized)
        self.process_json(normalized, show_error_dialog=True, expand_nested=True)

    # ====== 新建窗口静态方法 ======
    @staticmethod
    def new_json_window_action():
        app = QApplication.instance()
        action = getattr(app, "new_json_window_action", None)
        if action is None:
            # 同一个 QAction 可加入多个窗口，避免应用级快捷键重复注册。
            action = QAction("新建 JSON 窗口", app)
            action.setShortcuts(QKeySequence.StandardKey.New)
            action.setShortcutContext(Qt.ApplicationShortcut)
            action.triggered.connect(JsonFormatterWindow.new_window_static)
            app.new_json_window_action = action
        return action

    @staticmethod
    def new_window_static():
        """新建并显示一个 JSON 窗口；注册在 __init__ 内完成。"""
        win = JsonFormatterWindow()
        win.show()

    @staticmethod
    def quit_app():
        QApplication.quit()

    def open_string_formatter_window(self):
        """
        打开字符串格式化窗口（复用语义）：
        若窗口已存在，只恢复并激活它，
        不重复创建，也绝不隐藏其他窗口。
        """
        manager = WindowManager.instance()
        entry = manager.first_entry_of_kind("string")
        if entry is not None:
            manager.show_and_activate(entry.window_id)
            return
        win = FormatterWindow()
        win.addAction(self.new_json_window_action())
        manager.register(win, title="String 工具", kind="string")
        win.show()

    def open_timestamp_converter_window(self):
        """打开时间戳转换窗口（复用语义，同字符串窗口）。"""
        manager = WindowManager.instance()
        entry = manager.first_entry_of_kind("timestamp")
        if entry is not None:
            manager.show_and_activate(entry.window_id)
            return
        win = TimestampConverterWindow()
        win.addAction(self.new_json_window_action())
        manager.register(win, title="时间戳工具", kind="timestamp")
        win.show()

    def on_tree_item_clicked(self, item, column):
        data = item.json_value
        if not isinstance(data, (dict, list)) and item.json_key is not None:
            data = {item.json_key: data}
        self.output_edit.setPlainText(json.dumps(data, indent=4, ensure_ascii=False))

    # ====== 右键菜单 ======
    def open_tree_context_menu(self, position):
        """显示树形控件的右键菜单。"""
        if self.format_timer.isActive():
            self.auto_format_input()
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
            expand_recursive_action.triggered.connect(lambda: self.output_tree.expand_subtree(item))
            
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
            self.format_timer.stop()
            self.set_json_result(compressed, data)
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "压缩失败", f"{e.msg}\n行: {e.lineno}, 列: {e.colno}")

    def save_file(self):
        """
        保存右侧 JSON 结果到文件
        """
        if self.format_timer.isActive():
            self.auto_format_input()
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
        if self.format_timer.isActive():
            self.auto_format_input()
        text = self.output_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.btn_copy.setText("复制成功")
            self.copy_feedback.start(1200)

    def collapsed_panel_at_handle(self, index):
        for panel in (self.splitter.widget(index - 1), self.splitter.widget(index)):
            if not panel.is_expanded and not panel.isHidden():
                return panel
        return None

    def toggle_workspace_panel(self, panel):
        if panel.is_expanded and sum(current.is_expanded for current in self.workspace_panels) == 1:
            self.switch_layout(True, True, True)
            return

        panel.set_expanded(not panel.is_expanded)

    def update_panel_toggles(self, visible_indices):
        for panel in self.workspace_panels:
            for controls in (panel.leading_controls, panel.trailing_controls):
                while controls.count():
                    controls.takeAt(0)

        for index, panel in enumerate(self.workspace_panels):
            if not visible_indices:
                panel.toggle_btn.hide()
                continue
            nearest = min(visible_indices, key=lambda visible: abs(visible - index))
            host = self.workspace_panels[nearest]
            if index == nearest:
                panel.update_toggle_button(restore=len(visible_indices) == 1)
                host.trailing_controls.addWidget(panel.toggle_btn)
            elif index < nearest:
                panel.update_toggle_button(destination="left")
                host.leading_controls.addWidget(panel.toggle_btn)
            else:
                panel.update_toggle_button(destination="right")
                host.trailing_controls.addWidget(panel.toggle_btn)
            panel.toggle_btn.show()

    def update_splitter_handles(self):
        editors_only = (
            self.left_panel.is_expanded
            and not self.middle_panel.is_expanded
            and self.right_panel.is_expanded
        )
        # 隐藏中栏后，QSplitter 会在两个编辑区之间只保留一个可拖动手柄。
        self.middle_panel.setVisible(not editors_only)

        visible_indices = [index for index, panel in enumerate(self.workspace_panels) if panel.is_expanded]
        self.update_panel_toggles(visible_indices)

        for index in range(1, self.splitter.count()):
            handle = self.splitter.handle(index)
            panel = self.collapsed_panel_at_handle(index)
            handle.setCursor(Qt.PointingHandCursor if panel else Qt.SplitHCursor)
            handle.setToolTip(panel.toolTip() if panel else "")
        self.schedule_layout_save()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            for index in range(1, self.splitter.count()):
                if watched is self.splitter.handle(index):
                    panel = self.collapsed_panel_at_handle(index)
                    if panel is not None:
                        panel.set_expanded(True)
                        return True
                    break
        return super().eventFilter(watched, event)

    def switch_layout(self, show_left, show_mid, show_right):
        """
        切换布局模式
        :param show_left: 是否显示原始 JSON
        :param show_mid: 是否显示 JSON 树
        :param show_right: 是否显示 JSON 结果
        """
        visible_count = sum((show_left, show_mid, show_right))
        if visible_count == 0:
            return

        self.left_panel.set_expanded(show_left)
        self.middle_panel.set_expanded(show_mid)
        self.right_panel.set_expanded(show_right)
        
        total_width = self.splitter.width()
        if visible_count == 3:
            self.splitter.setSizes(self.default_splitter_sizes())
            self.schedule_layout_save()
            return

        collapsed_width = CollapsiblePanel.COLLAPSED_WIDTH
        
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
        self.schedule_layout_save()

    def settings(self):
        # 将布局配置统一写入固定的应用配置域，方便下次启动时恢复。
        return QtCore.QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)

    def default_splitter_sizes(self):
        return [self.DEFAULT_WINDOW_WIDTH * ratio // 100 for ratio in (35, 25, 40)]

    def schedule_layout_save(self):
        # 连续调整窗口大小或 splitter 时只在短暂停顿后写一次配置，减少无意义写盘。
        self.layout_save_timer.start(300)

    def save_layout_state(self):
        settings = self.settings()
        settings.beginGroup(self.SETTINGS_GROUP)

        # 记录窗口位置、窗口大小、三栏显示状态以及 splitter 实际比例。
        settings.setValue("x", self.x())
        settings.setValue("y", self.y())
        settings.setValue("width", self.width())
        settings.setValue("height", self.height())
        settings.setValue("left_expanded", self.left_panel.is_expanded)
        settings.setValue("middle_expanded", self.middle_panel.is_expanded)
        settings.setValue("right_expanded", self.right_panel.is_expanded)
        settings.setValue("splitter_sizes", self.splitter.sizes())

        settings.endGroup()
        settings.sync()

    def restore_layout_state(self):
        settings = self.settings()
        settings.beginGroup(self.SETTINGS_GROUP)

        width_value = settings.value("width")
        height_value = settings.value("height")

        # 没有历史布局时，直接回到默认的三栏布局和默认窗口大小。
        if width_value is None or height_value is None:
            settings.endGroup()
            self.restore_default_layout(save_after_restore=False)
            return

        x_value = settings.value("x")
        y_value = settings.value("y")
        splitter_sizes = settings.value("splitter_sizes")

        # QSettings 取出的值可能是字符串或字符串列表，这里统一转换成整数列表。
        normalized_sizes = []
        if isinstance(splitter_sizes, list):
            normalized_sizes = [int(size) for size in splitter_sizes]
        elif isinstance(splitter_sizes, str) and splitter_sizes.strip():
            normalized_sizes = [int(part) for part in splitter_sizes.split(",") if part.strip()]

        self.resize(int(width_value), int(height_value))
        if x_value is not None and y_value is not None:
            self.move(int(x_value), int(y_value))

        self.left_panel.set_expanded(str(settings.value("left_expanded", True)).lower() in ("true", "1"))
        self.middle_panel.set_expanded(str(settings.value("middle_expanded", False)).lower() in ("true", "1"))
        self.right_panel.set_expanded(str(settings.value("right_expanded", True)).lower() in ("true", "1"))
        if not any(panel.is_expanded for panel in (self.left_panel, self.middle_panel, self.right_panel)):
            self.left_panel.set_expanded(True)

        settings.endGroup()

        if len(normalized_sizes) == 3:
            self.splitter.setSizes(normalized_sizes)
        else:
            # 历史配置不完整时，回退到默认三栏比例，避免界面布局异常。
            self.splitter.setSizes(self.default_splitter_sizes())

    def restore_default_layout(self, _checked=False, save_after_restore=True):
        # 恢复到应用默认布局：
        # 1. 窗口大小恢复到默认值
        # 2. 三栏全部展开
        # 3. splitter 恢复默认三栏比例
        self.resize(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.left_panel.set_expanded(True)
        self.middle_panel.set_expanded(True)
        self.right_panel.set_expanded(True)
        self.splitter.setSizes(self.default_splitter_sizes())

        if save_after_restore:
            self.save_layout_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_layout_save()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.schedule_layout_save()

    def closeEvent(self, event):
        self.save_layout_state()
        manager = WindowManager.instance()
        if manager.is_quitting:
            super().closeEvent(event)
            return
        event.ignore()
        manager.request_close_window(self)

    def showEvent(self, event):
        super().showEvent(event)
        # 窗口变为可见（含从 orderOut 恢复）：刷新「窗口」菜单 ✓ 状态。
        # visibilityChanged 信号也会触发刷新，这里作为兼容兑底。
        WindowManager.instance().rebuild_menus()

    def hideEvent(self, event):
        super().hideEvent(event)
        WindowManager.instance().rebuild_menus()

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开 JSON 文件", "", "JSON 文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.input_edit.setPlainText(text)
                self.auto_format_input()
            except Exception as e:
                QMessageBox.critical(self, "打开失败", str(e))

    def show_about_dialog(self):
        """
        显示关于对话框
        """
        version = "v2.0.5"
        info = f"""
        <h3>JSON 工具 {version}</h3>
        <p>桌面版 JSON 工具。</p>
        <p>支持 JSON 格式化、压缩、树形展示等功能。</p>
        <p>作者：lawliet</p>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("关于 JSON 工具")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def current_editor_key(self):
        w = QApplication.focusWidget()
        for key, panel in self.search_panels.items():
            if w is not None and (w is panel or panel.isAncestorOf(w)):
                return key

        if w in (self.input_edit, self.input_edit.viewport()):
            return "input"

        if w in (self.output_edit, self.output_edit.viewport()):
            return "output"
            
        if w in (self.output_tree, self.output_tree.viewport()):
            return "tree"

        return None

    def open_search(self, key=None):
        key = key or self.current_editor_key()
        
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

        if key != "input" and self.format_timer.isActive():
            self.auto_format_input()
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
        }

    def make_format(self, color, bg=None, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bg:
            fmt.setBackground(QColor(bg))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        return fmt

    tokens = re.compile(
        r'(?P<string>"(?:[^"\\]|\\.)*")(?P<key>\s*:)?'
        r'|(?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
        r'|(?P<boolean>true|false)|(?P<null>null)'
    )
    supplementary_char = re.compile(r'[\U00010000-\U0010FFFF]')

    def highlightBlock(self, text):
        supplementary = self.supplementary_char.finditer(text)
        extra_unit = next(supplementary, None)
        offset = 0
        for match in self.tokens.finditer(text):
            kind = match.lastgroup
            if kind in ("string", "key"):
                start, end = match.span("string")
                start += 1
                end -= 1
            else:
                start, end = match.span()
                if kind == "boolean":
                    kind = "bool"

            # Qt positions are UTF-16 units. Python match positions count code points.
            while extra_unit is not None and extra_unit.start() < start:
                offset += 1
                extra_unit = next(supplementary, None)
            qt_start = start + offset
            while extra_unit is not None and extra_unit.start() < end:
                offset += 1
                extra_unit = next(supplementary, None)
            self.setFormat(qt_start, end + offset - qt_start, self.formats[kind])


class SearchPanel(QWidget):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.parent = parent
        self.editor = editor
        # self.setFixedWidth(320)  # 移除固定宽度
        self.theme = THEMES["light"]

        # 布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 6, 5, 6)
        layout.setSpacing(3)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索")
        self.search_edit.setMinimumWidth(0)
        # 👉 让 ESC 等同关闭
        self.search_edit.installEventFilter(self)
        self.label = QLabel("0 / 0")
        self.btn_prev = QPushButton("↑")
        self.btn_next = QPushButton("↓")
        self.btn_close = QPushButton("✕")
        for button, label in ((self.btn_prev, "上一处"), (self.btn_next, "下一处"), (self.btn_close, "关闭搜索")):
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setFixedWidth(22)

        layout.addWidget(self.search_edit)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_close)

        # 高亮器
        # self.highlighter = SearchHighlighter(self.editor.document())

        self.matches = []
        self.match_selections = []
        self.index = 0
        if isinstance(editor, CodeEditor):
            self.search_timer = QtCore.QTimer(self)
            self.search_timer.setSingleShot(True)
            self.search_timer.setInterval(150)
            self.search_timer.timeout.connect(self.refresh_matches)
            editor.textChanged.connect(self.schedule_search_refresh)

        # 信号
        self.btn_close.clicked.connect(self.close_search)
        self.search_edit.textChanged.connect(self.do_search)
        self.search_edit.returnPressed.connect(self.next_match)
        self.btn_next.clicked.connect(self.next_match)
        self.btn_prev.clicked.connect(self.prev_match)

    def close_search(self):
        self.search_edit.clear()
        self.hide()

    def set_theme(self, theme):
        self.theme = theme
        self.setStyleSheet(f"""
            SearchPanel {{
                background: {theme['header_bg']};
                border-bottom: 1px solid {theme['header_border']};
            }}
            QLabel {{ color: {theme['tree_value']}; }}
            QLineEdit {{
                background: {theme['input_bg']};
                color: {theme['text_color']};
                border: 1px solid {theme['border_color']};
                border-radius: 5px;
                min-height: 24px;
                padding: 0 6px;
            }}
            QLineEdit:focus {{ border-color: {theme['accent']}; }}
            QPushButton {{
                background: transparent;
                color: {theme['btn_text']};
                border: 1px solid transparent;
                border-radius: 4px;
                min-height: 24px;
            }}
            QPushButton:hover {{ background: {theme['btn_hover']}; }}
            QPushButton:focus {{ border-color: {theme['accent']}; }}
        """)
        if self.search_edit.text():
            self.refresh_highlight()

    def reposition(self):
        # 布局管理模式下不需要手动定位
        pass
        
    def schedule_search_refresh(self):
        if self.search_edit.text():
            self.search_timer.start()

    def do_search(self):
        if self.search_edit.text():
            self.editor.expand_all_folds()
        self.refresh_matches()
        if self.matches:
            self.goto(0)

    def refresh_matches(self):
        self.search_timer.stop()
        self.matches.clear()
        self.index = 0
        keyword = self.search_edit.text()
        if keyword:
            document = self.editor.document()
            cursor = document.find(keyword)
            while not cursor.isNull():
                self.matches.append(cursor)
                cursor = document.find(keyword, cursor)
        self.refresh_highlight()
        self.update_label()

    def refresh_highlight(self):
        match_format = QTextCharFormat()
        match_format.setBackground(QColor(self.theme["highlight"]["search_match"]))
        self.match_selections = []
        for cursor in self.matches:
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = match_format
            self.match_selections.append(selection)
        self.show_current_highlight()

    def show_current_highlight(self, cursor=None):
        selections = self.match_selections
        if selections:
            current = QTextEdit.ExtraSelection()
            current.cursor = self.matches[self.index]
            current.format.setBackground(QColor(self.theme["highlight"]["search_current"]))
            current.format.setForeground(QColor(self.theme["highlight"]["highlight_fg"]))
            current.format.setFontWeight(QFont.Bold)
            selections = [*selections, current]
        self.editor.set_search_selections(selections, cursor)

    def update_label(self):
        if not self.matches:
            self.label.setText("0 / 0")
        else:
            self.label.setText(f"{self.index+1} / {len(self.matches)}")

    def goto(self, idx):
        self.index = idx
        position = self.matches[idx].selectionStart()
        self.editor.expand_folds_for_position(position)
        cursor = self.editor.textCursor()
        cursor.setPosition(position)
        self.show_current_highlight(cursor)
        self.editor.ensureCursorVisible()
        self.update_label()

    def next_match(self):
        if self.search_timer.isActive():
            self.refresh_matches()
        if self.matches:
            self.goto((self.index + 1) % len(self.matches))

    def prev_match(self):
        if self.search_timer.isActive():
            self.refresh_matches()
        if self.matches:
            self.goto((self.index - 1) % len(self.matches))

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
        self.tree_matches = []  # 存储节点路径和该节点内的匹配序号

    def do_search(self):
        text = self.search_edit.text()
        self.highlight_search(text)
        self.tree_matches.clear()
        self.index = 0

        if text:
            pattern = re.compile(re.escape(text), re.IGNORECASE)
            for path, label in self.editor.iter_labels():
                for match_index, _ in enumerate(pattern.finditer(label)):
                    self.tree_matches.append((path, match_index))

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
        path, match_index = self.tree_matches[idx]
        item = self.editor.reveal_path(path)
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

    def refresh_highlight(self):
        self.highlight_search(self.search_edit.text())
        if self.tree_matches:
            path, match_index = self.tree_matches[self.index]
            item = self.editor.reveal_path(path)
            self.editor.itemDelegate().set_current_match(item, match_index)

    def highlight_search(self, keyword):
        # 树控件文本内的高亮
        delegate = self.editor.itemDelegate()
        if hasattr(delegate, 'set_search_config'):
            delegate.set_search_config(keyword, self.theme)
            self.editor.viewport().update()


class JsonToolsApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        self.aboutToQuit.connect(WindowManager.instance().destroy_all)

    def event(self, event):
        if event.type() != QtCore.QEvent.Quit:
            return super().event(event)

        # Dock 退出会让 Qt 先关闭窗口，此时允许 closeEvent 正常完成。
        manager = WindowManager.instance()
        manager.is_quitting = True
        try:
            return super().event(event)
        finally:
            manager.is_quitting = False


if __name__ == "__main__":
    app = JsonToolsApplication(sys.argv)
    # 启动即显示第一个 JSON 窗口（注册在窗口管理器内完成）
    first_window = JsonFormatterWindow()
    first_window.show()
    sys.exit(app.exec())
