import os
import webbrowser
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def export_pdf(
    metrics: dict,
    alerts: list,
    filters: dict,
    client_name: str,
    date: str,
    output_path: str,
) -> str:
    """
    Gera um HTML otimizado para impressão/PDF com os filtros aplicados.
    O usuário usa Ctrl+P (ou Cmd+P) no navegador para salvar como PDF.
    """
    include_units = filters.get("include_units", True)
    include_attendants = filters.get("include_attendants", True)
    include_alerts = filters.get("include_alerts", True)
    period_days = filters.get("period_days", 1)

    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
    )
    template = env.get_template("report_pdf.html")

    filtered_alerts = alerts if include_alerts else []

    html = template.render(
        metrics=metrics,
        alerts=filtered_alerts,
        client_name=client_name,
        date=date,
        include_units=include_units,
        include_attendants=include_attendants,
        include_alerts=include_alerts,
        period_days=period_days,
    )

    os.makedirs(output_path, exist_ok=True)
    filename = os.path.join(output_path, f"{date}_relatorio.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename
