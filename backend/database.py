
    # جدول instructors
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

    # جدول users - UPDATED to include instructor_id
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'operations', 'instructor')),
            instructor_id INTEGER REFERENCES instructors(id),  -- NEW COLUMN
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # جدول cubesats
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
            m3_10mm INTEGER DEFAULT 0,
            m3_10mm_thread INTEGER DEFAULT 0,
            m3_9mm_thread INTEGER DEFAULT 0,
            m3_20mm_thread INTEGER DEFAULT 0,
            m3_6mm INTEGER DEFAULT 0,
            iscomplete BOOLEAN DEFAULT FALSE,
            missingitems TEXT,
            is_received BOOLEAN DEFAULT FALSE
        );
        """
    )

    # جدول workshops
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

    # جدول receipts
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

    # جدول notifications
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

    # Insert default instructors if they don't exist
    cur.execute("""
        INSERT INTO instructors (id, name, email, phone, location) 
        VALUES 
            (1, 'Instructor One', 'instructor1@spacepoint.com', '+971501234567', 'Dubai'),
            (2, 'Instructor Two', 'instructor2@spacepoint.com', '+971501234568', 'Abu Dhabi'),
            (3, 'Instructor Three', 'instructor3@spacepoint.com', '+971501234569', 'Sharjah')
        ON CONFLICT (id) DO NOTHING;
    """)

    # Check if instructor_id column exists in users, if not add it
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' and column_name='instructor_id';
    """)
    
    if not cur.fetchone():
        # Add the instructor_id column
        cur.execute("ALTER TABLE users ADD COLUMN instructor_id INTEGER REFERENCES instructors(id);")
        print("Added instructor_id column to users table")

    # Check if user_id column exists in instructors, if not add it
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='instructors' and column_name='user_id';
    """)
    
    if not cur.fetchone():
        # Add the user_id column
        cur.execute("ALTER TABLE instructors ADD COLUMN user_id INTEGER REFERENCES users(id);")
        print("Added user_id column to instructors table")

    # Check if is_received column exists in cubesats, if not add it
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='cubesats' and column_name='is_received';
    """)
    
    if not cur.fetchone():
        # Add the is_received column
        cur.execute("ALTER TABLE cubesats ADD COLUMN is_received BOOLEAN DEFAULT FALSE;")
        print("Added is_received column to cubesats table")

    # Check if received_date column exists in cubesats, if not add it
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='cubesats' and column_name='received_date';
    """)
    
    if not cur.fetchone():
        # Add the received_date column
        cur.execute("ALTER TABLE cubesats ADD COLUMN received_date DATE;")
        print("Added received_date column to cubesats table")

    # Insert default users if they don't exist - UPDATED with instructor_id
    cur.execute("""
        INSERT INTO users (username, password, full_name, role, instructor_id) 
        VALUES 
            ('admin', 'admin123', 'Admin User', 'admin', NULL),
            ('ahmadyacine', 'op123', 'Operations One', 'operations', NULL),
            ('op2', 'op123', 'Operations Two', 'operations', NULL),
            ('inst1', 'inst123', 'Instructor One', 'instructor', 1)
        ON CONFLICT (username) DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()