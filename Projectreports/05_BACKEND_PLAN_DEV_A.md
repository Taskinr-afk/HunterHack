# Backend Plan — Developer A: Data & ML Pipeline

> **Your role:** Build everything behind the API — database, data fetching, cleaning, geospatial joins, feature engineering, ML training, and impact scoring. You produce the data and models that Developer B's API serves.

> **Your files — ONLY you edit these:**
> - `backend/app/database.py`
> - `backend/app/services/etl.py`
> - `backend/app/services/geospatial.py`
> - `backend/app/services/impact.py`
> - `backend/ml/feature_engineering.py`
> - `backend/ml/train_accident_risk.py`
> - `backend/ml/train_repair_timeline.py`
> - `backend/data/raw/` (downloaded data)
> - `backend/data/processed/` (cleaned data)

> **DO NOT touch these files (Developer B owns them):**
> - `backend/app/main.py`
> - `backend/app/schemas.py`
> - `backend/app/api/` (all endpoint files)
> - `backend/app/models/ml_models.py`
> - `backend/app/services/alert_service.py`

> **Shared contract with Developer B:**
> - You create the SQLite schema — B reads from it
> - You produce `ml/model_accident_risk.pkl` and `ml/model_repair_timeline.pkl` — B loads them
> - You compute `impact_score` on potholes — B serves it via API

---

## Phase 0: Python Environment Setup

### Step 0.1: Install Python
**What:** Python runs our backend and ML code.

**How:**
1. Go to https://www.python.org/downloads/
2. Download Python 3.11+ (3.11 or 3.12 recommended)
3. **Important:** Check "Add Python to PATH" during installation on Windows
4. Verify:
```bash
python --version    # Should show 3.11.x or 3.12.x
pip --version       # Should show pip 24.x
```

**If `python` doesn't work on Windows:** Try `py` instead, or restart your terminal.

---

### Step 0.2: Create a virtual environment
**What:** A virtual environment keeps this project's Python packages separate from your system Python.

```bash
cd ~/HunterHack
mkdir -p backend
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows with bash):
source venv/Scripts/activate

# Verify you're in the venv:
which python  # Should show .../backend/venv/bin/python or .../Scripts/python
```

**Every time you open a new terminal**, you need to activate the venv:
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
```

You'll know it's active when your terminal prompt shows `(venv)`.

---

### Step 0.3: Install all Python dependencies at once
**Create `backend/requirements.txt`:**
```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
pandas==2.2.3
numpy==2.1.0
scikit-learn==1.5.2
xgboost==2.1.1
joblib==1.4.2
python-dotenv==1.0.1
slowapi==0.5.1
pydantic==2.9.0
```

**Install:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
pip install -r requirements.txt
```

**Verify:**
```bash
python -c "import fastapi; print(fastapi.__version__)"  # Should print 0.115.0
python -c "import xgboost; print(xgboost.__version__)"  # Should print 2.1.1
```

---

### Step 0.4: Create project folder structure
```bash
cd ~/HunterHack/backend
mkdir -p app/{api,models,services}
mkdir -p ml
mkdir -p data/{raw,processed}
```

Your structure (only the parts you own):
```
backend/
├── app/
│   ├── __init__.py          ← Shared (create if missing)
│   ├── database.py         ← YOU OWN
│   ├── services/
│   │   ├── __init__.py     ← Shared (create if missing)
│   │   ├── etl.py          ← YOU OWN
│   │   ├── geospatial.py   ← YOU OWN
│   │   └── impact.py       ← YOU OWN
├── ml/
│   ├── feature_engineering.py       ← YOU OWN
│   ├── train_accident_risk.py       ← YOU OWN
│   └── train_repair_timeline.py     ← YOU OWN
├── data/
│   ├── raw/                 ← YOU OWN
│   └── processed/           ← YOU OWN
├── venv/
├── requirements.txt
└── .env
```

Create the empty `__init__.py` files (both developers need these):
```bash
cd ~/HunterHack/backend
touch app/__init__.py
touch app/api/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
```

---

