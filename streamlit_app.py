# app.py

import streamlit as st
import json
import re
from io import BytesIO
from pathlib import Path

# Assuming utils.py and template.html are in the same directory
from utils import (
    run_analysis_and_summarize, 
    save_to_pdf_weasyprint, 
    get_video_id, 
    inject_custom_css,
    segment_raw_transcript 
)

# --- Configuration and Constants ---
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_OPTIONS = [DEFAULT_MODEL, "gemini-2.5-pro"] 

ALL_SECTIONS = {
    "Topic Breakdown": "topic_breakdown",
    "Key Vocabulary": "key_vocabulary",
    "Formulas & Principles": "formulas_and_principles",
    "Teacher Insights": "teacher_insights",
    "Exam Focus Points": "exam_focus_points",
    "Common Mistakes": "common_mistakes_explained",
    "Key Points": "key_points",
    "Short Tricks": "short_tricks",
    "Must Remembers": "must_remembers",
}

# --- SESSION STATE INITIALIZATION ---
if 'math_on' not in st.session_state: st.session_state.math_on = False
if 'chem_on' not in st.session_state: st.session_state.chem_on = False
if 'sections_to_include' not in st.session_state:
    st.session_state.sections_to_include = list(ALL_SECTIONS.values())

# --- UI Layout ---
def main():
    inject_custom_css()
    st.title("🧠 AI Study Notes Generator")
    
    # --- A. SIDEBAR: Settings ---
    st.sidebar.header("⚙️ Analysis Settings")

    # A1. Model Selection
    model_choice = st.sidebar.selectbox(
        "Select AI Model:",
        options=MODEL_OPTIONS,
        index=MODEL_OPTIONS.index(DEFAULT_MODEL),
        help="2.5 Flash is fastest and cheapest. Pro offers superior reasoning but is slower."
    )
    
    # A2. Output Length (Words)
    st.sidebar.subheader("📄 Output Length")
    max_words = st.sidebar.number_input(
        "Target Length (Words):", 
        min_value=200, 
        max_value=20000, 
        value=750, 
        step=100,
        help="Sets the approximate total word count for the notes (200 min, 20k max)."
    )

    # A3. Transcript Division
    st.sidebar.subheader("🗂️ Analysis Depth")
    transcript_divisions = st.sidebar.number_input(
        "Transcript Divisions:",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Higher divisions lead to more focused, segmented analysis (1 min, 10 max)."
    )
    st.sidebar.info(f"Analysis Depth: **{transcript_divisions} divisions**") # This value is used in the prompt instructions

    # A4. Maths/Chemistry Options
    st.sidebar.subheader("🧪 $\\LaTeX$ Support")
    st.sidebar.checkbox(
        "Enable **Maths** $\sum$",
        key='math_on',
        help="Enables complex $\\LaTeX$ math rendering."
    )
    st.sidebar.checkbox(
        "Enable **Chemistry** $\\ce{H2O}$",
        key='chem_on',
        help="Enables specialized $\\LaTeX$ mhchem commands."
    )
    st.sidebar.info(f"Mode: **{'Specialized' if st.session_state.math_on or st.session_state.chem_on else 'General'}**")


    # A5. Output Section Checkboxes
    st.sidebar.subheader("✅ Select Output Sections")
    
    selected_sections_keys = []
    for readable_name, key_name in ALL_SECTIONS.items():
        if st.sidebar.checkbox(
            readable_name, 
            value=key_name in st.session_state.sections_to_include,
            key=f"check_{key_name}"
        ):
            selected_sections_keys.append(key_name)
    
    st.session_state.sections_to_include = selected_sections_keys


    # --- B. MAIN AREA: Inputs and Output ---

    # 1. API Key Input
    # Ensure you set the GEMINI_API_KEY secret in Streamlit
    api_key = st.secrets.get("GEMINI_API_KEY") or st.text_input(
        "Enter your Gemini API Key:", type="password"
    )

    # 2. Main Inputs
    video_url = st.text_input("YouTube Video URL:", help="Paste the full link here.")
    
    # PDF Output Format
    format_choice = st.radio(
        "PDF Layout:",
        ["Default (Compact)", "Easier Read (Spacious & Highlighted)"],
        index=0,
        horizontal=True
    )
    
    # 3. Transcript and Query Input
    st.subheader("Transcript & Query")
    transcript_input = st.text_area(
        "Paste Transcript (Raw Text or JSON Segments):", 
        height=250, 
        help="Paste raw text from a transcript. The tool will automatically segment it. For timestamps, paste your original JSON array."
    )
    user_prompt = st.text_area("Specific Focus/Query:", "Summarize the key concepts and formulas presented in the video.", height=100)
    
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
            
        # --- Transcript Processing (Smart Validation) ---
        transcript_input_raw = transcript_input.strip()

        if not transcript_input_raw:
            st.error("Transcript Input box cannot be empty.")
            return

        transcript_segments_to_send = []
        try:
            if transcript_input_raw.startswith('['):
                # ATTEMPT JSON PARSING (Structured input)
                transcript_segments_to_send = json.loads(transcript_input_raw)
                if not isinstance(transcript_segments_to_send, list):
                    raise TypeError("JSON input is not a list/array.")
            else:
                # FALLBACK TO RAW TEXT (Unstructured input)
                transcript_segments_to_send = segment_raw_transcript(transcript_input_raw)

        except (json.JSONDecodeError, TypeError):
            # If parsing failed, try the segmenter one last time (safer check)
            transcript_segments_to_send = segment_raw_transcript(transcript_input_raw)
            
        if not transcript_segments_to_send:
            st.error("Could not process or segment the transcript text.")
            return
        
        # --- CORE ANALYSIS CALL ---
        with st.spinner(f"Analyzing transcript using {model_choice} (Length: {max_words} words)..."):
            notes_data, error_msg, full_prompt = run_analysis_and_summarize(
                api_key=api_key,
                transcript_segments=transcript_segments_to_send,
                max_words=max_words,
                sections_list_keys=st.session_state.sections_to_include, 
                user_prompt=user_prompt,
                model_name=model_choice,
                is_easy_read=format_choice.startswith("Easier Read"),
                is_maths_on=st.session_state.math_on,
                is_chemistry_on=st.session_state.chem_on
            )

        # --- PDF Generation ---
        if notes_data:
            st.success("Analysis complete! Generating PDF...")
            output_buffer = BytesIO()
            
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
            with st.expander("Show Prompt Sent to API (for debugging)"):
                 st.code(full_prompt, language='json')

if __name__ == "__main__":
    main()
