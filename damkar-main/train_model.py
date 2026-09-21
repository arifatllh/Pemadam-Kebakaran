import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# =========================================================
# 1. LOAD DATASET
# =========================================================
df = pd.read_csv("dataset_urgensi_damkar_1500.csv")

print("=" * 50)
print("INFO DATASET")
print("=" * 50)
print("Kolom:", df.columns.tolist())
print("Jumlah baris:", len(df))

print("\nDistribusi target (tingkat_urgensi):")
print(df["tingkat_urgensi"].value_counts())


# =========================================================
# 2. FITUR & TARGET
# =========================================================
FEATURE_COLUMNS = [
    "skala_api",
    "korban_terjebak",
    "jumlah_korban",
    "jenis_bangunan",
    "kepadatan_lokasi",
]

TARGET_COLUMN = "tingkat_urgensi"

X = df[FEATURE_COLUMNS]
y = df[TARGET_COLUMN]


# =========================================================
# 3. SPLIT DATA
# =========================================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nData training: {len(X_train)} baris")
print(f"Data testing : {len(X_test)} baris")


# =========================================================
# 4. PIPELINE
# =========================================================
categorical_features = [
    "skala_api",
    "korban_terjebak",
    "jenis_bangunan",
    "kepadatan_lokasi",
]
numeric_features = ["jumlah_korban"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ("num", "passthrough", numeric_features),
    ]
)

model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )),
])


# =========================================================
# 5. TRAINING
# =========================================================
print("\nTraining model...")
model.fit(X_train, y_train)
print("✅ Training selesai")


# =========================================================
# 6. EVALUASI
# =========================================================
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\nAkurasi: {accuracy * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))


# =========================================================
# 7. TEST PREDIKSI MANUAL
# =========================================================
print("\nTest prediksi manual:")
contoh = pd.DataFrame([{
    "skala_api": "besar",
    "korban_terjebak": "ya",
    "jumlah_korban": 5,
    "jenis_bangunan": "pabrik",
    "kepadatan_lokasi": "tinggi",
}])
prediksi = model.predict(contoh)[0]
print(f"Input  : {contoh.to_dict('records')[0]}")
print(f"Hasil  : {prediksi}")


# =========================================================
# 8. SIMPAN MODEL
# =========================================================
joblib.dump(model, "model_urgensi_damkar.joblib")
print("\n✅ Model disimpan ke: model_urgensi_damkar.joblib")