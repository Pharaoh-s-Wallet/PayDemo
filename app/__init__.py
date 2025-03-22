from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.payments import payments_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(payments_bp, url_prefix='/api')
    
    return app 