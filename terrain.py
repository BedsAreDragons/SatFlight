from aiohttp import web
from PIL import Image
from io import BytesIO
import numpy as np
import json
import random

# Constants for generating synthetic or testing data
TILE_SIZE = 400  # 400x400 grid for tiles
ELEVATION_MAX = 50  # Maximum elevation in studs

# Function to generate synthetic elevation data
def generate_elevation_data():
    elevation_data = []
    for _ in range(TILE_SIZE * TILE_SIZE):
        elevation_data.append(random.randint(0, ELEVATION_MAX))  # Random elevation
    return elevation_data

# Function to generate synthetic color data
def generate_color_data():
    color_data = []
    for _ in range(TILE_SIZE * TILE_SIZE):
        color_data.append([random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)])  # Random color
    return color_data

# API endpoint to provide terrain data
async def get_terrain_data(request):
    try:
        # Parse the incoming request
        data = await request.json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])

        # Log the requested coordinates
        print(f"Received terrain request for Latitude: {latitude}, Longitude: {longitude}")

        # Here you could fetch real-world terrain data if available
        # Instead, we generate synthetic data for this example
        elevation_data = generate_elevation_data()
        color_data = generate_color_data()

        # Send the generated data back as JSON
        response = {
            "heights": elevation_data,
            "colors": color_data
        }
        return web.json_response(response)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# Set up the web application
app = web.Application()
app.router.add_post('/get_pixels_with_elevation', get_terrain_data)

# Run the server
if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)
