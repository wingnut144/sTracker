from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import requests
import logging

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://intimateuser:password@db:5432/intimatetracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Session configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    partner_code = db.Column(db.String(32), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    sms_notifications = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Encounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time)
    position = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer)
    rating = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'), nullable=False)
    commenter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'))
    proposed_encounter_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProposedEncounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proposer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    proposed_date = db.Column(db.DateTime, nullable=False)
    position = db.Column(db.String(50))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomIcon(db.Model):
    __tablename__ = 'custom_icon'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    position_name = db.Column(db.String(50), nullable=False)
    svg_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'position_name', name='custom_icon_user_position_unique'),
    )

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
# HELPER FUNCTIONS
# ============================================================================

def send_notification_message(phone_number, message):
    """Send notification via Signal or Twilio"""
    try:
        # Try Signal first
        signal_url = os.environ.get('SIGNAL_API_URL', 'http://signal:8080')
        signal_number = os.environ.get('SIGNAL_NUMBER')
        
        if signal_number:
            response = requests.post(
                f'{signal_url}/v2/send',
                json={
                    'number': signal_number,
                    'recipients': [phone_number],
                    'message': message
                },
                timeout=5
            )
            
            if response.status_code == 201:
                logger.info(f"✅ Signal notification sent to {phone_number}")
                return True
        
        # Fallback to Twilio
        twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        twilio_token = os.environ.get('TWILIO_AUTH_TOKEN')
        twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if twilio_sid and twilio_token and twilio_number:
            import twilio.rest
            client = twilio.rest.Client(twilio_sid, twilio_token)
            
            client.messages.create(
                to=phone_number,
                from_=twilio_number,
                body=message
            )
            
            logger.info(f"✅ Twilio SMS sent to {phone_number}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to send notification: {e}")
    
    return False

def create_notification(user_id, notification_type, message, encounter_id=None):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        encounter_id=encounter_id
    )
    db.session.add(notification)
    db.session.commit()

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('calendar.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        
        if user and check_password_hash(user.password, data['password']):
            session.permanent = True
            session['user_id'] = user.id
            return jsonify({'success': True})
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    partner_code = secrets.token_hex(8)
    
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        partner_code=partner_code
    )
    
    db.session.add(user)
    db.session.commit()
    
    session.permanent = True
    session['user_id'] = user.id
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============================================================================
# PAGE ROUTES
# ============================================================================

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    partner = User.query.get(user.partner_id) if user.partner_id else None
    return render_template('profile.html', user=user, partner=partner)

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return redirect(url_for('index'))
    
    return render_template('admin.html')

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('messages.html')

@app.route('/proposals')
def proposals():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('proposals.html')

# ============================================================================
# API ROUTES - Profile
# ============================================================================

