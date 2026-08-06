"""
snowflake_test_config.py

Small Snowflake connection test using values stored in a local .env file.
No credentials or connection values are printed.
"""

import os
import sys
from pathlib import Path

import snowflake.connector
from snowflake.connector.errors import Error
from dotenv import load_dotenv


# Locate .env relative to this Python file.
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

# Load variables without overriding existing Windows environment variables.
load_dotenv(dotenv_path=ENV_FILE, override=False)


def require_env(name: str) -> str:
    """
    Return a required environment variable.

    Raise a clear error when the variable is missing or blank.
    """
    value = os.getenv(name, "").strip()

    if not value:
        raise ValueError(
            f"Required environment variable {name} is missing or blank."
        )

    return value


def build_connection_parameters() -> dict[str, str]:
    """Build Snowflake connection parameters from environment variables."""

    parameters = {
        "user": require_env("SNOWFLAKE_USER"),
        "account": require_env("SNOWFLAKE_ACCOUNT"),
        "warehouse": require_env("SNOWFLAKE_WAREHOUSE"),
        "database": require_env("SNOWFLAKE_DATABASE"),
        "schema": require_env("SNOWFLAKE_SCHEMA"),
        "authenticator": os.getenv(
            "SNOWFLAKE_AUTHENTICATOR",
            "externalbrowser",
        ).strip(),
    }

    # Role is optional. Snowflake will use the user's default role when omitted.
    role = os.getenv("SNOWFLAKE_ROLE", "").strip()

    if role:
        parameters["role"] = role

    return parameters


def test_connection() -> None:
    """Connect to Snowflake and display the active session context."""

    connection = None

    try:
        if not ENV_FILE.exists():
            raise FileNotFoundError(
                f"No .env file was found at:\n{ENV_FILE}"
            )

        connection_parameters = build_connection_parameters()

        print("Opening Snowflake connection...")
        print("Complete the corporate browser login when prompted.")

        connection = snowflake.connector.connect(
            **connection_parameters
        )

        query = """
            SELECT
                CURRENT_USER()      AS CURRENT_USER,
                CURRENT_ROLE()      AS CURRENT_ROLE,
                CURRENT_WAREHOUSE() AS CURRENT_WAREHOUSE,
                CURRENT_DATABASE()  AS CURRENT_DATABASE,
                CURRENT_SCHEMA()    AS CURRENT_SCHEMA
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()

        labels = [
            "User",
            "Role",
            "Warehouse",
            "Database",
            "Schema",
        ]

        print("\nSnowflake connection succeeded.")

        for label, value in zip(labels, result):
            print(f"{label:<10}: {value}")

    except FileNotFoundError as exc:
        print(f"\nConfiguration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    except ValueError as exc:
        print(f"\nConfiguration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    except Error as exc:
        print("\nSnowflake connection failed.", file=sys.stderr)
        print(f"Error code: {exc.errno}", file=sys.stderr)
        print(f"SQL state:  {exc.sqlstate}", file=sys.stderr)
        print(f"Message:    {exc.msg}", file=sys.stderr)
        sys.exit(1)

    except Exception as exc:
        print(
            f"\nUnexpected error: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    test_connection()