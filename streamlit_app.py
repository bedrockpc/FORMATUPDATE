# app.py

import streamlit as st
import json
import re
from pathlib import Path
from io import BytesIO
from utils import (
    run_analysis_and_summarize, 
    save_to_pdf_weasyprint, 
    get_video_id, 
    inject_custom_css
)

# --- Configuration and Constants ---
# You would usually get this from your environment variables or secrets
MODEL_NAME = "gemini-2.5-flash" 

# --- SESSION STATE INITIALIZATION ---
if 'math_on' not in st.session_state:
    st.session_state.math_on = False
if 'chem_on' not in st.session_state:
    st.session_state.chem_on = False

# --- UI Layout ---
def main():
    inject_custom_css()
    st.title("🧠 AI Study Notes Generator")
    
    # 1. API Key Input (Required for Gemini access)
    # Using secrets is highly recommended for production apps
    api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input(
        "Enter your Gemini API Key:", type="password"
    )

    # 2. Input and Settings Columns
    col1, col2 = st.columns([3, 1])

    with col1:
        video_url = st.text_input("YouTube Video URL:", help="Paste the full link here.")
        user_prompt = st.text_area("Specific Focus/Query:", "Summarize the key concepts and formulas presented in the video.", height=100)

    with col2:
        st.subheader("Formatting")
        format_choice = st.radio(
            "PDF Layout:",
            ["Default (Compact)", "Easier Read (Spacious & Highlighted)"],
            index=0
        )
        max_words = st.number_input("Target Length (Words):", min_value=100, max_value=2000, value=750, step=50, help="Approximate total length.")
    
    st.divider()
    
    # 3. Maths/Chemistry Options (The new features)
    st.subheader("🧪 Specialized $\\LaTeX$ Support")
    
    math_col, chem_col, general_col = st.columns(3)
    
    # Maths Checkbox
    with math_col:
        st.checkbox(
            "Enable **Maths** $\sum$",
            key='math_on',
            help="Enables complex $\\LaTeX$ math rendering (e.g., integrals, fractions)."
        )

    # Chemistry Checkbox
    with chem_col:
        st.checkbox(
            "Enable **Chemistry** $\\ce{H2O}$",
            key='chem_on',
            help="Enables specialized $\\LaTeX$ mhchem commands for chemical formulas."
        )
    
    # General Mode Indicator
    with general_col:
        is_specialized = st.session_state.math_on or st.session_state.chem_on
        mode_text = "Specialized" if is_specialized else "General"
        st.info(f"Current Mode: **{mode_text}**")
    
    st.divider()

    # 4. Generate Button
    if st.button("Generate Study Notes PDF"):
        if not api_key:
            st.error("Please enter your Gemini API Key.")
            return

        video_id = get_video_id(video_url)
        if not video_id:
            st.error("Please enter a valid YouTube URL.")
            return
            
        # Mock Transcript Data (Replace with real transcript fetching logic)
        mock_transcript = [{"time": 10, "text": "This is a concept discussed at the beginning."}, {"time": 60, "text": "We'll solve for the variable x using the quadratic formula which is x = (-b ± \\sqrt{b^2 - 4ac}) / 2a. This is a very important formula."}, {"time": 120, "text": "Now, let's look at the reaction of sulfur trioxide with water, which is $\\ce{SO3(g) + H2O(l) -> H2SO4(aq)}$. This is a core reaction."}, {"time": 180, "text": "The main idea of this lesson is that force equals mass times acceleration, F=ma."}]
        
        # --- CORE ANALYSIS CALL ---
        with st.spinner("Analyzing video transcript and structuring notes..."):
            notes_data, error_msg, full_prompt = run_analysis_and_summarize(
                api_key=api_key,
                transcript_segments=mock_transcript, # Replace with your real transcript var
                max_words=max_words,
                sections_list_keys=["main_subject", "topic_breakdown", "key_vocabulary", "formulas_and_principles"], # Simplified for demo
                user_prompt=user_prompt,
                model_name=MODEL_NAME,
                is_easy_read=format_choice.startswith("Easier Read"),
                is_maths_on=st.session_state.math_on,   # PASS NEW FLAGS
                is_chemistry_on=st.session_state.chem_on # PASS NEW FLAGS
            )

        # --- PDF Generation ---
        if notes_data:
            st.success("Analysis complete! Generating PDF...")
            output_buffer = BytesIO()
            
            # Call the new WeasyPrint function
            save_to_pdf_weasyprint(
                data=notes_data,
                video_id=video_id,
                output=output_buffer,
                format_choice=format_choice
            )
            
            # Offer download button
            st.download_button(
                label="📥 Download Study Notes PDF",
                data=output_buffer.getvalue(),
                file_name=f"{video_id}_study_notes.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"Analysis Failed: {error_msg}")
            st.code(full_prompt, language='json', label="Prompt Sent to API (for debugging)")

if __name__ == "__main__":
    main()
