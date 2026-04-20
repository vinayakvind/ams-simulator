"""
Report Generator - Generate simulation and test reports.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json


@dataclass
class ReportSection:
    """A section in a report."""
    title: str
    content: str = ''
    level: int = 1
    data: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Generate simulation reports in various formats.
    """
    
    def __init__(self, title: str = "Simulation Report"):
        self.title = title
        self._sections: List[ReportSection] = []
        self._metadata: Dict[str, Any] = {
            'generated_at': datetime.now().isoformat(),
            'generator': 'AMS Simulator',
        }
    
    def add_section(self, title: str, content: str = '', level: int = 1,
                    data: Optional[Dict[str, Any]] = None) -> ReportSection:
        """Add a section to the report."""
        section = ReportSection(
            title=title,
            content=content,
            level=level,
            data=data or {}
        )
        self._sections.append(section)
        return section
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the report."""
        self._metadata[key] = value
    
    def add_summary(self, summary: Dict[str, Any]):
        """Add a summary section."""
        content = ""
        for key, value in summary.items():
            if isinstance(value, float):
                content += f"- **{key}**: {value:.3f}\n"
            else:
                content += f"- **{key}**: {value}\n"
        
        self.add_section("Summary", content, level=1, data=summary)
    
    def add_specs_results(self, specs_report):
        """Add specification check results."""
        content = f"""
