from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import secrets
import logging
import requests
from werkzeug.security import generate_password_hash, check_password_hash

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Database configuration - supports both PostgreSQL and SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///data/intimate_tracker.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max

# Session cookie configuration
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'funtracker_session'
app.config['PERMANENT_SESSION_LIFETIME'] = 7200  # 2 hours

db = SQLAlchemy(app)

# ============================================================================
# CONTEXT PROCESSORS - Make variables available to all templates
# ============================================================================

@app.context_processor
def inject_positions():
    """Make positions dictionary available to all templates"""
    return {
        'positions': {
            'missionary': 'Missionary',
            'doggy': 'Doggy Style',
            'cowgirl': 'Cowgirl',
            'reverse_cowgirl': 'Reverse Cowgirl',
            'spoon': 'Spooning',
            'standing': 'Standing',
            'oral': 'Oral',
            '69': '69',
            'other': 'Other'
        }
    }

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # Partner system
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    partner_code = db.Column(db.String(20), unique=True, nullable=True)
    
    # Profile information
    full_name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    private_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    encounters = db.relationship('Encounter', backref='user', lazy=True, cascade='all, delete-orphan')
    comments_made = db.relationship('Comment', foreign_keys='Comment.commenter_id', backref='commenter', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    proposed_encounters = db.relationship('ProposedEncounter', foreign_keys='ProposedEncounter.proposer_id', backref='proposer', lazy=True)

class Encounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=True)
    position = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # in minutes
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='encounter', lazy=True, cascade='all, delete-orphan')

class ProposedEncounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proposer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    proposed_date = db.Column(db.Date, nullable=False)
    proposed_time = db.Column(db.Time, nullable=True)
    position = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, declined, cancelled
    decline_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'), nullable=False)
    commenter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'), nullable=True)
    proposed_encounter_id = db.Column(db.Integer, db.ForeignKey('proposed_encounter.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)  # 'new_encounter', 'new_comment', 'proposal', 'proposal_confirmed', 'proposal_declined'
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomIcon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position_name = db.Column(db.String(50), nullable=False)
    svg_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message_text = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EncounterRating(db.Model):
    __tablename__ = 'encounter_rating'
    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
# ============================================================================
# NOTIFICATION SYSTEM - Signal + Twilio with Smart Fallback
# ============================================================================

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
        
        # Format phone number
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


def create_notification(user_id, notification_type, message, encounter_id=None, proposed_encounter_id=None):
    """Create in-app notification"""
    notification = Notification(
        user_id=user_id,
        encounter_id=encounter_id,
        proposed_encounter_id=proposed_encounter_id,
        type=notification_type,
        message=message
    )
    db.session.add(notification)
    db.session.commit()


def notify_partner(current_user_id, notification_type, message, encounter_id=None, proposed_encounter_id=None):
    """
    Notify partner about new encounter, comment, or proposal
    Uses Signal first, falls back to Twilio
    """
    user = User.query.get(current_user_id)
    
    if not user or not user.partner_id:
        return
    
    partner = User.query.get(user.partner_id)
    if not partner:
        return
    
    # Create in-app notification (always works)
    create_notification(partner.id, notification_type, message, encounter_id, proposed_encounter_id)
    
    # Send external notification if enabled and phone number exists
    if partner.sms_notifications and partner.phone_number:
        success, method, error = send_notification_message(partner.phone_number, message)
        
        if success:
            logger.info(f"✅ Partner notified via {method}: {partner.username}")
        else:
            logger.warning(f"⚠️ Failed to notify partner {partner.username}: {error}")
    else:
        logger.info(f"ℹ️ External notifications disabled for {partner.username}")

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and check_password_hash(user.password_hash, data['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = True
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Invalid credentials'})
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'error': 'Username already exists'})
    
    new_user = User(
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        partner_code=secrets.token_urlsafe(12)  # Generate unique code
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    session['username'] = new_user.username
    session.permanent = True
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('calendar.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    partner = User.query.get(user.partner_id) if user.partner_id else None  # ✅ Get partner
    return render_template('profile.html', user=user, partner=partner)  # ✅ Pass both

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('admin.html')

@app.route('/proposals')
def proposals():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('proposals.html')

# ============================================================================
# API ROUTES - Profile & Partner Management
# ============================================================================

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    partner = User.query.get(user.partner_id) if user.partner_id else None
    
    return jsonify({
        'username': user.username,
        'full_name': user.full_name or '',
        'phone_number': user.phone_number or '',
        'sms_notifications': user.sms_notifications,
        'private_notes': user.private_notes or '',
        'partner_code': user.partner_code,
        'partner_username': partner.username if partner else None,
        'partner_connected': partner is not None
    })

@app.route('/api/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    user.full_name = data.get('full_name', '')
    user.phone_number = data.get('phone_number', '')
    user.sms_notifications = data.get('sms_notifications', False)
    user.private_notes = data.get('private_notes', '')
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/connect-partner', methods=['POST'])
def connect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    code = data.get('partner_code', '').strip()
    
    user = User.query.get(session['user_id'])
    
    # Don't allow connecting to self
    if code == user.partner_code:
        return jsonify({'success': False, 'error': 'Cannot connect to your own code'})
    
    # Find partner by code
    partner = User.query.filter_by(partner_code=code).first()
    
    if not partner:
        return jsonify({'success': False, 'error': 'Invalid partner code'})
    
    # Create bidirectional connection
    user.partner_id = partner.id
    partner.partner_id = user.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'partner_username': partner.username
    })

@app.route('/api/disconnect-partner', methods=['POST'])
def disconnect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    
    if user.partner_id:
        partner = User.query.get(user.partner_id)
        
        # Remove bidirectional connection
        user.partner_id = None
        if partner:
            partner.partner_id = None
        
        db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Proposed Encounters (Scheduling)
# ============================================================================

@app.route('/api/proposed-encounters', methods=['GET'])
def get_proposed_encounters():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all proposals where user is either proposer or partner
    proposals = ProposedEncounter.query.filter(
        (ProposedEncounter.proposer_id == session['user_id']) |
        (ProposedEncounter.partner_id == session['user_id'])
    ).order_by(ProposedEncounter.proposed_date.desc()).all()
    
    return jsonify([{
        'id': p.id,
        'proposer_id': p.proposer_id,
        'partner_id': p.partner_id,
        'proposer_username': User.query.get(p.proposer_id).username,
        'partner_username': User.query.get(p.partner_id).username,
        'proposed_date': p.proposed_date.isoformat(),
        'proposed_time': p.proposed_time.isoformat() if p.proposed_time else None,
        'position': p.position,
        'notes': p.notes,
        'status': p.status,
        'decline_reason': p.decline_reason,
        'created_at': p.created_at.isoformat(),
        'responded_at': p.responded_at.isoformat() if p.responded_at else None,
        'is_own': p.proposer_id == session['user_id']
    } for p in proposals])

@app.route('/api/proposed-encounters', methods=['POST'])
def create_proposal():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Get user's partner
    user = User.query.get(session['user_id'])
    if not user.partner_id:
        return jsonify({'error': 'No partner connected'}), 400
    
    proposal = ProposedEncounter(
        proposer_id=session['user_id'],
        partner_id=user.partner_id,
        proposed_date=datetime.fromisoformat(data['proposed_date']).date(),
        proposed_time=datetime.fromisoformat(data['proposed_time']).time() if data.get('proposed_time') else None,
        position=data.get('position'),
        notes=data.get('notes', '')
    )
    
    db.session.add(proposal)
    db.session.commit()
    
    # Notify partner
    date_str = proposal.proposed_date.strftime('%B %d, %Y')
    time_str = proposal.proposed_time.strftime('%I:%M %p') if proposal.proposed_time else 'anytime'
    message = f"📅 {user.username} proposed getting together on {date_str} at {time_str}"
    
    notify_partner(session['user_id'], 'proposal', message, proposed_encounter_id=proposal.id)
    
    return jsonify({
        'id': proposal.id,
        'success': True
    })

@app.route('/api/proposed-encounters/<int:proposal_id>/confirm', methods=['POST'])
def confirm_proposal(proposal_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    proposal = ProposedEncounter.query.get(proposal_id)
    
    if not proposal:
        return jsonify({'error': 'Proposal not found'}), 404
    
    # Only partner can confirm
    if proposal.partner_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Can only confirm pending proposals
    if proposal.status != 'pending':
        return jsonify({'error': 'Proposal already responded to'}), 400
    
    proposal.status = 'confirmed'
    proposal.responded_at = datetime.utcnow()
    db.session.commit()
    
    # Notify proposer
    user = User.query.get(session['user_id'])
    date_str = proposal.proposed_date.strftime('%B %d, %Y')
    time_str = proposal.proposed_time.strftime('%I:%M %p') if proposal.proposed_time else 'anytime'
    message = f"✅ {user.username} confirmed your proposal for {date_str} at {time_str}"
    
    notify_partner(session['user_id'], 'proposal_confirmed', message, proposed_encounter_id=proposal.id)
    
    return jsonify({'success': True})

@app.route('/api/proposed-encounters/<int:proposal_id>/decline', methods=['POST'])
def decline_proposal(proposal_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    proposal = ProposedEncounter.query.get(proposal_id)
    
    if not proposal:
        return jsonify({'error': 'Proposal not found'}), 404
    
    # Only partner can decline
    if proposal.partner_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Can only decline pending proposals
    if proposal.status != 'pending':
        return jsonify({'error': 'Proposal already responded to'}), 400
    
    data = request.get_json()
    reason = data.get('reason', '')
    
    proposal.status = 'declined'
    proposal.decline_reason = reason
    proposal.responded_at = datetime.utcnow()
    db.session.commit()
    
    # Notify proposer
    user = User.query.get(session['user_id'])
    date_str = proposal.proposed_date.strftime('%B %d, %Y')
    reason_text = f" Reason: {reason}" if reason else ""
    message = f"❌ {user.username} declined your proposal for {date_str}.{reason_text}"
    
    notify_partner(session['user_id'], 'proposal_declined', message, proposed_encounter_id=proposal.id)
    
    return jsonify({'success': True})

@app.route('/api/proposed-encounters/<int:proposal_id>', methods=['DELETE'])
def cancel_proposal(proposal_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    proposal = ProposedEncounter.query.get(proposal_id)
    
    if not proposal:
        return jsonify({'error': 'Proposal not found'}), 404
    
    # Only proposer can cancel
    if proposal.proposer_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Can only cancel pending proposals
    if proposal.status != 'pending':
        return jsonify({'error': 'Cannot cancel non-pending proposal'}), 400
    
    proposal.status = 'cancelled'
    db.session.commit()
    
    # Notify partner
    user = User.query.get(session['user_id'])
    date_str = proposal.proposed_date.strftime('%B %d, %Y')
    message = f"🚫 {user.username} cancelled their proposal for {date_str}"
    
    notify_partner(session['user_id'], 'proposal_cancelled', message, proposed_encounter_id=proposal.id)
    
    return jsonify({'success': True})

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('messages.html')

# ============================================================================
# API ROUTES - Notifications
# ============================================================================

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    notifications = Notification.query.filter_by(
        user_id=session['user_id']
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    unread_count = Notification.query.filter_by(
        user_id=session['user_id'],
        read=False
    ).count()
    
    return jsonify({
        'notifications': [{
            'id': n.id,
            'type': n.type,
            'message': n.message,
            'read': n.read,
            'encounter_id': n.encounter_id,
            'proposed_encounter_id': n.proposed_encounter_id,
            'created_at': n.created_at.isoformat()
        } for n in notifications],
        'unread_count': unread_count
    })

@app.route('/api/notifications/unread_count', methods=['GET'])  # ← NEW ENDPOINT
def get_unread_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    unread_count = Notification.query.filter_by(
        user_id=session['user_id'],
        read=False
    ).count()
    
    return jsonify({'count': unread_count})

@app.route('/api/notifications/<int:notification_id>/mark-read', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    notification = Notification.query.get(notification_id)
    
    if notification and notification.user_id == session['user_id']:
        notification.read = True
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Notification not found'}), 404

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    Notification.query.filter_by(
        user_id=session['user_id'],
        read=False
    ).update({'read': True})
    
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Encounters
# ============================================================================

@app.route('/api/encounters', methods=['GET'])
def get_encounters():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get encounters for current user and partner (if connected)
    user = User.query.get(session['user_id'])
    user_ids = [user.id]
    if user.partner_id:
        user_ids.append(user.partner_id)
    
    encounters = Encounter.query.filter(
        Encounter.user_id.in_(user_ids)
    ).all()
    
    # Position names mapping
    positions_dict = {
        'missionary': 'Missionary',
        'doggy': 'Doggy Style',
        'cowgirl': 'Cowgirl',
        'reverse_cowgirl': 'Reverse Cowgirl',
        'spoon': 'Spooning',
        'standing': 'Standing',
        'oral': 'Oral',
        '69': '69',
        'other': 'Other'
    }
    
    return jsonify([{
        'id': e.id,
        'date': e.date.isoformat(),
        'time': e.time.isoformat() if e.time else None,
        'position': e.position,
        'position_name': positions_dict.get(e.position, 'Other'),  # ← ADD THIS
        'duration': e.duration,
        'rating': e.rating,
        'notes': e.notes,
        'user_id': e.user_id,
        'is_own': e.user_id == session['user_id'],
        'username': User.query.get(e.user_id).username
    } for e in encounters])

@app.route('/api/encounters/<int:encounter_id>', methods=['GET'])
def get_encounter_details(encounter_id):
    """Get single encounter with all details, ratings, and comments"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    
    if not encounter:
        return jsonify({'error': 'Encounter not found'}), 404
    
    user = User.query.get(session['user_id'])
    
    # Check access: owner or partner only
    if encounter.user_id != session['user_id'] and user.partner_id != encounter.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    encounter_user = User.query.get(encounter.user_id)
    
    # Get both ratings
    creator_rating_obj = EncounterRating.query.filter_by(
        encounter_id=encounter_id,
        user_id=encounter.user_id
    ).first()
    
    partner_rating_obj = None
    partner_username = None
    if user.partner_id:
        partner_rating_obj = EncounterRating.query.filter_by(
            encounter_id=encounter_id,
            user_id=user.partner_id
        ).first()
        partner = User.query.get(user.partner_id)
        partner_username = partner.username if partner else None
    
    # Get comments with usernames
    comments = Comment.query.filter_by(encounter_id=encounter_id).order_by(Comment.created_at.asc()).all()
    
    # Position names mapping
    positions_dict = {
        'missionary': 'Missionary',
        'doggy': 'Doggy Style',
        'cowgirl': 'Cowgirl',
        'reverse_cowgirl': 'Reverse Cowgirl',
        'spoon': 'Spooning',
        'standing': 'Standing',
        'oral': 'Oral',
        '69': '69',
        'other': 'Other'
    }
    
    return jsonify({
        'id': encounter.id,
        'date': encounter.date.isoformat(),
        'time': encounter.time.isoformat() if encounter.time else None,
        'position': encounter.position,
        'position_name': positions_dict.get(encounter.position, 'Other'),
        'duration': encounter.duration,
        'notes': encounter.notes,
        'username': encounter_user.username,
        'is_own': encounter.user_id == session['user_id'],
        'creator_rating': {
            'value': creator_rating_obj.rating if creator_rating_obj else None,
            'username': encounter_user.username,
            'user_id': encounter.user_id,
            'can_edit': encounter.user_id == session['user_id']
        },
        'partner_rating': {
            'value': partner_rating_obj.rating if partner_rating_obj else None,
            'username': partner_username,
            'user_id': user.partner_id,
            'can_edit': user.partner_id == session['user_id']
        } if user.partner_id else None,
        'comments': [{
            'id': c.id,
            'user': User.query.get(c.commenter_id).username,
            'user_id': c.commenter_id,
            'text': c.text,
            'rating': c.rating,
            'created_at': c.created_at.isoformat(),
            'is_own': c.commenter_id == session['user_id']
        } for c in comments]
    })

@app.route('/api/encounters/<int:encounter_id>/rating', methods=['POST'])
def rate_encounter(encounter_id):
    """Add or update rating for an encounter"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    if not encounter:
        return jsonify({'error': 'Encounter not found'}), 404
    
    user = User.query.get(session['user_id'])
    
    # Check access: owner or partner only
    if encounter.user_id != session['user_id'] and user.partner_id != encounter.user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    rating_value = data.get('rating')
    
    if not rating_value or not (1 <= rating_value <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Check if rating already exists
    existing_rating = EncounterRating.query.filter_by(
        encounter_id=encounter_id,
        user_id=session['user_id']
    ).first()
    
    if existing_rating:
        existing_rating.rating = rating_value
    else:
        new_rating = EncounterRating(
            encounter_id=encounter_id,
            user_id=session['user_id'],
            rating=rating_value
        )
        db.session.add(new_rating)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/encounters', methods=['POST'])
def add_encounter():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Convert empty strings to None for integer fields
    duration = data.get('duration')
    if duration == '':
        duration = None
    elif duration:
        duration = int(duration)
    
    rating = data.get('rating')
    if rating == '':
        rating = None
    elif rating:
        rating = int(rating)
    
    new_encounter = Encounter(
        user_id=session['user_id'],
        date=datetime.fromisoformat(data['date']).date(),
        time=datetime.fromisoformat(data['time']).time() if data.get('time') else None,
        position=data['position'],
        duration=duration,
        rating=rating,
        notes=data.get('notes', '')
    )
    
    db.session.add(new_encounter)
    db.session.commit()
    
    # Notify partner
    user = User.query.get(session['user_id'])
    if user.partner_id:
        message = f"💕 {user.username} added a new intimate moment"
        notify_partner(session['user_id'], 'new_encounter', message, encounter_id=new_encounter.id)
    
    return jsonify({
        'id': new_encounter.id,
        'success': True
    })

@app.route('/api/encounters/<int:encounter_id>', methods=['PUT'])
def update_encounter(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    
    if not encounter or encounter.user_id != session['user_id']:
        return jsonify({'error': 'Encounter not found'}), 404
    
    data = request.get_json()
    
    encounter.date = datetime.fromisoformat(data['date']).date()
    encounter.time = datetime.fromisoformat(data['time']).time() if data.get('time') else None
    encounter.position = data['position']
    encounter.duration = data.get('duration')
    encounter.rating = data.get('rating')
    encounter.notes = data.get('notes', '')
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/encounters/<int:encounter_id>', methods=['DELETE'])
def delete_encounter(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    
    if not encounter or encounter.user_id != session['user_id']:
        return jsonify({'error': 'Encounter not found'}), 404
    
    # Delete associated notifications first
    Notification.query.filter_by(encounter_id=encounter_id).delete()
    
    db.session.delete(encounter)
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Comments
# ============================================================================

@app.route('/api/encounters/<int:encounter_id>/comments', methods=['GET'])
def get_comments(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    
    if not encounter:
        return jsonify({'error': 'Encounter not found'}), 404
    
    # Check if user has access (owner or partner)
    user = User.query.get(session['user_id'])
    if encounter.user_id != session['user_id'] and encounter.user_id != user.partner_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    comments = Comment.query.filter_by(encounter_id=encounter_id).order_by(Comment.created_at.asc()).all()
    
    return jsonify([{
        'id': c.id,
        'text': c.text,
        'rating': c.rating,
        'commenter_username': User.query.get(c.commenter_id).username,
        'is_own': c.commenter_id == session['user_id'],
        'created_at': c.created_at.isoformat()
    } for c in comments])

@app.route('/api/encounters/<int:encounter_id>/comments', methods=['POST'])
def add_comment(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get(encounter_id)
    
    if not encounter:
        return jsonify({'error': 'Encounter not found'}), 404
    
    # Check if user has access (owner or partner)
    user = User.query.get(session['user_id'])
    if encounter.user_id != session['user_id'] and encounter.user_id != user.partner_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    comment = Comment(
        encounter_id=encounter_id,
        commenter_id=session['user_id'],
        text=data['text'],
        rating=data.get('rating')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Notify encounter owner if comment is from partner
    if encounter.user_id != session['user_id']:
        message = f"💬 {user.username} commented on your intimate moment"
        notify_partner(session['user_id'], 'new_comment', message, encounter_id=encounter_id)
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Statistics
# ============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get encounters for current user and partner
    user = User.query.get(session['user_id'])
    user_ids = [user.id]
    if user.partner_id:
        user_ids.append(user.partner_id)
    
    all_encounters = Encounter.query.filter(Encounter.user_id.in_(user_ids)).all()
    
    # This month
    first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = Encounter.query.filter(
        Encounter.user_id.in_(user_ids),
        Encounter.date >= first_day.date()
    ).count()
    
    # Average rating
    ratings = [e.rating for e in all_encounters if e.rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Pending proposals
    pending_proposals = ProposedEncounter.query.filter(
        ProposedEncounter.partner_id == session['user_id'],
        ProposedEncounter.status == 'pending'
    ).count()
    
    return jsonify({
        'total': len(all_encounters),
        'this_month': this_month,
        'average_rating': round(avg_rating, 1),
        'pending_proposals': pending_proposals
    })

# ============================================================================
# API ROUTES - Custom Icons
# ============================================================================

@app.route('/api/custom-icons', methods=['GET'])
def get_custom_icons():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    icons = CustomIcon.query.filter_by(user_id=session['user_id']).all()
    
    return jsonify([{
        'position_name': icon.position_name,
        'svg_content': icon.svg_content
    } for icon in icons])

@app.route('/api/custom-icons', methods=['POST'])
def upload_custom_icon():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    position_name = data.get('position_name')
    svg_content = data.get('svg_content', '')
    
    # Validate SVG
    if not svg_content.strip().startswith('<svg') or not svg_content.strip().endswith('</svg>'):
        return jsonify({'error': 'Invalid SVG format'}), 400
    
    # Check if icon already exists
    existing_icon = CustomIcon.query.filter_by(
        user_id=session['user_id'],
        position_name=position_name
    ).first()
    
    if existing_icon:
        # Update existing
        existing_icon.svg_content = svg_content
    else:
        # Create new
        new_icon = CustomIcon(
            user_id=session['user_id'],
            position_name=position_name,
            svg_content=svg_content
        )
        db.session.add(new_icon)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/custom-icons/<position_name>', methods=['DELETE'])
def delete_custom_icon(position_name):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    icon = CustomIcon.query.filter_by(
        user_id=session['user_id'],
        position_name=position_name
    ).first()
    
    if icon:
        db.session.delete(icon)
        db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Messages
# ============================================================================

@app.route('/api/messages', methods=['GET'])
def get_messages():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get all messages where user is sender or recipient
    sent_messages = Message.query.filter_by(sender_id=session['user_id']).all()
    received_messages = Message.query.filter_by(recipient_id=session['user_id']).all()
    
    def format_message(msg, is_sent=False):
        if is_sent:
            other_user = User.query.get(msg.recipient_id)
            other_label = 'To'
        else:
            other_user = User.query.get(msg.sender_id)
            other_label = 'From'
        
        return {
            'id': msg.id,
            'subject': msg.subject or '(No subject)',
            'message': msg.message_text,
            'read': msg.read,
            'created_at': msg.created_at.isoformat(),
            'is_sent': is_sent,
            'other_user': other_user.username if other_user else 'Unknown',
            'other_label': other_label
        }
    
    all_messages = []
    all_messages.extend([format_message(m, is_sent=True) for m in sent_messages])
    all_messages.extend([format_message(m, is_sent=False) for m in received_messages])
    
    # Sort by created_at descending
    all_messages.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Count unread
    unread_count = Message.query.filter_by(
        recipient_id=session['user_id'],
        read=False
    ).count()
    
    return jsonify({
        'messages': all_messages,
        'unread_count': unread_count
    })

@app.route('/api/messages', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user.partner_id:
        return jsonify({'error': 'No partner connected'}), 400
    
    data = request.get_json()
    
    new_message = Message(
        sender_id=session['user_id'],
        recipient_id=user.partner_id,
        subject=data.get('subject', ''),
        message_text=data.get('message', '')
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Create notification for recipient
    sender = User.query.get(session['user_id'])
    notification_msg = f"💌 New message from {sender.username}"
    if data.get('subject'):
        notification_msg += f": {data.get('subject')}"
    
    create_notification(
        user.partner_id,
        'new_message',
        notification_msg
    )
    
    # Send external notification if enabled
    partner = User.query.get(user.partner_id)
    if partner.sms_notifications and partner.phone_number:
        send_notification_message(partner.phone_number, notification_msg)
    
    return jsonify({'success': True, 'id': new_message.id})

@app.route('/api/messages/<int:message_id>/mark-read', methods=['POST'])
def mark_message_read(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    message = Message.query.get(message_id)
    
    if message and message.recipient_id == session['user_id']:
        message.read = True
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Message not found'}), 404

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    message = Message.query.get(message_id)
    
    # Only sender or recipient can delete
    if message and (message.sender_id == session['user_id'] or message.recipient_id == session['user_id']):
        db.session.delete(message)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Message not found'}), 404

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
