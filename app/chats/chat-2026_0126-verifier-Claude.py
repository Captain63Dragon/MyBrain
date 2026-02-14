from neo4j import GraphDatabase
from app.models import get_session
from pathlib import Path
import os

class FileNodeVerifier:
    def __init__(self, uri, user, password):
        # self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.junk = 0
    
    def verify_meta_path(self, meta_path):
        """Verify meta path exists and has read/write access"""
        if not meta_path:
            return False, "Meta path is null"
        
        path = Path(meta_path)
        
        if not path.exists():
            return False, f"Path does not exist: {meta_path}"
        
        if not path.is_dir():
            return False, f"Path is not a directory: {meta_path}"
        
        # Check read access
        if not os.access(path, os.R_OK):
            return False, f"No read access: {meta_path}"
        
        # Check write access
        if not os.access(path, os.W_OK):
            return False, f"No write access: {meta_path}"
        
        return True, f"Valid meta path: {meta_path}"
    
    def verify_file_in_meta_path(self, file_path, meta_path):
        """Verify file exists within the meta path"""
        if not file_path:
            return False, "File path is null"
        if not meta_path:
            return False, "Meta path is null - cannot verify file location"
        file = Path(file_path)
        meta = Path(meta_path)
        
        # Check if file exists
        if not file.exists():
            return False, f"File does not exist: {file_path}"
        
        # Check if file is within meta path
        try:
            file.resolve().relative_to(meta.resolve())
            return True, f"File exists in meta path: {file_path}"
        except ValueError:
            return False, f"File is not in meta path: {file_path} not in {meta_path}"
    
    def verify_node_id_exists(self, node_id):
        """Verify FILE-NODE-id exists in database"""
        if not node_id:
            return False, "Node ID is null"
        
        query = """
        MATCH (n:FileNode)
        WHERE n.`FILE-NODE-id` = $node_id
        RETURN count(n) as count
        """
        
        with get_session() as session:
            result = session.run(query, node_id=node_id)
            record = result.single()
            count = record["count"] if record else 0
            
            if count > 0:
                return True, f"Node ID exists in database: {node_id} (count: {count})"
            else:
                return False, f"Node ID not found in database: {node_id}"
    
    def get_file_nodes(self):
        """Retrieve all FileNode records"""
        query = """
        MATCH (n:FileNode) 
        RETURN n.`FILE-NODE-id` as id, 
               n.`META-FILE-NODE` as meta, 
               n.filepath as fpath, 
               n.path as mpath
        """
        
        with get_session() as session:
            result = session.run(query)
            return [dict(record) for record in result]
    
    def verify_all(self):
        """Main verification loop"""
        nodes = self.get_file_nodes()
        
        print(f"Found {len(nodes)} FileNode records\n")
        print("=" * 80)
        
        for idx, node in enumerate(nodes, 1):
            print(f"\n--- Record {idx} ---")
            print(f"ID: {node['id']}")
            print(f"Meta: {node['meta']}")
            print(f"File Path: {node['fpath']}")
            print(f"Meta Path: {node['mpath']}")
            print()
            
            # Verify node ID exists (exercise)
            success, message = self.verify_node_id_exists(node['id'])
            print(f"✓ {message}" if success else f"✗ {message}")
            
            # Verify meta path
            success, message = self.verify_meta_path(node['mpath'])
            print(f"✓ {message}" if success else f"✗ {message}")
            
            # Verify file exists in meta path
            success, message = self.verify_file_in_meta_path(node['fpath'], node['mpath'])
            print(f"✓ {message}" if success else f"✗ {message}")
            
            print("-" * 80)


if __name__ == "__main__":
    # Configure your Neo4j connection
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = "your_password"
    
    verifier = FileNodeVerifier(URI, USER, PASSWORD)
    
    try:
        verifier.verify_all()
    finally:
        verifier.close()
        