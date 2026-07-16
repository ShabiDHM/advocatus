# Helper for direct access during SaaS Operations
def get_db_instance():
    from ..main import app
    if hasattr(app.state, "mongo_db") and app.state.mongo_db is not None:
        return app.state.mongo_db
    
    # Fallback if state is empty (e.g. testing)
    import os
    from pymongo import MongoClient
    client = MongoClient(os.getenv("DATABASE_URI"))
    return client[os.getenv("MONGO_DB_NAME", "advocatus_db")]