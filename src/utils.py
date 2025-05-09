import re
from urllib.parse import urlparse

def validate_url(url):
    """Validate and prepend http:// if scheme is missing."""
    if not url:
        return None
    if not re.match(r'(?:http|ftp|https)://', url):
        return 'http://' + url
    return url

def get_company_name_from_url(url):
    """Extract a company name from a URL."""
    if not url:
        return "company"
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname  # e.g., www.example.com or example.co.uk
        if hostname:
            if hostname.startswith('www.'):
                hostname = hostname[4:]
            # Take the part before the first dot (e.g., 'example' from 'example.com')
            return hostname.split('.')[0]
    except Exception:
        pass
    return "company"

def get_active_lead_objective_link(lead_objective_type, demo_link, sales_link):
    """Returns the correct link based on the selected lead objective type."""
    if lead_objective_type == "Demo Booking":
        return demo_link
    elif lead_objective_type == "Sales Meeting":
        return sales_link
    return "" # Should not happen if inputs are validated