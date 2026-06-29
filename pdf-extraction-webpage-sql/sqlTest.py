# TESTING IF THE LAPTOP CAN REACH FACTS SQL DATABASE

import os
import pymssql # translator between Python and MicroSoft SQL Server 
from dotenv import load_dotenv

# LOADING ENVIRONMENT VARIABLES
load_dotenv()
server = os.getenv("SQL_SERVER")
port = os.getenv("SQL_PORT")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USER")
password = os.getenv("SQL_PASSWORD") 

print("Connecting to SQL Server...")

# if server's firewall is blocking the laptop's IP add, script will give up and 
# show error after 5 secs instead of freezing forever
conn = pymssql.connect(
        server = server,
        port = port, 
        database = database,
        user = username,
        password = password,
        login_timeout = 5
)
cursor = conn.cursor() # cursor is the object that delivers the SQL commands and carries data back to Python

# TESTING CONNECTION
print("Connection successful !!")
cursor.execute("SELECT @@version;") # SQL command to fetch server version details 
row = cursor.fetchone() # when db answers the data comes back in rows, so to fetch the 1st row of response

print(f"\nServer Info: {row[0]}") # contains server version info 

# CLOSING THE CONNECTION
conn.close()
print("\nConnection closed.")