**Total Specs**: {specs_report.total}
**Passed**: {specs_report.passed}
**Failed**: {specs_report.failed}
**Warnings**: {specs_report.warnings}
**Pass Rate**: {specs_report.pass_rate:.1f}%
"""
        
        self.add_section("Specifications", content, level=1)
        
        # Add details table
        if specs_report.results:
            table = "| Spec | Signal | Status | Measured | Message |\n"
            table += "|------|--------|--------|----------|--------|\n"
            
            for result in specs_report.results:
                status_icon = '✅' if result.status.value == 'pass' else '❌' if result.status.value == 'fail' else '⚠️'
                table += f"| {result.spec.name} | {result.spec.signal} | {status_icon} | {result.measured_value:.6g} | {result.message} |\n"
            
            self.add_section("Specification Details", table, level=2)
    
    def add_waveform_table(self, waveform_name: str, time: List[float], 
                           values: List[float], sample_count: int = 10):
        """Add a sampled waveform table."""
        if len(time) == 0:
            return
        
        # Sample points
        step = max(1, len(time) // sample_count)
        
        table = "| Time | Value |\n|------|------|\n"
        for i in range(0, len(time), step):
            table += f"| {time[i]:.6g} | {values[i]:.6g} |\n"
        
        self.add_section(f"Waveform: {waveform_name}", table, level=2)
    
    def generate_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [f"# {self.title}\n"]
        
        # Metadata
        lines.append("## Report Info\n")
        for key, value in self._metadata.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("\n")
        
        # Sections
        for section in self._sections:
            header = '#' * (section.level + 1)
            lines.append(f"{header} {section.title}\n")
            if section.content:
                lines.append(section.content)
            lines.append("\n")
        
        return '\n'.join(lines)
    
    def generate_html(self) -> str:
        """Generate HTML report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .report-container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        h3 {{ color: #555; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background: #1a73e8;
            color: white;
        }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        tr:hover {{ background: #e8f0fe; }}
        .pass {{ color: #34a853; font-weight: bold; }}
        .fail {{ color: #ea4335; font-weight: bold; }}
        .warn {{ color: #fbbc04; font-weight: bold; }}
        .metadata {{
            background: #e8f0fe;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .metadata p {{ margin: 5px 0; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="report-container">
        <h1>{self.title}</h1>
        
        <div class="metadata">
"""
        
        for key, value in self._metadata.items():
            html += f"            <p><strong>{key}:</strong> {value}</p>\n"
        
        html += """        </div>
"""
        
        for section in self._sections:
            level = section.level + 1
            html += f"        <h{level}>{section.title}</h{level}>\n"
            
            if section.content:
                content = self._markdown_to_html(section.content)
                html += f"        {content}\n"
        
        html += """    </div>
</body>
</html>
"""
        return html
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Simple Markdown to HTML conversion."""
        import re
        
        lines = markdown.strip().split('\n')
        html_lines = []
        in_table = False
        in_list = False
        
        for line in lines:
            # Table
            if line.startswith('|'):
                if not in_table:
                    html_lines.append('<table>')
                    in_table = True
                
                if '---' in line:
                    continue  # Skip separator
                
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if html_lines[-1] == '<table>':
                    html_lines.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                else:
                    # Handle status indicators
                    cells = [c.replace('✅', '<span class="pass">✅ PASS</span>')
                              .replace('❌', '<span class="fail">❌ FAIL</span>')
                              .replace('⚠️', '<span class="warn">⚠️ WARN</span>')
                             for c in cells]
                    html_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
            else:
                if in_table:
                    html_lines.append('</table>')
                    in_table = False
            
            # List
            if line.startswith('- '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                item = line[2:]
                # Bold
                item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
                html_lines.append(f'<li>{item}</li>')
            else:
                if in_list and not line.strip():
                    html_lines.append('</ul>')
                    in_list = False
            
            # Plain paragraph
            if not line.startswith('|') and not line.startswith('-') and line.strip():
                if not in_table and not in_list:
                    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                    html_lines.append(f'<p>{text}</p>')
        
        if in_table:
            html_lines.append('</table>')
        if in_list:
            html_lines.append('</ul>')
        
        return '\n        '.join(html_lines)
    
    def generate_json(self) -> str:
        """Generate JSON report."""
        report = {
            'title': self.title,
            'metadata': self._metadata,
            'sections': []
        }
        
        for section in self._sections:
            report['sections'].append({
                'title': section.title,
                'level': section.level,
                'content': section.content,
                'data': section.data
            })
        
        return json.dumps(report, indent=2)
    
    def save(self, filename: str, format: str = 'auto'):
        """Save report to file."""
        path = Path(filename)
        
        if format == 'auto':
            suffix = path.suffix.lower()
            format = {
                '.md': 'markdown',
                '.html': 'html',
                '.json': 'json',
                '.txt': 'markdown',
            }.get(suffix, 'markdown')
        
        if format == 'markdown':
            content = self.generate_markdown()
        elif format == 'html':
            content = self.generate_html()
        elif format == 'json':
            content = self.generate_json()
        else:
            content = self.generate_markdown()
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


class TestReportGenerator(ReportGenerator):
    """
    Specialized report generator for test results.
    """
    
    def __init__(self, test_name: str = "Test Report"):
        super().__init__(test_name)
        self._test_cases: List[Dict[str, Any]] = []
    
    def add_test_case(self, name: str, status: str, duration: float = 0,
                      details: str = '', data: Optional[Dict[str, Any]] = None):
        """Add a test case result."""
        self._test_cases.append({
            'name': name,
            'status': status,
            'duration': duration,
            'details': details,
            'data': data or {}
        })
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        total = len(self._test_cases)
        passed = sum(1 for t in self._test_cases if t['status'] == 'pass')
        failed = sum(1 for t in self._test_cases if t['status'] == 'fail')
        skipped = sum(1 for t in self._test_cases if t['status'] == 'skip')
        
        total_duration = sum(t['duration'] for t in self._test_cases)
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': passed / total * 100 if total > 0 else 0,
            'total_duration': total_duration,
        }
    
    def finalize(self):
        """Finalize the report with test summary."""
        summary = self.generate_test_summary()
        self.add_summary(summary)
        
        # Test cases table
        table = "| Test | Status | Duration | Details |\n"
        table += "|------|--------|----------|--------|\n"
        
        for tc in self._test_cases:
            status_icon = '✅' if tc['status'] == 'pass' else '❌' if tc['status'] == 'fail' else '⏭️'
            table += f"| {tc['name']} | {status_icon} | {tc['duration']:.3f}s | {tc['details']} |\n"
        
        self.add_section("Test Cases", table, level=1)
