from daos import get_connection

try:
    conn = get_connection()
    print("SUCCESS: Connection established")
    conn.close()
except Exception as e:
    print("ERROR:", e)