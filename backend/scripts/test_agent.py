# FILE: backend/scripts/test_agent.py
import asyncio
import os
import sys

# Add the parent directory to sys.path to import app modules
sys.path.append(os.getcwd())

from app.core.db import connect_to_motor, get_async_db, close_mongo_connections
from app.services.albanian_rag_service import AlbanianRAGService

async def test():
    print("🚀 Initializing DB Connection...")
    
    # 1. Manually trigger the async connection
    await connect_to_motor()
    
    # 2. Get the DB instance (it's a sync generator, so we use next())
    try:
        db_generator = get_async_db()
        db = next(db_generator)
        print("✅ DB Connected.")
    except Exception as e:
        print(f"❌ DB Connection Failed: {e}")
        return

    # 3. Initialize Agent
    print("🤖 Initializing Agent...")
    try:
        agent = AlbanianRAGService(db)
        print("✅ Agent Initialized.")
    except Exception as e:
        print(f"❌ Agent Init Failed: {e}")
        return

    # 4. Mock Data (Use real IDs from your database if possible)
    # If these IDs don't exist, the agent might say "I don't have info", but it shouldn't crash.
    user_id = "65a123456789012345678901" 
    case_id = "65a123456789012345678902" 
    
    # 5. Test Query (with typo to test linguistic normalization)
    query = "qka permban rasti" 

    print(f"\n🧪 Testing Chat with query: '{query}'")
    try:
        response = await agent.chat(
            query=query,
            user_id=user_id,
            case_id=case_id
        )
        print(f"\n📝 RESPONSE:\n{response}")
    except Exception as e:
        print(f"\n❌ FATAL ERROR During Chat:\n{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 6. Cleanup
        close_mongo_connections()

if __name__ == "__main__":
    asyncio.run(test())