import random

def gen_rand_loc(precision: int = 6):
    """
    Generates random global coordinates.
    Latitude: -90 to 90
    Longitude: -180 to 180
    """
    return (
        round(random.uniform(-90.0, 90.0), precision),
        round(random.uniform(-180.0, 180.0), precision)
    )

def gen_near_loc(seed_account, seed_acc_txns, time): 
    transactions_before_time = [t for t in seed_acc_txns if t.get("txn_time") <= time]
    # Fallback if no last transaction 
    if len(transactions_before_time) == 0: 
        return gen_rand_loc()

    last_txn = max(transactions_before_time, key=lambda x: x.get("txn_time"))

    

    origin_lat = last_txn["latitude"]
    origin_lon = last_txn["longitude"]

    # Thanks AI 
    # 3. Generate a point within max_km radius
    earth_radius_km = 6371.0
    max_radius_rad = max_km / earth_radius_km
    
    # Square root ensures uniform spatial coverage over the circle area
    radius = math.sqrt(random.uniform(0, 1)) * max_radius_rad
    angle = random.uniform(0, 2 * math.pi)

    # Convert to radians
    origin_lat_rad = math.radians(origin_lat)
    origin_lon_rad = math.radians(origin_lon)

    # Calculate offset coordinates
    new_lat_rad = math.asin(
        math.sin(origin_lat_rad) * math.cos(radius) +
        math.cos(origin_lat_rad) * math.sin(radius) * math.cos(angle)
    )
    
    new_lon_rad = origin_lon_rad + math.atan2(
        math.sin(angle) * math.sin(radius) * math.cos(origin_lat_rad),
        math.cos(radius) - math.sin(origin_lat_rad) * math.sin(new_lat_rad)
    )

    # Convert back to degrees and format
    new_lat = round(math.degrees(new_lat_rad), 6)
    new_lon = round(math.degrees(new_lon_rad), 6)

    # Wrap longitude bounds (-180 to 180)
    new_lon = (new_lon + 180) % 360 - 180

    return new_lat, new_lon