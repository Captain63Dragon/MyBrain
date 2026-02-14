import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://mybrain-neo4j:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'tester11')
    # Add other configuration settings here