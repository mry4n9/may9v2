import streamlit as st
from src.text_extractor import extract_text_from_url, extract_text_from_pdf, extract_text_from_pptx
from src.openai_handler import (
    get_openai_client, summarize_text_with_ai, generate_content_with_ai,
    create_email_prompt, create_linkedin_facebook_prompt,
    create_google_search_prompt, create_google_display_prompt
)
from src.excel_generator import create_excel_file
from src.utils import validate_url, get_company_name_from_url, get_active_lead_objective_link
import time

st.set_page_config(layout="wide")
st.title("🚀 Branding & Marketing Ad Content Generator")

# --- Inputs ---
st.sidebar.header("Client Context & Materials")
client_url = st.sidebar.text_input("Client's Website URL (e.g., https://www.example.com)")
additional_context_file = st.sidebar.file_uploader("Upload Additional Context (PDF or PPTX)", type=['pdf', 'pptx'])
downloadable_material_file = st.sidebar.file_uploader("Upload Downloadable Lead Material (PDF, Ebook as PDF/PPTX)", type=['pdf', 'pptx'])

st.sidebar.header("Campaign Options & Links")
lead_objective_type = st.sidebar.selectbox("Primary Lead Objective", ["Demo Booking", "Sales Meeting"])
learn_more_link = st.sidebar.text_input("Link for 'Learn More' (Brand Awareness CTAs)")
downloadable_material_link_input = st.sidebar.text_input("Link to Downloadable Material (Demand Gen CTAs)")
demo_booking_link = st.sidebar.text_input("Link for Demo Booking (Demand Capture CTAs)")
sales_meeting_link = st.sidebar.text_input("Link for Sales Meeting (Demand Capture CTAs)")

content_count = st.sidebar.slider("Number of Ad Variations per Objective", 1, 20, 10)

generate_button = st.sidebar.button("✨ Generate Ad Content", type="primary")

# --- Main Area for Progress and Download ---
status_placeholder = st.empty()
progress_bar = st.progress(0)

