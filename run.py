# Start full system wiht neo4j and server:
# docker-compose up mybrain-neo4j mybrain-server 
from app import create_app

app = create_app()
with app.app_context():
    import app.models as models
    models.neo4j.init_app(app)
    
if __name__ == '__main__':
    # Enable debug mode so the auto-reloader restarts the server on code changes
    app.run(debug=True, host='0.0.0.0', port=5000)