## Phase 1: Database Setup

### Step 1.1: Create the database module
**What:** SQLite database with all the tables our app needs. This is the shared contract — Developer B will read from these tables.

**Create `backend/app/database.py`:**
```python
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./potholes.db").replace("sqlite:///", "")

def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS potholes (
                id TEXT PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                borough TEXT,
                zip_code TEXT,
                descriptor TEXT,
                status TEXT,
                created_date TEXT NOT NULL,
                closed_date TEXT,
                days_open INTEGER,
                street_segment TEXT,
                impact_score REAL
            );

            CREATE TABLE IF NOT EXISTS collisions (
                id TEXT PRIMARY KEY,
                crash_date TEXT,
                latitude REAL,
                longitude REAL,
                persons_injured INTEGER DEFAULT 0,
                persons_killed INTEGER DEFAULT 0,
                contributing_factor TEXT
            );

            CREATE TABLE IF NOT EXISTS pothole_collisions (
                pothole_id TEXT REFERENCES potholes(id),
                collision_id TEXT REFERENCES collisions(id),
                distance_m REAL,
                PRIMARY KEY (pothole_id, collision_id)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pothole_id TEXT REFERENCES potholes(id),
                sent_date TEXT,
                status TEXT DEFAULT 'sent',
                message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_potholes_status ON potholes(status);
            CREATE INDEX IF NOT EXISTS idx_potholes_borough ON potholes(borough);
            CREATE INDEX IF NOT EXISTS idx_potholes_location ON potholes(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_collisions_location ON collisions(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_alerts_pothole ON alerts(pothole_id);
        """)
    print(f"Database initialized at {DB_PATH}")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
```

**Run it:**
```bash
cd ~/HunterHack/backend
python -m app.database
# Should print: "Database initialized at potholes.db"
```

**Verify:**
```bash
ls potholes.db  # File should exist
```

---

## Phase 2: Data Ingestion (ETL)

### Step 2.1: Create the data fetcher
**What:** Download pothole and collision data from NYC Open Data.

