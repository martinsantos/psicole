import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

# Create a minimal Flask app
app = Flask(__name__)

# Configure SQLite database with absolute path in the user's home directory
home_dir = os.path.expanduser('~')
db_path = os.path.join(home_dir, 'psicole_test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'test-secret-key'  # For testing only

# Initialize the database
db = SQLAlchemy(app)

# Define a simple User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(80), default='user')
    
    def set_password(self, password):
        # Use a basic hashing method that's compatible with older Python versions
        self.password_hash = f"plain:{password}"  # For testing only, not for production

# Create all database tables
with app.app_context():
    print(f"Creating database at: {db_path}")
    try:
        db.create_all()
        print("Database tables created successfully!")
        
        # Create a test user
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created test admin user with username: admin, password: admin123")
            
        # List all users
        users = User.query.all()
        print(f"Current users in database: {[u.username for u in users]}")
        
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        raise

if __name__ == '__main__':
    print("Test script completed.")
