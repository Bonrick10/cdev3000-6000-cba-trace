import random

from geopy import Point
from geopy.distance import geodesic

IMPOSSIBLE_TRAVEL_THRESHOLD = 500 / 60  # Note that this is km/minute


def generate_point_within_dist(center, radius_km):
    # https://stackoverflow.com/a/69917474
    random_distance = random.random() * radius_km
    random_bearing = random.random() * 360
    return geodesic(kilometers=random_distance).destination(center, random_bearing)


def gen_rand_loc(precision: int = 6):
    """Generates random global coordinates.
    Latitude: -90 to 90
    Longitude: -180 to 180
    """
    # Note that this is NOT guaranteed to make a impossible travel case
    # As can still fall within threshold
    return (
        round(random.uniform(-90.0, 90.0), precision),
        round(random.uniform(-180.0, 180.0), precision),
    )


# def gen_near_loc(seed_acc_txns, new_txn_time):
def gen_near_loc(seed_acc_txns):
    if len(seed_acc_txns) == 0:
        # Fallback if no last transaction, this shouldn't happen since in young period
        return gen_rand_loc()

    last_txn_lat = seed_acc_txns[-1]["sender_latitude"]
    last_txn_lon = seed_acc_txns[-1]["sender_longitude"]
    # delta_time = new_txn_time - seed_acc_txns[-1]["transaction_time"]

    point = generate_point_within_dist(Point(last_txn_lat, last_txn_lon), 40)

    return (point.latitude, point.longitude)


def gen_far_loc(lat, lon):
    center = Point(lat, lon)
    random_bearing = random.random() * 360
    distance_km = random.uniform(IMPOSSIBLE_TRAVEL_THRESHOLD, IMPOSSIBLE_TRAVEL_THRESHOLD * 1.5)
    point = geodesic(kilometers=distance_km).destination(center, random_bearing)
    return (point.latitude, point.longitude)
