# utils.py

import streamlit as st
import json
import re
from pathlib import Path
import google.generativeai as genai
from io import BytesIO
import time
from typing import Optional, Tuple, Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os # For FileSystemLoader path

# --- MODERN COLOR PALETTE (Kept for CSS in template) ---
COLORS = {
    "primary": "#1E88E5",
    "primary_dark": "#1565C0",
    "secondary": "#26A69A",
    "accent": "#FF6F00",
    "text_dark": "#212121",
    "text_medium": "#424242",
    "text_light": "#757575",
    "bg_section": "#E3F2FD",
    "bg_highlight": "#FFF59D",
    "bg_card": "#FAFAFA",
    "link": "#1976D2",
}

# Section icons/emojis (Kept for use in template)
SECTION_ICONS = {
    "topic_breakdown": "📚",
    "key_vocabulary": "📖",
    "formulas_and_principles": "🔬",
    "teacher_insights": "💡",
    "exam_focus_points": "⭐",
    "common_mistakes_explained": "⚠️",
    "key_points": "✨",
    "short_tricks": "⚡",
    "must_remembers": "🧠"
}

# --- Configuration and Constants ---
EXPECTED_KEYS = [
    "main_subject", "topic_breakdown", "key_vocabulary",
    "formulas_and_principles", "teacher_insights",
    "exam_focus_points", "common_mistakes_explained", 
    "key_points", "short_tricks", "must_remembers" 
]

# --- UTILITY FUNCTIONS ---

