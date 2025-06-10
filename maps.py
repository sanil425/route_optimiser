import googlemaps

GOOGLEMAPS_API_KEY = "AIzaSyA_mnq-8XaTO8pH64EXolOrKjMnkK3dSqc"

# initalise client
gmaps = googlemaps.Client(key = GOOGLEMAPS_API_KEY)


def geocode_addresses(address_list, gmaps_client):
    coords = []
    for address in address_list:
        geocode_res = gmaps_client.geocode(address)
        if geocode_res:
            location = geocode_res[0]['geometry']['location']
            lat_lng = (location['lat'], location['lng'])
            coords.append(lat_lng)
        else:
            print(f"Warning: No geocode result for address: {address}")
            coords.append((None, None))  # fallback
    return coords

# construct time matrix
def get_time_matrix(address_list, gmaps_client):
    matrix = gmaps_client.distance_matrix(
        origins=address_list,
        destinations=address_list,
        mode='driving'
    )

    time_matrix = []
    for row in matrix['rows']:
        time_row = []
        for element in row['elements']:
            if element['status'] == 'OK':
                time_sec = element['duration']['value']
                time_min = time_sec // 60
                time_row.append(time_min)
            else:
                print("Warning: Distance Matrix element error:", element['status'])
                time_row.append(99999)  # large value for unreachable
        time_matrix.append(time_row)

    return time_matrix


def get_distance_matrix(location_addresses, gmaps):
    n = len(location_addresses)
    distance_matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        origins = [location_addresses[i]]
        destinations = location_addresses

        response = gmaps.distance_matrix(origins, destinations, mode='driving')

        for j in range(n):
            element = response['rows'][0]['elements'][j]
            distance_in_km = element['distance']['value'] / 1000  # meters → km
            distance_matrix[i][j] = distance_in_km

    return distance_matrix
