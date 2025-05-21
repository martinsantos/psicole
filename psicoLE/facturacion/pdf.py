from flask import render_template
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration # For potential font issues
import os # For path handling if needed

def generate_invoice_pdf_weasyprint(factura):
    """
    Generates a PDF for the given invoice object using WeasyPrint.
    Renders an HTML template and converts it to PDF.
    """
    # It's good practice to make paths absolute if templates are in non-standard locations
    # For Flask, render_template usually handles this if templates are in the app's template folder
    # or a blueprint's template folder.
    
    # Example: Constructing path to a shared CSS file if needed
    # css_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'invoice_pdf.css')
    # For now, we'll assume simple inline styles or a very basic template that doesn't need external CSS.
    
    html_string = render_template('facturacion/invoice_pdf_template.html', factura=factura)
    
    # font_config = FontConfiguration() # Use if you have font issues on the server
    # html = HTML(string=html_string, base_url=request.host_url) # base_url for relative paths in HTML
    html = HTML(string=html_string) # Simpler if no relative paths to static assets in PDF template

    # stylesheets = [CSS(css_path)] if os.path.exists(css_path) else []
    # pdf_bytes = html.write_pdf(stylesheets=stylesheets, font_config=font_config)
    pdf_bytes = html.write_pdf() # No external CSS for now

    return pdf_bytes