**Create `backend/app/services/etl.py`:**
```python
import pandas as pd
import httpx
import os
from datetime import datetime
from app.database import get_db

NYC_311_API = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
NYC_COLLISIONS_API = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
NYC_TRAFFIC_API = "https://data.cityofnewyork.us/resource/bf4a-6vgj.json"

APP_TOKEN = os.getenv("NYC_OPENDATA_APP_TOKEN", "")

def fetch_potholes(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch pothole complaints from NYC 311."""
    params = {
        "$where": f"descriptor='Pothole' AND created_date > '{year_from}T00:00:00'",
        "$limit": limit,
        "$order": "created_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_311_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} pothole records")
    return df

def fetch_collisions(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch motor vehicle collision data."""
    params = {
        "$where": f"latitude IS NOT NULL AND crash_date > '{year_from}'",
        "$limit": limit,
        "$order": "crash_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_COLLISIONS_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} collision records")
    return df

def clean_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate pothole data."""
    # Keep only rows with valid coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # Convert types
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Filter to NYC bounding box
    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    # Normalize status
    df["status"] = df["status"].str.strip().str.lower()

    # Compute days_open
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")

    now = pd.Timestamp.now()
    df["days_open"] = (df["closed_date"].fillna(now) - df["created_date"]).dt.days
    df["days_open"] = df["days_open"].fillna(0).astype(int)

    # Select needed columns
    columns = ["unique_key", "latitude", "longitude", "borough", "incident_zip",
                "descriptor", "status", "created_date", "closed_date", "days_open"]
    df = df[[c for c in columns if c in df.columns]]

    # Rename to match our schema
    df = df.rename(columns={
        "unique_key": "id",
        "incident_zip": "zip_code",
    })

    df = df.dropna(subset=["id"])
    return df

def clean_collisions(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate collision data."""
    df = df.dropna(subset=["latitude", "longitude"])

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    df["persons_injured"] = pd.to_numeric(df.get("number_of_persons_injured", 0), errors="coerce").fillna(0).astype(int)
    df["persons_killed"] = pd.to_numeric(df.get("number_of_persons_killed", 0), errors="coerce").fillna(0).astype(int)

    columns = ["collision_id", "crash_date", "latitude", "longitude",
                "persons_injured", "persons_killed", "contributing_factor_vehicle_1"]
    df = df[[c for c in columns if c in df.columns]]

    df = df.rename(columns={
        "collision_id": "id",
        "contributing_factor_vehicle_1": "contributing_factor",
    })

    df = df.dropna(subset=["id"])
    return df

def save_potholes_to_db(df: pd.DataFrame):
    """Insert pothole data into SQLite."""
    with get_db() as conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO potholes
                (id, latitude, longitude, borough, zip_code, descriptor, status, created_date, closed_date, days_open)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("id", "")),
                float(row.get("latitude", 0)),
                float(row.get("longitude", 0)),
                str(row.get("borough", "")),
                str(row.get("zip_code", "")),
                str(row.get("descriptor", "")),
                str(row.get("status", "")),
                str(row.get("created_date", "")),
                str(row.get("closed_date", "")) if pd.notna(row.get("closed_date")) else None,
                int(row.get("days_open", 0)),
            ))
        conn.commit()
    print(f"Saved {len(df)} potholes to database")

def save_collisions_to_db(df: pd.DataFrame):
    """Insert collision data into SQLite."""
    with get_db() as conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO collisions
                (id, crash_date, latitude, longitude, persons_injured, persons_killed, contributing_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("id", "")),
                str(row.get("crash_date", "")),
                float(row.get("latitude", 0)),
                float(row.get("longitude", 0)),
                int(row.get("persons_injured", 0)),
                int(row.get("persons_killed", 0)),
                str(row.get("contributing_factor", "")),
            ))
        conn.commit()
    print(f"Saved {len(df)} collisions to database")

def run_etl():
    """Full ETL pipeline: fetch, clean, save."""
    print("Starting ETL pipeline...")

    # Step 1: Fetch data
    print("\n1. Fetching pothole data...")
    potholes_df = fetch_potholes(limit=50000, year_from="2024-01-01")

    print("\n2. Fetching collision data...")
    collisions_df = fetch_collisions(limit=50000, year_from="2024-01-01")

    # Step 2: Clean data
    print("\n3. Cleaning pothole data...")
    potholes_df = clean_potholes(potholes_df)

    print("\n4. Cleaning collision data...")
    collisions_df = clean_collisions(collisions_df)

    # Step 3: Save to database
    print("\n5. Saving potholes to database...")
    save_potholes_to_db(potholes_df)

    print("\n6. Saving collisions to database...")
    save_collisions_to_db(collisions_df)

    # Step 4: Run geospatial join
    print("\n7. Running geospatial join...")
    from app.services.geospatial import join_potholes_collisions
    join_potholes_collisions()

    print("\nETL pipeline complete!")

if __name__ == "__main__":
    run_etl()
```

---

### Step 2.2: Create the geospatial join service
**What:** Link collisions to nearby potholes using distance calculations.

