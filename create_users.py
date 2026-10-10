import mysql.connector
from werkzeug.security import generate_password_hash

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="gaurav",
    database="pharmacy_db"
)

cursor = db.cursor()

# Remove existing users
cursor.execute("DELETE FROM users")

# Create hashed passwords
admin_password = generate_password_hash("admin123")
pharmacist_password = generate_password_hash("pharma123")

# Create Admin user
cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES (%s, %s, %s)
""", ("admin", admin_password, "Admin"))

# Create Pharmacist user
cursor.execute("""
    INSERT INTO users (username, password, role)
    VALUES (%s, %s, %s)
""", ("pharmacist", pharmacist_password, "Pharmacist"))

db.commit()

cursor.close()
db.close()

print("Users created successfully.")
print("Admin      : admin / admin123")
print("Pharmacist : pharmacist / pharma123")