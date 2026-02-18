import requests
from datetime import timedelta, timezone, datetime
lat, lon = -0.680482, 34.777061
# Get weather
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
try:
    response = requests.get(url).json()
    current_weather = response['current_weather']
    time = datetime.now(timezone(timedelta(hours=3))).strftime("%d/%m/%Y %H:%M:%S")
    temperature = current_weather['temperature']
    windspeed = current_weather['windspeed']
    wind_direction = current_weather['winddirection']
    is_day = "Day" if current_weather['is_day'] == 1 else "Night"
    # Clear
    weather_codes = {
        0: "Clear sky",

        # Mainly clear, partly cloudy, and overcast
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",

        # Fog
        45: "Fog",
        48: "Depositing rime fog",

        # Drizzle
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",

        # Freezing Drizzle
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",

        # Rain
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",

        # Freezing Rain
        66: "Light freezing rain",
        67: "Heavy freezing rain",

        # Snow
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",

        # Snow grains
        77: "Snow grains",

        # Rain showers
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",

        # Snow showers
        85: "Slight snow showers",
        86: "Heavy snow showers",

        # Thunderstorm
        95: "Thunderstorm",

        # Thunderstorm with hail
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }    
    weather_code = weather_codes.get(current_weather['weathercode'])
    print(f"Time: {time}")
    print(f"Temperature: {temperature}°C")
    print(f"Wind Speed: {windspeed} km/h")
    print(f"Wind Direction: {wind_direction}°")
    print(f"At: {is_day}")
    print(f"Weather Code: {weather_code}")
except KeyError as e:
    print(f"Error: Could not retrieve current weather data: {e}.")
except requests.exceptions.RequestException:
    print("Error: Could not connect to the weather API.")
