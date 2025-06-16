# visualization.py

import folium
import googlemaps
import polyline
import time

def visualize_route(
    address_list,
    visit_order,
    location_durations,
    location_names,
    distance_matrix,
    time_matrix,
    arrival_departure_info,
    return_to_start=True,
    map_style='CartoDB positron',
    api_key="YOUR_GOOGLE_API_KEY"
):
    gmaps = googlemaps.Client(key=api_key)

    lat_list = []
    lon_list = []
    for addy in address_list:
        geocode_res = gmaps.geocode(addy)
        location = geocode_res[0]['geometry']['location']
        lat_list.append(location['lat'])
        lon_list.append(location['lng'])
        time.sleep(0.1)

    route_coords = [(lat_list[i], lon_list[i]) for i in visit_order]
    start_lat, start_lon = route_coords[0]
    m = folium.Map(location=[start_lat, start_lon], zoom_start=8, tiles=map_style)

    # (cut for brevity: your full marker/popup/polylines/legend logic here)

    m.save('route_map.html')
    print("Map successfully saved to route_map.html — open it in your browser!")
