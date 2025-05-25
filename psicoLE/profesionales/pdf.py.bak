from flask import render_template
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration
import datetime

def generate_register_pdf(professionals_list, filter_params):
    """
    Generates a PDF byte string for the professional register.

    Args:
        professionals_list: List of Professional objects.
        filter_params: Dictionary of filter parameters applied.
    Returns:
        bytes: The generated PDF as a byte string.
    """
    
    # Prepare filter display string
    filters_applied = []
    if filter_params.get('search'):
        filters_applied.append(f"Search: '{filter_params['search']}'")
    if filter_params.get('status_matricula'):
        filters_applied.append(f"Status: {filter_params['status_matricula'].title()}")
    else: # Default status if not explicitly set
        filters_applied.append("Status: Active")
    if filter_params.get('title'):
        filters_applied.append(f"Title: '{filter_params['title']}'")
    if filter_params.get('specialization'):
        filters_applied.append(f"Specialization: '{filter_params['specialization']}'")
    if filter_params.get('university'):
        filters_applied.append(f"University: '{filter_params['university']}'")
    
    filter_summary = ", ".join(filters_applied) if filters_applied else "None"

    # Render the HTML template for PDF
    rendered_html = render_template(
        'profesionales/professional_register_pdf_template.html',
        professionals=professionals_list,
        filter_summary=filter_summary,
        current_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # Use WeasyPrint to convert HTML to PDF
    font_config = FontConfiguration()
    css_string = """
        @page { size: A4 landscape; margin: 1cm; }
        body { font-family: sans-serif; font-size: 9pt; }
        h1 { text-align: center; color: #333; font-size: 16pt; margin-bottom: 5px;}
        h2 { text-align: center; color: #555; font-size: 10pt; margin-top: 0; margin-bottom: 10px;}
        .meta-info { text-align: center; font-size: 8pt; margin-bottom: 15px; color: #666; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ccc; padding: 4px; text-align: left; }
        th { background-color: #f2f2f2; font-size: 10pt; }
        .badge { 
            padding: 0.2em 0.4em; 
            font-size: 0.75em; 
            font-weight: 700; 
            line-height: 1; 
            color: #fff; 
            text-align: center; 
            white-space: nowrap; 
            vertical-align: baseline; 
            border-radius: 0.25rem;
        }
        .bg-success { background-color: #28a745 !important; }
        .bg-warning { background-color: #ffc107 !important; color: #000 !important; }
        .bg-danger { background-color: #dc3545 !important; }
        .bg-secondary { background-color: #6c757d !important; }
        /* Add more specific styles if needed */
    """
    css = CSS(string=css_string, font_config=font_config)
    
    pdf_bytes = HTML(string=rendered_html).write_pdf(stylesheets=[css], font_config=font_config)
    
    return pdf_bytes
