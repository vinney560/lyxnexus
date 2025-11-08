from flask import Blueprint, jsonify
from sqlalchemy import text
from app import db

db_tools = Blueprint("db_tools", __name__, url_prefix='/db')

@db_tools.route("/fix-sequences", methods=["POST"])
def fix_sequences():
    try:
        # Query all sequences and their linked tables/columns
        sql = text("""
        SELECT 
            c.relname AS sequence_name,
            t.relname AS table_name,
            a.attname AS column_name
        FROM pg_class c
        JOIN pg_depend d ON d.objid = c.oid
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE c.relkind = 'S';
        """)
        
        sequences = db.session.execute(sql).fetchall()
        fixed = []

        for seq in sequences:
            seq_name = seq.sequence_name
            table_name = seq.table_name
            col_name = seq.column_name

            # Get the max ID of the table
            max_id = db.session.execute(
                text(f"SELECT COALESCE(MAX({col_name}), 0) FROM {table_name}")
            ).scalar()

            # Get current sequence value
            current_val = db.session.execute(
                text(f"SELECT last_value FROM {seq_name}")
            ).scalar()

            # Fix only if sequence is behind
            if current_val < max_id:
                db.session.execute(
                    text(f"SELECT setval('{seq_name}', {max_id})")
                )
                fixed.append({ "table": table_name, "sequence": seq_name, "new_value": max_id })

        db.session.commit()
        return jsonify({"status": "ok", "fixed": fixed})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

print("✅ DATABASE FIXING SCRIPT!!!")
print("!!!!FIX SCRIPT INITIATED!!!!")