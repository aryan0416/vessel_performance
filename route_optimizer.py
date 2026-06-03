import numpy as np
import folium

import random

# Generate a high-resolution 0.25-degree weather grid over the region
# In a real system this would come from pilot charts or weather API
# Grid format: (lat, lon, wind_speed_kts, wave_height_m, current_kts)

WEATHER_GRID = []
for glat in np.arange(1.0, 3.25, 0.25):
    for glon in np.arange(101.0, 105.25, 0.25):
        # Base weather is calm
        wind = random.uniform(2, 6)
        wave = random.uniform(0.1, 0.5)
        curr = random.uniform(0.1, 0.3)
        
        # Simulate a high wind zone (severe weather) in the South China Sea / East of Singapore
        if glat < 1.8 and glon > 103.5:
            wind = random.uniform(15, 25)
            wave = random.uniform(1.5, 3.0)
            curr = random.uniform(0.6, 1.2)
        # Simulate another small squall area in Malacca Strait
        elif 2.0 <= glat <= 2.5 and 102.0 <= glon <= 102.5:
            wind = random.uniform(12, 18)
            wave = random.uniform(1.0, 2.0)
            
        WEATHER_GRID.append((glat, glon, wind, wave, curr))

def _interpolate_weather(lat, lon):
    """
    Get estimated weather at a point by inverse-distance weighting
    from the nearest grid points.
    """
    weights, wind_sum, wave_sum, curr_sum = 0, 0, 0, 0
    for (glat, glon, wind, wave, curr) in WEATHER_GRID:
        dist = np.sqrt((lat - glat)**2 + (lon - glon)**2)
        if dist < 0.01:
            return wind, wave, curr
        w = 1 / dist
        weights  += w
        wind_sum += w * wind
        wave_sum += w * wave
        curr_sum += w * curr
    return wind_sum/weights, wave_sum/weights, curr_sum/weights


def _speed_reduction(wind_kts, wave_m, base_speed):
    """
    Estimate speed reduction due to weather.
    Simple model:
      - Every 5 kts of wind above 10 kts reduces speed by 0.3 kts
      - Every 0.5m of wave above 1m reduces speed by 0.2 kts
    """
    wind_penalty = max(0, (wind_kts - 10) / 5) * 0.3
    wave_penalty = max(0, (wave_m - 1.0) / 0.5) * 0.2
    reduction    = wind_penalty + wave_penalty
    return max(base_speed - reduction, base_speed * 0.7)


def _fuel_increase(wind_kts, wave_m, base_fuel):
    """
    Estimate daily fuel increase due to weather.
    Rough model: 2% increase per Beaufort above 4.
    """
    beaufort  = min(int(wind_kts / 3), 12)
    increase  = max(0, beaufort - 4) * 0.02
    return round(base_fuel * (1 + increase), 3)


def _great_circle_waypoints(start, end, n=30):
    """Generate intermediate waypoints along a straight line."""
    lats = np.linspace(start[0], end[0], n)
    lons = np.linspace(start[1], end[1], n)
    return list(zip(lats, lons))


def _avoid_weather_waypoints(start, end, n=30):
    """
    Generate an alternate route that shifts to avoid bad weather.
    Now uses denser sampling (n=30) and more granular offset logic
    to take advantage of 0.25-degree resolution.
    """
    waypoints = _great_circle_waypoints(start, end, n)
    adjusted  = []
    for i, (lat, lon) in enumerate(waypoints):
        wind, wave, _ = _interpolate_weather(lat, lon)
        # If weather is bad, shift south or west slightly based on intensity
        if wind > 12 or wave > 1.5:
            shift_lat = min((wind - 12) / 25, 0.3)
            shift_lon = min((wave - 1.5) / 5, 0.1)
            lat = lat - shift_lat
            lon = lon - shift_lon
        adjusted.append((lat, lon))
    return adjusted


