"""Standalone regression tracker window for LIN ASIC verification."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class TestTrackerWindow(QMainWindow):
    """Show ASIC test cases, live regression status, and debug output."""

    run_regression_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    open_regression_log_requested = pyqtSignal()
    open_test_plan_requested = pyqtSignal()
    show_terminal_requested = pyqtSignal()
    show_api_monitor_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LIN ASIC Test Tracker")
        self.setMinimumSize(980, 620)
        self.resize(1180, 760)

        self._case_items: dict[str, QTreeWidgetItem] = {}

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        controls = QWidget()
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.run_btn = QPushButton("Run ASIC Regression")
        self.run_btn.clicked.connect(self.run_regression_requested.emit)
        self.refresh_btn = QPushButton("Refresh Results")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.log_btn = QPushButton("View Regression Log")
        self.log_btn.clicked.connect(self.open_regression_log_requested.emit)
        self.plan_btn = QPushButton("Open Test Plan")
        self.plan_btn.clicked.connect(self.open_test_plan_requested.emit)
        self.terminal_btn = QPushButton("Focus Terminal")
        self.terminal_btn.clicked.connect(self.show_terminal_requested.emit)
        self.api_btn = QPushButton("Show API Monitor")
        self.api_btn.clicked.connect(self.show_api_monitor_requested.emit)

        controls_layout.addWidget(self.run_btn, 0, 0)
        controls_layout.addWidget(self.refresh_btn, 0, 1)
        controls_layout.addWidget(self.log_btn, 0, 2)
        controls_layout.addWidget(self.plan_btn, 0, 3)
        controls_layout.addWidget(self.terminal_btn, 0, 4)
        controls_layout.addWidget(self.api_btn, 0, 5)
        layout.addWidget(controls)

        summary = QGroupBox("Regression Summary")
        summary_layout = QGridLayout(summary)
        self.summary_label = QLabel("No regression report loaded")
        self.coverage_label = QLabel("Coverage: ---")
        self.command_label = QLabel("Command: idle")
        self.terminal_label = QLabel("Terminal: idle")
        self.report_path_label = QLabel("Report: ---")
        self.log_path_label = QLabel("Log: ---")
        summary_layout.addWidget(self.summary_label, 0, 0, 1, 2)
        summary_layout.addWidget(self.coverage_label, 1, 0)
        summary_layout.addWidget(self.terminal_label, 1, 1)
        summary_layout.addWidget(self.command_label, 2, 0, 1, 2)
        summary_layout.addWidget(self.report_path_label, 3, 0, 1, 2)
        summary_layout.addWidget(self.log_path_label, 4, 0, 1, 2)
        layout.addWidget(summary)

        self.case_tree = QTreeWidget()
        self.case_tree.setHeaderLabels(["Case ID", "Block", "Category", "Standard", "Status", "Details"])
        self.case_tree.setAlternatingRowColors(True)
        self.case_tree.setRootIsDecorated(False)
        self.case_tree.setColumnWidth(0, 160)
        self.case_tree.setColumnWidth(1, 160)
        self.case_tree.setColumnWidth(2, 120)
        self.case_tree.setColumnWidth(3, 180)
        self.case_tree.setColumnWidth(4, 90)
        layout.addWidget(self.case_tree, 1)

        debug_group = QGroupBox("Debug Log")
        debug_layout = QVBoxLayout(debug_group)
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        debug_layout.addWidget(self.debug_log)
        layout.addWidget(debug_group, 1)

    def set_test_cases(self, cases: list[dict]) -> None:
        self.case_tree.clear()
        self._case_items.clear()
        for case in cases:
            item = QTreeWidgetItem([
                case.get("case_id", ""),
                case.get("block", ""),
                case.get("category", ""),
                case.get("standard", ""),
                "NOT RUN",
                case.get("description", ""),
            ])
            self.case_tree.addTopLevelItem(item)
            self._case_items[case.get("case_id", "")] = item

    def update_report(self, report: dict) -> None:
        summary = report.get("summary", {})
        coverage = report.get("coverage", {})
        self.summary_label.setText(
            f"Summary: total={summary.get('total', 0)}  passed={summary.get('passed', 0)}  "
            f"failed={summary.get('failed', 0)}  overall={summary.get('overall', '---')}"
        )
        self.coverage_label.setText(
            f"Coverage: functional={coverage.get('functional_percent', 0):.1f}%  "
            f"standard={coverage.get('standards_percent', 0):.1f}%"
        )
        self.report_path_label.setText(f"Report: {report.get('report_path', '---')}")
        self.log_path_label.setText(f"Log: {report.get('log_path', '---')}")

        for entry in report.get("tests", []):
            item = self._case_items.get(entry.get("case_id", ""))
            if item is None:
                continue
            status = entry.get("status", "UNKNOWN")
            item.setText(4, status)
            item.setText(5, entry.get("details", ""))
            color = QColor("#B00020")
            if status == "PASS":
                color = QColor("#2E7D32")
            elif status in {"RUNNING", "QUEUED"}:
                color = QColor("#EF6C00")
            item.setForeground(4, color)

    def set_regression_state(self, running: bool, command: str = "") -> None:
        state = "running" if running else "idle"
        self.command_label.setText(f"Command: {command or state}")
        self.terminal_label.setText(f"Terminal: {state}")

    def set_terminal_status(self, status: dict) -> None:
        state = "running" if status.get("running") else "idle"
        self.terminal_label.setText(f"Terminal: {state}")
        command = status.get("active_command") or status.get("last_command") or "idle"
        self.command_label.setText(f"Command: {command}")

    def append_debug_line(self, text: str) -> None:
        self.debug_log.append(text.rstrip())