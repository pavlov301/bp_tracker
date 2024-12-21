from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import plotly.graph_objects as go
import plotly.utils
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database configuration
if os.environ.get('PYTHONANYWHERE_DOMAIN'):
    # Use a private directory in the user's home folder
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/paulrichardson25/bp_tracker/instance/bp_readings.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bp_readings.db'

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    readings = db.relationship('BPReading', backref='user', lazy=True)

class BPReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    systolic = db.Column(db.Integer, nullable=False)
    diastolic = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        weekday = self.timestamp.strftime('%A')
        date = self.timestamp.strftime('%d/%m/%Y')
        time = self.timestamp.strftime('%H:%M')
        formatted_date = f"{weekday}, {date} {time}"
        return {
            'id': self.id,
            'systolic': self.systolic,
            'diastolic': self.diastolic,
            'timestamp': formatted_date
        }

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Only create tables if they don't exist
with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        user = User.query.filter_by(username=data['username']).first()
        if user and check_password_hash(user.password_hash, data['password']):
            login_user(user)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        print(f"Received registration request for user: {data['username']}")  # Debug print
        if User.query.filter_by(username=data['username']).first():
            print(f"User {data['username']} already exists")  # Debug print
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        try:
            user = User(
                username=data['username'],
                password_hash=generate_password_hash(data['password'])
            )
            db.session.add(user)
            db.session.commit()
            print(f"Successfully registered user: {data['username']}")  # Debug print
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error registering user: {str(e)}")  # Debug print
            return jsonify({'success': False, 'error': str(e)}), 500
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/readings', methods=['GET'])
@login_required
def get_readings():
    readings = BPReading.query.filter_by(user_id=current_user.id).order_by(BPReading.timestamp.desc()).all()
    return jsonify([reading.to_dict() for reading in readings])

@app.route('/api/readings', methods=['POST'])
@login_required
def add_reading():
    data = request.json
    try:
        timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M')
        reading = BPReading(
            systolic=data['systolic'],
            diastolic=data['diastolic'],
            timestamp=timestamp,
            user_id=current_user.id
        )
        db.session.add(reading)
        db.session.commit()
        return jsonify({'success': True, 'reading': reading.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/readings/<int:reading_id>', methods=['DELETE'])
@login_required
def delete_reading(reading_id):
    reading = BPReading.query.get_or_404(reading_id)
    if reading.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    db.session.delete(reading)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/graph')
@login_required
def get_graph():
    readings = BPReading.query.filter_by(user_id=current_user.id).order_by(BPReading.timestamp.asc()).all()
    if not readings:
        return jsonify({'error': 'No data available'})

    dates = [reading.timestamp for reading in readings]
    systolic = [reading.systolic for reading in readings]
    diastolic = [reading.diastolic for reading in readings]

    # Calculate averages
    avg_systolic = sum(systolic) / len(systolic) if systolic else 0
    avg_diastolic = sum(diastolic) / len(diastolic) if diastolic else 0

    # Create figure
    fig = go.Figure()

    # Add traces
    fig.add_trace(
        go.Scatter(x=dates, y=systolic, name="Systolic", line=dict(color='red'),
                  hovertemplate="<b>%{x|%A, %d/%m/%Y %H:%M}</b><br>" +
                               "Systolic: %{y}<br><extra></extra>")
    )
    fig.add_trace(
        go.Scatter(x=dates, y=diastolic, name="Diastolic", line=dict(color='blue'),
                  hovertemplate="<b>%{x|%A, %d/%m/%Y %H:%M}</b><br>" +
                               "Diastolic: %{y}<br><extra></extra>")
    )

    # Add average lines
    fig.add_hline(y=avg_systolic, line_dash="dash", line_color="rgba(255,0,0,0.5)",
                  annotation_text=f"Avg Systolic: {avg_systolic:.1f}")
    fig.add_hline(y=avg_diastolic, line_dash="dash", line_color="rgba(0,0,255,0.5)",
                  annotation_text=f"Avg Diastolic: {avg_diastolic:.1f}")

    # Add reference lines for normal ranges
    fig.add_hline(y=120, line_dash="dot", line_color="green", annotation_text="Normal Systolic")
    fig.add_hline(y=80, line_dash="dot", line_color="green", annotation_text="Normal Diastolic")

    # Update layout
    fig.update_layout(
        title='Blood Pressure Trends',
        xaxis_title='Date',
        yaxis_title='Blood Pressure (mmHg)',
        hovermode='x unified',
        xaxis=dict(
            tickformat='%a, %d/%m/%Y',
            tickangle=45,
            tickmode='auto',
            nticks=10
        )
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return jsonify(graphJSON)

if __name__ == '__main__':
    # Check if we're running in production
    if os.environ.get('PRODUCTION'):
        # Production settings
        app.run(ssl_context='adhoc')
    else:
        # Development settings
        app.run(debug=True, port=5001, host='0.0.0.0')
