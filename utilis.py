import io
from jinja2 import Template
from weasyprint import HTML
from latex2mathml.converter import convert as latex_to_mathml

def render_latex_to_pdf(latex_text: str) -> bytes:
    """
    Converts LaTeX equations inside $$...$$ into MathML
    and generates a PDF using WeasyPrint.
    """
    # Replace $$...$$ blocks with MathML
    processed = ""
    parts = latex_text.split("$$")
    for i, part in enumerate(parts):
        if i % 2 == 1:  # inside LaTeX block
            try:
                mathml = latex_to_mathml(part.strip())
                processed += mathml
            except Exception:
                processed += f"<code>{part}</code>"
        else:
            processed += part

    # Load and render HTML template
    with open("template.html", "r", encoding="utf-8") as f:
        template_str = f.read()

    template = Template(template_str)
    html_content = template.render(content=processed)

    # Convert HTML → PDF
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()