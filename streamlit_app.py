import streamlit as st
import json
import os
from datetime import datetime
import google.generativeai as genai
from utils import run_analysis_and_summarize, segment_raw_transcript, generate_pdf

# Page configuration
st.set_page_config(
    page_title="AI Study Notes Generator",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'math_mode' not in st.session_state:
    st.session_state.math_mode = True
if 'chem_mode' not in st.session_state:
    st.session_state.chem_mode = True
if 'pdf_generated' not in st.session_state:
    st.session_state.pdf_generated = False

# Header
st.title("📚 AI Study Notes Generator")
st.markdown("""
Transform unstructured academic content (YouTube transcripts, lectures, etc.) into professionally formatted PDF study notes with LaTeX math and chemistry support.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key Input
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=st.session_state.api_key,
        help="Enter your Google Gemini API key"
    )
    
    if api_key:
        st.session_state.api_key = api_key
        os.environ['GEMINI_API_KEY'] = api_key
    
    st.markdown("---")
    
    # Feature toggles
    st.header("🎛️ Feature Toggles")
    
    st.session_state.math_mode = st.checkbox(
        "Math Mode",
        value=st.session_state.math_mode,
        help="Enable LaTeX math rendering (e.g., \\sum, \\int, \\frac)"
    )
    
    st.session_state.chem_mode = st.checkbox(
        "Chemistry Mode",
        value=st.session_state.chem_mode,
        help="Enable chemical formula rendering (e.g., \\ce{H2O}, \\ce{CO2})"
    )
    
    st.markdown("---")
    
    # Instructions
    st.header("📖 How to Use")
    st.markdown("""
    1. Enter your Gemini API key
    2. Toggle Math/Chemistry modes
    3. Paste your transcript (structured JSON or raw text)
    4. Click "Process Content"
    5. Download your PDF
    """)
    
    st.markdown("---")
    st.markdown("**Note:** Math Mode uses LaTeX syntax like `$\\sum_{i=1}^{n}$`")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Input Content")
    
    input_format = st.radio(
        "Input Format",
        ["Raw Text", "Structured JSON"],
        help="Select input format. Raw text will be auto-segmented."
    )
    
    if input_format == "Raw Text":
        user_input = st.text_area(
            "Paste your transcript or lecture content here:",
            height=400,
            placeholder="Example:\n\nIntroduction to Calculus\n\nCalculus is the mathematical study of continuous change...\n\nDerivatives\n\nA derivative represents the rate of change..."
        )
        
        st.info("💡 Raw text will be automatically segmented into structured sections.")
        
    else:
        user_input = st.text_area(
            "Paste your structured JSON here:",
            height=400,
            placeholder="""Example:
{
  "title": "Introduction to Calculus",
  "segments": [
    {
      "heading": "What is Calculus?",
      "content": "Calculus is the study of continuous change..."
    },
    {
      "heading": "Derivatives",
      "content": "A derivative represents the rate of change..."
    }
  ]
}"""
        )
        
        st.info("💡 Provide structured JSON with 'title' and 'segments' fields.")

with col2:
    st.header("🎨 Preview & Output")
    
    if st.session_state.processed_data:
        st.success("✅ Content processed successfully!")
        
        # Display processed data preview
        with st.expander("View Processed Structure", expanded=False):
            st.json(st.session_state.processed_data)
        
        # Show summary
        data = st.session_state.processed_data
        st.metric("Document Title", data.get('title', 'N/A'))
        st.metric("Number of Sections", len(data.get('segments', [])))
        
    else:
        st.info("👆 Enter content and click 'Process Content' to begin")

# Processing button
st.markdown("---")
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

with col_btn2:
    if st.button("🚀 Process Content", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("❌ Please enter your Gemini API key in the sidebar.")
        elif not user_input or user_input.strip() == "":
            st.error("❌ Please enter some content to process.")
        else:
            with st.spinner("🔄 Processing content with AI..."):
                try:
                    # Configure Gemini
                    genai.configure(api_key=st.session_state.api_key)
                    
                    # Parse or segment input
                    if input_format == "Structured JSON":
                        try:
                            input_data = json.loads(user_input)
                        except json.JSONDecodeError:
                            st.error("❌ Invalid JSON format. Please check your input.")
                            st.stop()
                    else:
                        # Auto-segment raw text
                        input_data = segment_raw_transcript(user_input)
                    
                    # Run AI analysis and summarization
                    processed_data = run_analysis_and_summarize(
                        input_data,
                        math_mode=st.session_state.math_mode,
                        chem_mode=st.session_state.chem_mode
                    )
                    
                    st.session_state.processed_data = processed_data
                    st.session_state.pdf_generated = False
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error processing content: {str(e)}")
                    st.exception(e)

# PDF Generation
if st.session_state.processed_data:
    st.markdown("---")
    col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 1, 1])
    
    with col_pdf2:
        if st.button("📄 Generate PDF", type="secondary", use_container_width=True):
            with st.spinner("🎨 Generating PDF with LaTeX rendering..."):
                try:
                    pdf_bytes = generate_pdf(st.session_state.processed_data)
                    st.session_state.pdf_generated = True
                    st.session_state.pdf_bytes = pdf_bytes
                    
                    # Offer download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"study_notes_{timestamp}.pdf"
                    
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("✅ PDF generated successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
                    st.exception(e)
    
    # If PDF already generated, show download button
    if st.session_state.pdf_generated and 'pdf_bytes' in st.session_state:
        with col_pdf2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"study_notes_{timestamp}.pdf"
            
            st.download_button(
                label="⬇️ Download PDF",
                data=st.session_state.pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Built with Streamlit • Powered by Gemini 2.5 Flash • Rendered with WeasyPrint + KaTeX</p>
</div>
""", unsafe_allow_html=True)