import csv

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from openai import OpenAI
from django.conf import settings
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import base64
from io import BytesIO
import json
import sqlite3
import os

from backend.settings import MEDIA_ROOT

def csv_to_db(name):
    csv_file_path =  MEDIA_ROOT + '/csv/' + name + '.csv'

    # Подключение к SQLite базе данных
    conn = sqlite3.connect(MEDIA_ROOT + name + '.db')
    cursor = conn.cursor()

    # Чтение данных из CSV файла
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames  # Получаем названия столбцов из заголовков CSV

        # Удаление дубликатов из названий столбцов
        unique_columns = []
        seen = set()
        for col in columns:
            if col in seen:
                # Добавляем суффикс для устранения дубликата
                count = 1
                new_col = f"{col}_{count}"
                while new_col in seen:
                    count += 1
                    new_col = f"{col}_{count}"
                unique_columns.append(new_col)
                seen.add(new_col)
            else:
                unique_columns.append(col)
                seen.add(col)

        # Создание таблицы с динамической структурой
        table_name = 'data'
        column_definitions = ', '.join([f'"{col}" TEXT' for col in unique_columns])  # Все столбцы как TEXT
        create_table_query = f'CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions})'
        cursor.execute(create_table_query)

        # Подготовка данных для вставки
        rows = [tuple(row[col] if col in row else None for col in columns) for row in reader]
        placeholders = ', '.join(['?' for _ in unique_columns])  # Плейсхолдеры для значений
        quoted_columns = ', '.join([f'"{col}"' for col in unique_columns])  # Заключаем названия колонок в кавычки
        insert_query = f'INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})'

        # Добавление данных в таблицу
        cursor.executemany(insert_query, rows)

    # Сохранение изменений и закрытие подключения
    conn.commit()
    conn.close()

    print("Данные успешно загружены в таблицу SQLite.")

# Initialize OpenAI with the API key
client = OpenAI(api_key=settings.OPENAI_AI_KEY)
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def process_query_and_visualize(request):
    """Process natural language query and create visualization."""
    if request.method == 'GET':
        return render(request, 'ai.html')

    try:
        data = json.loads(request.body)
        user_query = data.get('query', '').strip()

        if(request.user.is_authenticated):
            db_path = MEDIA_ROOT + data.get('db_path', '').strip() + '.db'
            csv_to_db(data.get('db_path', '').strip())

            connection = sqlite3.connect(db_path)
            cursor = connection.cursor()

            # Fetch table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            # Get schema details for each table
            schema_details = []
            for table_name, in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()

                cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                foreign_keys = cursor.fetchall()

                schema_details.append({
                    "table_name": table_name,
                    "columns": columns,
                    "foreign_keys": foreign_keys,
                })

            # Generate schema representation
            schema_representation = []
            for table in schema_details:
                table_name = table["table_name"]
                schema_representation.append(f"-- Table: {table_name}")
                schema_representation.append(f"CREATE TABLE {table_name} (")

                column_definitions = []
                for column in table["columns"]:
                    col_name = column[1]
                    col_type = column[2]
                    col_nullable = "NOT NULL" if column[3] == 0 else ""
                    col_pk = "PRIMARY KEY" if column[5] == 1 else ""
                    column_definitions.append(f"  {col_name} {col_type} {col_nullable} {col_pk}".strip())

                schema_representation.extend(column_definitions)

                if table["foreign_keys"]:
                    schema_representation.append(",\n  -- Foreign Keys:")
                    for fk in table["foreign_keys"]:
                        fk_def = f"  FOREIGN KEY ({fk[3]}) REFERENCES {fk[2]}({fk[4]})"
                        schema_representation.append(fk_def)

                schema_representation.append(");")
                schema_representation.append("")

            schema_sql = "\n".join(schema_representation)
        else:
            db_path = MEDIA_ROOT + 'def/mydatabase.db'

        if not user_query or not db_path:
            return JsonResponse({
                'error': 'Both query and database path are required'
            }, status=400)

        print("us" + schema_sql)
        # Generate SQL query using GPT
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a SQL expert. Convert natural language queries to SQL for the following schema. Return ONLY the SQL query without any explanations or markdown: {schema_sql}
                    );"""
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ],
            temperature=0,
            max_tokens=500
        )

        sql_query = response.choices[0].message.content.strip()

        # Validate database path
        if not os.path.isabs(db_path):
            raise ValueError("Database path must be absolute")
        if not db_path.endswith('.db'):
            raise ValueError("Only .db files are allowed")
        if not os.path.exists(db_path):
            raise FileNotFoundError("Database file not found")

        # Execute query and fetch data using pandas
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(sql_query, conn)

        if df.empty:
            return JsonResponse({
                'message': 'Query executed successfully but returned no results',
                'sql_query': sql_query,
                'query_results': []
            })

        # Convert DataFrame to list of dictionaries
        query_results = df.to_dict(orient='records')
        print(query_results)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "based on query select and request from user make a conclusion about statistic"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{user_query} {query_results}",
                        }
                    ]
                }
            ],
            response_format={
                "type": "text"
            },
            temperature=0,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        text = response.choices[0].message.content.strip()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "based on data and a diagram that user want to see return data for visualizing in python and save it as image and save it as image with name img return only python code and dont write python on start"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{user_query} {query_results}",
                        }
                    ]
                }
            ],
            response_format={
                "type": "text"
            },
            temperature=0,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        code = response.choices[0].message.content.strip()
        if code.startswith("```python") and code.endswith("```"):
            code = code[9:-3].strip()  # Remove the "```python" and "```"
        print(code)
        exec (code)
        img_path = '/home/easwirt/1_projects/python/SegFault/backend/img.png'
        with open(img_path, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        # Create visualization
        return JsonResponse({
            'query_results': query_results,
            'sql_query': sql_query,
            'visualization': img_base64,
            'text': text
        })

    except ValueError as e:
        return JsonResponse({'error': f'Validation error: {str(e)}'}, status=400)
    except FileNotFoundError as e:
        return JsonResponse({'error': f'File error: {str(e)}'}, status=400)
    except sqlite3.Error as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
