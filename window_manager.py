"""
window_manager.py — 多窗口管理器（配合《多窗口设计.md》实施）

核心职责：
1. 为每个窗口分配稳定的业务级 ID（uuid4.hex），不再使用 id(window)
   作为窗口标识（对象地址不稳定，且存在 PyObjC representedObject
   桥接兼容风险）。
2. 维护「多选」语义的窗口集合：多个窗口允许同时可见、同时在
   「窗口」菜单中显示 ✓；激活任一窗口只允许 show/raise/activate
   （macOS 下等价 makeKeyAndOrderFront），严禁 hide 其他窗口。
3. 「红叉关闭」语义：macOS 下最小化目标窗口，其他平台隐藏目标窗口。
   窗口实例继续保留在管理器中，只有「退出应用」才真正销毁。
4. 构建/刷新各窗口菜单栏中的「窗口」菜单（菜单名称固定为「窗口」）。
5. Dock 右键菜单中的窗口列表完全交给 macOS 原生自动维护，
   不再自建第二套窗口列表（避免重复列表问题）。
"""

import sys
import uuid

import shiboken6
from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QWidget

try:
    from macos_bridge import (
        activate_application,
        is_macos_native_available,
        make_key_and_order_front,
    )
except ImportError:
    # 桥接模块缺失时降级为纯 Qt 行为
    def is_macos_native_available():
        return False

    def make_key_and_order_front(_widget):
        return False

    def activate_application():
        return False


class WindowEntry:
    """
    单个窗口的注册条目。

    属性说明：
    - window_id : 稳定 UUID（注册时生成，整个生命周期不变）
    - window    : QWidget 窗口实例
    - title     : 菜单/列表中显示的业务名称
    - kind      : 窗口类型标识（如 "json" / "string" / "timestamp"），
                  用于同类型窗口复用查找
    """

    def __init__(self, window_id, window, title, kind):
        self.window_id = window_id
        self.window = window
        self.title = title
        self.kind = kind


