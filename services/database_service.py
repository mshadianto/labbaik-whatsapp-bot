"""
LABBAIK.AI WhatsApp Bot - Database Service
==========================================
Service for PostgreSQL database operations
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncpg
from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.is_connected = False
    
    async def initialize(self):
        """Initialize database connection pool"""
        if not settings.DATABASE_URL:
            logger.warning("⚠️ DATABASE_URL not set - running without database")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            self.is_connected = True
            logger.info("✅ Database connection pool created")
            
            # Create tables if not exist
            await self._create_tables()
            
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            self.is_connected = False
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.is_connected = False
            logger.info("Database connection pool closed")
    
    async def _create_tables(self):
        """Create necessary tables if they don't exist"""
        if not self.pool:
            return
        
        async with self.pool.acquire() as conn:
            # WhatsApp users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wa_users (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100),
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    preferences JSONB DEFAULT '{}',
                    is_blocked BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Conversation history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wa_conversations (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    role VARCHAR(10) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            
            # Bot analytics table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wa_analytics (
                    id SERIAL PRIMARY KEY,
                    event_type VARCHAR(50) NOT NULL,
                    phone VARCHAR(20),
                    data JSONB DEFAULT '{}',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wa_conversations_phone 
                ON wa_conversations(phone)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wa_analytics_timestamp 
                ON wa_analytics(timestamp)
            """)
            
            logger.info("✅ Database tables verified/created")
    
    async def get_or_create_user(self, phone: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Get existing user or create new one"""
        if not self.pool:
            return {"phone": phone, "name": name, "message_count": 0}
        
        try:
            async with self.pool.acquire() as conn:
                # Try to get existing user
                user = await conn.fetchrow(
                    "SELECT * FROM wa_users WHERE phone = $1",
                    phone
                )
                
                if user:
                    # Update last active
                    await conn.execute(
                        """UPDATE wa_users 
                           SET last_active = CURRENT_TIMESTAMP, 
                               message_count = message_count + 1
                           WHERE phone = $1""",
                        phone
                    )
                    return dict(user)
                else:
                    # Create new user
                    await conn.execute(
                        """INSERT INTO wa_users (phone, name, message_count)
                           VALUES ($1, $2, 1)""",
                        phone, name
                    )
                    return {
                        "phone": phone,
                        "name": name,
                        "message_count": 1,
                        "is_new": True
                    }
        
        except Exception as e:
            logger.error(f"Database error in get_or_create_user: {e}")
            return {"phone": phone, "name": name, "message_count": 0}
    
    async def save_conversation(
        self,
        phone: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Save conversation message to database"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Convert metadata dict to JSON string
                metadata_json = json.dumps(metadata or {})
                
                await conn.execute(
                    """INSERT INTO wa_conversations (phone, role, content, metadata)
                       VALUES ($1, $2, $3, $4)""",
                    phone, role, content, metadata_json
                )
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    async def get_conversation_history(
        self,
        phone: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Get recent conversation history for a user"""
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT role, content FROM wa_conversations
                       WHERE phone = $1
                       ORDER BY timestamp DESC
                       LIMIT $2""",
                    phone, limit
                )
                
                # Reverse to get chronological order
                history = [{"role": row["role"], "content": row["content"]} for row in rows]
                history.reverse()
                return history
        
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    async def clear_old_conversations(self, hours: int = 24):
        """Clear conversations older than specified hours"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                result = await conn.execute(
                    "DELETE FROM wa_conversations WHERE timestamp < $1",
                    cutoff
                )
                logger.info(f"Cleared old conversations: {result}")
        except Exception as e:
            logger.error(f"Error clearing old conversations: {e}")
    
    async def log_analytics(
        self,
        event_type: str,
        phone: Optional[str] = None,
        data: Optional[Dict] = None
    ):
        """Log analytics event"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Convert data dict to JSON string
                data_json = json.dumps(data or {})
                
                await conn.execute(
                    """INSERT INTO wa_analytics (event_type, phone, data)
                       VALUES ($1, $2, $3)""",
                    event_type, phone, data_json
                )
        except Exception as e:
            logger.error(f"Error logging analytics: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        if not self.pool:
            return {"status": "database_not_connected"}
        
        try:
            async with self.pool.acquire() as conn:
                # Total users
                total_users = await conn.fetchval(
                    "SELECT COUNT(*) FROM wa_users"
                )
                
                # Active today
                active_today = await conn.fetchval(
                    """SELECT COUNT(*) FROM wa_users 
                       WHERE last_active > CURRENT_DATE"""
                )
                
                # Total messages
                total_messages = await conn.fetchval(
                    "SELECT SUM(message_count) FROM wa_users"
                )
                
                # Messages today
                messages_today = await conn.fetchval(
                    """SELECT COUNT(*) FROM wa_conversations 
                       WHERE timestamp > CURRENT_DATE"""
                )
                
                # Top intents (from analytics)
                top_intents = await conn.fetch(
                    """SELECT data->>'intent' as intent, COUNT(*) as count
                       FROM wa_analytics
                       WHERE event_type = 'message_received'
                       AND timestamp > CURRENT_DATE - INTERVAL '7 days'
                       GROUP BY data->>'intent'
                       ORDER BY count DESC
                       LIMIT 5"""
                )
                
                return {
                    "total_users": total_users or 0,
                    "active_today": active_today or 0,
                    "total_messages": total_messages or 0,
                    "messages_today": messages_today or 0,
                    "top_intents": [dict(r) for r in top_intents]
                }
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    async def is_user_blocked(self, phone: str) -> bool:
        """Check if user is blocked"""
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT is_blocked FROM wa_users WHERE phone = $1",
                    phone
                )
                return result or False
        except Exception as e:
            logger.error(f"Error checking blocked status: {e}")
            return False
    
    async def block_user(self, phone: str, reason: Optional[str] = None):
        """Block a user"""
        if not self.pool:
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Convert update dict to JSON string for the || operator
                update_json = json.dumps({"block_reason": reason})
                
                await conn.execute(
                    """UPDATE wa_users SET is_blocked = TRUE,
                       preferences = preferences || $2
                       WHERE phone = $1""",
                    phone, update_json
                )
                await self.log_analytics("user_blocked", phone, {"reason": reason})
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
