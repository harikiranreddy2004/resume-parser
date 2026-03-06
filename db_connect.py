import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="resume_parser_db",
    user="postgres",
    password="2004",
    port="5432"
)

cursor = conn.cursor()

print("Database connected successfully")