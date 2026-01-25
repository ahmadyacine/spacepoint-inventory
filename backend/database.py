import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST = os.getenv("DATABASE_HOSTNAME", "localhost")
    DB_PORT = os.getenv("DATABASE_PORT", "5432")
    DB_NAME = os.getenv("DATABASE_NAME", "spacepoint_inventory")
    DB_USER = os.getenv("DATABASE_USERNAME", "postgres")
    DB_PASS = os.getenv("DATABASE_PASSWORD", "postgres")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Setup
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_connection():
    conn = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
    )
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Table instructors
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS instructors (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            location TEXT
        );
        """
    )

    # Table users
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'operations', 'instructor', 'coo')),
            instructor_id INTEGER REFERENCES instructors(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

        # ---------- UPDATE USERS ROLE CHECK CONSTRAINT TO ADD 'coo' ----------

    # Find existing CHECK constraint on users.role (if any)
    cur.execute(
        """
        SELECT ccu.constraint_name
        FROM information_schema.constraint_column_usage AS ccu
        JOIN information_schema.table_constraints AS tc
          ON ccu.constraint_name = tc.constraint_name
         AND ccu.table_name = tc.table_name
        WHERE ccu.table_name = 'users'
          AND ccu.column_name = 'role'
          AND tc.constraint_type = 'CHECK';
        """
    )
    row = cur.fetchone()

    if row:
        constraint_name = row["constraint_name"]
        # Drop old constraint
        cur.execute(f'ALTER TABLE users DROP CONSTRAINT {constraint_name};')
        print(f"Dropped old CHECK constraint on users.role: {constraint_name}")

    # Add new constraint that includes 'coo'
    cur.execute(
        """
        ALTER TABLE users
        ADD CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'operations', 'instructor', 'coo'));
        """
    )
    print("Updated users.role CHECK constraint to allow role = 'coo'")


    # Table cubesats  (OLD m3_* removed here)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cubesats (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            location TEXT,
            delivereddate DATE,
            instructorid INTEGER REFERENCES instructors(id),
            structures INTEGER DEFAULT 0,
            currentsensors INTEGER DEFAULT 0,
            tempsensors INTEGER DEFAULT 0,
            fram INTEGER DEFAULT 0,
            sdcard INTEGER DEFAULT 0,
            reactionwheel INTEGER DEFAULT 0,
            mpu INTEGER DEFAULT 0,
            gps INTEGER DEFAULT 0,
            motordriver INTEGER DEFAULT 0,
            phillipsscrewdriver INTEGER DEFAULT 0,
            screwgauge3d INTEGER DEFAULT 0,
            standofftool3d INTEGER DEFAULT 0,
            iscomplete BOOLEAN DEFAULT FALSE,
            missingitems TEXT,
            is_received BOOLEAN DEFAULT FALSE,
            received_date DATE
        );
        """
    )

    # Table workshops
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workshops (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            workshop_type TEXT NOT NULL CHECK (workshop_type IN ('demo', 'online', 'hands_on', 'training')),
            status TEXT NOT NULL CHECK (status IN ('upcoming', 'in_progress', 'completed', 'cancelled')),
            location TEXT,
            instructor_id INTEGER REFERENCES instructors(id),
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            max_participants INTEGER,
            current_participants INTEGER DEFAULT 0,
            requirements TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Table receipts
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            cubesat_id INTEGER REFERENCES cubesats(id),
            instructor_id INTEGER REFERENCES instructors(id),
            items TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
            generated_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Table notifications
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            related_entity_id INTEGER,
            related_entity_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Table cubesat_session_logs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cubesat_session_logs (
            id SERIAL PRIMARY KEY,
            cubesat_id INTEGER REFERENCES cubesats(id),
            instructor_id INTEGER REFERENCES instructors(id),
            missing_items TEXT,
            status TEXT DEFAULT 'pending_refill',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

        # Table components (extra sensors/boards/tools outside CubeSats)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS components (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('sensor', 'board', 'tool', 'other')),
            image_url TEXT,
            tag TEXT,
            total_quantity INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Table component_logs (history of stock changes)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS component_logs (
            id SERIAL PRIMARY KEY,
            component_id INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
            change INTEGER NOT NULL,      -- +5, -3, etc.
            reason TEXT,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


    


    # Ensure extra columns on users/instructors/cubesats

    # Check if instructor_id column exists in users, if not add it
    cur.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' and column_name='instructor_id';
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE users ADD COLUMN instructor_id INTEGER REFERENCES instructors(id);")
        print("Added instructor_id column to users table")

    # Check if user_id column exists in instructors, if not add it
    cur.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='instructors' and column_name='user_id';
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE instructors ADD COLUMN user_id INTEGER REFERENCES users(id);")
        print("Added user_id column to instructors table")

    # Check if is_received column exists in cubesats, if not add it
    cur.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='cubesats' and column_name='is_received';
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE cubesats ADD COLUMN is_received BOOLEAN DEFAULT FALSE;")
        print("Added is_received column to cubesats table")

    # Check if received_date column exists in cubesats, if not add it
    cur.execute(
        """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='cubesats' and column_name='received_date';
        """
    )
    if not cur.fetchone():
        cur.execute("ALTER TABLE cubesats ADD COLUMN received_date DATE;")
        print("Added received_date column to cubesats table")

    # Insert default users if they don't exist
    cur.execute(
        """
        INSERT INTO users (username, password, full_name, role, instructor_id) 
        VALUES ('admin', 'admin123', 'Admin User', 'admin', NULL)
        ON CONFLICT (username) DO NOTHING;
        """
    )

    # ---------- HELPERS (FIXED INDENTATION) ----------

    def drop_column_if_exists(table: str, column: str):
        cur.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s;
            """,
            (table, column),
        )
        if cur.fetchone():
            cur.execute(f"ALTER TABLE {table} DROP COLUMN {column};")
            print(f"Dropped column {column} from {table} table")

    def add_column_if_not_exists(table: str, column: str, col_type: str):
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name=%s AND column_name=%s;
            """,
            (table, column),
        )
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
            print(f"Added {column} column to {table} table")

    # ---------- DROP OLD M3 COLUMNS ----------

    drop_column_if_exists("cubesats", "m3_10mm")
    drop_column_if_exists("cubesats", "m3_10mm_thread")
    drop_column_if_exists("cubesats", "m3_9mm_thread")
    drop_column_if_exists("cubesats", "m3_20mm_thread")
    drop_column_if_exists("cubesats", "m3_6mm")

    # ---------- ADD NEW CUBESAT COMPONENT COLUMNS ----------

    # Boards
    add_column_if_not_exists("cubesats", "cdhs_board", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "eps_board", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "adcs_board", "INTEGER DEFAULT 0")

    # Electronics
    add_column_if_not_exists("cubesats", "esp32_cam", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "esp32", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "magnetorquer", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "buck_converter_module", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "li_ion_battery", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "pin_socket", "INTEGER DEFAULT 0")

    # Mechanical
    add_column_if_not_exists("cubesats", "m3_screws", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "m3_hex_nut", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "m3_9_6mm_brass_standoff", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "m3_10mm_brass_standoff", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "m3_10_6mm_brass_standoff", "INTEGER DEFAULT 0")
    add_column_if_not_exists("cubesats", "m3_20_6mm_brass_standoff", "INTEGER DEFAULT 0")

    # Add tag column to components
    add_column_if_not_exists("components", "tag", "TEXT")

    # NEW: optional attachment link
    add_column_if_not_exists("reports", "image_url", "TEXT")

    # --- QR / public scan fields ---
    add_column_if_not_exists("cubesats", "public_token", "TEXT UNIQUE")
    add_column_if_not_exists("cubesats", "qr_box_png", "BYTEA")
    add_column_if_not_exists("cubesats", "qr_check_png", "BYTEA")
    add_column_if_not_exists("cubesats", "qr_box_url", "TEXT")
    add_column_if_not_exists("cubesats", "qr_check_url", "TEXT")    

    # ---------- WORKSHOPS: LEAD INSTRUCTOR COLUMN ----------

    add_column_if_not_exists(
        "workshops",
        "lead_instructor_id",
        "INTEGER REFERENCES instructors(id)"
    )

    cur.execute(
        """
        UPDATE workshops w
        SET lead_instructor_id = w.instructor_id
        WHERE w.lead_instructor_id IS NULL
          AND w.instructor_id IS NOT NULL;
        """
    )

    # ---------- WORKSHOP INSTRUCTORS (MANY-TO-MANY) ----------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workshop_instructors (
            id SERIAL PRIMARY KEY,
            workshop_id INTEGER NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
            instructor_id INTEGER NOT NULL REFERENCES instructors(id),
            is_lead BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (workshop_id, instructor_id)
        );
        """
    )

    cur.execute(
        """
        INSERT INTO workshop_instructors (workshop_id, instructor_id, is_lead)
        SELECT id AS workshop_id, instructor_id, TRUE AS is_lead
        FROM workshops
        WHERE instructor_id IS NOT NULL
        ON CONFLICT (workshop_id, instructor_id) DO NOTHING;
        """
    )

        # ---------- REPORTS (INSTRUCTOR ↔ ADMIN THREADS) ----------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            instructorid INTEGER NOT NULL REFERENCES instructors(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            cubesat_id INTEGER REFERENCES cubesats(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Ensure cubesat_id exists if table was created earlier without it
    add_column_if_not_exists("reports", "cubesat_id", "INTEGER REFERENCES cubesats(id)")

        # NEW: COO comment on package requests
    add_column_if_not_exists("package_requests", "coo_comment", "TEXT")


    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS report_messages (
            id SERIAL PRIMARY KEY,
            report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
            sender_role TEXT NOT NULL,          -- 'instructor' or 'admin'
            sender_user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


        # ---------- PACKAGE REQUESTS (ADMIN/OPS -> COO) ----------

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS package_requests (
            id SERIAL PRIMARY KEY,
            requested_by INTEGER NOT NULL REFERENCES users(id),
            -- Info about where to send
            contact_name TEXT,
            contact_phone TEXT,
            location TEXT,
            url_location TEXT,
            -- Items requested (simple text for now, e.g. '4 EPS, 2 ADCS, 1 TEMP, 4 CDHS')
            items TEXT NOT NULL,
            total_items INTEGER NOT NULL DEFAULT 0,
            -- Status: pending -> on_way -> delivered (or cancelled)
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'on_way', 'delivered', 'cancelled')),
            sent_date DATE,
            delivered_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )




    conn.commit()
    cur.close()
    conn.close()
