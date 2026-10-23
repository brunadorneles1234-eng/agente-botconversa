import os
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def generate_dashboard(
    metrics: dict,
    alerts: list,
    history: list,
    client_name: str,
    date: str,
    output_path: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
    )
    template = env.get_template("dashboard.html")

    html = template.render(
        metrics=metrics,
        alerts=alerts,
        history=history,
        client_name=client_name,
        date=date,
    )

    os.makedirs(output_path, exist_ok=True)
    filename = os.path.join(output_path, f"{date}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename
