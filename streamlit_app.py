import streamlit as st
from utilis import render_latex_to_pdf, latex_to_png_base64, latex_to_unicode

# --- Configuration ---
st.set_page_config(layout="wide", page_title="LaTeX to PDF Converter")

# --- UI Elements ---
st.title("🧮 Reliable LaTeX PDF Generator")
st.markdown("Enter your $\\LaTeX$ math code below (e.g., `\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$`)")

latex_input = st.text_area(
    "Paste LaTeX Code Here (Wrap in $...$ for Matplotlib compatibility)",
    value=r"\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
    height=150,
    key="latex_code"
)

# --- Dynamic Preview Tabs ---
if latex_input:
    st.subheader("Dynamic Preview (Before PDF)")
    tab1, tab2, tab3 = st.tabs(["Rendered Image (PDF Source)", "Raw LaTeX Source", "Unicode View"])

    with tab1:
        st.markdown("#### PNG Image Preview (What goes into the PDF)")
        image_uri = latex_to_png_base64(latex_input)
        
        if image_uri:
            st.image(image_uri, caption="Matplotlib Rendered PNG Image")
            st.success("Rendering successful. This image will be embedded in the PDF.")
        else:
            st.warning("Rendering failed. Check your LaTeX syntax.")

    with tab2:
        st.markdown("#### Raw LaTeX Code")
        st.code(latex_input, language="latex")
        
    with tab3:
        st.markdown("#### Unicode Text Equivalent (Limited Conversion)")
        unicode_output = latex_to_unicode(latex_input)
        st.text_area("Unicode Result", value=unicode_output, height=100)

    # --- PDF Generation Button ---
    st.markdown("---")
    
    pdf_bytes = render_latex_to_pdf(latex_input)
    
    st.download_button(
        label="⬇️ Download PDF with Embedded Image",
        data=pdf_bytes,
        file_name="rendered_math_document.pdf",
        mime="application/pdf"
    )

else:
    st.info("Paste your LaTeX code above to begin rendering and generate the PDF.")