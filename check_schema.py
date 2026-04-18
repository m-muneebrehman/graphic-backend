import psycopg2
conn = psycopg2.connect('postgresql://postgres:Gmail.com123@db.xcbjvscvnilefhplbwxv.supabase.co:5432/postgres')
cur = conn.cursor()
# Insert a test 512-d vector and see if it works
import random
vec = "[" + ",".join(str(random.random()) for _ in range(512)) + "]"
try:
    cur.execute("INSERT INTO faces (embedding) VALUES (%s::vector) RETURNING grab_id", (vec,))
    gid = cur.fetchone()[0]
    conn.commit()
    print(f"512-d insert OK, grab_id={gid}")
    cur.execute("DELETE FROM faces WHERE grab_id=%s", (gid,))
    conn.commit()
    print("Cleanup OK")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
cur.close()
conn.close()
