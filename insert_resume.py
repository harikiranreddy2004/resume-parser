import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="resume_parser_db",
    user="postgres",
    password="2004",
    port="5432"
)

cursor = conn.cursor()

query = """
INSERT INTO resumes
("Name","Job title","Key Hiring Assets","Education",
"Professional Summary","Project Exposure",
"Client Description","Roles & Responsibilities")
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
"""

data = (
    "Ganesh Mokadam",
    "SAP Technical Lead Consultant",
    "S/4HANA Migration, Fiori Apps, CDS Views, REST APIs",
    "MCA - Osmania University",
    "15 years experience in ABAP and S/4HANA",
    "S/4HANA Migration Project",
    "Macmillan publishing company",
    "Led SAP ABAP development and integrations"
)

cursor.execute(query, data)

conn.commit()

print("Resume inserted successfully")

cursor.close()
conn.close()