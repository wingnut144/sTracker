from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///intimate_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/custom_icons'
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    partner_code = db.Column(db.String(50), unique=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # User profile information
    full_name = db.Column(db.String(200))
    phone_number = db.Column(db.String(20))
    private_notes = db.Column(db.Text)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    encounters = db.relationship('Encounter', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_partner_code(self):
        import secrets
        self.partner_code = secrets.token_hex(8)

class Encounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time)
    position = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer)  # in minutes
    notes = db.Column(db.Text)
    rating = db.Column(db.Integer)  # 1-5
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='encounter', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

class CustomIcon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(50), unique=True, nullable=False)
    svg_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    encounter_id = db.Column(db.Integer, db.ForeignKey('encounter.id'), nullable=True)
    type = db.Column(db.String(50), nullable=False)  # 'new_encounter', 'new_comment'
    message = db.Column(db.String(200), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User')

# Position types with silhouette icons
POSITIONS = {
    'missionary': {'icon': 'missionary', 'name': 'Missionary'},
    'doggy': {'icon': 'doggy', 'name': 'Doggy Style'},
    'cowgirl': {'icon': 'cowgirl', 'name': 'Cowgirl'},
    'reverse_cowgirl': {'icon': 'reverse_cowgirl', 'name': 'Reverse Cowgirl'},
    'spooning': {'icon': 'spooning', 'name': 'Spooning'},
    'standing': {'icon': 'standing', 'name': 'Standing'},
    'oral': {'icon': 'oral', 'name': 'Oral'},
    'anal': {'icon': 'anal', 'name': 'Anal'},
    'other': {'icon': 'other', 'name': 'Other'}
}

# Helper functions
def send_sms(phone_number, message):
    """Send SMS notification using Twilio (optional)"""
    # Twilio configuration (set these in environment variables)
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    if not all([account_sid, auth_token, from_number]):
        print("SMS not configured - skipping")
        return False
    
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        
        return True
    except Exception as e:
        print(f"SMS send error: {e}")
        return False

def create_notification(user_id, encounter_id, notification_type, message):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        encounter_id=encounter_id,
        type=notification_type,
        message=message
    )
    db.session.add(notification)
    db.session.commit()
    
    # Send SMS if enabled
    user = User.query.get(user_id)
    if user and user.sms_notifications and user.phone_number:
        send_sms(user.phone_number, message)
    
    return notification

def notify_partner(current_user_id, encounter_id, notification_type, message):
    """Notify partner about new encounter or comment"""
    user = User.query.get(current_user_id)
    if user and user.partner_id:
        create_notification(user.partner_id, encounter_id, notification_type, message)

@app.route('/')
def index():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('calendar.html', positions=POSITIONS)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    
    user = User(username=data['username'])
    user.set_password(data['password'])
    user.generate_partner_code()
    
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    session['username'] = user.username
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/encounters', methods=['GET'])
def get_encounters():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if month and year:
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        encounters = Encounter.query.filter(
            Encounter.user_id == session['user_id'],
            Encounter.date >= start_date,
            Encounter.date < end_date
        ).all()
    else:
        encounters = Encounter.query.filter_by(user_id=session['user_id']).all()
    
    return jsonify([{
        'id': e.id,
        'date': e.date.isoformat(),
        'time': e.time.isoformat() if e.time else None,
        'position': e.position,
        'position_icon': POSITIONS.get(e.position, {}).get('icon', '✨'),
        'position_name': POSITIONS.get(e.position, {}).get('name', 'Other'),
        'duration': e.duration,
        'notes': e.notes,
        'rating': e.rating,
        'comment_count': len(e.comments)
    } for e in encounters])

@app.route('/api/encounters', methods=['POST'])
def create_encounter():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    encounter = Encounter(
        user_id=session['user_id'],
        date=datetime.fromisoformat(data['date']).date(),
        time=datetime.fromisoformat(data['time']).time() if data.get('time') else None,
        position=data['position'],
        duration=data.get('duration'),
        notes=data.get('notes'),
        rating=data.get('rating')
    )
    
    db.session.add(encounter)
    db.session.commit()
    
    # Notify partner
    position_name = POSITIONS.get(data['position'], {}).get('name', 'Unknown')
    notify_partner(
        session['user_id'],
        encounter.id,
        'new_encounter',
        f"New encounter added: {position_name} on {data['date']}"
    )
    
    return jsonify({'success': True, 'id': encounter.id})