def analyze_route(waypoints, base_speed, base_fuel_per_day):
    """
    Walk along waypoints, estimate weather impact at each point,
    and compute total voyage metrics.
    """
    total_distance = 0
    total_hours    = 0
    total_fuel     = 0
    segment_data   = []

    for i in range(len(waypoints) - 1):
        p1  = waypoints[i]
        p2  = waypoints[i+1]

        # Distance in nm (rough: 1 deg lat ≈ 60 nm)
        dlat = (p2[0] - p1[0]) * 60
        dlon = (p2[1] - p1[1]) * 60 * np.cos(np.radians((p1[0]+p2[0])/2))
        dist = np.sqrt(dlat**2 + dlon**2)

        # Weather at midpoint
        mid_lat = (p1[0] + p2[0]) / 2
        mid_lon = (p1[1] + p2[1]) / 2
        wind, wave, curr = _interpolate_weather(mid_lat, mid_lon)

        # Adjusted speed and fuel
        adj_speed = _speed_reduction(wind, wave, base_speed)
        adj_fuel  = _fuel_increase(wind, wave, base_fuel_per_day)

        hours = dist / adj_speed if adj_speed > 0 else 0
        fuel  = adj_fuel * (hours / 24)

        total_distance += dist
        total_hours    += hours
        total_fuel     += fuel

        segment_data.append({
            "from":      p1,
            "to":        p2,
            "dist_nm":   round(dist, 1),
            "wind_kts":  round(wind, 1),
            "wave_m":    round(wave, 2),
            "speed_kts": round(adj_speed, 1),
            "fuel_mt":   round(fuel, 3),
        })

    return {
        "waypoints":       waypoints,
        "segments":        segment_data,
        "total_distance":  round(total_distance, 1),
        "total_hours":     round(total_hours, 1),
        "total_days":      round(total_hours / 24, 2),
        "total_fuel":      round(total_fuel, 3),
        "avg_speed":       round(total_distance / total_hours, 2) if total_hours > 0 else 0,
    }


def build_route_map(direct_result, optimal_result, start, end):
    """Build a folium map showing both routes side by side."""

    center_lat = (start[0] + end[0]) / 2
    center_lon = (start[1] + end[1]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB dark_matter"
    )

    # Direct route — red dashed
    folium.PolyLine(
        locations=direct_result["waypoints"],
        color="#e74c3c",
        weight=2.5,
        dash_array="6 4",
        tooltip="Direct Route",
        popup=folium.Popup(
            f"<b>Direct Route</b><br>"
            f"Distance: {direct_result['total_distance']} nm<br>"
            f"ETA: {direct_result['total_days']} days<br>"
            f"Fuel: {direct_result['total_fuel']} MT",
            max_width=200
        )
    ).add_to(m)

    # Optimal route — teal solid
    folium.PolyLine(
        locations=optimal_result["waypoints"],
        color="#0f9b8e",
        weight=3,
        tooltip="Optimized Route",
        popup=folium.Popup(
            f"<b>Optimized Route</b><br>"
            f"Distance: {optimal_result['total_distance']} nm<br>"
            f"ETA: {optimal_result['total_days']} days<br>"
            f"Fuel: {optimal_result['total_fuel']} MT",
            max_width=200
        )
    ).add_to(m)

    # Weather hotspots
    for (glat, glon, wind, wave, curr) in WEATHER_GRID:
        if wind > 12:
            folium.CircleMarker(
                location=[glat, glon],
                radius=wind / 4,
                color="#e74c3c",
                fill=True,
                fill_opacity=0.4,
                tooltip=f"⚠️ Wind: {wind:.1f} kts | Wave: {wave:.1f}m"
            ).add_to(m)
        elif wind > 8:
            folium.CircleMarker(
                location=[glat, glon],
                radius=wind / 5,
                color="#f39c12",
                fill=True,
                fill_opacity=0.2,
                tooltip=f"⚡ Wind: {wind:.1f} kts | Wave: {wave:.1f}m"
            ).add_to(m)

    # Start / End markers
    folium.Marker(start, tooltip="Departure",
                  icon=folium.Icon(color="green", icon="ship", prefix="fa")).add_to(m)
    folium.Marker(end,   tooltip="Destination",
                  icon=folium.Icon(color="blue",  icon="anchor", prefix="fa")).add_to(m)

    return m