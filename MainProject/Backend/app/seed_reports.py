"""
Seed 100 unverified pothole reports across all 5 NYC boroughs.
Inserts into BOTH the reports table AND the potholes table
with status='unverified' so they appear on the map immediately.

Run: python -m Backend.app.seed_reports
"""

import os
import sys
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Backend.app.database import (
    init_db, insert_report, insert_unverified_pothole,
    infer_borough, BOROUGH_BOUNDS,
)

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]

STREET_NAMES = {
    "MANHATTAN": [
        "Broadway", "5th Avenue", "Madison Avenue", "Park Avenue",
        "Amsterdam Avenue", "1st Avenue", "Houston Street", "Canal Street",
    ],
    "BROOKLYN": [
        "Flatbush Avenue", "Atlantic Avenue", "4th Avenue", "Court Street",
        "Ocean Parkway", "Kings Highway", "Fulton Street", "Nostrand Avenue",
    ],
    "QUEENS": [
        "Queens Boulevard", "Northern Boulevard", "Roosevelt Avenue",
        "Woodhaven Boulevard", "Jamaica Avenue", "Astoria Boulevard",
        "31st Avenue", "Steinway Street",
    ],
    "BRONX": [
        "Grand Concourse", "Fordham Road", "Pelham Parkway",
        "Boston Road", "Webster Avenue", "Jerome Avenue",
        "Southern Boulevard", "Tremont Avenue",
    ],
    "STATEN ISLAND": [
        "Victory Boulevard", "Hylan Boulevard", "Richmond Road",
        "Forest Avenue", "Stapleton Road", "Bay Street",
        "Arthur Kill Road", "Clove Road",
    ],
}

DESCRIPTORS = [
    "Large pothole in the right lane",
    "Deep pothole near crosswalk",
    "Multiple potholes in a cluster",
    "Pothole causing tire damage",
    "Pothole filled with standing water",
    "Pothole near bus stop",
    "Cave-in forming around pothole",
    "Pothole on highway on-ramp",
    "Pothole at intersection",
    "Recurring pothole, previously patched",
]

REPORTER_NAMES = [
    "Jane Doe", "John Smith", "Maria Garcia", "David Kim",
    "Sarah Johnson", "Michael Brown", "Lisa Chen", "James Wilson",
    "Anonymous", "Anonymous",
]


def seed_reports(n_per_borough: int = 20) -> int:
    init_db()
    total = 0
    ts_base = int(time.time())

    for borough in BOROUGHS:
        (lat_lo, lat_hi), (lon_lo, lon_hi) = BOROUGH_BOUNDS[borough]
        for i in range(n_per_borough):
            lat = round(random.uniform(lat_lo, lat_hi), 6)
            lon = round(random.uniform(lon_lo, lon_hi), 6)
            street = random.choice(STREET_NAMES[borough])
            descriptor = random.choice(DESCRIPTORS)
            name = random.choice(REPORTER_NAMES)
            email = f"{name.lower().replace(' ', '.')}@example.com" if name != "Anonymous" else ""
            image_url = f"https://example.com/pothole_{ts_base + total}.jpg" if random.random() > 0.5 else None

            unique_key = f"RPT-{ts_base + total}-{random.randint(1000, 9999)}"

            insert_unverified_pothole(
                unique_key=unique_key,
                latitude=lat,
                longitude=lon,
                borough=borough,
                street_name=street,
                descriptor=descriptor,
            )

            insert_report(
                latitude=lat,
                longitude=lon,
                borough=borough,
                street_name=street,
                descriptor=descriptor,
                reporter_name=name,
                reporter_email=email,
                image_url=image_url or "",
                pothole_key=unique_key,
            )
            total += 1

    print(f"Seeded {total} unverified pothole reports across {len(BOROUGHS)} boroughs")
    return total


if __name__ == "__main__":
    seed_reports()