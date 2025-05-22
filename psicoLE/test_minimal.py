from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Create a minimal Flask app
app = Flask(__name__)

# Configure SQLite with a relative path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_minimal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'test-secret-key'

# Initialize SQLAlchemy
db = SQLAlchemy()
db.init_app(app)

# Define a simple model
class TestModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)

# Create database and tables
with app.app_context():
    print("Creating database and tables...")
    try:
        # Create all tables
        db.create_all()
        print("Successfully created database and tables!")
        
        # Test database operations
        test = TestModel(name='test')
        db.session.add(test)
        db.session.commit()
        print("Successfully inserted test record!")
        
        # Query the database
        result = TestModel.query.first()
        print(f"Retrieved record: id={result.id}, name={result.name}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Database file exists: {os.path.exists('test_minimal.db')}")
        if os.path.exists('test_minimal.db'):
            print(f"File permissions: {oct(os.stat('test_minimal.db').st_mode)[-3:]}")
        raise

print("Test completed successfully!")