class WindowManager(QObject):
    """
    全局单例窗口管理器（继承 QObject 以便作为事件过滤器监听窗口显隐）。

    所有窗口的创建/激活/隐藏都应当经过本管理器，
    以保证 Qt 状态、NSWindow 状态与「窗口」菜单状态一致。
    """

    _instance = None

    def __init__(self):
        super().__init__()
        self.is_quitting = False
        self._entries = []          # 注册顺序列表（决定菜单显示顺序）
        self._entry_by_id = {}      # window_id -> WindowEntry（设计文档第四节要求）
        self._menus = []            # 各窗口菜单栏中挂着的「窗口」菜单实例

    @staticmethod
    def _is_alive(obj):
        """判断 Qt 对象的 C++ 侧是否仍然存活（窗口析构期 Python 包装可能还在）。"""
        try:
            return shiboken6.isValid(obj)
        except Exception:
            return False

    def eventFilter(self, watched, event):
        """
        监听已注册窗口的 Show/Hide 事件（含 macOS orderOut /
        makeKeyAndOrderFront 引发的显隐变化），刷新「窗口」菜单的 ✓。
        窗口析构期间也会发出 Hide 事件，此时 rebuild_menus 内部会通过
        _is_alive 跳过已销毁的菜单/窗口；索引清理交给 destroyed 信号。
        """
        event_type = event.type()
        if event_type in (QEvent.Show, QEvent.Hide, QEvent.WindowStateChange):
            try:
                self.rebuild_menus()
            except Exception:
                # 刷新菜单属于辅助行为，任何异常都不允许干扰窗口事件流
                pass
        return super().eventFilter(watched, event)

    @classmethod
    def instance(cls):
        """获取全局唯一的 WindowManager 实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ==================== 注册 / 注销 ====================

    def register(self, window, title=None, kind=None):
        """
        注册窗口并分配稳定 UUID。

        UUID 同时写入 window._wm_id，后续若需要向原生菜单传递
        representedObject，也应使用 window._wm_id 而不是 id(window)。
        """
        if window is None:
            return None
        # 防止重复注册（例如窗口重建后再次调用）
        existing_id = getattr(window, "_wm_id", None)
        if existing_id is not None and existing_id in self._entry_by_id:
            entry = self._entry_by_id[existing_id]
            entry.title = title or entry.title or window.windowTitle()
            return existing_id

        window_id = uuid.uuid4().hex
        window._wm_id = window_id

        entry = WindowEntry(
            window_id=window_id,
            window=window,
            title=title or window.windowTitle() or "窗口",
            kind=kind,
        )
        self._entries.append(entry)
        self._entry_by_id[window_id] = entry

        # 通过事件过滤器监听显隐变化（Show/Hide），刷新「窗口」菜单 ✓。
        window.installEventFilter(self)
        # 窗口被真正销毁时自动清理索引（destroyed 在析构前发出）
        window.destroyed.connect(lambda *_args, _id=window_id: self.unregister_by_id(_id))

        self.rebuild_menus()
        return window_id

    def unregister_by_id(self, window_id):
        """按 ID 注销窗口并同步删除所有索引。"""
        entry = self._entry_by_id.pop(window_id, None)
        if entry is None:
            return
        try:
            entry.window.removeEventFilter(self)
        except RuntimeError:
            # 窗口已被 C++ 侧销毁时无法移除过滤器，忽略即可
            pass
        self._entries = [e for e in self._entries if e.window_id != window_id]
        self.rebuild_menus()

    # ==================== 查询接口（设计文档第四节） ====================

    def entries(self):
        """按注册顺序返回所有窗口条目。"""
        return list(self._entries)

    def entry_for_id(self, window_id):
        """根据 window_id 查找注册条目。"""
        return self._entry_by_id.get(window_id)

    def window_for_id(self, window_id):
        """根据 window_id 查找窗口实例。"""
        entry = self._entry_by_id.get(window_id)
        return entry.window if entry else None

    def id_for_window(self, window):
        """查找窗口对应的 window_id；未注册返回 None。"""
        window_id = getattr(window, "_wm_id", None)
        if window_id is not None and window_id in self._entry_by_id:
            return window_id
        for entry in self._entries:
            if entry.window is window:
                return entry.window_id
        return None

    def first_entry_of_kind(self, kind):
        """查找第一个指定类型的窗口条目（用于同类型窗口复用）。"""
        for entry in self._entries:
            if entry.kind == kind:
                return entry
        return None

    # ==================== 窗口操作（全部是目标窗口级别操作） ====================

    @staticmethod
    def _restore_window(window):
        if window.isMinimized():
            window.setWindowState(window.windowState() & ~Qt.WindowMinimized)
        if not window.isVisible():
            # 窗口处于隐藏（macOS 下即 orderOut）状态：先恢复显示。
            window.show()
            if is_macos_native_available():
                # Qt 侧已标记可见时，用原生调用确保 NSWindow 真正回到前台
                make_key_and_order_front(window)

    def show_and_activate(self, window_id):
        """恢复并激活目标窗口。"""
        window = self.window_for_id(window_id)
        if window is None or not self._is_alive(window):
            return

        self._restore_window(window)
        # 激活应用本身，再置顶并聚焦目标窗口（仅操作目标窗口）
        activate_application()
        window.raise_()
        window.activateWindow()

    def show_all_windows(self):
        """恢复所有已注册窗口的显示；每个窗口各自 show，互不隐藏。"""
        for entry in list(self._entries):
            window = entry.window
            if not self._is_alive(window):
                continue
            self._restore_window(window)

    def request_close_window(self, window):
        """保留窗口和内容，macOS 下通过原生最小化收起窗口。"""
        if window is None or not self._is_alive(window) or not window.isVisible():
            return
        if sys.platform == "darwin":
            window.setWindowState(window.windowState() | Qt.WindowMinimized)
        else:
            window.hide()

    def destroy_all(self):
        """
        退出应用：真正销毁所有窗口。
        使用 deleteLater 清理仍然注册的窗口，包括已经收起的窗口。
        """
        for entry in list(self._entries):
            try:
                if self._is_alive(entry.window):
                    entry.window.deleteLater()
            except RuntimeError:
                # 窗口可能已被提前销毁
                pass
        self._entries.clear()
        self._entry_by_id.clear()
        self._menus.clear()

    # ==================== 「窗口」菜单 ====================

    def _window_is_shown(self, window):
        return self._is_alive(window) and window.isVisible() and not window.isMinimized()

    def _activate_menu_window(self, window_id, action):
        self.show_and_activate(window_id)
        # 如果窗口原本已显示，点击不会触发菜单重建，但 QAction 会自行切换勾选。
        if self._is_alive(action):
            action.setChecked(self._window_is_shown(self.window_for_id(window_id)))

    def register_window_menu(self, menu):
        """登记一个窗口菜单栏中的「窗口」菜单，并立即填充内容。"""
        if menu not in self._menus:
            self._menus.append(menu)
            # 打开菜单时再刷新一次 ✓ 状态，保证状态始终最新（只连接一次）
            menu.aboutToShow.connect(self.rebuild_menus)
        self.rebuild_menus()

    def rebuild_menus(self):
        """
        重建所有已登记的「窗口」菜单。

        菜单规则（设计文档第三节）：
        - 菜单名称保持「窗口」不变（创建处负责命名）
        - 列表为当前注册的全部窗口
        - ✓ 表示窗口当前可见，允许多个窗口同时 ✓（多选，非单选）
        - 点击某项只显示/激活该窗口
        """
        # 先过滤掉 C++ 侧已销毁的菜单（窗口销毁会连带删除其菜单，
        # 此时 Python 包装对象可能还在，直接访问会导致段错误）
        alive_menus = [m for m in self._menus if self._is_alive(m)]
        self._menus = alive_menus

        for menu in alive_menus:
            menu.clear()

            # 每个窗口条目：可勾选 = 当前是否可见；允许多个同时勾选
            for entry in self._entries:
                # 窗口 C++ 对象可能已在析构中（析构期会补发 Hide 事件），
                # 此时按不可见处理，等 destroyed 信号清理索引。
                action = QAction(entry.title, menu)
                action.setCheckable(True)
                action.setChecked(self._window_is_shown(entry.window))
                action.triggered.connect(
                    lambda _checked=False, window_id=entry.window_id, menu_action=action:
                        self._activate_menu_window(window_id, menu_action)
                )
                menu.addAction(action)

            menu.addSeparator()

            show_all_action = QAction("显示所有窗口", menu)
            show_all_action.triggered.connect(self.show_all_windows)
            menu.addAction(show_all_action)
