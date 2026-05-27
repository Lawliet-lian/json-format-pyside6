import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TimestampConverterWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("时间戳转换工具")
        self.resize(900, 500)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "输入时间戳或时间字符串（支持多行）\n"
            "例如:\n"
            "1716372222\n"
            "1716372222000\n"
            "2026-05-22 12:34:56\n"
            "2026/05/22 12:34\n"
            "2026-05-22T12:34:56\n"
        )

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("转换结果会显示在这里")

        self.btn_ts_to_time = QPushButton("时间戳 → 时间")
        self.btn_time_to_ts = QPushButton("时间 → 时间戳")
        self.copy_btn = QPushButton("复制结果")
        self.clear_btn = QPushButton("清空")

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["自动识别", "秒", "毫秒"])

        self.tz_combo = QComboBox()
        self.tz_combo.addItems(["Asia/Shanghai"])

        self.format_input = QLineEdit()
        self.format_input.setPlaceholderText("输出格式（strftime），例如: %Y-%m-%d %H:%M:%S")
        self.format_input.setText("%Y-%m-%d %H:%M:%S")

        self.btn_ts_to_time.clicked.connect(self.convert_ts_to_time)
        self.btn_time_to_ts.clicked.connect(self.convert_time_to_ts)
        self.copy_btn.clicked.connect(self.copy_output)
        self.clear_btn.clicked.connect(self.clear_all)

        # 顶部工具栏使用更小的边距和间距，避免按钮行占用过多垂直空间。
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)
        top_layout.addWidget(self.btn_ts_to_time)
        top_layout.addWidget(self.btn_time_to_ts)
        top_layout.addWidget(QLabel("单位"))
        top_layout.addWidget(self.unit_combo)
        top_layout.addWidget(QLabel("时区"))
        top_layout.addWidget(self.tz_combo)
        top_layout.addWidget(QLabel("格式"))
        top_layout.addWidget(self.format_input, 1)
        top_layout.addWidget(self.copy_btn)
        top_layout.addWidget(self.clear_btn)

        # 左右两侧只保留文本框，不再显示“输入/输出”标题，进一步节省垂直空间。
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        left_layout.addWidget(self.input_edit)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        right_layout.addWidget(self.output_edit)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)
        body_layout.addLayout(left_layout, 1)
        body_layout.addLayout(right_layout, 1)

        # 主布局整体收紧上下左右边距，并压缩各区域之间的垂直距离，
        # 让第一行、第二行、第三行看起来更贴近。
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(body_layout)
        self.setLayout(main_layout)

        try:
            self._shanghai_tz()
        except Exception as e:
            QMessageBox.critical(self, "时区加载失败", str(e))
            self.output_edit.setPlainText(str(e))
            self.btn_ts_to_time.setEnabled(False)
            self.btn_time_to_ts.setEnabled(False)

    def _normalized_lines(self) -> list[str]:
        lines = self.input_edit.toPlainText().splitlines()
        result: list[str] = []
        for line in lines:
            value = line.strip()
            if not value:
                continue
            if value.endswith(","):
                value = value[:-1].rstrip()
            if (
                len(value) >= 2
                and (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                )
            ):
                value = value[1:-1]
            result.append(value)
        return result

    def _shanghai_tz(self):
        try:
            return ZoneInfo("Asia/Shanghai")
        except Exception as e:
            raise RuntimeError(
                "无法加载时区 Asia/Shanghai。\n"
                "可能原因：运行环境缺少 IANA tzdata。\n"
                "建议：升级到 Python 3.9+ 并确保系统/环境提供 tzdata（某些环境需要安装 tzdata 包）。"
            ) from e

    def _parse_datetime(self, text: str) -> datetime:
        value = text.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass

        patterns = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]
        for fmt in patterns:
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        raise ValueError(f"无法解析时间: {text}")

    def _unit_mode(self) -> str:
        text = self.unit_combo.currentText()
        if text == "秒":
            return "s"
        if text == "毫秒":
            return "ms"
        return "auto"

    def _use_utc(self) -> bool:
        return False

    def convert_ts_to_time(self) -> None:
        unit_mode = self._unit_mode()
        out_format = self.format_input.text().strip() or "%Y-%m-%d %H:%M:%S"

        try:
            tzinfo = self._shanghai_tz()
        except Exception as e:
            QMessageBox.critical(self, "时区加载失败", str(e))
            self.output_edit.setPlainText(str(e))
            return

        results: list[str] = []
        for raw in self._normalized_lines():
            try:
                num = float(raw)
            except Exception:
                results.append(f"[错误] 非数字时间戳: {raw}")
                continue

            if unit_mode == "ms":
                seconds = num / 1000.0
            elif unit_mode == "s":
                seconds = num
            else:
                seconds = num / 1000.0 if abs(num) >= 1_000_000_000_000 else num

            try:
                dt = datetime.fromtimestamp(seconds, tz=tzinfo)
                results.append(dt.strftime(out_format))
            except Exception as e:
                results.append(f"[错误] 转换失败: {raw} ({e})")

        self.output_edit.setPlainText("\n".join(results))

    def convert_time_to_ts(self) -> None:
        unit_mode = self._unit_mode()
        try:
            tzinfo = self._shanghai_tz()
        except Exception as e:
            QMessageBox.critical(self, "时区加载失败", str(e))
            self.output_edit.setPlainText(str(e))
            return

        results: list[str] = []
        for raw in self._normalized_lines():
            try:
                dt = self._parse_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tzinfo)

                ts = dt.timestamp()
                if unit_mode == "ms":
                    results.append(str(int(round(ts * 1000))))
                else:
                    results.append(str(int(round(ts))))
            except Exception as e:
                results.append(f"[错误] 转换失败: {raw} ({e})")

        self.output_edit.setPlainText("\n".join(results))

    def clear_all(self) -> None:
        self.input_edit.clear()
        self.output_edit.clear()

    def copy_output(self) -> None:
        QApplication.clipboard().setText(self.output_edit.toPlainText())


def main() -> None:
    app = QApplication(sys.argv)
    window = TimestampConverterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
