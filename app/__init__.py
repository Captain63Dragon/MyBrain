from flask import Flask
from neo4j import GraphDatabase
from app.routes.buscard_routes import buscard_bp
# from app.routes.timeline_routes import timeline_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    # remove the following when TODO: to cache static files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Initialize Neo4j via models' client
    
    with app.app_context():
        # Register blueprints inside app context
        app.register_blueprint(buscard_bp)
        # app.register_blueprint(timeline_bp)

    return app