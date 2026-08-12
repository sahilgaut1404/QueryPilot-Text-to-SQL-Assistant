import pandas as pd
from sqlalchemy import create_engine

# -----------------------------
# MySQL connection details
# -----------------------------

username = "root"
password = "1404"
host = "localhost"
port = 3306
database = "text_to_sql"

# -----------------------------
# Create MySQL connection
# -----------------------------

engine = create_engine(
    f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
)

# -----------------------------
# Read cleaned CSV
# -----------------------------

df = pd.read_csv("cleaned_sales_data.csv")

print("CSV shape:", df.shape)

# -----------------------------
# Convert date columns
# -----------------------------

df["order_date"] = pd.to_datetime(df["order_date"])
df["ship_date"] = pd.to_datetime(df["ship_date"])

# -----------------------------
# Load data into MySQL
# -----------------------------

df.to_sql(
    "sales_data",
    con=engine,
    if_exists="append",
    index=False,
    chunksize=500
)

print("Data successfully loaded into MySQL!")