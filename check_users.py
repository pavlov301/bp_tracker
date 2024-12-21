from app import app, User, db

with app.app_context():
    users = User.query.all()
    print("\nRegistered users:")
    for user in users:
        print(f"ID: {user.id}, Username: {user.username}")
    
    # Print the total count
    print(f"\nTotal users: {len(users)}")
    
    # Check if specific user exists
    test_user = User.query.filter_by(username="paul_richardson25@hotmail.com").first()
    if test_user:
        print(f"\nFound user paul_richardson25@hotmail.com with ID: {test_user.id}")
    else:
        print("\nUser paul_richardson25@hotmail.com not found")
        
    # List all tables in the database
    print("\nDatabase tables:")
    for table in db.metadata.tables.keys():
        print(f"- {table}")
