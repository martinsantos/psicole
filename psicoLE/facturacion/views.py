from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, make_response
from psicoLE.database import db
from .models import Factura, NotaCredito, NotaDebito
from psicoLE.cobranzas.models import Pago
from .forms import InvoiceForm, NotaCreditoForm, NotaDebitoForm
from .services import generate_next_invoice_number, generate_next_credit_note_number, generate_next_debit_note_number
from .pdf import generate_invoice_pdf_weasyprint, generate_credit_note_pdf, generate_debit_note_pdf
from psicoLE.auth.decorators import roles_required
from decimal import Decimal
from datetime import date as dt_date
