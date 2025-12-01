from app.db.session import SessionLocal
from app.models.db_models import User, Course, Document, PlannerItem, ProcessingJob
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    # Display connection info for debugging
    db_url = os.getenv("DATABASE_URL", "Not set")
    if db_url != "Not set":
        # Mask password in URL for display
        if "@" in db_url:
            parts = db_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    masked_url = db_url.replace(user_pass, f"{user}:***")
                    print(f"Attempting to connect to: {masked_url}")
        else:
            print(f"Database URL format: {db_url[:50]}...")
    else:
        print("WARNING: DATABASE_URL environment variable is not set!")
    
    print("\nTesting database connection...")
    db = None
    try:
        db = SessionLocal()
        # Test connection with a simple query
        db.execute(text("SELECT 1"))
        db.commit()
        print("✓ Connection successful!\n")
    except OperationalError as e:
        print("\n✗ Connection failed!")
        print("\n🔍 DIAGNOSIS: Connection timeout detected")
        print("\nPossible causes:")
        print("  1. RDS is in a private subnet with NAT Gateway (no IGW route)")
        print("     → NAT allows outbound only, blocks inbound from internet")
        print("  2. RDS instance is not publicly accessible")
        print("  3. Security group doesn't allow your IP address")
        print("  4. Database subnet has IGW removed (private subnet)")
        print("\n💡 Solutions (choose one):")
        print("\n  Option A: Use AWS Systems Manager Session Manager (Recommended)")
        print("    1. Find an EC2 instance in the same VPC as RDS")
        print("    2. Ensure SSM agent is installed on EC2")
        print("    3. Run: aws ssm start-session --target <instance-id>")
        print("    4. From EC2, run this script (RDS is accessible from same VPC)")
        print("\n  Option B: Use Port Forwarding via SSM")
        print("    aws ssm start-session --target <instance-id> \\")
        print("      --document-name AWS-StartPortForwardingSessionToRemoteHost \\")
        print("      --parameters '{\"host\":[\"<rds-endpoint>\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}'")
        print("\n  Option C: Temporarily add IGW route (NOT recommended for production)")
        print("    - Add route table entry: 0.0.0.0/0 → IGW")
        print("    - Set RDS to 'Publicly accessible'")
        print("    - Add security group rule for your IP")
        print("\n  Option D: Run from Lambda/EC2 in same VPC")
        print("    - Deploy script to Lambda with VPC configuration")
        print("    - Or run from EC2 instance in same VPC")
        print(f"\nError details: {str(e)}")
        if db:
            db.close()
        return
    
    try:
        # 1. Get the first user
        user = db.query(User).first()
        
        if not user:
            print("No users found in the database.")
            return
        
        print(f"Found user:")
        print(f"  - ID: {user.id}")
        print(f"  - Email: {user.email}")
        print(f"  - Cognito Sub: {user.cognito_sub}")
        print(f"  - Created At: {user.created_at}")
        
        # 2. Count related records
        courses_count = db.query(Course).filter(Course.user_id == user.id).count()
        documents_count = db.query(Document).filter(Document.user_id == user.id).count()
        planner_items_count = db.query(PlannerItem).filter(PlannerItem.user_id == user.id).count()
        processing_jobs_count = db.query(ProcessingJob).filter(ProcessingJob.user_id == user.id).count()
        
        print(f"\nRelated records to be deleted:")
        print(f"  - Courses: {courses_count}")
        print(f"  - Documents: {documents_count}")
        print(f"  - Planner Items: {planner_items_count}")
        print(f"  - Processing Jobs: {processing_jobs_count}")
        
        # 3. Delete related records first (in correct order due to foreign key constraints)
        # Delete planner items first (they reference courses, documents, and users)
        planner_items_deleted = db.query(PlannerItem).filter(PlannerItem.user_id == user.id).delete()
        print(f"\nDeleted {planner_items_deleted} planner items")
        
        # Delete processing jobs (they reference users)
        processing_jobs_deleted = db.query(ProcessingJob).filter(ProcessingJob.user_id == user.id).delete()
        print(f"Deleted {processing_jobs_deleted} processing jobs")
        
        # Delete courses (they reference users)
        courses_deleted = db.query(Course).filter(Course.user_id == user.id).delete()
        print(f"Deleted {courses_deleted} courses")
        
        # Delete documents (they reference users)
        documents_deleted = db.query(Document).filter(Document.user_id == user.id).delete()
        print(f"Deleted {documents_deleted} documents")
        
        # 4. Finally, delete the user
        db.delete(user)
        db.commit()
        
        print(f"\n✓ User {user.id} and all related records deleted successfully.")
        
    except OperationalError as e:
        if db:
            db.rollback()
        print(f"\n✗ Database connection error: {str(e)}")
        print("\nThis is a network/connectivity issue, not a code problem.")
        print("Please check your network connection and AWS RDS security settings.")
        raise
    except Exception as e:
        if db:
            db.rollback()
        print(f"\n✗ Error deleting user: {str(e)}")
        raise
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()