**Create `backend/app/services/geospatial.py`:**
```python
import math
from app.database import get_db

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers using Haversine formula."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def join_potholes_collisions(radius_km: float = 0.025):
    """Find collisions within radius_km of each pothole.

    Default radius: 0.025 km = 25 meters
    """
    with get_db() as conn:
        potholes = conn.execute("""
            SELECT id, latitude, longitude, created_date, closed_date
            FROM potholes
        """).fetchall()

        collisions = conn.execute("""
            SELECT id, crash_date, latitude, longitude
            FROM collisions
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        """).fetchall()

    print(f"Joining {len(potholes)} potholes with {len(collisions)} collisions...")

    joined = 0
    with get_db() as conn:
        # Clear existing joins
        conn.execute("DELETE FROM pothole_collisions")

        for pothole in potholes:
            p_id, p_lat, p_lon, p_created, p_closed = pothole

            for collision in collisions:
                c_id, c_date, c_lat, c_lon = collision

                # Quick bounding box check first (much faster than haversine)
                lat_diff = abs(p_lat - c_lat)
                lon_diff = abs(p_lon - c_lon)
                if lat_diff > 0.001 or lon_diff > 0.001:  # ~100m rough check
                    continue

                # Precise distance check
                distance_km = haversine_km(p_lat, p_lon, c_lat, c_lon)
                if distance_km <= radius_km:
                    distance_m = distance_km * 1000
                    conn.execute("""
                        INSERT OR IGNORE INTO pothole_collisions
                        (pothole_id, collision_id, distance_m)
                        VALUES (?, ?, ?)
                    """, (p_id, c_id, round(distance_m, 1)))
                    joined += 1

        conn.commit()

    print(f"Found {joined} pothole-collision pairs within {radius_km*1000:.0f}m")

def update_collision_counts():
    """Update each pothole with its nearby collision count."""
    with get_db() as conn:
        conn.execute("""
            UPDATE potholes SET impact_score = (
                SELECT COUNT(*) * 0.2
                FROM pothole_collisions pc
                WHERE pc.pothole_id = potholes.id
            )
            WHERE impact_score IS NULL
        """)
        conn.commit()
    print("Updated collision-based impact scores")
```

---

### Step 2.3: Run ETL to populate data
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate

# Fetch data from NYC Open Data and load into SQLite
python -m app.services.etl
```

This will:
1. Fetch pothole data from NYC 311 API
2. Fetch collision data from NYPD API
3. Clean and validate both datasets
4. Save to SQLite
5. Run geospatial join (potholes ↔ collisions)

**Note:** This step takes 1-5 minutes depending on network speed and data volume.

**Verify:**
```bash
cd ~/HunterHack/backend
python -c "
from app.database import get_db
with get_db() as conn:
    p = conn.execute('SELECT COUNT(*) FROM potholes').fetchone()[0]
    c = conn.execute('SELECT COUNT(*) FROM collisions').fetchone()[0]
    pc = conn.execute('SELECT COUNT(*) FROM pothole_collisions').fetchone()[0]
    print(f'Potholes: {p}, Collisions: {c}, Joined pairs: {pc}')
"
```

---

## Phase 3: Feature Engineering

### Step 3.1: Create feature engineering
**What:** Transform raw pothole data into ML-ready features.

**Create `backend/ml/feature_engineering.py`:**
```python
import pandas as pd
import numpy as np
from app.database import get_db

def build_features():
    """Build ML features from database data.

    Returns a DataFrame with one row per pothole and columns for features.
    """
    with get_db() as conn:
        potholes = pd.read_sql("SELECT * FROM potholes", conn)
        collisions = pd.read_sql("""
            SELECT p.id as pothole_id, COUNT(pc.collision_id) as nearby_collisions
            FROM potholes p
            LEFT JOIN pothole_collisions pc ON p.id = pc.pothole_id
            GROUP BY p.id
        """, conn)

    # Merge collision counts
    df = potholes.merge(collisions, on="pothole_id", how="left")
    df["nearby_collisions"] = df["nearby_collisions"].fillna(0).astype(int)

    # Feature engineering
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["month"] = df["created_date"].dt.month
    df["day_of_week"] = df["created_date"].dt.dayofweek

    # Borough encoding
    borough_map = {
        "Manhattan": 0, "Brooklyn": 1, "Queens": 2,
        "Bronx": 3, "Staten Island": 4,
    }
    df["borough_encoded"] = df["borough"].map(borough_map).fillna(-1).astype(int)

    # Binary target: has nearby collision?
    df["has_nearby_accident"] = (df["nearby_collisions"] > 0).astype(int)

    # For repair timeline: only closed potholes
    df["days_to_close"] = None
    closed_mask = df["status"] == "closed"
    if closed_mask.any():
        df.loc[closed_mask, "closed_date"] = pd.to_datetime(
            df.loc[closed_mask, "closed_date"], errors="coerce"
        )
        df.loc[closed_mask, "days_to_close"] = (
            df.loc[closed_mask, "closed_date"] - df.loc[closed_mask, "created_date"]
        ).dt.days

    # Traffic volume (proxy: use borough average if not available)
    # For hackathon, use a simple proxy based on borough
    borough_traffic = {
        "Manhattan": 25000,
        "Brooklyn": 15000,
        "Queens": 18000,
        "Bronx": 12000,
        "Staten Island": 8000,
    }
    df["traffic_volume_aadt"] = df["borough"].map(borough_traffic)

    # Nearby pothole count (within 100m — approximate with zip code for speed)
    pothole_counts_by_zip = df.groupby("zip_code").size().reset_index(name="nearby_pothole_count")
    df = df.merge(pothole_counts_by_zip, on="zip_code", how="left")
    df["nearby_pothole_count"] = df["nearby_pothole_count"].fillna(1).astype(int)

    # Select final feature columns
    feature_cols = [
        "pothole_id", "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month", "day_of_week", "latitude", "longitude",
        "has_nearby_accident", "nearby_collisions", "days_to_close", "status"
    ]

    df = df[[c for c in feature_cols if c in df.columns]]

    # Save to CSV for inspection
    df.to_csv("data/processed/features.csv", index=False)
    print(f"Built features for {len(df)} potholes → data/processed/features.csv")

    return df

