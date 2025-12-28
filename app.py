from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///intimate_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    partner_code = db.Column(db.String(50), unique=True)
    encounters = db.relationship('Encounter', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

# Position types with icons
POSITIONS = {
    'missionary': {'icon': '🛏️', 'name': 'Missionary'},
    'doggy': {'icon': '🐕', 'name': 'Doggy Style'},
    'cowgirl': {'icon': '🤠', 'name': 'Cowgirl'},
    'reverse_cowgirl': {'icon': '🔄', 'name': 'Reverse Cowgirl'},
    'spooning': {'icon': '🥄', 'name': 'Spooning'},
    'standing': {'icon': '🧍', 'name': 'Standing'},
    'oral': {'icon': '👅', 'name': 'Oral'},
    'anal': {'icon': '🍑', 'name': 'Anal'},
    'other': {'icon': '✨', 'name': 'Other'}
}

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
    user.partner_code = os.urandom(8).hex()
    
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
