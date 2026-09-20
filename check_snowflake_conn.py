"""
Snowflake connection checker.
Run this directly (bypasses dbt) to isolate whether the problem is
credentials/account vs. dbt profile config.

Usage:
    pip install snowflake-connector-python --break-system-packages
    python check_snowflake_conn.py
"""

import getpass
import sys

try:
    import snowflake.connector
except ImportError:
    sys.exit("snowflake-connector-python not installed. Run:\n"
              "  pip install snowflake-connector-python")


def check_connection():
    print("=== Snowflake Connection Check ===\n")

    account = input("Account identifier (e.g. GAJCCDQ-DO57900): ").strip()
    user = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    role = input("Role [DBT_ROLE]: ").strip() or "DBT_ROLE"
    warehouse = input("Warehouse [ZOMATO_WH]: ").strip() or "ZOMATO_WH"
    database = input("Database [ZOMATO]: ").strip() or "ZOMATO"
    schema = input("Schema [STAGING]: ").strip() or "STAGING"

    print("\nAttempting connection...\n")

    try:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            role=role,
            warehouse=warehouse,
            database=database,
            schema=schema,
            login_timeout=15,
        )
        cs = conn.cursor()
        try:
            cs.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
                       "CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_VERSION()")
            row = cs.fetchone()
            print("✅ CONNECTION SUCCESSFUL\n")
            print(f"  Logged in as : {row[0]}")
            print(f"  Active role  : {row[1]}")
            print(f"  Warehouse    : {row[2]}")
            print(f"  Database     : {row[3]}")
            print(f"  Schema       : {row[4]}")
            print(f"  Snowflake ver: {row[5]}")
        finally:
            cs.close()
            conn.close()

    except snowflake.connector.errors.DatabaseError as e:
        print("❌ CONNECTION FAILED\n")
        print(f"  Error code : {getattr(e, 'errno', 'n/a')}")
        print(f"  SQL state  : {getattr(e, 'sqlstate', 'n/a')}")
        print(f"  Message    : {e.msg if hasattr(e, 'msg') else e}\n")

        msg = str(e).lower()
        if "incorrect username or password" in msg:
            print("Diagnosis: Snowflake is rejecting the credentials themselves.")
            print("Checklist:")
            print("  1. Log into https://app.snowflake.com directly with the")
            print("     SAME username/password to confirm they work in the browser.")
            print("  2. If browser login also fails -> password is wrong/expired,")
            print("     reset it in Snowsight (Admin > Users) or ask your account admin.")
            print("  3. If browser login works but this script fails -> check whether")
            print("     your user has MFA/SSO enforced (password auth alone will always")
            print("     fail in that case; you'd need 'authenticator=externalbrowser'")
            print("     or key-pair auth instead).")
            print("  4. Double check the account identifier format — copy it exactly")
            print("     from Snowsight URL (Admin > Accounts), it may need a region/cloud")
            print("     suffix like 'xy12345.us-east-1'.")
        elif "role" in msg:
            print("Diagnosis: Auth succeeded but role/warehouse/db/schema may be wrong")
            print("or not granted to this user. Check with SHOW GRANTS TO USER <user>;")
        else:
            print("Diagnosis: Unclassified error — check network/account URL reachability.")

    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    check_connection()