if __name__ == "__main__":
    build_features()
```

**Run it:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
python -m ml.feature_engineering
```

**Verify:**
```bash
ls data/processed/features.csv  # Should exist
head -5 data/processed/features.csv  # Should show columns
```

---

## Phase 4: ML Training

### Step 4.1: Train the accident risk model
**What:** XGBoost classifier that predicts whether a pothole will cause a nearby accident.

**Create `backend/ml/train_accident_risk.py`:**
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import joblib
import os

def train_accident_risk_model():
    """Train XGBoost classifier to predict accident risk near a pothole."""
    print("Training Accident Risk Model...")

    # Load features
    df = pd.read_csv("data/processed/features.csv")

    # Features for prediction
    feature_cols = [
        "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month", "day_of_week",
        "latitude", "longitude",
    ]

    X = df[feature_cols].fillna(0)
    y = df["has_nearby_accident"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train model
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    try:
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC: {auc:.3f}")
    except ValueError:
        print("ROC-AUC: Could not compute (possible single class in test set)")

    # Feature importance
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    # Save model
    model_path = os.path.join(os.path.dirname(__file__), "model_accident_risk.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model

if __name__ == "__main__":
    train_accident_risk_model()
```

---

### Step 4.2: Train the repair timeline model
**What:** XGBoost regressor that predicts how many days until a pothole is fixed.

**Create `backend/ml/train_repair_timeline.py`:**
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
import joblib
import os

def train_repair_timeline_model():
    """Train XGBoost regressor to predict repair timeline for a pothole."""
    print("Training Repair Timeline Model...")

    # Load features
    df = pd.read_csv("data/processed/features.csv")

    # Only use closed potholes (we know how long they took to close)
    closed = df[df["status"] == "closed"].copy()
    closed = closed.dropna(subset=["days_to_close"])

    if len(closed) < 50:
        print(f"Warning: Only {len(closed)} closed potholes for training. Using heuristic fallback.")
        # Save a dummy model that uses heuristics
        model_path = os.path.join(os.path.dirname(__file__), "model_repair_timeline.pkl")
        joblib.dump(None, model_path)
        return None

    feature_cols = [
        "days_open", "borough_encoded", "traffic_volume_aadt",
        "nearby_pothole_count", "month",
        "nearby_collisions",
    ]

    X = closed[feature_cols].fillna(0)
    y = closed["days_to_close"]

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\nMean Absolute Error: {mae:.1f} days")
    print(f"Root Mean Squared Error: {rmse:.1f} days")

    # Feature importance
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    # Save model
    model_path = os.path.join(os.path.dirname(__file__), "model_repair_timeline.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model

if __name__ == "__main__":
    train_repair_timeline_model()
```

---

### Step 4.3: Run the full ML pipeline
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate

# Step 1: Build features from database data
python -m ml.feature_engineering

# Step 2: Train accident risk model
python -m ml.train_accident_risk

# Step 3: Train repair timeline model
python -m ml.train_repair_timeline
```

**Verify:**
```bash
ls ml/*.pkl
# Should show:
# model_accident_risk.pkl
# model_repair_timeline.pkl

ls data/processed/features.csv
# Should show the feature CSV
```

---

## Phase 5: Impact Score Computation

### Step 5.1: Create the impact scoring service
**What:** Calculate composite impact scores for all open potholes. This is what drives the alert system.

**Create `backend/app/services/impact.py`:**
```python
from app.database import get_db

def compute_impact_scores():
    """Calculate and update impact scores for all open potholes.

    Composite formula:
      impact = 0.4 * accident_risk_prob
             + 0.3 * (days_open / 90)         -- normalized to 0-1
             + 0.3 * (traffic_volume / 25000) -- normalized to 0-1
    """
    with get_db() as conn:
        potholes = conn.execute("""
            SELECT id, days_open, borough, impact_score
            FROM potholes WHERE status = 'open'
        """).fetchall()

    print(f"Computing impact scores for {len(potholes)} open potholes...")

    # Borough traffic proxy
    borough_traffic = {
        "Manhattan": 25000,
        "Brooklyn": 15000,
        "Queens": 18000,
        "Bronx": 12000,
        "Staten Island": 8000,
    }

    # Collision counts per pothole
    with get_db() as conn:
        collision_counts = {}
        rows = conn.execute("""
            SELECT pothole_id, COUNT(*) as cnt
            FROM pothole_collisions
            GROUP BY pothole_id
        """).fetchall()
        for r in rows:
            collision_counts[r["pothole_id"]] = r["cnt"]

    for pothole in potholes:
        p = dict(pothole)
        days_open = p.get("days_open", 0) or 0
        borough = p.get("borough", "Manhattan") or "Manhattan"

        # Accident risk probability (heuristic based on collisions + age)
        nearby_collisions = collision_counts.get(p["id"], 0)
        accident_prob = min(0.1 * nearby_collisions + days_open * 0.003, 0.95)

        # Traffic volume
        traffic = borough_traffic.get(borough, 15000)

        # Normalized components
        days_normalized = min(days_open / 90, 1.0)
        traffic_normalized = traffic / 25000

        impact_score = (
            0.4 * accident_prob +
            0.3 * days_normalized +
            0.3 * traffic_normalized
        )

        with get_db() as conn:
            conn.execute(
                "UPDATE potholes SET impact_score = ? WHERE id = ?",
                (round(impact_score, 3), p["id"])
            )
            conn.commit()

    print("Impact scores updated!")

if __name__ == "__main__":
    compute_impact_scores()
```

**Run it:**
```bash
cd ~/HunterHack/backend
source venv/Scripts/activate
python -m app.services.impact
```

**Verify:**
```bash
python -c "
from app.database import get_db
with get_db() as conn:
    rows = conn.execute('SELECT id, impact_score FROM potholes WHERE impact_score IS NOT NULL LIMIT 5').fetchall()
    for r in rows:
        print(dict(r))
"
# Should show pothole IDs with non-null impact scores
```

---

## Your Verification Checklist

After completing all your phases:

- [ ] `potholes.db` exists and has data
- [ ] `python -m app.database` runs and creates tables
- [ ] `python -m app.services.etl` fetches and loads data
- [ ] `python -m app.services.geospatial` joins potholes to collisions
- [ ] `python -m ml.feature_engineering` produces `data/processed/features.csv`
- [ ] `python -m ml.train_accident_risk` produces `ml/model_accident_risk.pkl`
- [ ] `python -m ml.train_repair_timeline` produces `ml/model_repair_timeline.pkl`
- [ ] `python -m app.services.impact` updates impact scores in DB
- [ ] Database query shows potholes with non-null `impact_score`

Once all checked, tell Developer B the database and models are ready to serve.