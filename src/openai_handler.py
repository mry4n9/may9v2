import streamlit as st
from openai import OpenAI
import json

# Use the model name you have access to. "gpt-4o-mini" is a recent model.
# If "gpt-4.1-mini" is a specific early access model, use that exact string.
AI_MODEL = "gpt-4o-mini" 

def get_openai_client():
    """Initializes and returns the OpenAI client."""
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set it in secrets.toml or Streamlit Cloud secrets.")
        return None
    return OpenAI(api_key=api_key)

def summarize_text_with_ai(client, text_content, section_name="content"):
    """Summarizes text using OpenAI API."""
    if not client or not text_content or len(text_content.strip()) < 50: # Basic check for meaningful content
        return ""
    
    prompt = f"""
    Please provide a comprehensive summary of the following {section_name}. 
    Focus on key information relevant for creating marketing ad copy, such as:
    - Core products/services offered
    - Unique selling propositions (USPs)
    - Target audience
    - Brand voice and tone (if discernible)
    - Key problems solved or benefits offered

    The summary should be detailed enough to inform the generation of diverse ad creatives.
    Avoid generic statements and extract specific, actionable insights.

    Full text to summarize:
    ---
    {text_content[:50000]} 
    ---
    Comprehensive Summary:
    """
    # Limiting to 15000 characters for the input to summarization to manage token limits,
    # even though the user said "don't worry". This is a practical limit.
    # For gpt-4o-mini, context window is 128k tokens, so this is very conservative.
    # You can increase this if needed, but extremely large single texts might still be an issue.

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant skilled in summarizing text for marketing purposes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        st.error(f"Error during AI summarization for {section_name}: {e}")
        return ""

def generate_content_with_ai(client, prompt_text):
    """Generates content using OpenAI API and expects JSON output."""
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert marketing copywriter. Generate content exactly in the specified JSON format."},
                {"role": "user", "content": prompt_text}
            ],
            response_format={"type": "json_object"}, # Ensure JSON mode is enabled if model supports
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content) # Parse JSON string to Python dict
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from AI response: {e}")
        st.text_area("Problematic AI Response:", content, height=200)
        return None
    except Exception as e:
        st.error(f"Error during AI content generation: {e}")
        return None

# --- Prompt Creation Functions ---

def create_email_prompt(context_summary, lead_objective_link, count):
    return f"""
    Based on the following company context:
    <context>
    {context_summary}
    </context>

    Generate {count} versions of Email ad content.
    The objective for these emails is "Demand Capture".
    The primary call-to-action link to embed in the email body is: {lead_objective_link}
    Use the placeholder "[LEAD_OBJECTIVE_LINK]" in the email body where this link should be embedded.

    Output the result as a JSON object with a single key "emails", which is a list of email objects.
    Each email object should have the following keys:
    - "version": (integer) The version number, starting from 1.
    - "headline": (string) A compelling headline for the email.
    - "subject_line": (string) An engaging subject line.
    - "body": (string) The email body, 2-3 paragraphs. Include emojis where appropriate. It MUST include the placeholder "[LEAD_OBJECTIVE_LINK]".
    - "cta": (string) A condensed call-to-action phrase, derived from the body's main CTA.

    Example of an email object:
    {{
      "version": 1,
      "headline": "Unlock Growth with Our Solution!",
      "subject_line": "🚀 Exclusive Offer Inside: Transform Your Business",
      "body": "Paragraph 1 introducing the problem and solution... Learn more and book your demo here: [LEAD_OBJECTIVE_LINK].\\n\\nParagraph 2 detailing benefits and value...",
      "cta": "Book Your Demo Now"
    }}
    """

def create_linkedin_facebook_prompt(platform, context_summary, objective, count, destination_link, cta_button_options):
    ad_name_instruction = "A descriptive ad name (up to 250 characters) for internal identification."
    if platform == "LinkedIn":
        text_field_name = "introductory_text"
        text_field_instruction = "Hook in the first 150 characters, total length between 300-400 characters. Embed relevant emojis."
        headline_chars = "~70 characters"
        link_desc_field = "" # No link description for LinkedIn in this spec
    else: # Facebook
        text_field_name = "primary_text"
        text_field_instruction = "Hook in the first 125 characters, total length between 300-400 characters. Embed relevant emojis."
        headline_chars = "~27 characters"
        link_desc_field = '\n    - "link_description": (string) Link description, ~27 characters (only for Facebook).'


    return f"""
    Based on the following company context:
    <context>
    {context_summary}
    </context>

    Generate {count} versions of {platform} ad content for the objective: "{objective}".
    The destination link for these ads is: {destination_link}
    The Call To Action (CTA) button text should be chosen from: {cta_button_options}. If multiple options, choose the most appropriate. If "empty" is an option, it means the CTA button can be omitted or set to a generic one like "Learn More" if that's also an option.

    Output the result as a JSON object with a single key "{platform.lower()}_{objective.lower().replace(' ', '_')}", which is a list of ad objects.
    Each ad object should have the following keys:
    - "version": (integer) The version number, starting from 1.
    - "ad_name": (string) {ad_name_instruction}
    - "{text_field_name}": (string) {text_field_instruction}
    - "image_copy": (string) Suggested text to overlay on an image or for the visual's concept.
    - "headline": (string) Ad headline, {headline_chars}.{link_desc_field}
    - "cta_button": (string) The chosen CTA button text from the provided options.

    Example of an ad object:
    {{
      "version": 1,
      "ad_name": "CompanyName - {platform} - {objective} - Campaign Q3 - V1",
      "{text_field_name}": "✨ Discover the future of X with our innovative solution! {text_field_instruction specifics}...",
      "image_copy": "Text for image: 'Revolutionize Your Workflow'",
      "headline": "Headline example within char limit",
      "cta_button": "{cta_button_options[0] if cta_button_options else 'Learn More'}"
      {(',"link_description": "Short desc for FB"' if platform == "Facebook" else "")}
    }}
    """

def create_google_search_prompt(context_summary):
    return f"""
    Based on the following company context:
    <context>
    {context_summary}
    </context>

    Generate Google Search Ad copy.
    Provide exactly 15 headlines, each around 30 characters.
    Provide exactly 4 descriptions, each around 90 characters.

    Output the result as a JSON object with two keys: "headlines" (a list of strings) and "descriptions" (a list of strings).

    Example JSON structure:
    {{
      "headlines": [
        "Headline 1 (approx 30 chars)",
        "Headline 2 (approx 30 chars)",
        // ...13 more headlines
      ],
      "descriptions": [
        "Description 1 (approx 90 chars). Drive results.",
        "Description 2 (approx 90 chars). Learn more now.",
        // ...2 more descriptions
      ]
    }}
    """

def create_google_display_prompt(context_summary):
    return f"""
    Based on the following company context:
    <context>
    {context_summary}
    </context>

    Generate Google Display Ad copy.
    Provide exactly 5 short headlines, each around 30 characters.
    Provide exactly 5 long headlines, each around 90 characters (these will be used as descriptions in the XLSX).

    Output the result as a JSON object with two keys: "headlines" (a list of 5 short headline strings) and "descriptions" (a list of 5 long headline/description strings).

    Example JSON structure:
    {{
      "headlines": [
        "Short Headline 1 (30char)",
        // ...4 more short headlines
      ],
      "descriptions": [
        "Long Headline/Description 1 (90char). Discover more today.",
        // ...4 more long headlines/descriptions
      ]
    }}
    """