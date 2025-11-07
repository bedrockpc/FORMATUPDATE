import io
import base64
import random
from jinja2 import Template
from weasyprint import HTML

# --- Libraries for different rendering methods ---

# 1. Matplotlib (High-Quality Raster/PNG)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 2. MathML (WeasyPrint Native HTML/CSS Interpretation)
from latex2mathml.converter import convert as latex_to_mathml

# 3. Unicode Text (Plain text conversion)
import latex2unicode

# --- Core Comparison Functions ---

def render_matplotlib_png(latex_code: str) -> str:
    """Renders LaTeX to a high-DPI PNG and returns it as a Base64 Data URI."""
    try:
        # High DPI (300) ensures a sharp, print-quality image.
        fig = plt.figure(figsize=(4, 1), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        
        # Must be wrapped in $...$ for Matplotlib to interpret as math.
        ax.text(0.5, 0.5, f'${latex_code}$', 
                fontsize=16, 
                verticalalignment='center', 
                horizontalalignment='center')
        
        ax.axis('off') # Hide the default axes
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, transparent=True)
        plt.close(fig) 
        
        base64_encoded_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{base64_encoded_data}"

    except Exception:
        return "" # Return empty string on failure

def render_mathml(latex_code: str) -> str:
    """Converts LaTeX to MathML, relying on WeasyPrint/browser for rendering."""
    try:
        # Note: MathML support in browsers/WeasyPrint can be inconsistent.
        return latex_to_mathml(latex_code).strip()
    except Exception:
        return f'<span class="error-text">[MathML Conversion Error]</span>'

def render_unicode(latex_code: str) -> str:
    """Converts LaTeX to a plain Unicode string for text comparison."""
    try:
        return latex2unicode.unicode_to_latex(latex_code)
    except Exception:
        return f'[Unicode Conversion Error]'

def generate_comparison_pdf(latex_code: str) -> bytes:
    """
    Compiles all three rendering results into a single HTML document 
    and converts it to a PDF using WeasyPrint.
    """
    # Run all three tests
    png_uri = render_matplotlib_png(latex_code)
    mathml_output = render_mathml(latex_code)
    unicode_output = render_unicode(latex_code)

    # Load and render HTML template
    try:
        with open("template.html", "r", encoding="utf-8") as f:
            template_str = f.read()
    except FileNotFoundError:
        return b"Error: template.html not found."

    template = Template(template_str)
    
    html_content = template.render(
        latex_input=latex_code,
        png_uri=png_uri,
        mathml_output=mathml_output,
        unicode_output=unicode_output,
        # Check success status for display in PDF
        png_success=bool(png_uri and png_uri != ""),
        mathml_success="[MathML Conversion Error]" not in mathml_output,
        unicode_success="[Unicode Conversion Error]" not in unicode_output
    )

    # Convert HTML → PDF
    pdf_file = io.BytesIO()
    # We set a base URL to handle external resources like Google Fonts
    HTML(string=html_content, base_url='').write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()

def get_placeholder_latex() -> str:
    """Provides a complex equation for initial testing."""
    return r'\sum_{n=1}^\infty \frac{1}{n^2} = \frac{\pi^2}{6} \quad \text{or} \quad \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}'

