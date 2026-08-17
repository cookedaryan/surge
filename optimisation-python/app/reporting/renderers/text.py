from app.reporting.renderers.base import ReportRenderer
from app.reporting.report import EngineeringReport


class TextRenderer(ReportRenderer):
    def render(self, report: EngineeringReport) -> str:
        lines = []

        lines.append("ENGINEERING DECISION REPORT")
        lines.append("===========================")
        lines.append("")

        for section in report.sections:
            lines.append(section.title.upper())
            lines.append("-" * len(section.title))

            if section.summary:
                lines.append(section.summary)
                lines.append("")

            if section.metrics:
                for metric in section.metrics:
                    lines.append(f"{metric.name}: {metric.value}")
                lines.append("")

            for table in section.tables:
                lines.append(f"[{table.title}]")

                # Calculate column widths
                col_widths = [len(str(h)) for h in table.headers]
                for row in table.rows:
                    for i, cell in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(str(cell)))

                # Create format string
                row_format = " | ".join(f"{{:<{w}}}" for w in col_widths)

                lines.append(row_format.format(*table.headers))
                lines.append("-+-".join("-" * w for w in col_widths))

                for row in table.rows:
                    # Pad row if it has fewer elements than headers
                    padded_row = list(row) + [""] * (len(table.headers) - len(row))
                    str_row = [str(c) for c in padded_row]
                    lines.append(row_format.format(*str_row))

                lines.append("")

            if section.notices:
                lines.append("Notices:")
                for notice in section.notices:
                    lines.append(f"  * {notice}")
                lines.append("")

            # Note: We don't render section.limitations here directly
            # because they are rolled up to the global report limitations section.

        if report.limitations:
            lines.append("REPORT LIMITATIONS")
            lines.append("-" * 18)
            for limitation in report.limitations:
                lines.append(f"  * {limitation}")
            lines.append("")

        return "\n".join(lines).strip()
