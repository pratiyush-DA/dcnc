#!/usr/bin/env python3
"""
Database Setup Script
Initialize PostgreSQL database for multi-tenant system
"""

import os
import sys
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Continuing without .env file support...")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Initialize database"""
    print("=" * 60)
    print("Database Setup for Multi-Tenant System")
    print("=" * 60)
    
    # Check environment variables (now loads from .env if available)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("\n⚠️  WARNING: DATABASE_URL not set!")
        print("Please set DATABASE_URL environment variable:")
        print("  export DATABASE_URL='postgresql://user:password@localhost:5432/dcnc_db'")
        print("\nOr create a .env file with:")
        print("  DATABASE_URL=postgresql://user:password@localhost:5432/dcnc_db")
        print("\nDefaulting to: postgresql://user:password@localhost:5432/dcnc_db")
        database_url = "postgresql://user:password@localhost:5432/dcnc_db"
    
    print(f"\n📊 Database URL: {database_url.split('@')[1] if '@' in database_url else 'Not set'}")
    
    try:
        # Import database components
        from backend.database.session import init_db, engine
        from backend.database.models import Base
        
        print("\n🔄 Initializing database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database tables created successfully!")
        print("\n📋 Created tables:")
        print("  - clients")
        print("  - users")
        print("  - refresh_tokens")
        print("  - jobs")
        print("  - fingerprints")
        print("  - detection_cache")
        print("  - correction_cache")
        print("  - audit_logs")
        
        print("\n✅ Database initialization complete!")
        print("\n💡 Next steps:")
        print("  1. Set JWT_SECRET_KEY environment variable")
        print("  2. Start the API: python run_api.py")
        print("  3. Test registration: POST /api/v1/auth/register")
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\n💡 Make sure you've installed dependencies:")
        print("  pip install -r requirements-api.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        print("\n💡 Make sure:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL is correct")
        print("  3. Database exists: CREATE DATABASE dcnc_db;")
        print("  4. User has permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()
