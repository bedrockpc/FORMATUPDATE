import streamlit as st
from utilis import (
    render_matplotlib_png,
    render_mathml,
    render_unicode,
    generate_comparison_pdf,
    get_placeholder_latex
)

# --- Configuration ---
st.set_page_config(layout="wide", page_title="LaTeX Renderer Testing Tool")

st.title("🔬 LaTeX Renderer Comparison Tool")
st.markdown(
    "Use this tool to test different pure-Python methods for rendering LaTeX math "
    "before integrating the best one into your main report generator."
)

# --- Input Area ---
latex_input = st.text_area(
    "Enter LaTeX Math Code Here",
    value=get_placeholder_latex(),
    height=150,
    key="latex_code"
)

# --- Dynamic Comparison Preview ---

if latex_input:
    st.subheader("Real-time Rendering Comparison")

    tab_png, tab_mathml, tab_unicode = st.tabs([
        "✅ 1. Matplotlib (PNG Image)", 
        "⚠️ 2. MathML (HTML/CSS)", 
        "📄 3. Unicode Text"
    ])

    # --- Matplotlib (PNG) Preview ---
    with tab_png:
        st.markdown("This method converts LaTeX to a **high-res PNG image**. It's the most reliable for complex math, as the PDF only embeds a static picture.")
        png_uri = render_matplotlib_png(latex_input)
        
        if png_uri:
            st.image(png_uri, caption="Matplotlib Rendered Image (High Quality)")
            st.success("Rendering successful. This is your most likely candidate.")
        else:
            st.error("Matplotlib rendering failed. Check LaTeX syntax or package installation.")
    
    # --- MathML Preview ---
    with tab_mathml:
        st.markdown("This method converts LaTeX to **MathML XML**. Its rendering quality depends entirely on the PDF engine's ability to display native MathML via HTML/CSS.")
        mathml_output = render_mathml(latex_input)
        
        if "[MathML Conversion Error]" not in mathml_output:
            # Note: st.markdown can render MathML if the browser supports it, 
            # but WeasyPrint often struggles with it.
            st.components.v1.html(f"<div style='font-size: 20px; text-align: center;'>{mathml_output}</div>", height=100)
            st.info("The output above is the raw MathML injected into the HTML.")
        else:
            st.error(f"MathML conversion failed: {mathml_output}")

    # --- Unicode Preview ---
    with tab_unicode:
        st.markdown("This converts math commands to **plain Unicode characters**. Useful for accessibility but will break complex formulas (e.g., fractions, roots).")
        unicode_output = render_unicode(latex_input)
        st.code(unicode_output, language="text")

    # --- PDF Generation ---
    st.markdown("---")
    st.subheader("Generate Comparison PDF")
    st.info("Click below to generate a single PDF report showing how all three methods render side-by-side in the final WeasyPrint output.")
    
    pdf_bytes = generate_comparison_pdf(latex_input)
    
    st.download_button(
        label="⬇️ Download Full Comparison PDF",
        data=pdf_bytes,
        file_name="latex_rendering_comparison_report.pdf",
        mime="application/pdf"
    )

else:
    st.info("Please enter a LaTeX expression above to start the tests.")

