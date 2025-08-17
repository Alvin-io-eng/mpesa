import psycopg2


DATABASE_URL = "postgresql://postgres:AD167cQvdGqDRzRz@db.tlbhsksctewsqrlpvujz.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)