from sqlalchemy import create_engine

DATABASE_URL = "mssql+pyodbc://sa:123456@LAPTOP-SVV28CTN%5CMSSQLSERVER2/SpacePointInventory?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"

engine = create_engine(DATABASE_URL)

print("Testing SQLAlchemy connection...")
try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✅ SQLAlchemy connected successfully!")
except Exception as e:
    print("❌ ERROR:")
    print(e)
