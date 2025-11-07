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
DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_OPTIONS = [DEFAULT_MODEL, "gemini-2.5-pro"] 

# Presets for Output Length (Pages/Words)
LENGTH_PRESETS = {
    "Short (1-2 pages)": 500,
    "Medium (3-4 pages)": 1000,
    "Detailed (5-6 pages)": 1500,
    "Max (7+ pages)": 2000
}

# Presets for Transcript Divisions (Affects analysis depth)
DIVISION_PRESETS = {
    "Quick": 1,
    "Medium": 3,
    "Detailed": 6
}

# All available output sections (used for the checkboxes)
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
    
    # A2. Output Length Preset
    st.sidebar.subheader("📄 Output Length")
    length_preset_key = st.sidebar.selectbox(
        "Choose Length Preset:",
        options=list(LENGTH_PRESETS.keys()),
        index=1
    )
    max_words = LENGTH_PRESETS[length_preset_key]
    st.sidebar.info(f"Approximate Length: **{max_words} words**")


    # A3. Transcript Division Preset
    st.sidebar.subheader("🗂️ Analysis Depth")
    div_preset_key = st.sidebar.selectbox(
        "Transcript Divisions:",
        options=list(DIVISION_PRESETS.keys()),
        index=1
    )
    # This feature requires custom logic to divide the transcript, 
    # but we store the value for the prompt instruction.
    transcript_divisions = DIVISION_PRESETS[div_preset_key] 
    st.sidebar.info(f"Analysis Depth: **{div_preset_key}** (uses {transcript_divisions} divisions)")


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
    
    # Generate checkboxes and update session state
    selected_sections_keys = []
    for readable_name, key_name in ALL_SECTIONS.items():
        if st.sidebar.checkbox(
            readable_name, 
            value=key_name in st.session_state.sections_to_include,
            key=f"check_{key_name}" # Unique key for checkbox
        ):
            selected_sections_keys.append(key_name)
    
    st.session_state.sections_to_include = selected_sections_keys


    # --- B. MAIN AREA: Inputs and Output ---

    # 1. API Key Input
    api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else st.text_input(
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
        "Paste Transcript Segments (JSON Array):", 
        height=250, 
        help="Paste your structured JSON transcript segments here. e.g., [{'time': 10, 'text': '...'}]"
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
            
        # --- Transcript Processing (Assume JSON input) ---
        try:
            transcript_segments_to_send = json.loads(transcript_input)
            if not isinstance(transcript_segments_to_send, list):
                st.error("Transcript input must be a valid JSON array of segments.")
                return
        except json.JSONDecodeError:
            st.error("Invalid JSON format in the Transcript Input box.")
            return

        # --- CORE ANALYSIS CALL ---
        with st.spinner(f"Analyzing transcript using {model_choice} (Length: {max_words} words)..."):
            notes_data, error_msg, full_prompt = run_analysis_and_summarize(
                api_key=api_key,
                transcript_segments=transcript_segments_to_send,
                max_words=max_words,
                sections_list_keys=st.session_state.sections_to_include, # Use dynamic sections
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
