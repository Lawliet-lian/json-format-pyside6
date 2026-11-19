"""
macos_bridge.py — macOS 原生窗口桥接模块（PyObjC）

设计文档核心约束（见《多窗口设计.md》第五、十四、十七章）：

1. 禁止再走 NSApp.dockMenu / setDockMenu_ / objc_msgSend 发送未确认的
   selector。QNSApplication 不响应 dockMenu selector，盲目发送会触发
   NSInvalidArgumentException 导致进程 abort。本模块不涉及任何
   dockMenu 相关调用，Dock 窗口列表交给 macOS 原生自动维护。
2. 禁止「视觉隐藏」workaround（setWindowOpacity(0)、move(-99999, -99999)、
   乱改 WindowFlags），统一使用原生 NSWindow 生命周期 API：
       -[NSWindow orderOut:]
       -[NSWindow makeKeyAndOrderFront:]
3. 所有原生调用都只作用于「目标窗口」本身，绝不触碰其他窗口。
4. pyobjc 不可用（非 macOS 平台/未安装）时静默降级为 no-op，
   保证跨平台可运行。
"""

import sys

# 仅在 macOS 平台尝试导入 pyobjc；其他平台全部降级为 no-op
_IS_MACOS = sys.platform == "darwin"

try:
    if _IS_MACOS:
        import AppKit  # noqa: F401  # pyobjc 的 AppKit 框架
        import objc
        _PYOBJC_AVAILABLE = True
    else:
        _PYOBJC_AVAILABLE = False
except ImportError:
    _PYOBJC_AVAILABLE = False


def is_macos_native_available():
    """
    当前环境是否具备 macOS 原生桥接能力：
    macOS + pyobjc 可用 + 当前 Qt 平台插件为 cocoa。
    （offscreen 等非 cocoa 插件下，winId 不是真实的 NSView 指针，
    继续桥接会导致段错误，必须降级。）
    """
    if not (_IS_MACOS and _PYOBJC_AVAILABLE):
        return False
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            return app.platformName() == "cocoa"
    except Exception:
        return False
    return True


def nswindow_for_widget(widget):
    """
    通过 QWidget 获取其对应的原生 NSWindow。

    桥接链路（设计文档第八节 Step 2 已验证的路线）：
        QWidget --winId()--> NSView --window--> NSWindow

    注意：winId() 返回的是底层原生窗口句柄（macOS 下即 NSView*），
    这里使用 objc.objc_object(c_void_p=...) 将其包装为 pyobjc 对象。

    返回 NSWindow 对象；不可用或获取失败时返回 None。
    """
    if not is_macos_native_available() or widget is None:
        return None
    try:
        widget.winId()  # 确保底层原生窗口已被创建
        handle = int(widget.winId())
        # offscreen 等非 cocoa 平台下 winId 可能为 0，
        # 用 0 构造 objc 对象再发消息会导致段错误，必须提前返回。
        if handle == 0:
            return None
        ns_view = objc.objc_object(c_void_p=handle)
        if ns_view is None:
            return None
        # NSView 的 window 属性即其所属的原生窗口；
        # 视图不在任何窗口中时返回 None，同样安全。
        return ns_view.window()
    except Exception:
        # 桥接失败时安静降级，不能影响 Qt 主流程
        return None


def order_out(widget):
    """
    对目标窗口执行 [nsWindow orderOut:nil]。

    语义：窗口从屏幕上移除（视觉上消失），但 NSWindow 对象仍然存在，
    仍然保留在 NSApp.windows 中，macOS Dock 的原生窗口列表也仍然
    能找到它——这正是「红叉关闭 = 隐藏而非销毁」所需要的原生行为。

    返回 True 表示原生调用已执行；False 表示环境不可用（调用方应
    回退到 Qt 的 hide() 等语义等价操作）。
    """
    ns_window = nswindow_for_widget(widget)
    if ns_window is None:
        return False
    try:
        ns_window.orderOut_(None)
        return True
    except Exception:
        return False


def make_key_and_order_front(widget):
    """
    对目标窗口执行 [nsWindow makeKeyAndOrderFront:nil]。

    语义：把处于 orderOut 状态的窗口重新显示出来并置为关键窗口（置顶、
    获得键盘焦点）。只操作目标窗口，不会隐藏任何其他窗口。

    返回 True 表示原生调用已执行；False 表示环境不可用。
    """
    ns_window = nswindow_for_widget(widget)
    if ns_window is None:
        return False
    try:
        ns_window.makeKeyAndOrderFront_(None)
        return True
    except Exception:
        return False


def activate_application():
    """
    激活当前应用（等价于 [NSApp activateIgnoringOtherApps:YES]）。

    用于从「窗口」菜单/Dock 激活某个窗口时，确保整个应用从其他
    应用切换回前台。只激活应用本身，不操作任何具体窗口的显隐。
    """
    if not is_macos_native_available():
        return False
    try:
        AppKit.NSApp.activateIgnoringOtherApps_(True)
        return True
    except Exception:
        return False
