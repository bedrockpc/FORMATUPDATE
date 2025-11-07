import json
import re
from typing import Dict, List, Any
import google.generativeai as genai
from google.generativeai import types
from jinja2 import Template
from weasyprint import HTML
import io

def segment_raw_transcript(raw_text: str) -> Dict[str, Any]:
    """
    Auto-segment raw transcript text into structured JSON format.
    
    Args:
        raw_text: Unstructured plain text content
        
    Returns:
        Dictionary with 'title' and 'segments' keys
    """
    lines = raw_text.strip().split('\n')
    
    # Extract title (first non-empty line)
    title = "Study Notes"
    content_start = 0
    
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            content_start = i + 1
            break
    
    # Segment by detecting headings (short lines, possibly capitalized)
    segments = []
    current_heading = "Introduction"
    current_content = []
    
    for line in lines[content_start:]:
        line = line.strip()
        
        if not line:
            continue
        
        # Heuristic: if line is short (< 60 chars) and looks like a heading
        if len(line) < 60 and (line[0].isupper() or line.isupper()) and not line.endswith('.'):
            # Save previous segment
            if current_content:
                segments.append({
                    "heading": current_heading,
                    "content": ' '.join(current_content)
                })
                current_content = []
            
            current_heading = line
        else:
            current_content.append(line)
    
    # Add final segment
    if current_content:
        segments.append({
            "heading": current_heading,
            "content": ' '.join(current_content)
        })
    
    return {
        "title": title,
        "segments": segments
    }


def run_analysis_and_summarize(input_data: Dict[str, Any], 
                                math_mode: bool = True, 
                                chem_mode: bool = True) -> Dict[str, Any]:
    """
    Process input data through Gemini API with dynamic prompt construction.
    
    Args:
        input_data: Dictionary with 'title' and 'segments'
        math_mode: Enable LaTeX math rendering
        chem_mode: Enable chemical formula rendering
        
    Returns:
        Enhanced structured JSON with formatted content
    """
    
    # Build dynamic system prompt based on feature toggles
    system_instructions = """You are an expert academic content processor and formatter.

Your task is to analyze the provided academic content and return a structured JSON object with enhanced, professionally formatted sections.

"""
    
    if math_mode:
        system_instructions += """
**MATH MODE ENABLED:**
- Detect mathematical expressions and formulas
- Format them using LaTeX syntax wrapped in $ delimiters
- Examples: $\\sum_{i=1}^{n} x_i$, $\\int_0^1 f(x)dx$, $\\frac{dy}{dx}$
- Use inline math $...$ for inline expressions
- Use display math for standalone equations
"""
    
    if chem_mode:
        system_instructions += """
**CHEMISTRY MODE ENABLED:**
- Detect chemical formulas and reactions
- Format them using mhchem LaTeX syntax: $\\ce{formula}$
- Examples: $\\ce{H2O}$, $\\ce{CO2}$, $\\ce{2H2 + O2 -> 2H2O}$
"""
    
    system_instructions += """

**OUTPUT FORMAT:**
Return ONLY a valid JSON object with this exact structure:
{
  "title": "Document title",
  "summary": "Brief 2-3 sentence overview of the content",
  "segments": [
    {
      "heading": "Section heading",
      "content": "Enhanced content with LaTeX formatting where appropriate",
      "key_points": ["Key point 1", "Key point 2", "Key point 3"]
    }
  ]
}

**IMPORTANT:**
- Return ONLY the JSON object, no additional text
- Ensure proper JSON formatting with correct quotes and commas
- Preserve all technical content accuracy
- Enhance readability while maintaining academic rigor
"""
    
    # Prepare user prompt
    user_prompt = f"""Process this academic content:

Title: {input_data.get('title', 'Untitled')}

Content Segments:
{json.dumps(input_data.get('segments', []), indent=2)}

Return the enhanced structured JSON as specified."""
    
    try:
        # Configure model
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp',
            generation_config=types.GenerationConfig(
                temperature=0.3,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
        )
        
        # Generate response
        response = model.generate_content(
            [system_instructions, user_prompt]
        )
        
        # Extract and parse JSON from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        # Parse JSON
        result = json.loads(response_text)
        
        return result
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}\nResponse: {response_text[:500]}")
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {str(e)}")


def generate_pdf(data: Dict[str, Any]) -> bytes:
    """
    Generate PDF from structured data using WeasyPrint and KaTeX.
    
    Args:
        data: Dictionary with 'title', 'summary', and 'segments'
        
    Returns:
        PDF file as bytes
    """
    
    # Load HTML template
    with open('template.html', 'r', encoding='utf-8') as f:
        template_str = f.read()
    
    template = Template(template_str)
    
    # Render HTML with data
    html_content = template.render(
        title=data.get('title', 'Study Notes'),
        summary=data.get('summary', ''),
        segments=data.get('segments', [])
    )
    
    # Generate PDF
    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file.read()