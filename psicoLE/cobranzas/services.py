from decimal import Decimal
from datetime import date
from psicoLE.database import db
from psicoLE.profesionales.models import Professional
from .models import Cuota
from sqlalchemy.exc import SQLAlchemyError

def generate_monthly_fees(periodo_str, fecha_vencimiento_date, monto_general_decimal):
    """
    Generates monthly fees (Cuotas) for all active professionals for a given period.

    Args:
        periodo_str (str): The period for the fees (e.g., "YYYY-MM").
        fecha_vencimiento_date (date): The due date for the fees.
        monto_general_decimal (Decimal): The general amount for the fee.

    Returns:
        tuple: (success_count, already_exist_count, error_count)
    """
    active_professionals = Professional.query.filter_by(status_matricula='active').all()
    
    success_count = 0
    already_exist_count = 0
    error_count = 0
    
    if not isinstance(monto_general_decimal, Decimal):
        try:
            monto_general_decimal = Decimal(str(monto_general_decimal))
        except Exception:
            # Consider logging this error
            # For now, if conversion fails, it might lead to issues later or use a fallback
            # This should ideally be validated before calling this service
            raise ValueError("monto_general_decimal must be a Decimal or convertible to Decimal.")

    for prof in active_professionals:
        try:
            existing_cuota = Cuota.query.filter_by(professional_id=prof.id, periodo=periodo_str).first()
            if existing_cuota:
                already_exist_count += 1
                continue

            new_cuota = Cuota(
                professional_id=prof.id,
                periodo=periodo_str,
                monto_esperado=monto_general_decimal,
                fecha_vencimiento=fecha_vencimiento_date,
                fecha_emision=date.today(), # Or pass as arg if needed
                estado='pending'
            )
            db.session.add(new_cuota)
            success_count += 1
        except SQLAlchemyError as e:
            # Log the error e
            db.session.rollback() # Rollback for this specific professional's fee
            error_count += 1
            print(f"Error generating fee for professional {prof.id} for period {periodo_str}: {e}")
        except Exception as e: # Catch other potential errors
            db.session.rollback()
            error_count += 1
            print(f"Unexpected error for professional {prof.id} for period {periodo_str}: {e}")


    if error_count == 0 and success_count > 0: # Only commit if no errors during the loop for new items
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            # Log the error e
            db.session.rollback()
            # If commit fails, all new fees in this batch are rolled back.
            # Set success_count to 0 as the transaction failed.
            error_count += success_count # All successfully added items are now errors due to commit failure
            success_count = 0
            print(f"Error committing fees to database: {e}")
    elif error_count > 0 : # If there were errors, rollback any potential partial adds from before an error.
        db.session.rollback()


    return success_count, already_exist_count, error_count

def update_fee_status_after_payment(cuota_id):
    """
    Updates the status and monto_pagado of a Cuota based on its confirmed payments.

    Args:
        cuota_id (int): The ID of the Cuota to update.

    Returns:
        bool: True if the cuota was updated successfully, False otherwise.
    """
    cuota = Cuota.query.get(cuota_id)
    if not cuota:
        # Log: Cuota not found
        return False

    try:
        # Sum of confirmed payments for this cuota
        total_pagado_confirmado = db.session.query(
            db.func.sum(Pago.monto)
        ).filter(
            Pago.cuota_id == cuota_id,
            Pago.confirmado == True
        ).scalar() or Decimal('0.00') # Ensure Decimal if sum is None

        cuota.monto_pagado = total_pagado_confirmado

        # Update estado
        if cuota.monto_pagado >= cuota.monto_esperado:
            cuota.estado = 'paid'
        elif cuota.monto_pagado > Decimal('0.00') and cuota.monto_pagado < cuota.monto_esperado:
            cuota.estado = 'partially_paid'
        elif cuota.monto_pagado == Decimal('0.00'):
            if cuota.fecha_vencimiento < date.today(): # Check if date object
                cuota.estado = 'overdue'
            else:
                cuota.estado = 'pending'
        # If monto_pagado < 0 (should not happen with validation), it will fall into pending/overdue

        db.session.add(cuota) # Add to session before commit
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        # Log error e
        print(f"Error updating fee status for cuota {cuota_id}: {e}")
        return False
    except Exception as e: # Catch other potential errors
        db.session.rollback()
        print(f"Unexpected error updating fee status for cuota {cuota_id}: {e}")
        return False

def create_mercadopago_preference(cuota, success_url, failure_url, pending_url, notification_url):
    """
    Creates a Mercado Pago payment preference for a given Cuota.
    """
    from psicoLE.main import get_mp_sdk # Import SDK getter
    sdk = get_mp_sdk()
    if not sdk:
        raise Exception("Mercado Pago SDK not initialized. Check configuration.")

    # Calculate remaining balance for the cuota
    remaining_balance = cuota.monto_esperado - cuota.monto_pagado
    if remaining_balance <= Decimal('0.00'):
        raise ValueError("This fee is already paid or has no pending amount.")

    preference_data = {
        "items": [
            {
                "title": f"Pago Cuota Matrícula {cuota.periodo} - PsicoLE",
                "description": f"Cuota profesional ID {cuota.professional_id}, Periodo {cuota.periodo}",
                "quantity": 1,
                "currency_id": "ARS", # Assuming Argentinian Pesos
                "unit_price": float(remaining_balance) # MP expects float
            }
        ],
        "payer": {
            # Payer info can be pre-filled if available
            # "name": cuota.professional.first_name if cuota.professional else None,
            # "surname": cuota.professional.last_name if cuota.professional else None,
            # "email": cuota.professional.email if cuota.professional else None,
            # "phone": {
            #     "area_code": "...",
            #     "number": "..."
            # },
            # "identification": {
            #     "type": "DNI", # or CUIT
            #     "number": "..."
            # },
            # "address": {
            #     "street_name": "...",
            #     "street_number": "...",
            #     "zip_code": "..."
            # }
        },
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url
        },
        "auto_return": "approved", # Automatically return to success URL if payment is approved
        "notification_url": notification_url,
        "external_reference": str(cuota.id), # Must be a string
        # "payment_methods": {
        #     "excluded_payment_types": [
        #         {"id": "ticket"} # Example: exclude offline payments
        #     ],
        #     "installments": 1 # Example: force single installment
        # }
    }
    
    if cuota.professional:
        preference_data["payer"]["name"] = cuota.professional.first_name
        preference_data["payer"]["surname"] = cuota.professional.last_name
        preference_data["payer"]["email"] = cuota.professional.email # Ensure this email is valid for MP

    preference_response = sdk.preference().create(preference_data)
    
    if preference_response["status"] == 201: # 201 Created
        # print("Preference created successfully:", preference_response["response"])
        return {
            "id": preference_response["response"]["id"],
            "init_point": preference_response["response"]["sandbox_init_point"] # Use sandbox_init_point for testing
            # "init_point": preference_response["response"]["init_point"] # For production
        }
    else:
        # Log error: preference_response
        print("Error creating preference:", preference_response)
        error_message = preference_response["response"].get('message', 'Unknown error from Mercado Pago.')
        if 'cause' in preference_response["response"] and preference_response["response"]['cause']:
            error_message += f" Cause: {preference_response['response']['cause']}"
        raise Exception(f"Could not create Mercado Pago preference: {error_message}")
