import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class FormatterWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("字符串格式化工具")
        self.resize(900, 500)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText('例如:\n"123232" \n"asd234324"\n"234234" ')
        self.input_edit.setPlainText('"123232" \n"asd234324"\n"234234" ')

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("格式化结果会显示在这里")

        self.basic_format_btn = QPushButton("基础格式化")
        self.db_format_btn = QPushButton("数据库格式化")
        self.copy_btn = QPushButton("复制结果")
        self.clear_btn = QPushButton("清空")

        self.basic_format_btn.clicked.connect(self.format_text)
        self.db_format_btn.clicked.connect(self.format_db_text)
        self.copy_btn.clicked.connect(self.copy_output)
        self.clear_btn.clicked.connect(self.clear_all)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.basic_format_btn)
        top_layout.addWidget(self.db_format_btn)
        top_layout.addWidget(self.copy_btn)
        top_layout.addWidget(self.clear_btn)
        top_layout.addStretch()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("输入"))
        left_layout.addWidget(self.input_edit)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("输出"))
        right_layout.addWidget(self.output_edit)

        body_layout = QHBoxLayout()
        body_layout.addLayout(left_layout, 1)
        body_layout.addLayout(right_layout, 1)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(body_layout)
        self.setLayout(main_layout)

    def format_text(self) -> None:
        lines = self.input_edit.toPlainText().splitlines()
        result = []
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
        self.output_edit.setPlainText("\n".join(result))

    def format_db_text(self) -> None:
        lines = self.input_edit.toPlainText().splitlines()
        normalized = []
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
            value = f"'{value}'"
            normalized.append(value)

        result = []
        for i, value in enumerate(normalized):
            if i < len(normalized) - 1:
                result.append(f"{value},")
            else:
                result.append(value)

        self.output_edit.setPlainText("\n".join(result))

    def clear_all(self) -> None:
        self.input_edit.clear()
        self.output_edit.clear()

    def copy_output(self) -> None:
        QApplication.clipboard().setText(self.output_edit.toPlainText())


def main() -> None:
    app = QApplication(sys.argv)
    window = FormatterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
