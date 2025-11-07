import io
import base64
from jinja2 import Template
from weasyprint import HTML

# Matplotlib setup for server-side rendering
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Library for Unicode fallback/view
import latex2unicode

def latex_to_png_base64(latex_code: str) -> str:
    """
    Renders LaTeX math string to a high-DPI PNG and returns it as a Base64 Data URI.
    This bypasses WeasyPrint's inability to run JavaScript for KaTeX/MathJax.
    """
    try:
        # Create figure for rendering. High DPI ensures quality.
        fig = plt.figure(figsize=(4, 1), dpi=300)
        ax = fig.add_axes([0, 0, 1, 1])
        
        # Add the LaTeX string. Must be wrapped in $...$ for Matplotlib to treat it as math.
        ax.text(0.5, 0.5, f'${latex_code}$', 
                fontsize=16, 
                verticalalignment='center', 
                horizontalalignment='center')
        
        # Hide the surrounding axis and borders
        ax.axis('off')
        
        # Save the image to an in-memory buffer (BytesIO)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, transparent=True)
        plt.close(fig) # MUST close the figure to release memory
        
        # Encode bytes to base64 and create the HTML-ready Data URI
        base64_encoded_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{base64_encoded_data}"

    except Exception as e:
        print(f"Matplotlib rendering error: {e}")
        return "" # Return empty string on failure

def latex_to_unicode(latex_code: str) -> str:
    """Converts a standard LaTeX math string to a Unicode math string."""
    try:
        # Note: latex2unicode works best with simple symbols
        return latex2unicode.unicode_to_latex(latex_code)
    except Exception:
        return f"⚠️ Unicode conversion failed for: {latex_code}"

def render_latex_to_pdf(latex_code: str) -> bytes:
    """
    Processes LaTeX input, generates a rendered image, and compiles a final PDF.
    """
    # 1. Convert LaTeX to the PNG image Data URI
    image_uri = latex_to_png_base64(latex_code)
    
    # 2. Convert LaTeX to Unicode for inclusion in the PDF
    unicode_output = latex_to_unicode(latex_code)

    # 3. Handle Template Rendering
    try:
        with open("template.html", "r", encoding="utf-8") as f:
            template_str = f.read()
    except FileNotFoundError:
        return b"Error: template.html not found."

    template = Template(template_str)
    
    html_content = template.render(
        # Pass all three formats to the template for inclusion in the static PDF
        math_image_src=image_uri,
        raw_latex_code=latex_code,
        unicode_math=unicode_output,
        # Determine if rendering succeeded for conditional display in PDF
        render_success=bool(image_uri)
    )

    # 4. Convert HTML (containing the embedded PNG) to PDF
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    return pdf_file.read()

