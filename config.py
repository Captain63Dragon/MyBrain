import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://mybrain-neo4j:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'tester11')
    ZAUDI_API_KEY  = os.getenv('ZAUDI_API_KEY', '')
    ZAUDI_BASE_URL = os.getenv('ZAUDI_BASE_URL', 'https://api.zaudi.com')
