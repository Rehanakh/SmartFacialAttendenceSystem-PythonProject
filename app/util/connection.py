import pyodbc

class DatabaseConnection:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            # Example connection string; you should replace it with your actual database connection details
            self.connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                                             'SERVER=localhost;'
                                             'DATABASE=attendance;'
                                             'UID=sa;'
                                             'PWD=sa@123')
            self.cursor = self.connection.cursor()
        except pyodbc.DatabaseError as e:
            print("Database connection error: ", e)
            # Handle connection errors as needed

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
        except pyodbc.Error as e:
            print("Error executing query: ", e)
            # Handle query execution errors as needed

    def fetch_all(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except pyodbc.Error as e:
            print("Error fetching data: ", e)
            # Handle data fetch errors as needed
            return []

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def commit(self):
        try:
            self.connection.commit()
        except pyodbc.Error as e:
            print("Error committing transaction: ", e)
            # Handle commit errors as needed


