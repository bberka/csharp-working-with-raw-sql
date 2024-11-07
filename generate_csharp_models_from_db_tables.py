import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection configuration from .env file
server = os.getenv('DB_SERVER')
database = os.getenv('DB_DATABASE')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
table_output_path = os.getenv('TABLE_OUTPUT_PATH', './TableModels')
use_nullable_types = os.getenv('USE_NULLABLE_TYPES', 'true').lower() == 'true'
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Ensure output directory exists
os.makedirs(table_output_path, exist_ok=True)

# Template for C# class
class_template = """
public partial class {class_name}
{{
{properties}
}}
"""

def get_table_columns(cursor, table_name):
    """Get columns for a table with data type information."""
    query = """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
    """
    cursor.execute(query, table_name)
    return cursor.fetchall()

def map_sql_to_csharp(sql_type, max_length, is_nullable):
    """Map SQL data types to C# data types."""
    mapping = {
        'int': 'int',
        'bigint': 'long',
        'smallint': 'short',
        'tinyint': 'byte',
        'bit': 'bool',
        'decimal': 'decimal',
        'numeric': 'decimal',
        'float': 'float',
        'real': 'float',
        'datetime': 'DateTime',
        'smalldatetime': 'DateTime',
        'char': 'string',
        'varchar': 'string',
        'text': 'string',
        'nchar': 'string',
        'nvarchar': 'string',
        'ntext': 'string'
    }
    csharp_type = mapping.get(sql_type, 'object')
    # Apply nullable type if applicable and configured in .env
    if is_nullable == 'YES' and csharp_type != 'string' and use_nullable_types:
        csharp_type += "?"
    return csharp_type

def generate_csharp_class(table_name, columns):
    """Generate a C# class model for a table."""
    class_name = table_name
    properties = ""

    for column in columns:
        column_name = column[0]
        sql_type = column[1]
        max_length = column[2]
        is_nullable = column[3]
        csharp_type = map_sql_to_csharp(sql_type, max_length, is_nullable)
        properties += f"    public {csharp_type} {column_name} {{ get; set; }}\n"

    return class_template.format(class_name=class_name, properties=properties)

def main():
    # Connect to the database
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # Fetch table names from the database
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = cursor.fetchall()

    # Generate and save C# models
    for table in tables:
        table_name = table[0]
        columns = get_table_columns(cursor, table_name)
        class_code = generate_csharp_class(table_name, columns)

        # Output the C# class to a file
        file_path = os.path.join(table_output_path, f"{table_name}.cs")
        with open(file_path, "w") as file:
            file.write(class_code)
        print(f"Generated model for table {table_name} at {file_path}")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
