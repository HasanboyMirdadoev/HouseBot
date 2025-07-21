class Database:
    def __init__(self, db_url):
        self.db_url = db_url
        self._ensure_tables()

    def connect(self):
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = True
        return conn

    def _ensure_tables(self):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'houses'
                );
            """)
            if not cursor.fetchone()[0]:
                cursor.execute("""
                    CREATE TABLE houses (
                        id SERIAL PRIMARY KEY,
                        district VARCHAR(255),
                        description TEXT,
                        price VARCHAR(50),
                        location VARCHAR(255)
                    );
                """)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'house_images'
                );
            """)
            if not cursor.fetchone()[0]:
                cursor.execute("""
                    CREATE TABLE house_images (
                        id SERIAL PRIMARY KEY,
                        house_id INTEGER REFERENCES houses(id),
                        image_url TEXT
                    );
                """)
        conn.close()

    def fetchall(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            result = cursor.fetchall()
        conn.close()
        return result

    def fetchone(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            result = cursor.fetchone()
        conn.close()
        return result

    def execute(self, query, params=None, returning=False):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if returning:
                result = cursor.fetchone()
            else:
                result = None
            conn.commit()
        conn.close()
        return result