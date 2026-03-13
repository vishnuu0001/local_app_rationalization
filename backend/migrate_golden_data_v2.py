"""Migration: add new columns to golden_data table (idempotent)."""
import sqlite3, os, sys

db_path = os.path.join(os.path.dirname(__file__), "instance", "infra_assessment.db")
if not os.path.exists(db_path):
    print("DB not found:", db_path); sys.exit(1)

NEW_COLS = [
    ("cloud_suitability",                       "TEXT"),
    ("volume_external_dependencies",            "TEXT"),
    ("distributed_architecture_design",         "TEXT"),
    ("level_of_data_residency_compliance",      "TEXT"),
    ("data_classification",                     "TEXT"),
    ("app_regulatory_contractual_requirements", "TEXT"),
    ("impact_due_to_data_loss",                 "TEXT"),
    ("financial_impact_due_to_unavailability",  "TEXT"),
    ("business_criticality",                    "TEXT"),
    ("customer_facing",                         "TEXT"),
    ("application_status_lifecycle_state",      "TEXT"),
    ("availability_requirements",               "TEXT"),
    ("support_level",                           "TEXT"),
    ("business_function_readiness",             "TEXT"),
    ("level_of_internal_governance",            "TEXT"),
    ("no_of_internal_users",                    "TEXT"),
    ("no_of_external_users",                    "TEXT"),
    ("estimated_app_growth",                    "TEXT"),
    ("impact_to_users",                         "TEXT"),
    ("ai_filled_cols",                          "TEXT"),
]

conn = sqlite3.connect(db_path)
cur  = conn.cursor()
cur.execute("PRAGMA table_info(golden_data)")
existing = {r[1] for r in cur.fetchall()}

added = []
for col_name, col_type in NEW_COLS:
    if col_name not in existing:
        cur.execute(f"ALTER TABLE golden_data ADD COLUMN {col_name} {col_type}")
        added.append(col_name)
    else:
        print(f"[SKIP] {col_name}")

conn.commit()
conn.close()
print("Added:", added if added else "(none — all already present)")
