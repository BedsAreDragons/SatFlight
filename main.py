import aiohttp
from aiohttp import web
from PIL import Image
from io import BytesIO
from geopy.distance import geodesic
import asyncio

# Constants
TILE_SIZE = 400
ARC_GIS_URL = "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export"

# Helper function to calculate bounding box
def get_bbox(latitude, longitude, offset):
    lat_offset_m = offset * 111320
    lon_offset_m = offset * 40075000 / 360 * abs(latitude / 90)
    bottom_left = geodesic(meters=lat_offset_m).destination((latitude, longitude), 225)
    top_right = geodesic(meters=lat_offset_m).destination((latitude, longitude), 45)
    xmin, ymin = bottom_left.longitude, bottom_left.latitude
    xmax, ymax = top_right.longitude, top_right.latitude
    return xmin, ymin, xmax, ymax

# Helper function to fetch and process an image
async def fetch_and_process_image(session, xmin, ymin, xmax, ymax):
    params = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": "4326",
        "size": f"{TILE_SIZE},{TILE_SIZE}",
        "imageSR": "4326",
        "format": "png32",
        "f": "image"
    }
    async with session.get(ARC_GIS_URL, params=params) as response:
        if response.status != 200:
            raise Exception(f"Failed to fetch image: HTTP {response.status}")
        img_data = await response.read()
        img = Image.open(BytesIO(img_data)).convert("RGB")
        pixelated_img = img.resize((TILE_SIZE, TILE_SIZE), resample=Image.NEAREST)
        return list(pixelated_img.getdata())

# API endpoint for high-resolution tile
async def get_pixels_high(request):
    try:
        data = await request.json()
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        offset = 0.02  # Adjust for desired resolution
        xmin, ymin, xmax, ymax = get_bbox(latitude, longitude, offset)
        
        async with aiohttp.ClientSession() as session:
            pixels = await fetch_and_process_image(session, xmin, ymin, xmax, ymax)
        
        return web.json_response(pixels)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# API endpoint for low-resolution tile
async def get_pixels_low(request):
    try:
        data = await request.json()
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        offset = 0.2  # Adjust for desired resolution
        xmin, ymin, xmax, ymax = get_bbox(latitude, longitude, offset)
        
        async with aiohttp.ClientSession() as session:
            pixels = await fetch_and_process_image(session, xmin, ymin, xmax, ymax)
        
        return web.json_response(pixels)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# API endpoint for extra tiles (3x3 grid)
async def get_extra_tiles(request):
    try:
        data = await request.json()
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        offset = 0.0035  # Adjust for tile proximity
        tile_size = TILE_SIZE

        # Prepare bounding box data for 3x3 grid
        tasks = []
        async with aiohttp.ClientSession() as session:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    tile_xmin, tile_ymin, tile_xmax, tile_ymax = get_bbox(
                        latitude + dy * offset, longitude + dx * offset, offset
                    )
                    tasks.append(fetch_and_process_image(session, tile_xmin, tile_ymin, tile_xmax, tile_ymax))
            
            tiles = await asyncio.gather(*tasks)

        # Merge tiles into a single image
        big_image = Image.new("RGB", (tile_size * 3, tile_size * 3))
        for i, tile_pixels in enumerate(tiles):
            tile_img = Image.new("RGB", (tile_size, tile_size))
            tile_img.putdata([tuple(pixel) for pixel in tile_pixels])
            row, col = divmod(i, 3)
            adjusted_row = 2 - row  # Flip rows to align correctly
            big_image.paste(tile_img, (col * tile_size, adjusted_row * tile_size))

        # Pixelate and convert to pixel data
        pixelated_img = big_image.resize((TILE_SIZE, TILE_SIZE), resample=Image.NEAREST)
        pixels = list(pixelated_img.getdata())

        return web.json_response(pixels)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# Application setup
app = web.Application()
app.router.add_post("/get_pixels_high", get_pixels_high)
app.router.add_post("/get_pixels_low", get_pixels_low)
app.router.add_post("/get_extra_tiles", get_extra_tiles)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
