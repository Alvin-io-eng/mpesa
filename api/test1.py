import psycopg2
from urllib.parse import urlparse

DATABASE_URL = "your_database_url_here"
url = urlparse(DATABASE_URL)

try:
    conn = psycopg2.connect(
        host=url.hostname,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        port=url.port or 5432,
        sslmode='require'
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")