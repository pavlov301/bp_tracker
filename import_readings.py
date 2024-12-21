import csv
from datetime import datetime
from app import app, db, User, BPReading
from sqlalchemy import func

def parse_reading(reading_str):
    """Parse a reading string like '127/85' into systolic and diastolic values"""
    parts = reading_str.split('/')
    if len(parts) != 2:
        raise ValueError(f"Invalid reading format: {reading_str}")
    return int(parts[0]), int(parts[1])

def import_readings_from_csv(filename, username):
    with app.app_context():
        # Get the user (case-insensitive search)
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        if not user:
            print(f"User {username} not found!")
            return

        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            readings = []
            
            for row in reader:
                try:
                    # Parse the date
                    date_str = row['Date/Time']
                    try:
                        # Try to parse the date (assuming DD/MM/YY format)
                        timestamp = datetime.strptime(date_str, '%d/%m/%y %H:%M')
                    except ValueError as e:
                        print(f"Could not parse timestamp: {date_str}")
                        print(f"Error: {str(e)}")
                        continue

                    # Parse the blood pressure reading
                    systolic, diastolic = parse_reading(row['Reading'])

                    reading = BPReading(
                        systolic=systolic,
                        diastolic=diastolic,
                        timestamp=timestamp,
                        user_id=user.id
                    )
                    readings.append(reading)
                    print(f"Processed reading: Systolic={reading.systolic}, Diastolic={reading.diastolic}, Time={reading.timestamp}")
                except Exception as e:
                    print(f"Error processing row: {row}")
                    print(f"Error: {str(e)}")
                    continue

            if readings:
                db.session.bulk_save_objects(readings)
                db.session.commit()
                print(f"Successfully imported {len(readings)} readings")
            else:
                print("No readings were imported")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python import_readings.py <csv_file> <username>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    username = sys.argv[2]
    import_readings_from_csv(csv_file, username)