@app.route('/api/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    data = request.get_json()
    
    user.full_name = data.get('full_name', '')
    user.phone_number = data.get('phone_number', '')
    user.sms_notifications = data.get('sms_notifications', False)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/connect-partner', methods=['POST'])
def connect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    data = request.get_json()
    partner_code = data.get('partner_code')
    
    partner = User.query.filter_by(partner_code=partner_code).first()
    
    if not partner:
        return jsonify({'error': 'Invalid partner code'}), 404
    
    if partner.id == user.id:
        return jsonify({'error': 'Cannot connect to yourself'}), 400
    
    user.partner_id = partner.id
    partner.partner_id = user.id
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/disconnect-partner', methods=['POST'])
def disconnect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    
    if user.partner_id:
        partner = User.query.get(user.partner_id)
        if partner:
            partner.partner_id = None
        user.partner_id = None
        db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Encounters
# ============================================================================

@app.route('/api/encounters', methods=['GET', 'POST'])
def encounters():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if request.method == 'GET':
        user = User.query.get(session['user_id'])
        user_ids = [user.id]
        if user.partner_id:
            user_ids.append(user.partner_id)
        
        encounters = Encounter.query.filter(
            Encounter.user_id.in_(user_ids)
        ).all()
        
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
            'position_name': positions_dict.get(e.position, 'Other'),
            'duration': e.duration,
            'rating': e.rating,
            'notes': e.notes,
            'user_id': e.user_id,
            'is_own': e.user_id == session['user_id'],
            'username': User.query.get(e.user_id).username
        } for e in encounters])
    
    else:  # POST
        data = request.get_json()
        
        # Validate empty strings for integer fields
        duration = data.get('duration')
        if duration == '':
            duration = None
        elif duration is not None:
            duration = int(duration)
        
        rating = data.get('rating')
        if rating == '':
            rating = None
        elif rating is not None:
            rating = int(rating)
        
        current_user_id = session['user_id']
        
        encounter = Encounter(
            user_id=current_user_id,
            date=datetime.fromisoformat(data['date']).date(),
            time=datetime.fromisoformat(data['time']).time() if data.get('time') else None,
            position=data['position'],
            duration=duration,
            rating=rating,
            notes=data.get('notes', '')
        )
        
        db.session.add(encounter)
        db.session.commit()
        
        # Notify partner if connected
        user = User.query.get(current_user_id)
        if user.partner_id:
            partner = User.query.get(user.partner_id)
            notification_msg = f"💕 {user.username} added a new intimate moment"
            
            create_notification(
                user.partner_id,
                'new_encounter',
                notification_msg,
                encounter.id
            )
            
            # Send external notification if enabled
            if partner.sms_notifications and partner.phone_number:
                send_notification_message(partner.phone_number, notification_msg)
            else:
                logger.info(f"ℹ️ External notifications disabled for {partner.username}")
        
        return jsonify({'success': True, 'id': encounter.id})

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

