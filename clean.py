import pandas as pd

# Load dataset
df = pd.read_csv("sales.csv")

print("Original shape:", df.shape)

# --------------------------------------------------
# 1. Remove unnecessary columns
# --------------------------------------------------

df.drop(
    columns=["Row ID+O6G3A1:R6", "ind1", "ind2"],
    inplace=True
)

# --------------------------------------------------
# 2. Convert date columns
# --------------------------------------------------

df["Order Date"] = pd.to_datetime(
    df["Order Date"],
    format="mixed",
    dayfirst=True
)

df["Ship Date"] = pd.to_datetime(
    df["Ship Date"],
    format="mixed",
    dayfirst=True
)

# --------------------------------------------------
# 3. Convert Returns into a binary flag
# --------------------------------------------------

df["Returned"] = df["Returns"].notna().astype(int)

# Remove original Returns column
df.drop(columns=["Returns"], inplace=True)

# --------------------------------------------------
# 4. Rename columns
# --------------------------------------------------

df.rename(columns={
    "Order ID": "order_id",
    "Order Date": "order_date",
    "Ship Date": "ship_date",
    "Ship Mode": "ship_mode",
    "Customer ID": "customer_id",
    "Customer Name": "customer_name",
    "Segment": "segment",
    "Country": "country",
    "City": "city",
    "State": "state",
    "Region": "region",
    "Product ID": "product_id",
    "Category": "category",
    "Sub-Category": "sub_category",
    "Product Name": "product_name",
    "Sales": "sales",
    "Quantity": "quantity",
    "Profit": "profit",
    "Payment Mode": "payment_mode"
}, inplace=True)

# --------------------------------------------------
# 5. Check result
# --------------------------------------------------

print("\nCleaned shape:", df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nData types:")
print(df.dtypes)

print("\nMissing values:")
print(df.isnull().sum())

print("\nFirst 10 rows:")
print(df.head(10))

# --------------------------------------------------
# 6. Save cleaned dataset
# --------------------------------------------------

df.to_csv("cleaned_sales_data.csv", index=False)

print("\nCleaned dataset saved as cleaned_sales_data.csv")