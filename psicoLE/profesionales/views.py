from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, current_app, send_from_directory
from flask_login import current_user
from sqlalchemy import func, case
import os
from psicoLE.database import db
from .models import Professional, DocumentoProfesional
from .forms import ProfessionalForm, ProfessionalFilterForm, SpecializationReportFilterForm
from .pdf import generate_register_pdf 
from psicoLE.auth.decorators import roles_required
