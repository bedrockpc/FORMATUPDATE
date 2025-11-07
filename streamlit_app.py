import streamlit as st
from utilis import render_latex_to_pdf

st.set_page_config(page_title="LaTeX → PDF Test", page_icon="🧮", layout="centered")

st.title("🧪 LaTeX to PDF Tester")
st.write("Enter any LaTeX below and generate a rendered PDF.")

latex_input = st.text_area(
    "Write LaTeX here (use $$ for equations):",
    value="$$E = mc^2$$\n\n$$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$",
    height=200
)

if st.button("Generate PDF"):
    try:
        pdf_bytes = render_latex_to_pdf(latex_input)
        st.success("✅ PDF generated successfully!")

        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name="latex_output.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error: {e}")

st.caption("Powered by Streamlit + WeasyPrint + KaTeX")