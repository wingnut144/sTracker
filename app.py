# Updated Notification System for app.py
# Replace the send_sms() function with these functions

import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_signal_message(phone_number, message):
    """
    Send message via Signal-CLI REST API
    Returns: (success: bool, method: str, error: str or None)
    """
    try:
        signal_api_url = os.environ.get('SIGNAL_API_URL', 'http://signal:8080')
        signal_number = os.environ.get('SIGNAL_NUMBER')
        
        if not signal_number:
            logger.warning("SIGNAL_NUMBER not configured, skipping Signal")
            return False, 'signal', 'Signal number not configured'
        
        # Format phone number (remove any non-digits except leading +)
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # Send via Signal API
        url = f"{signal_api_url}/v2/send"
        payload = {
            "message": message,
            "number": signal_number,
            "recipients": [phone_number]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 201:
            logger.info(f"✅ Signal message sent successfully to {phone_number}")
            return True, 'signal', None
        else:
            error_msg = f"Signal API returned {response.status_code}: {response.text}"
            logger.warning(f"⚠️ Signal failed: {error_msg}")
            return False, 'signal', error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Signal API timeout"
        logger.warning(f"⚠️ {error_msg}")
        return False, 'signal', error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Cannot connect to Signal service"
        logger.warning(f"⚠️ {error_msg}")
        return False, 'signal', error_msg
    except Exception as e:
        error_msg = f"Signal error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return False, 'signal', error_msg


def send_twilio_sms(phone_number, message):
    """
    Send SMS via Twilio
    Returns: (success: bool, method: str, error: str or None)
    """
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, twilio_number]):
            logger.warning("Twilio not configured, skipping SMS")
            return False, 'twilio', 'Twilio credentials not configured'
        
        client = Client(account_sid, auth_token)
        
        sms = client.messages.create(
            body=message,
            from_=twilio_number,
            to=phone_number
        )
        
        logger.info(f"✅ Twilio SMS sent successfully to {phone_number} (SID: {sms.sid})")
        return True, 'twilio', None
        
    except ImportError:
        error_msg = "Twilio library not installed"
        logger.error(f"❌ {error_msg}")
        return False, 'twilio', error_msg
    except Exception as e:
        error_msg = f"Twilio error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return False, 'twilio', error_msg


def send_notification_message(phone_number, message):
    """
    Smart notification sender: tries Signal first, falls back to Twilio
    Returns: (success: bool, method_used: str, error: str or None)
    """
    logger.info(f"📱 Attempting to send notification to {phone_number}")
    
    # Try Signal first
    logger.info("Trying Signal-CLI...")
    success, method, error = send_signal_message(phone_number, message)
    
    if success:
        return True, method, None
    
    # Signal failed, try Twilio
    logger.info("Signal failed, falling back to Twilio...")
    success, method, error = send_twilio_sms(phone_number, message)
    
    if success:
        return True, method, None
    
    # Both failed
    logger.error(f"❌ All notification methods failed for {phone_number}")
    return False, 'none', 'Both Signal and Twilio failed'


# Update the notify_partner function to use the new system
def notify_partner(current_user_id, encounter_id, notification_type, message):
    """
    Notify partner about new encounter or comment
    Uses Signal first, falls back to Twilio
    """
    user = User.query.get(current_user_id)
    
    if not user or not user.partner_id:
        return
    
    partner = User.query.get(user.partner_id)
    if not partner:
        return
    
    # Create in-app notification (always works)
    create_notification(partner.id, encounter_id, notification_type, message)
    
    # Send external notification if enabled and phone number exists
    if partner.sms_notifications and partner.phone_number:
        success, method, error = send_notification_message(partner.phone_number, message)
        
        if success:
            logger.info(f"✅ Partner notified via {method}: {partner.username}")
        else:
            logger.warning(f"⚠️ Failed to notify partner {partner.username}: {error}")
    else:
        logger.info(f"ℹ️ External notifications disabled for {partner.username}")
