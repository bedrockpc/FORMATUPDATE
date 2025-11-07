import streamlit as st
from utilis import render_latex_to_pdf

st.title("🧮 Free LaTeX → PDF Renderer (No Gemini)")

sample = """Here are some test formulas:

$$E = mc^2$$

$$\\int_0^\\infty e^{-x^2} \\, dx = \\frac{\\sqrt{\\pi}}{2}$$
"""

latex_input = st.text_area("Enter LaTeX text here:", sample, height=250)

if st.button("Generate PDF"):
    with st.spinner("Rendering PDF..."):
        pdf_bytes = render_latex_to_pdf(latex_input)
        st.success("✅ Done!")
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name="latex_rendered.pdf",
            mime="application/pdf"
        )