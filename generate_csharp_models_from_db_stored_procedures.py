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
generate_empty_classes = os.getenv('GENERATE_EMPTY_CLASSES', 'false').lower() == 'true'
input_output_path = os.getenv('INPUT_OUTPUT_PATH', './')
output_output_path = os.getenv('OUTPUT_OUTPUT_PATH', './')
connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

os.makedirs(input_output_path, exist_ok=True)
os.makedirs(output_output_path, exist_ok=True)

# Template for C# class
class_template = """
public sealed partial class {class_name}
{{
{properties}
}}
"""

def get_stored_procedure_parameters(cursor, procedure_name):
    """Get parameters for a stored procedure, separating inputs and outputs."""
    query = """
        SELECT PARAMETER_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, PARAMETER_MODE
        FROM INFORMATION_SCHEMA.PARAMETERS
        WHERE SPECIFIC_NAME = ?
        ORDER BY ORDINAL_POSITION
    """
    cursor.execute(query, procedure_name)
    parameters = cursor.fetchall()
    inputs, outputs = [], []

    for param in parameters:
        param_name = param[0].replace('@', '')  # Remove @ from parameter name
        data_type = param[1]
        max_length = param[2]
        mode = param[3]
        if mode == 'IN':
            inputs.append((param_name, data_type, max_length))
        else:
            outputs.append((param_name, data_type, max_length))

    return inputs, outputs

def map_sql_to_csharp(sql_type, max_length):
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
    return csharp_type if sql_type != 'string' or max_length <= 0 else f"{csharp_type}?"

def generate_csharp_class(procedure_name, parameters, class_suffix):
    """Generate a C# class model for a stored procedure's parameters."""
    class_name = f"{procedure_name}{class_suffix}"
    properties = ""

    for param in parameters:
        param_name = param[0]
        sql_type = param[1]
        max_length = param[2]
        csharp_type = map_sql_to_csharp(sql_type, max_length)
        properties += f"    public {csharp_type} {param_name} {{ get; set; }}\n"

    # Skip empty classes if the option is set in .env
    if not generate_empty_classes and not properties.strip():
        return None

    return class_template.format(class_name=class_name, properties=properties)

def main():
    # Connect to the database
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # Fetch stored procedure names from the database
    cursor.execute("SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE='PROCEDURE'")
    procedures = cursor.fetchall()

    # Generate and save C# models
    for procedure in procedures:
        procedure_name = procedure[0]
        inputs, outputs = get_stored_procedure_parameters(cursor, procedure_name)

        # Generate input class
        if inputs:
            input_class_code = generate_csharp_class(procedure_name, inputs, "Input")
            if input_class_code:
                filename = f"SqlRequest{procedure_name}.cs"
                input_file_path = os.path.join(input_output_path, filename)
                with open(input_file_path, "w") as file:
                    file.write(input_class_code)
                    print(f"Input model created: {filename}")

        # Generate output class
        if outputs:
            output_class_code = generate_csharp_class(procedure_name, outputs, "Output")
            if output_class_code:
                filename = f"SqlResult{procedure_name}.cs"
                output_file_path = os.path.join(output_output_path,filename )
                with open(output_file_path, "w") as file:
                    file.write(output_class_code)
                    print(f"Output model created: {filename}")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    main()
