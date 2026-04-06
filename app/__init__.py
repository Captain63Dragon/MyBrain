import os

# Simple service registry - just titles and template names
SERVICES = {
    'search_database': {
        'title': 'Search Database',
        'template': 'search_database.html'
    },
    'review_filenode': {
        'title': 'Review FileNode',
        'template': 'review_filenode.html'
    }
}

def create_app():
    from flask import Flask
    from neo4j import GraphDatabase
    from app.routes.buscard_routes import buscard_bp
    from app.routes.sse_routes import sse_bp
    from app.routes.r2hodo_routes import r2hodo_bp
    from app.routes.base_routes import base_bp
    from app.routes.bots_routes import bots_bp
    from app.services.mfi_broker import start_mfi_broker
    # from app.routes.timeline_routes import timeline_bp
    app = Flask(__name__)
    app.config.from_object('config.Config')
    # remove the following when TODO: to cache static files
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Initialize Neo4j via models' client
    
    with app.app_context():
        # Register blueprints inside app context
        app.register_blueprint(buscard_bp)
        app.register_blueprint(sse_bp)
        app.register_blueprint(r2hodo_bp)
        app.register_blueprint(base_bp)
        app.register_blueprint(bots_bp)
        # app.register_blueprint(timeline_bp)
        
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_mfi_broker()        
    return app
