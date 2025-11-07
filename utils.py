from jinja2 import Template
from weasyprint import HTML

def render_latex_to_pdf(latex_code: str) -> bytes:
    # HTML Template for rendering LaTeX using KaTeX
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>LaTeX Render</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
            onload="renderMathInElement(document.body, {delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false}
            ]});"></script>
        <style>
            body {
                font-family: "Helvetica", sans-serif;
                margin: 40px;
                line-height: 1.6;
                color: #222;
            }
            .latex {
                font-size: 18px;
            }
        </style>
    </head>
    <body>
        <div class="latex">{{ content }}</div>
    </body>
    </html>
    """

    template = Template(html_template)
    rendered_html = template.render(content=latex_code.replace("\n", "<br>"))
    pdf = HTML(string=rendered_html).write_pdf()
    return pdf