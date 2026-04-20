"""
Netlist Viewer - Display and edit netlists.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QToolBar, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor

import re


class NetlistHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for SPICE netlists."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._rules = []
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        self._rules.append((re.compile(r'\*.*$'), comment_format))
        
        # Directives (starting with .)
        directive_format = QTextCharFormat()
        directive_format.setForeground(QColor("#0000ff"))
        directive_format.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'^\.[A-Za-z]+', re.MULTILINE), directive_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#098658"))
        self._rules.append((
            re.compile(r'\b[+-]?[0-9]*\.?[0-9]+([eE][+-]?[0-9]+)?[a-zA-Z]*\b'),
            number_format
        ))
        
        # Component references
        ref_format = QTextCharFormat()
        ref_format.setForeground(QColor("#a31515"))
        self._rules.append((re.compile(r'^[RVCLMQDIJKXWB][A-Za-z0-9_]*', re.MULTILINE), ref_format))
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000ff"))
        keywords = ['DC', 'AC', 'TRAN', 'PULSE', 'SIN', 'PWL', 'IC', 'TEMP']
        self._rules.append((
            re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE),
            keyword_format
        ))
    
    def highlightBlock(self, text: str):
        """Highlight a block of text."""
        for pattern, format in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)


class NetlistViewer(QWidget):
    """Widget for viewing and editing netlists."""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QToolBar()
        toolbar.addAction("Copy", self._copy)
        toolbar.addAction("Save", self._save)
        toolbar.addAction("Clear", self._clear)
        layout.addWidget(toolbar)
        
        # Text editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setReadOnly(True)
        
        # Syntax highlighter
        self._highlighter = NetlistHighlighter(self.editor.document())
        
        layout.addWidget(self.editor)
    
    def set_netlist(self, netlist: str):
        """Set the netlist content."""
        self.editor.setPlainText(netlist)
    
    def get_netlist(self) -> str:
        """Get the netlist content."""
        return self.editor.toPlainText()
    
    def _copy(self):
        """Copy netlist to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.editor.toPlainText())
    
    def _save(self):
        """Save netlist to file."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Netlist",
            "",
            "SPICE Netlist (*.sp *.spice);;All Files (*.*)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(self.editor.toPlainText())
    
    def _clear(self):
        """Clear the netlist."""
        self.editor.clear()
