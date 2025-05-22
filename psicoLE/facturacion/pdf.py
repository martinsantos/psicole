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


def generate_credit_note_pdf(credit_note):
    """
    Generates a PDF for the given credit note object using WeasyPrint.
    Renders an HTML template and converts it to PDF.
    """
    html_string = render_template('facturacion/credit_note_pdf_template.html', credit_note=credit_note)
    html = HTML(string=html_string)
    
    # Basic CSS for the PDF - can be expanded or moved to a file
    # This CSS is very rudimentary and should be enhanced for a production system.
    css_string = """
        body { font-family: sans-serif; font-size: 12px; }
        .container { width: 90%; margin: auto; }
        h1 { text-align: center; color: #333; }
        .header, .client-details, .credit-note-details { margin-bottom: 20px; padding-bottom:10px; border-bottom: 1px solid #eee; }
        .header p, .client-details p, .credit-note-details p { margin: 5px 0; }
        .total { text-align: right; font-weight: bold; font-size: 1.2em; margin-top: 30px; }
        .footer { text-align: center; font-size: 0.8em; color: #777; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    """
    css = CSS(string=css_string)
    
    pdf_bytes = html.write_pdf(stylesheets=[css])
    return pdf_bytes


def generate_debit_note_pdf(debit_note):
    """
    Generates a PDF for the given debit note object using WeasyPrint.
    Renders an HTML template and converts it to PDF.
    """
    html_string = render_template('facturacion/debit_note_pdf_template.html', debit_note=debit_note)
    html = HTML(string=html_string)
    
    # Basic CSS for the PDF - can be shared or customized
    css_string = """
        body { font-family: sans-serif; font-size: 12px; }
        .container { width: 90%; margin: auto; }
        h1 { text-align: center; color: #333; }
        .header, .client-details, .debit-note-details { margin-bottom: 20px; padding-bottom:10px; border-bottom: 1px solid #eee; }
        .header p, .client-details p, .debit-note-details p { margin: 5px 0; }
        .total { text-align: right; font-weight: bold; font-size: 1.2em; margin-top: 30px; }
        .footer { text-align: center; font-size: 0.8em; color: #777; margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    """
    css = CSS(string=css_string)
    
    pdf_bytes = html.write_pdf(stylesheets=[css])
    return pdf_bytes