@app.route('/api/encounters/<int:encounter_id>/comments', methods=['POST'])
def add_comment(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    comment = Comment(
        encounter_id=encounter_id,
        commenter_id=session['user_id'],
        text=data['text'],
        rating=data.get('rating')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Notify the encounter owner
    encounter = Encounter.query.get(encounter_id)
    if encounter and encounter.user_id != session['user_id']:
        user = User.query.get(session['user_id'])
        notification_msg = f"💬 {user.username} commented on your encounter"
        
        create_notification(
            encounter.user_id,
            'new_comment',
            notification_msg,
            encounter_id
        )
        
        # Send external notification if enabled
        owner = User.query.get(encounter.user_id)
        if owner.sms_notifications and owner.phone_number:
            send_notification_message(owner.phone_number, notification_msg)
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Stats
# ============================================================================

@app.route('/api/stats')
def stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    user_ids = [user.id]
    if user.partner_id:
        user_ids.append(user.partner_id)
    
    total = Encounter.query.filter(Encounter.user_id.in_(user_ids)).count()
    
    now = datetime.now()
    this_month = Encounter.query.filter(
        Encounter.user_id.in_(user_ids),
        Encounter.date >= datetime(now.year, now.month, 1).date()
    ).count()
    
    # Calculate average rating from encounter_rating table
    ratings = db.session.query(EncounterRating.rating).join(
        Encounter, EncounterRating.encounter_id == Encounter.id
    ).filter(Encounter.user_id.in_(user_ids)).all()
    
    avg_rating = sum(r[0] for r in ratings) / len(ratings) if ratings else 0
    
    pending = ProposedEncounter.query.filter_by(
        recipient_id=session['user_id'],
        status='pending'
    ).count()
    
    return jsonify({
        'total': total,
        'this_month': this_month,
        'average_rating': avg_rating,
        'pending_proposals': pending
    })

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

@app.route('/api/notifications/unread_count', methods=['GET'])
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
# API ROUTES - Proposals
# ============================================================================

@app.route('/api/proposals', methods=['GET', 'POST'])
def proposals():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if request.method == 'GET':
        sent = ProposedEncounter.query.filter_by(proposer_id=session['user_id']).all()
        received = ProposedEncounter.query.filter_by(recipient_id=session['user_id']).all()
        
        return jsonify({
            'sent': [{
                'id': p.id,
                'proposed_date': p.proposed_date.isoformat(),
                'position': p.position,
                'notes': p.notes,
                'status': p.status,
                'created_at': p.created_at.isoformat()
            } for p in sent],
            'received': [{
                'id': p.id,
                'proposed_date': p.proposed_date.isoformat(),
                'position': p.position,
                'notes': p.notes,
                'status': p.status,
                'proposer': User.query.get(p.proposer_id).username,
                'created_at': p.created_at.isoformat()
            } for p in received]
        })
    
    else:  # POST
        data = request.get_json()
        user = User.query.get(session['user_id'])
        
        if not user.partner_id:
            return jsonify({'error': 'No partner connected'}), 400
        
        proposal = ProposedEncounter(
            proposer_id=session['user_id'],
            recipient_id=user.partner_id,
            proposed_date=datetime.fromisoformat(data['proposed_date']),
            position=data.get('position'),
            notes=data.get('notes', '')
        )
        
        db.session.add(proposal)
        db.session.commit()
        
        # Notify partner
        notification_msg = f"💌 {user.username} proposed an intimate encounter"
        create_notification(
            user.partner_id,
            'new_proposal',
            notification_msg
        )
        
        partner = User.query.get(user.partner_id)
        if partner.sms_notifications and partner.phone_number:
            send_notification_message(partner.phone_number, notification_msg)
        
        return jsonify({'success': True})

@app.route('/api/proposals/<int:proposal_id>/<action>', methods=['POST'])
def respond_to_proposal(proposal_id, action):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    proposal = ProposedEncounter.query.get(proposal_id)
    
    if not proposal or proposal.recipient_id != session['user_id']:
        return jsonify({'error': 'Proposal not found'}), 404
    
    if action == 'accept':
        proposal.status = 'accepted'
        
        # Create encounter
        encounter = Encounter(
            user_id=proposal.proposer_id,
            date=proposal.proposed_date.date(),
            time=proposal.proposed_date.time(),
            position=proposal.position or 'other',
            notes=proposal.notes
        )
        db.session.add(encounter)
        
        # Notify proposer
        user = User.query.get(session['user_id'])
        notification_msg = f"✅ {user.username} accepted your proposal"
        create_notification(
            proposal.proposer_id,
            'proposal_accepted',
            notification_msg
        )
        
    elif action == 'decline':
        proposal.status = 'declined'
        
        # Notify proposer
        user = User.query.get(session['user_id'])
        notification_msg = f"❌ {user.username} declined your proposal"
        create_notification(
            proposal.proposer_id,
            'proposal_declined',
            notification_msg
        )
    
    db.session.commit()
    
    return jsonify({'success': True})

# ============================================================================
# API ROUTES - Custom Icons
# ============================================================================

@app.route('/api/custom-icons', methods=['GET'])
def get_custom_icons():
    if 'user_id' not in session:
        return jsonify([])
    
    icons = CustomIcon.query.filter_by(user_id=session['user_id']).all()
    
    return jsonify([{
        'id': icon.id,
        'position_name': icon.position_name,
        'svg_data': icon.svg_content,
        'created_at': icon.created_at.isoformat() if icon.created_at else None
    } for icon in icons])

@app.route('/api/custom-icons', methods=['POST'])
def add_custom_icon():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    # Check if icon already exists
    existing = CustomIcon.query.filter_by(
        user_id=session['user_id'],
        position_name=data['position_name']
    ).first()
    
    if existing:
        # Update existing
        existing.svg_content = data['svg_content']
    else:
        # Create new
        icon = CustomIcon(
            user_id=session['user_id'],
            position_name=data['position_name'],
            svg_content=data['svg_content']
        )
        db.session.add(icon)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/custom-icons/<int:icon_id>', methods=['DELETE'])
def delete_custom_icon(icon_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    icon = CustomIcon.query.get(icon_id)
    
    if not icon or icon.user_id != session['user_id']:
        return jsonify({'error': 'Icon not found'}), 404
    
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
# MAIN
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
