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
        db_path = data.get('db_path', '').strip()

        if not user_query or not db_path:
            return JsonResponse({
                'error': 'Both query and database path are required'
            }, status=400)

        # Generate SQL query using GPT
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """You are a SQL expert. Convert natural language queries to SQL for the following schema. Return ONLY the SQL query without any explanations or markdown:

                    CREATE TABLE Orders (
                        OrderID int,
                        CustomerID int,
                        OrderDate datetime,
                        OrderTime varchar(8),
                        PRIMARY KEY (OrderID)
                    );

                    CREATE TABLE OrderDetails (
                        OrderDetailID int,
                        OrderID int,
                        ProductID int,
                        Quantity int,
                        PRIMARY KEY (OrderDetailID)
                    );

                    CREATE TABLE Products (
                        ProductID int,
                        ProductName varchar(50),
                        Category varchar(50),
                        UnitPrice decimal(10, 2),
                        Stock int,
                        PRIMARY KEY (ProductID)
                    );

                    CREATE TABLE Customers (
                        CustomerID int,
                        FirstName varchar(50),
                        LastName varchar(50),
                        Email varchar(100),
                        Phone varchar(20),
                        PRIMARY KEY (CustomerID)
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
                            "text": "based on data and  a diagram that user want to see return data for visualizing in python return only python code and dont write python on start"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"based on this data make a relation diagram between orders and orders quantity {sql_query}"
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
        # Create visualization
        return JsonResponse({
            'query_results': query_results,
            'sql_query': sql_query
        })

    except ValueError as e:
        return JsonResponse({'error': f'Validation error: {str(e)}'}, status=400)
    except FileNotFoundError as e:
        return JsonResponse({'error': f'File error: {str(e)}'}, status=400)
    except sqlite3.Error as e:
        return JsonResponse({'error': f'Database error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
