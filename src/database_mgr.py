import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config.settings import settings

class DatabaseManager:
    def __init__(self):
        """
            Builds state-managed connection pools to remote MongoDB Atlas Cluster.
        """
        if not settings.MONGO_URI:
            raise ValueError("Cloud Configuration Mismatch: MONGO_URI string undefined!")
            
        try:
            self.client = MongoClient(settings.MONGO_URI)
            # Send an instant packet ping to verify network permissions
            self.client.admin.command('ping')
            print("Production Connection Established: MongoDB Atlas Cloud Connected.")
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Atlas Cluster Connection Refused: {e}")

        self.db = self.client.get_database('deadline_tracker')
        self.users_col = self.db['users']
        self.processed_emails_col = self.db['processed_emails']
        
        # Build relational indexing patterns automatically
        self._initialize_indexes()

    def _initialize_indexes(self):
        """
            Spawns performance unique indexing tables at the engine layer.
        """
        self.users_col.create_index("email", unique=True)
        
        # Idempotency Guard: Compound Index prevents duplicate processing for a user/email pair
        self.processed_emails_col.create_index(
            [("user_email", 1), ("email_id", 1)], 
            unique=True
        )

    def upsert_user(self, email: str, token_info: dict):
        """
            Atomically inserts or updates student profile records with authorization maps.
        """
        query = {"email": email}
        update_data = {
            "$set": {
                "email": email,
                "token_info": token_info, # Stored natively as a document object
                "active": 1,
                "updated_at": datetime.datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.datetime.utcnow()
            }
        }
        self.users_col.update_one(query, update_data, upsert=True)

    def get_all_active_users(self) -> list:
        """
            Pulls active student profile records out of the database mapping layer.
        """
        cursor = self.users_col.find({"active": 1}, {"_id": 0, "email": 1, "token_info": 1})
        return list(cursor)

    def is_email_processed(self, user_email: str, email_id: str) -> bool:
        """
            Validates if a targeted email ID has already been recorded in the database.
        """
        query = {"user_email": user_email, "email_id": email_id}
        return self.processed_emails_col.count_documents(query) > 0

    def mark_email_as_processed(self, user_email: str, email_id: str):
        """
            Logs processed email records in the database to prevent duplicate scheduling entries.
        """
        doc = {
            "user_email": user_email,
            "email_id": email_id,
            "processed_at": datetime.datetime.utcnow()
        }
        self.processed_emails_col.update_one(
            {"user_email": user_email, "email_id": email_id},
            {"$set": doc},
            upsert=True
        )