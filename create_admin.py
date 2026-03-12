import mysql.connector

# Database connection details
db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="Charan@123",
    database="water_booking"
)

cursor = db.cursor()

# Admin Details
name = "System Admin"
email = "admin@water.com"
password = "admin123" # Plain text as requested

# SQL to insert admin
sql = "INSERT INTO users (name, email, password, is_admin) VALUES (%s, %s, %s, 1)"
values = (name, email, password)

try:
    cursor.execute(sql, values)
    db.commit()
    print("✅ Admin account created successfully!")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()