import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='123456')
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Check user
cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'driftsense'")
if not cur.fetchone():
    cur.execute("CREATE USER driftsense WITH PASSWORD 'driftsense_password' SUPERUSER;")
    print("User 'driftsense' created.")
else:
    print("User 'driftsense' already exists.")

# Check database
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'driftsense'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE driftsense OWNER driftsense;")
    print("Database 'driftsense' created.")
else:
    print("Database 'driftsense' already exists.")

cur.close()
conn.close()

# Now connect to driftsense database and ensure uuid-ossp extension
conn = psycopg2.connect(host='localhost', port=5432, user='driftsense', password='driftsense_password', dbname='driftsense')
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
print("Extension uuid-ossp enabled.")
cur.close()
conn.close()
print("PostgreSQL setup completed successfully.")