if generate_button:
    # Validate inputs
    client_url = validate_url(client_url)
    learn_more_link = validate_url(learn_more_link)
    downloadable_material_link_input = validate_url(downloadable_material_link_input)
    demo_booking_link = validate_url(demo_booking_link)
    sales_meeting_link = validate_url(sales_meeting_link)

    active_lead_link = get_active_lead_objective_link(lead_objective_type, demo_booking_link, sales_meeting_link)

    if not client_url:
        st.sidebar.error("Please provide a valid client website URL.")
    # Add more specific link validations if needed (e.g. ensure demo link is provided if demo objective)
    elif not active_lead_link:
        st.sidebar.error(f"Please provide the link for '{lead_objective_type}'.")
    elif not learn_more_link:
        st.sidebar.error("Please provide the 'Learn More' link.")
    elif not downloadable_material_link_input:
        st.sidebar.error("Please provide the link to the downloadable material.")
    else:
        openai_client = get_openai_client()
        if not openai_client:
            st.stop()

        company_name_for_file = get_company_name_from_url(client_url)
        all_summaries = []
        total_steps = 3 + 1 + 3 + 3 + 1 + 1 # Summaries + Email + LinkedIn(3) + Facebook(3) + GSearch + GDisplay
        current_step = 0

        def update_progress(step_increment=1, message=""):
            nonlocal current_step
            current_step += step_increment
            progress_percentage = int((current_step / total_steps) * 100)
            progress_bar.progress(progress_percentage)
            if message:
                status_placeholder.info(f"⏳ {message}")
            time.sleep(0.1) # Small delay for UI update

        # 1. Extract and Summarize Context
        update_progress(0, "Starting content extraction and summarization...")
        if client_url:
            update_progress(0, f"Extracting content from URL: {client_url}...")
            url_text = extract_text_from_url(client_url)
            if url_text and not url_text.startswith("Error"):
                update_progress(0, "Summarizing URL content with AI...")
                url_summary = summarize_text_with_ai(openai_client, url_text, "website content")
                if url_summary: all_summaries.append(f"Website Summary:\n{url_summary}")
            else:
                status_placeholder.warning(f"Could not extract significant content from URL or error occurred: {url_text}")
        update_progress(1) # Step for URL processing

        if additional_context_file:
            update_progress(0, f"Extracting content from additional context file: {additional_context_file.name}...")
            ext = additional_context_file.name.split('.')[-1].lower()
            additional_text = ""
            if ext == 'pdf':
                additional_text = extract_text_from_pdf(additional_context_file)
            elif ext == 'pptx':
                additional_text = extract_text_from_pptx(additional_context_file)
            
            if additional_text and not additional_text.startswith("Error"):
                update_progress(0, "Summarizing additional context with AI...")
                additional_summary = summarize_text_with_ai(openai_client, additional_text, "additional context document")
                if additional_summary: all_summaries.append(f"Additional Context Summary:\n{additional_summary}")
            else:
                 status_placeholder.warning(f"Could not extract text from additional context file or error occurred: {additional_text}")
        update_progress(1) # Step for additional context

        if downloadable_material_file:
            update_progress(0, f"Extracting content from downloadable material: {downloadable_material_file.name}...")
            ext = downloadable_material_file.name.split('.')[-1].lower()
            downloadable_text = ""
            if ext == 'pdf':
                downloadable_text = extract_text_from_pdf(downloadable_material_file)
            elif ext == 'pptx':
                downloadable_text = extract_text_from_pptx(downloadable_material_file)

            if downloadable_text and not downloadable_text.startswith("Error"):
                update_progress(0, "Summarizing downloadable material with AI...")
                # This summary is primarily for context, not just the downloadable itself
                downloadable_summary = summarize_text_with_ai(openai_client, downloadable_text, "downloadable lead material")
                if downloadable_summary: all_summaries.append(f"Downloadable Material Summary:\n{downloadable_summary}")
            else:
                status_placeholder.warning(f"Could not extract text from downloadable material or error occurred: {downloadable_text}")
        update_progress(1) # Step for downloadable material

        if not all_summaries:
            status_placeholder.error("No context could be summarized. Please provide a valid URL or upload context files.")
            st.stop()
        
        comprehensive_context = "\n\n---\n\n".join(all_summaries)
        st.expander("View Comprehensive Context Summary Used for Ad Generation").markdown(comprehensive_context)

        # 2. Generate Ad Content
        ad_data_for_excel = {}
        
        # Email
        update_progress(0, "Generating Email content...")
        email_prompt = create_email_prompt(comprehensive_context, active_lead_link, content_count)
        email_content = generate_content_with_ai(openai_client, email_prompt)
        if email_content and 'emails' in email_content:
            ad_data_for_excel['email'] = email_content['emails']
        else:
            status_placeholder.warning("Failed to generate Email content or received unexpected format.")
        update_progress(1)

        # LinkedIn
        linkedin_ads_all_objectives = []
        linkedin_objectives = {
            "Brand Awareness": {"link": learn_more_link, "cta": ["Learn More", ""]},
            "Demand Gen": {"link": downloadable_material_link_input, "cta": ["Download"]},
            "Demand Capture": {"link": active_lead_link, "cta": ["Register", "Request Demo"]}
        }
        for obj, details in linkedin_objectives.items():
            update_progress(0, f"Generating LinkedIn content for {obj}...")
            prompt = create_linkedin_facebook_prompt("LinkedIn", comprehensive_context, obj, content_count, details["link"], details["cta"])
            content = generate_content_with_ai(openai_client, prompt)
            if content and f'linkedin_{obj.lower().replace(" ", "_")}' in content:
                ads = content[f'linkedin_{obj.lower().replace(" ", "_")}']
                for ad in ads: # Add objective type and destination link for Excel
                    ad['objective_type'] = obj
                    ad['destination_link'] = details["link"]
                linkedin_ads_all_objectives.extend(ads)
            else:
                status_placeholder.warning(f"Failed to generate LinkedIn {obj} content or received unexpected format.")
            update_progress(1)
        if linkedin_ads_all_objectives:
            ad_data_for_excel['linkedin'] = linkedin_ads_all_objectives
        
        # Facebook
        facebook_ads_all_objectives = []
        facebook_objectives = {
            "Brand Awareness": {"link": learn_more_link, "cta": ["Learn More", ""]},
            "Demand Gen": {"link": downloadable_material_link_input, "cta": ["Download"]},
            "Demand Capture": {"link": active_lead_link, "cta": ["Book Now"]}
        }
        for obj, details in facebook_objectives.items():
            update_progress(0, f"Generating Facebook content for {obj}...")
            prompt = create_linkedin_facebook_prompt("Facebook", comprehensive_context, obj, content_count, details["link"], details["cta"])
            content = generate_content_with_ai(openai_client, prompt)
            if content and f'facebook_{obj.lower().replace(" ", "_")}' in content:
                ads = content[f'facebook_{obj.lower().replace(" ", "_")}']
                for ad in ads: # Add objective type and destination link for Excel
                    ad['objective_type'] = obj
                    ad['destination_link'] = details["link"]
                facebook_ads_all_objectives.extend(ads)
            else:
                status_placeholder.warning(f"Failed to generate Facebook {obj} content or received unexpected format.")
            update_progress(1)
        if facebook_ads_all_objectives:
            ad_data_for_excel['facebook'] = facebook_ads_all_objectives

        # Google Search
        update_progress(0, "Generating Google Search content...")
        gsearch_prompt = create_google_search_prompt(comprehensive_context)
        gsearch_content = generate_content_with_ai(openai_client, gsearch_prompt)
        if gsearch_content and 'headlines' in gsearch_content and 'descriptions' in gsearch_content:
            ad_data_for_excel['google_search'] = gsearch_content
        else:
            status_placeholder.warning("Failed to generate Google Search content or received unexpected format.")
        update_progress(1)

        # Google Display
        update_progress(0, "Generating Google Display content...")
        gdisplay_prompt = create_google_display_prompt(comprehensive_context)
        gdisplay_content = generate_content_with_ai(openai_client, gdisplay_prompt)
        # The prompt for GDisplay asks for "descriptions" which are long headlines.
        if gdisplay_content and 'headlines' in gdisplay_content and 'descriptions' in gdisplay_content:
            ad_data_for_excel['google_display'] = gdisplay_content
        else:
            status_placeholder.warning("Failed to generate Google Display content or received unexpected format.")
        update_progress(1)
        
        # 3. Create Excel File
        if ad_data_for_excel:
            status_placeholder.info("✅ All content generated. Creating Excel file...")
            progress_bar.progress(100)
            
            user_links_for_excel = {
                "learn_more_link": learn_more_link,
                "downloadable_material_link": downloadable_material_link_input,
                "demo_booking_link": demo_booking_link,
                "sales_meeting_link": sales_meeting_link,
                "active_lead_objective_link": active_lead_link
            }

            excel_bytes = create_excel_file(ad_data_for_excel, company_name_for_file, user_links_for_excel)
            
            st.sidebar.download_button(
                label="📥 Download Ad Content XLSX",
                data=excel_bytes,
                file_name=f"{company_name_for_file}_ads_creative.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            status_placeholder.success(f"🎉 Excel file '{company_name_for_file}_ads_creative.xlsx' is ready for download from the sidebar!")
        else:
            status_placeholder.error("Could not generate any ad content. Please check the context and try again.")
            progress_bar.progress(0)

# Add some instructions or information
st.markdown("""
---
### How to Use:
1.  **Provide Context:** Enter your client's website URL. Optionally, upload PDF/PPTX files for additional company context or the content of a downloadable lead magnet (like a white paper or ebook).
2.  **Set Campaign Options:**
    *   Choose the primary `Lead Objective` (Demo Booking or Sales Meeting). This influences the main call-to-action link in some ads.
    *   Provide specific URLs for:
        *   `Learn More`: Used for Brand Awareness ads.
        *   `Downloadable Material`: Used for Demand Generation ads (e.g., link to a white paper landing page).
        *   `Demo Booking`: Used if "Demo Booking" is the lead objective.
        *   `Sales Meeting`: Used if "Sales Meeting" is the lead objective.
    *   Select the `Number of Ad Variations` to generate for Email, LinkedIn, and Facebook objectives. Google Ads will have a fixed number of variations.
3.  **Generate:** Click "Generate Ad Content". The app will extract text, summarize it using AI, and then generate tailored ad copy.
4.  **Download:** Once complete, an XLSX file will be available for download from the sidebar.

**XLSX File Structure:**
The Excel file will contain separate sheets for:
*   Email Ads
*   LinkedIn Ads (covering Brand Awareness, Demand Gen, Demand Capture)
*   Facebook Ads (covering Brand Awareness, Demand Gen, Demand Capture)
*   Google Search Ads
*   Google Display Ads

Styling (black header, white font, centered text, borders, etc.) is applied as per specifications.
""")