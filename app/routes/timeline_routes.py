from flask import Blueprint, render_template, jsonify
from app.models import neo4j
timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')

@timeline_bp.route("/timeline-data")
# @timeline_bp.route("/timeline-data<int:ver>")
def load_timeline_data(ver=None):
    if ver is None:
        return render_template('timeline-neo4jload_001.html')
    elif ver == 2:
        return render_template('timeline-neo4jload_003.html')
    return f"doh!"

@timeline_bp.route("/hello")
@timeline_bp.route("/index")
def helloworld():
    return render_template('index.html')

@timeline_bp.route("/data-entry")  # default to latest magic string version
@timeline_bp.route("/data-entry/") # this is a typo in flask, treat same as above
@timeline_bp.route("/data-entry/<string:magic_str>")
def data_entry(magic_str="001"):
    if magic_str == "001" or magic_str is None:
        return render_template('data-entry_001.html')
    else:
        return render_template('index.html')

@timeline_bp.route("/slide")
def index():
    return render_template('timeline-slide-event_002.html')

@timeline_bp.route("/")
def load_test():
    return render_template('timeline-neo4jload_004.html')

@timeline_bp.route("/bubble")
def testBubble():
    return render_template('timeline-size-bubble.html')

@timeline_bp.route("/init")
def testInit():
    
    with neo4j.driver.session() as session:
        # If you have helper methods on models, call them here; otherwise use session directly
        if hasattr(neo4j, 'create_nodes_and_relationship'):
            session.execute_write(neo4j.create_nodes_and_relationship)
        else:
            # placeholder: no-op or custom init
            pass
        # Query to get the count of nodes
        nodes = session.run("MATCH (n) RETURN count(n) AS nodes").single()["nodes"]
        
        # Query to get the count of relationships
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS rels").single()["rels"]
    return f"Initialized the database with some test data. ({nodes} nodes and {rels} relationships)"

