import os
import pymssql
from dotenv import load_dotenv

load_dotenv()


try:
    conn = pymssql.connect(
        server=os.getenv("SQL_SERVER"),
        port=os.getenv("SQL_PORT"),
        database=os.getenv("SQL_DATABASE"),
        user=os.getenv("SQL_USER"),
        password=os.getenv("SQL_PASSWORD"),
        login_timeout=5
    )
    cursor = conn.cursor()
    
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'purchase_details'")
    
    print("\n--- COLUMN NAMES ---")
    for row in cursor.fetchall():
        print(row[0])
        
    conn.close()
except Exception as e:
    print(f"Failed: {e}")