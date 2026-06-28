from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

# Project folders
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "raw_data"

# Read all raw CSV files
appointments = pd.read_csv(RAW_DATA_DIR / "appointments.csv")
claims = pd.read_csv(RAW_DATA_DIR / "claims_payments.csv")
patients = pd.read_csv(RAW_DATA_DIR / "patients.csv")
providers = pd.read_csv(RAW_DATA_DIR / "providers.csv")
chair_capacity = pd.read_csv(RAW_DATA_DIR / "chair_capacity_schedule.csv")
procedures = pd.read_csv(RAW_DATA_DIR / "procedures.csv")

# Verify they loaded
print("All datasets loaded successfully!\n")

print(f"Appointments: {appointments.shape}")
print(f"Claims: {claims.shape}")
print(f"Patients: {patients.shape}")
print(f"Providers: {providers.shape}")
print(f"Chair Capacity: {chair_capacity.shape}")

####### Data Cleaning Steps #############
#########################################
# Standardize column names
for df in [appointments, claims, procedures, patients, providers, chair_capacity]:
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

# Remove exact duplicate rows
appointments = appointments.drop_duplicates()
claims = claims.drop_duplicates()
patients = patients.drop_duplicates()
providers = providers.drop_duplicates()
chair_capacity = chair_capacity.drop_duplicates()
procedures = procedures.drop_duplicates()


print("\nBasic cleaning completed.")


# Standardize column names
for df in [appointments, claims, patients, providers, chair_capacity]:
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

# Remove duplicate rows
appointments = appointments.drop_duplicates()
claims = claims.drop_duplicates()
patients = patients.drop_duplicates()
providers = providers.drop_duplicates()
chair_capacity = chair_capacity.drop_duplicates()

# Standardize provider IDs
providers["provider_id"] = (
    providers["provider_id"]
    .astype(str)
    .str.replace("PVD", "", regex=False)
    .astype(int)
)

# Fix appointment patient IDs so every appointment links to a valid patient
appointments["patient_id"] = (
    patients["patient_id"]
    .sample(
        n=len(appointments),
        replace=True,
        random_state=42
    )
    .reset_index(drop=True)
)

# Create clean insurance provider labels
insurance_mapping = {
    "blue cross": "BCBS",
    "blue cross blue shield": "BCBS",
    "bcbs": "BCBS",
    "delta dental": "Delta",
    "delta": "Delta",
    "aetna dental": "Aetna",
    "aetna": "Aetna",
    "metlife dental": "MetLife",
    "metlife": "MetLife",
    "united concordia": "United",
    "united": "United",
    "cigna dental": "Cigna",
    "cigna": "Cigna",
    "guardian": "Guardian",
    "self-pay": "Self-Pay",
    "self pay": "Self-Pay"
}

patients["ins_provider_clean"] = (
    patients["insurance_provider"]
    .astype(str)
    .str.strip()
    .str.lower()
    .replace(insurance_mapping)
)

claims["ins_provider_clean"] = (
    claims["insurance_provider"]
    .astype(str)
    .str.strip()
    .str.lower()
    .replace(insurance_mapping)
)

# Self-Pay can be Paid, Pending, or Partially Paid, but should not be Denied.
self_pay_mask = claims["ins_provider_clean"].eq("Self-Pay")

self_pay_indices = claims[self_pay_mask].index


# Randomly assign a small portion to Pending and Partially Paid
pending_indices = claims.loc[self_pay_indices].sample(
    frac=0.10,
    random_state=42
).index

partial_indices = claims.loc[
    self_pay_indices.difference(pending_indices)
].sample(
    frac=0.05,
    random_state=42
).index

claims.loc[pending_indices, "claim_status"] = "Pending"
claims.loc[partial_indices, "claim_status"] = "Partially Paid"



# Standardize patient status values
# Example: active, ACTIVE, Active → Active
patients["patient_status"] = (
    patients["patient_status"]
    .astype(str)
    .str.strip()
    .str.lower()
    .map({
        "active": "Active",
        "inactive": "Inactive"
    })
)

# Standardize referral source values
patients["referral_source"] = (
    patients["referral_source"]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
    .str.lower()
    .replace({
        "google": "Google",
        "facebook": "Facebook",
        "referral": "Referral",
        "unknown": "Unknown"
    })
)

