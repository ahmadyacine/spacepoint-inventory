from database import get_connection

print("Connecting to SQL Server...")

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='TestFastAPI' AND xtype='U')
CREATE TABLE TestFastAPI (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(100)
);
""")
conn.commit()

cursor.execute("INSERT INTO TestFastAPI (Name) VALUES ('Connected via FastAPI pyodbc');")
conn.commit()

print("Table created and row inserted successfully!")

cursor.close()
conn.close()