@app.route('/api/encounters/<int:encounter_id>', methods=['GET'])
def get_encounter(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get_or_404(encounter_id)
    
    if encounter.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    comments = [{
        'id': c.id,
        'user': c.user.username,
        'text': c.text,
        'rating': c.rating,
        'suggestions': c.suggestions,
        'created_at': c.created_at.isoformat()
    } for c in encounter.comments]
    
    return jsonify({
        'id': encounter.id,
        'date': encounter.date.isoformat(),
        'time': encounter.time.isoformat() if encounter.time else None,
        'position': encounter.position,
        'position_icon': POSITIONS.get(encounter.position, {}).get('icon', '✨'),
        'position_name': POSITIONS.get(encounter.position, {}).get('name', 'Other'),
        'duration': encounter.duration,
        'notes': encounter.notes,
        'rating': encounter.rating,
        'comments': comments
    })

@app.route('/api/encounters/<int:encounter_id>', methods=['DELETE'])
def delete_encounter(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounter = Encounter.query.get_or_404(encounter_id)
    
    if encounter.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(encounter)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/encounters/<int:encounter_id>/comments', methods=['POST'])
def add_comment(encounter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    
    comment = Comment(
        encounter_id=encounter_id,
        user_id=session['user_id'],
        text=data['text'],
        rating=data.get('rating'),
        suggestions=data.get('suggestions')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Notify encounter owner if different user
    encounter = Encounter.query.get(encounter_id)
    if encounter and encounter.user_id != session['user_id']:
        notify_partner(
            session['user_id'],
            encounter_id,
            'new_comment',
            f"New comment added to your encounter"
        )
    
    return jsonify({'success': True, 'id': comment.id})

@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    encounters = Encounter.query.filter_by(user_id=session['user_id']).all()
    
    position_counts = {}
    for e in encounters:
        position_counts[e.position] = position_counts.get(e.position, 0) + 1
    
    avg_rating = sum(e.rating for e in encounters if e.rating) / len([e for e in encounters if e.rating]) if encounters else 0
    
    return jsonify({
        'total_encounters': len(encounters),
        'position_counts': position_counts,
        'average_rating': round(avg_rating, 1),
        'this_month': len([e for e in encounters if e.date.month == datetime.now().month])
    })

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return render_template('login.html')
    return render_template('admin.html', positions=POSITIONS)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return render_template('login.html')
    
    user = User.query.get(session['user_id'])
    partner = User.query.get(user.partner_id) if user.partner_id else None
    
    return render_template('profile.html', user=user, partner=partner, positions=POSITIONS)

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    partner = User.query.get(user.partner_id) if user.partner_id else None
    
    return jsonify({
        'username': user.username,
        'full_name': user.full_name,
        'phone_number': user.phone_number,
        'private_notes': user.private_notes,
        'sms_notifications': user.sms_notifications,
        'partner_code': user.partner_code,
        'partner': partner.username if partner else None
    })

@app.route('/api/profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    data = request.json
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'phone_number' in data:
        user.phone_number = data['phone_number']
    if 'private_notes' in data:
        user.private_notes = data['private_notes']
    if 'sms_notifications' in data:
        user.sms_notifications = data['sms_notifications']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Profile updated'})

@app.route('/api/partner/connect', methods=['POST'])
def connect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    partner_code = data.get('partner_code')
    
    if not partner_code:
        return jsonify({'error': 'Partner code required'}), 400
    
    # Find partner by code
    partner = User.query.filter_by(partner_code=partner_code).first()
    
    if not partner:
        return jsonify({'error': 'Invalid partner code'}), 404
    
    if partner.id == session['user_id']:
        return jsonify({'error': 'Cannot connect to yourself'}), 400
    
    # Connect both users
    user = User.query.get(session['user_id'])
    user.partner_id = partner.id
    partner.partner_id = user.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Connected to {partner.username}',
        'partner': partner.username
    })

@app.route('/api/partner/disconnect', methods=['POST'])
def disconnect_partner():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(session['user_id'])
    
    if not user.partner_id:
        return jsonify({'error': 'No partner connected'}), 400
    
    # Disconnect both users
    partner = User.query.get(user.partner_id)
    if partner:
        partner.partner_id = None
    
    user.partner_id = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Partner disconnected'})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).limit(50).all()
    
    return jsonify([{
        'id': n.id,
        'type': n.type,
        'message': n.message,
        'read': n.read,
        'encounter_id': n.encounter_id,
        'created_at': n.created_at.isoformat()
    } for n in notifications])

@app.route('/api/notifications/unread_count', methods=['GET'])
def get_unread_count():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    count = Notification.query.filter_by(user_id=session['user_id'], read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/mark_all_read', methods=['POST'])
def mark_all_read():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    Notification.query.filter_by(user_id=session['user_id'], read=False).update({'read': True})
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/icons', methods=['GET'])
def get_custom_icons():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    custom_icons = CustomIcon.query.all()
    icons_dict = {icon.position: icon.svg_content for icon in custom_icons}
    
    return jsonify(icons_dict)

@app.route('/api/admin/icons/<position>', methods=['POST'])
def upload_custom_icon(position):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if position not in POSITIONS:
        return jsonify({'error': 'Invalid position'}), 400
    
    data = request.json
    svg_content = data.get('svg_content', '').strip()
    
    if not svg_content:
        return jsonify({'error': 'No SVG content provided'}), 400
    
    # Validate it's SVG
    if not svg_content.startswith('<svg') or not svg_content.endswith('</svg>'):
        return jsonify({'error': 'Invalid SVG format'}), 400
    
    # Check if custom icon exists
    custom_icon = CustomIcon.query.filter_by(position=position).first()
    
    if custom_icon:
        custom_icon.svg_content = svg_content
    else:
        custom_icon = CustomIcon(position=position, svg_content=svg_content)
        db.session.add(custom_icon)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Icon updated successfully'})

@app.route('/api/admin/icons/<position>', methods=['DELETE'])
def delete_custom_icon(position):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    custom_icon = CustomIcon.query.filter_by(position=position).first()
    
    if custom_icon:
        db.session.delete(custom_icon)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Reverted to default icon'})
    
    return jsonify({'success': False, 'message': 'No custom icon found'}), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