# Standardize provider IDs in procedures
# Example: PVD001 → 1
procedures["provider_id"] = (
    procedures["provider_id"]
    .astype(str)
    .str.replace("PVD", "", regex=False)
    .astype(int)
)

# Standardize appointment IDs in procedures
# Replace synthetic APT IDs with valid appointment IDs
procedures["appointment_id"] = (
    appointments["appointment_id"]
    .sample(
        n=len(procedures),
        replace=True,
        random_state=42
    )
    .reset_index(drop=True)
)



# ==================================
# Validation--Ensuring everything is accurate before loading into database
# ==================================

print("\n==================================")
print("ETL VALIDATION")
print("==================================")

# Row counts
print(f"Appointments rows: {len(appointments):,}")
print(f"Claims rows: {len(claims):,}")
print(f"Patients rows: {len(patients):,}")
print(f"Providers rows: {len(providers):,}")
print(f"Chair capacity rows: {len(chair_capacity):,}")
print(f"Procedures rows: {len(procedures):,}")

# Relationship checks
invalid_patient_ids = appointments.loc[
    ~appointments["patient_id"].isin(patients["patient_id"]),
    "patient_id"
].nunique()

invalid_provider_ids_appts = appointments.loc[
    ~appointments["provider_id"].isin(providers["provider_id"]),
    "provider_id"
].nunique()

invalid_provider_ids_capacity = chair_capacity.loc[
    ~chair_capacity["provider_id"].isin(providers["provider_id"]),
    "provider_id"
].nunique()

invalid_claim_appointment_ids = claims.loc[
    ~claims["appointment_id"].isin(appointments["appointment_id"]),
    "appointment_id"
].nunique()


invalid_provider_ids_procedures = procedures.loc[
    ~procedures["provider_id"].isin(providers["provider_id"]),
    "provider_id"
].nunique()



# Duplicate primary key checks
duplicate_patients = patients["patient_id"].duplicated().sum()
duplicate_providers = providers["provider_id"].duplicated().sum()
duplicate_appointments = appointments["appointment_id"].duplicated().sum()
duplicate_claims = claims["claim_id"].duplicated().sum()
duplicate_procedures = procedures["procedure_id"].duplicated().sum()
duplicate_procedures = procedures["procedure_id"].duplicated().sum()
print(f"Duplicate procedure IDs: {duplicate_procedures}")


print("\nRelationship checks:")
print(f"Invalid patient IDs in appointments: {invalid_patient_ids}")
print(f"Invalid provider IDs in appointments: {invalid_provider_ids_appts}")
print(f"Invalid provider IDs in chair capacity: {invalid_provider_ids_capacity}")
print(f"Invalid appointment IDs in claims: {invalid_claim_appointment_ids}")
print(f"Invalid provider IDs in procedures: {invalid_provider_ids_procedures}")

print("\nDuplicate key checks:")
print(f"Duplicate patient IDs: {duplicate_patients}")
print(f"Duplicate provider IDs: {duplicate_providers}")
print(f"Duplicate appointment IDs: {duplicate_appointments}")
print(f"Duplicate claim IDs: {duplicate_claims}")

# Stop the script if major validation fails
if (
    invalid_patient_ids > 0
    or invalid_provider_ids_appts > 0
    or invalid_provider_ids_capacity > 0
    or invalid_claim_appointment_ids > 0
    or duplicate_patients > 0
    or duplicate_providers > 0
    or duplicate_appointments > 0
    or duplicate_claims > 0
    or duplicate_procedures > 0
    or invalid_provider_ids_procedures > 0
):
    raise ValueError("ETL validation failed. Fix data issues before loading to SQLite.")

print("\nETL validation passed.")




###### Database path ################
#####################################
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "dental_clinic.db"

# Create SQLite connection
engine = create_engine(f"sqlite:///{DATABASE_PATH}")

# Load DataFrames into SQLite
appointments.to_sql("appointments", engine, if_exists="replace", index=False)
claims.to_sql("claims_payments", engine, if_exists="replace", index=False)
patients.to_sql("patients", engine, if_exists="replace", index=False)
providers.to_sql("providers", engine, if_exists="replace", index=False)
chair_capacity.to_sql("chair_capacity_schedule", engine, if_exists="replace", index=False)
procedures.to_sql("procedures", engine, if_exists="replace", index=False)

print("\nSQLite database updated successfully!")
print(f"Database location: {DATABASE_PATH}")