"""
Database utilities for Lambda functions
Connection pooling and query helpers for RDS PostgreSQL
"""
import os
import json
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Global connection pool (reused across Lambda invocations)
connection_pool = None


def get_db_secret():
    """Retrieve database credentials from Secrets Manager"""
    secret_arn = os.environ["DB_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def get_connection_pool():
    """Get or create database connection pool"""
    global connection_pool

    if connection_pool is None:
        secret = get_db_secret()
        db_config = {
            "host": os.environ["DB_PROXY_ENDPOINT"],
            "database": os.environ["DB_NAME"],
            "user": secret["username"],
            "password": secret["password"],
            "port": 5432,
            "sslmode": "require",
            "connect_timeout": 5,
        }

        connection_pool = SimpleConnectionPool(1, 10, **db_config)

    return connection_pool


def get_db_connection():
    """Get a connection from the pool"""
    pool = get_connection_pool()
    return pool.getconn()


def release_db_connection(conn):
    """Return a connection to the pool"""
    pool = get_connection_pool()
    pool.putconn(conn)


def execute_query(query, params=None, fetch=True):
    """
    Execute a database query with automatic connection management

    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: Whether to fetch results (False for INSERT/UPDATE/DELETE)

    Returns:
        List of dicts (if fetch=True) or None
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)

        if fetch:
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        else:
            conn.commit()
            cursor.close()
            return None

    except Exception as e:
        if conn:
            conn.rollback()
        raise e

    finally:
        if conn:
            release_db_connection(conn)