def inject_custom_css():
    """Modern CSS styling"""
    st.markdown("""
        <style>
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        p, label, .stMarkdown {
            font-size: 1.05rem !important;
            line-height: 1.6;
        }
        .stButton>button {
            background: linear-gradient(90deg, #1E88E5, #1565C0);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            font-weight: 600;
            border-radius: 8px;
            transition: transform 0.2s;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

def get_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID"""
    patterns = [r"(?<=v=)[^&#?]+", r"(?<=be/)[^&#?]+", r"(?<=live/)[^&#?]+", r"(?<=embed/)[^&#?]+", r"(?<=shorts/)[^&#?]+"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(0)
    return None

def extract_gemini_text(response) -> Optional[str]:
    """Extract text from Gemini API response"""
    if hasattr(response, 'text'):
        return response.text
    if hasattr(response, 'candidates') and response.candidates:
        try:
            return response.candidates[0].content.parts[0].text
        except (AttributeError, IndexError):
            pass
    return None

def extract_clean_json(response_text: str) -> Optional[str]:
    """Extract JSON from response with markdown cleanup"""
    cleaned = re.sub(r'```json\s*|\s*```', '', response_text)
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass
    return None

def format_timestamp(seconds: int) -> str:
    """Convert seconds to [MM:SS] or [HH:MM:SS]"""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def get_content_text(item):
    """Extract text content from various item structures"""
    if isinstance(item, dict):
        for key in ['detail', 'explanation', 'point', 'text', 'definition', 
                    'formula_or_principle', 'insight', 'mistake', 'content']:
            if key in item and item[key]:
                return str(item[key])
    return str(item) if item else ''


# --- API INTERACTION ---

@st.cache_data(ttl=0)
def run_analysis_and_summarize(
    api_key: str, 
    transcript_segments: List[Dict], 
    max_words: int, 
    sections_list_keys: list, 
    user_prompt: str, 
    model_name: str, 
    is_easy_read: bool,
    is_maths_on: bool,        # <-- NEW
    is_chemistry_on: bool     # <-- NEW
) -> Tuple[Optional[Dict[str, Any]], Optional[str], str]:
    """Call Gemini API and return structured JSON"""
    
    sections_str = ", ".join(sections_list_keys)
    
    # 1. Base Prompt (Always on)
    base_instruction = "You are an expert academic content analyzer. Extract structured study notes from video transcripts."
    
    # 2. LaTeX Configuration
    maths_instruction = ""
    chem_instruction = ""
    
    if is_maths_on or is_chemistry_on:
        # If any specialized mode is ON, set the core instruction for LaTeX use.
        base_instruction += " **Use LaTeX formatting for all complex mathematical and chemical notation.**"
    else:
        # If General mode, instruct it to use plain text only.
        base_instruction += " **Use plain text only. AVOID using any LaTeX commands unless absolutely necessary.**"

    if is_maths_on:
        maths_instruction = "For all mathematics, use standard LaTeX syntax (e.g., $$\frac{a}{b}$$ or $\\sqrt{x^2}$). Enclose all display equations in double dollar signs ($$...). "
        
    if is_chemistry_on:
        chem_instruction = "For all chemistry, use the mhchem LaTeX command (e.g., $\\ce{H2O}$ or $\\ce{A + B -> C}$). "

    # 3. Highlighting Instruction
    highlighting_instruction = (
        "4. **Highlighting:** Wrap 2-4 critical words in <hl>text</hl> tags."
        if is_easy_read else
        "4. **NO special tags:** Use plain text only."
    )
    
    # 4. Final Prompt Assembly
    prompt_instructions = f"""
{base_instruction}

OUTPUT: Valid JSON object with these exact keys (use snake_case):
{{ "main_subject": "...", "topic_breakdown": [...], ... }} 

RULES:
1. Use EXACT 'time' values from input (in seconds)
2. {highlighting_instruction}
3. Keep content concise and academic
4. Return ONLY valid JSON (no markdown, no comments)
5. Fill ALL requested sections with available content
6. Target total length: ~{max_words} words across all sections
7. Extract ONLY these categories: {sections_str}

**SPECIAL FORMATTING RULES:**
{maths_instruction}{chem_instruction}

USER PREFERENCES: {user_prompt}
"""
    
    transcript_json = json.dumps(transcript_segments, indent=2)
    full_prompt = f"{prompt_instructions}\n\nTRANSCRIPT DATA:\n{transcript_json}"
    
    # ... (rest of the API interaction code is mostly unchanged, handles API call and JSON cleanup)
    if not api_key:
        return None, "API Key Missing", full_prompt
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(full_prompt)
        response_text = extract_gemini_text(response)
        
        if not response_text:
            return None, "Empty API response", full_prompt
        
        json_str = extract_clean_json(response_text)
        if not json_str:
            return None, f"No valid JSON found in response", full_prompt
        
        json_data = json.loads(json_str)
        
        def to_snake_case(s):
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Ensure keys are snake_case and default values are present
        json_data = {to_snake_case(k): v for k, v in json_data.items()}
        for key in EXPECTED_KEYS:
            if key not in json_data:
                json_data[key] = "" if key == "main_subject" else []
            elif key != "main_subject" and not isinstance(json_data[key], list):
                json_data[key] = [json_data[key]] if json_data[key] else []
        
        return json_data, None, full_prompt
        
    except json.JSONDecodeError as e:
        return None, f"JSON Parse Error: {e}", full_prompt
    except Exception as e:
        return None, f"API Error: {e}", full_prompt

# --- WEASYPRINT/JINJA2 PDF GENERATION ---

# Set up Jinja2 environment (assumes template.html is in the same directory)
# In Streamlit cloud, Path(__file__).parent is usually the root directory
template_loader = FileSystemLoader(Path(__file__).parent)
template_env = Environment(loader=template_loader)


def process_data_for_template(data: dict, video_id: Optional[str], is_easy_read: bool) -> dict:
    """Pre-process data: add timestamps, process highlights, and handle nested structures."""
    
    base_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
    processed_data = data.copy()

    def process_item(item):
        """Processes a single dictionary item to add HTML-ready fields."""
        if not isinstance(item, dict):
            return item
        
        new_item = item.copy()
        
        # 1. Add formatted clickable timestamp link (HTML string)
        timestamp = new_item.get('time')
        if timestamp and base_url:
            ts_formatted = format_timestamp(timestamp)
            link_url = f"{base_url}&t={int(timestamp)}s"
            new_item['timestamp_html'] = f'<a href="{link_url}" class="timestamp-link">[{ts_formatted}]</a>'
        else:
            new_item['timestamp_html'] = ''

        # 2. Process highlighting tags (from <hl> to HTML/CSS)
        # Note: We rely on the template CSS for the color/bolding
        for key in new_item.keys():
            if isinstance(new_item[key], str):
                if is_easy_read:
                    # Convert Gemini's custom tag to HTML span
                    new_item[key] = re.sub(
                        r'<hl>(.*?)</hl>', 
                        r'<span class="highlight-text"><b>\1</b></span>', 
                        new_item[key]
                    )
                else:
                    # Remove tags if not in easy-read mode
                    new_item[key] = re.sub(r'<hl>(.*?)</hl>', r'\1', new_item[key])
        
        return new_item

    # Iterate over all sections (which are lists of items)
    for k, v in processed_data.items():
        if isinstance(v, list):
            new_list = []
            for item in v:
                if k == 'topic_breakdown':
                    # Handle nested topic breakdown structure
                    new_topic = process_item(item)
                    if 'details' in new_topic and isinstance(new_topic['details'], list):
                        new_topic['details'] = [process_item(detail) for detail in new_topic['details']]
                    new_list.append(new_topic)
                else:
                    # Handle flat lists
                    new_list.append(process_item(item))
            processed_data[k] = new_list
            
    return processed_data


def save_to_pdf_weasyprint(
    data: dict, 
    video_id: Optional[str], 
    output: BytesIO, 
    format_choice: str = "Default (Compact)"
):
    """Generate PDF using WeasyPrint and KaTeX/mhchem HTML rendering."""
    
    template = template_env.get_template("template.html")
    is_easy_read = format_choice.startswith("Easier Read")
    
    # Pre-process data for HTML rendering
    processed_data = process_data_for_template(data, video_id, is_easy_read)
    
    # Render HTML using Jinja2
    html_out = template.render(
        data=processed_data,
        section_icons=SECTION_ICONS,
        is_easy_read=is_easy_read,
        colors=COLORS
    )
    
    # Generate PDF using WeasyPrint
    HTML(string=html_out).write_pdf(output)
    output.seek(0)
    print("✅ PDF generated successfully using WeasyPrint/KaTeX.")
