"""Standalone source-code viewer windows used for RTL and test-plan inspection."""

from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class SourceHighlighter(QSyntaxHighlighter):
    """Very small syntax highlighter for RTL, SPICE, and Markdown text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []

    def set_language(self, language: str) -> None:
        self._rules = []
        language = (language or "text").lower()

        comment = QTextCharFormat()
        comment.setForeground(QColor("#6A9955"))

        keyword = QTextCharFormat()
        keyword.setForeground(QColor("#569CD6"))
        keyword.setFontWeight(QFont.Weight.Bold)

        number = QTextCharFormat()
        number.setForeground(QColor("#B5CEA8"))

        header = QTextCharFormat()
        header.setForeground(QColor("#4EC9B0"))
        header.setFontWeight(QFont.Weight.Bold)

        if language in {"verilog", "systemverilog", "sv"}:
            words = (
                "module|endmodule|input|output|inout|wire|reg|logic|always|if|else|"
                "case|endcase|begin|end|assign|function|task|localparam|parameter|"
                "posedge|negedge|for|integer"
            )
            self._rules.extend([
                (re.compile(r"//.*$"), comment),
                (re.compile(r"/\*.*?\*/"), comment),
                (re.compile(rf"\b({words})\b"), keyword),
                (re.compile(r"\b\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+\b|\b\d+\b"), number),
            ])
        elif language == "spice":
            self._rules.extend([
                (re.compile(r"\*.*$"), comment),
                (re.compile(r"^\.[A-Za-z_]+", re.MULTILINE), keyword),
                (re.compile(r"\b[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[a-zA-Z]*\b"), number),
            ])
        elif language == "markdown":
            self._rules.extend([
                (re.compile(r"^#+.*$", re.MULTILINE), header),
                (re.compile(r"\*\*.*?\*\*"), keyword),
            ])

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class SourceCodeWindow(QMainWindow):
    """Standalone text window for RTL, SPICE, or Markdown sources."""

    def __init__(self, title: str = "Source Viewer"):
        super().__init__()
        self._file_path: str = ""
        self._language: str = "text"

        self.setWindowTitle(title)
        self.setMinimumSize(900, 600)
        self.resize(1100, 720)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar("Source")
        toolbar.addAction("Copy", self._copy)
        toolbar.addAction("Save As", self._save_as)
        toolbar.addAction("Reload", self._reload)
        layout.addWidget(toolbar)

        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(self.path_label.textInteractionFlags() | self.path_label.textInteractionFlags().TextSelectableByMouse)
        self.path_label.setMargin(6)
        layout.addWidget(self.path_label)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setFont(QFont("Consolas", 10))
        layout.addWidget(self.editor)

        self._highlighter = SourceHighlighter(self.editor.document())

    @property
    def file_path(self) -> str:
        """Return the currently loaded source file path, if any."""
        return self._file_path

    def set_source(self, title: str, text: str, file_path: str = "", language: str = "text") -> None:
        self._file_path = file_path
        self._language = language or "text"
        self.setWindowTitle(title)
        self.path_label.setText(file_path or "Unsaved content")
        self.editor.setPlainText(text)
        self._highlighter.set_language(self._language)

    def _copy(self) -> None:
        self.editor.selectAll()
        self.editor.copy()
        cursor = self.editor.textCursor()
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)

    def _save_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Source As",
            Path(self._file_path).name if self._file_path else "source.txt",
            "All Files (*.*)",
        )
        if not filename:
            return
        Path(filename).write_text(self.editor.toPlainText(), encoding="utf-8")

    def _reload(self) -> None:
        if not self._file_path:
            return
        path = Path(self._file_path)
        if not path.exists():
            QMessageBox.warning(self, "Missing File", f"Could not reload:\n{path}")
            return
        self.set_source(self.windowTitle(), path.read_text(encoding="utf-8", errors="replace"), str(path), self._language)