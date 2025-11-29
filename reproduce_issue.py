
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure the current directory is in sys.path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Mock psycopg2 before importing backend.database
sys.modules["psycopg2"] = MagicMock()
sys.modules["psycopg2.extras"] = MagicMock()

# Import the modules to ensure they are loaded before patching
import backend.database
from backend.routers.cubesats import list_cubesats
from backend.routers.workshops import list_workshops

# Mock the database connection
mock_conn = MagicMock()
mock_cursor = MagicMock()
mock_conn.cursor.return_value = mock_cursor

# Mock the get_connection function in the routers
with patch("backend.routers.cubesats.get_connection", return_value=mock_conn), \
     patch("backend.routers.workshops.get_connection", return_value=mock_conn):
    
    # Test case: Instructor user
    instructor_user = {
        "username": "rock",
        "full_name": "Rock Instructor",
        "role": "instructor",
        "instructor_id": 123
    }

    print("Testing list_cubesats with instructor user...")
    try:
        # Reset mock
        mock_cursor.reset_mock()
        
        list_cubesats(current_user=instructor_user)
        
        # Check the SQL query executed
        call_args = mock_cursor.execute.call_args
        if call_args:
            query = call_args[0][0]
            print(f"Executed Query: {query}")
            if "WHERE instructorid" in query:
                print("PASS: Query filters by instructorid")
            else:
                print("FAIL: Query does NOT filter by instructorid")
        else:
            print("FAIL: No query executed")
    except Exception as e:
        print(f"Error: {e}")

    print("\nTesting list_workshops with instructor user...")
    try:
        # Reset mock
        mock_cursor.reset_mock()
        
        list_workshops(current_user=instructor_user)
        
        # Check the SQL query executed
        call_args = mock_cursor.execute.call_args
        if call_args:
            query = call_args[0][0]
            print(f"Executed Query: {query}")
            if "WHERE instructor_id" in query:
                print("PASS: Query filters by instructor_id")
            else:
                print("FAIL: Query does NOT filter by instructor_id")
        else:
            print("FAIL: No query executed")
    except Exception as e:
        print(f"Error: {e}")
