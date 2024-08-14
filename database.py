import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',           # Change if needed
            user='root',                # Replace with your MySQL username
            password='',                # Replace with your MySQL password
            database='image_processing_db',
            port='3307'                 # Replace with your MySQL port if needed
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error: {e}")
    return None

def save_to_database(text):
    conn = get_db_connection()
    if conn is not None:
        cursor = conn.cursor()
        # Create the table if it does not exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_texts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            text TEXT NOT NULL
        )
        """)
        
        # Insert the entire text data into a single row
        cursor.execute("INSERT INTO extracted_texts (text) VALUES (%s)", (text,))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Text has been saved to the database.")
    else:
        print("Failed to connect to the database.")
