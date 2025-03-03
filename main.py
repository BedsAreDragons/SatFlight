from aiohttp import web
from PIL import Image
import aiohttp
import asyncio
from io import BytesIO
import json
from geopy.distance import geodesic

async def get_image(xmin, ymin, xmax, ymax):
    url = (
        'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
        'bbox={xmin},{ymin},{xmax},{ymax}'
        '&bboxSR=4326'
        '&size=800,800'
        '&imageSR=4326'
        '&format=png32'
        '&f=image'
    ).format(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                img = Image.open(BytesIO(await response.read()))
                return img
            else:
                raise Exception('Failed to retrieve the image')

def get_bbox(latitude, longitude, offset):
    # Calculate the offsets in meters
    lat_offset_m = offset * 111320  # Approx conversion of degrees to meters
    lon_offset_m = offset * 40075000 / 360 * abs(latitude / 90)  # Longitude conversion varies with latitude

    # Calculate new bounding box coordinates considering the Earth's curvature
    bottom_left = geodesic(meters=lat_offset_m).destination((latitude, longitude), 225)  # SW
    top_right = geodesic(meters=lat_offset_m).destination((latitude, longitude), 45)  # NE
    xmin, ymin = bottom_left.longitude, bottom_left.latitude
    xmax, ymax = top_right.longitude, top_right.latitude
    return xmin, ymin, xmax, ymax

async def get_pixels(offset, request):
    data = await request.json()
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    xmin, ymin, xmax, ymax = get_bbox(latitude, longitude, offset)

    img = await get_image(xmin, ymin, xmax, ymax)

    # Resize down to 400x400 to achieve pixelation
    pixelated_img = img.resize((400, 400), resample=Image.NEAREST)
    pixelated_img = pixelated_img.convert('RGB')
    pixel_data = list(pixelated_img.getdata())
    pixels = [list(pixel) for pixel in pixel_data]
    return web.json_response(pixels)

async def get_extra_tiles(request):
    data = await request.json()
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    offset = 0.0035  # Same offset as before
    tile_size = 800  # Size of each tile image
    tiles = []

    for dy in [-1, 0, 1]:  # Iterate from bottom to top
        for dx in [-1, 0, 1]:
            tile_xmin = longitude + dx * offset
            tile_ymin = latitude + dy * offset
            tile_xmax = tile_xmin + offset
            tile_ymax = tile_ymin + offset
            tile_img = await get_image(tile_xmin, tile_ymin, tile_xmax, tile_ymax)
            tiles.append(tile_img)

    big_image = Image.new('RGB', (tile_size * 3, tile_size * 3))  # Create a new image for the tiles
    for i, tile_img in enumerate(tiles):
        row = i // 3
        col = i % 3
        adjusted_row = 2 - row  # Swap rows
        big_image.paste(tile_img, (col * tile_size, adjusted_row * tile_size))

    # Resize down to 400x400 to achieve pixelation
    pixelated_img = big_image.resize((400, 400), resample=Image.NEAREST)
    pixelated_img = pixelated_img.convert('RGB')
    pixel_data = list(pixelated_img.getdata())
    pixels = [list(pixel) for pixel in pixel_data]
    return web.json_response(pixels)

app = web.Application()
app.router.add_post('/get_pixels_high', lambda request: get_pixels(0.02, request))
app.router.add_post('/get_pixels_med', lambda request: get_pixels(0.08, request))
app.router.add_post('/get_pixels_low', lambda request: get_pixels(0.2, request))
app.router.add_post('/get_extra_tiles', get_extra_tiles)

if __name__ == '__main__':
    web.run app.run(host="0.0.0.0", port=5000)
