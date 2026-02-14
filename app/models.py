from neo4j import GraphDatabase as db4j
from enum import Enum
# from .schema_handlers import 
# , basicFN_mockup
from flask import current_app as app
import atexit


####
# Models + Neo4j client combined. This file exposes `neo4j` which should be
# initialized by calling `neo4j.init_app(app)` inside the application factory.

class Neo4jClient:
    """Singleton-ish Neo4j client with init_app lifecycle.

    Provides convenience methods used by existing code: `driver`, `query`,
    `get_driver`, `get_session`, and `close`. Call `init_app(app)` from
    `create_app()` to initialize the driver with app config.
    """
    def __init__(self):
        self.driver = None
        self.current_schema = None

    def init_app(self, app):
        # print(f"INIT_APP: Called on instance {id(self)}")
        # print(f"INIT_APP: Current driver value: {self.driver}")
        if self.driver:
            # print(f"INIT_APP: Driver already exists, returning early")
            return
        
        self.driver = db4j.driver(
            app.config['NEO4J_URI'],
            auth=(app.config['NEO4J_USER'], app.config['NEO4J_PASSWORD'])
        )
        # print(f"INIT_APP: Driver created: {self.driver}")
        # print(f"INIT_APP: Instance after init: {id(self)}, driver: {self.driver}")

        # @app.teardown_appcontext
        # def _close(exc):
        #     self.close()

        atexit.register(lambda: self.close())

    def query(self, cypher_query, parameters=None, return_result=True):
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters)
            if return_result:
                return [record for record in result]

    @classmethod
    def get_driver(cls):
        inst = cls.get_instance()
        return inst.driver

    def get_session(self):
        # print(f"GET_SESSION: Called on instance {id(self)}")
        # print(f"GET_SESSION: Driver value: {self.driver}")
        return self.driver.session()
    
    def close(self):
        if self.driver:
            try:
                self.driver.close()
            finally:
                self.driver = None

    # Optional helper placeholder to avoid AttributeError in other code.
    # Implement actual behavior if needed.
    def create_nodes_and_relationship(self, tx):
        # no-op placeholder
        return


# Public client instance used by routes: `from app.models import neo4j`
neo4j = Neo4jClient()
# print(f"MODULE LOAD: Created neo4j instance: {id(neo4j)}")