from aiohttp import web, ClientSession
from PIL import Image
from io import BytesIO
import json
from geopy.distance import geodesic

async def get_bbox(latitude, longitude, offset):
    lat_offset_m = offset * 111320
    lon_offset_m = offset * 40075000 / 360 * abs(latitude / 90)
    bottom_left = geodesic(meters=lat_offset_m).destination((latitude, longitude), 225)
    top_right = geodesic(meters=lat_offset_m).destination((latitude, longitude), 45)
    return bottom_left.longitude, bottom_left.latitude, top_right.longitude, top_right.latitude

async def fetch_image(session, xmin, ymin, xmax, ymax):
    url = (
        'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
        f'bbox={xmin},{ymin},{xmax},{ymax}'
        '&bboxSR=4326'
        '&size=800,800'
        '&imageSR=4326'
        '&format=png32'
        '&f=image'
    )
    async with session.get(url) as response:
        if response.status == 200:
            img = Image.open(BytesIO(await response.read()))
            return img
        raise web.HTTPInternalServerError(text='Failed to retrieve image')

async def get_pixels(request, offset):
    try:
        data = await request.json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        xmin, ymin, xmax, ymax = await get_bbox(latitude, longitude, offset)
        async with ClientSession() as session:
            img = await fetch_image(session, xmin, ymin, xmax, ymax)
        pixelated_img = img.resize((400, 400), resample=Image.NEAREST).convert('RGB')
        pixels = [list(pixel) for pixel in pixelated_img.getdata()]
        return web.json_response(pixels)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def get_extra_tiles(request):
    try:
        data = await request.json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        offset = 0.0035
        tile_size = 800
        tiles = []
        async with ClientSession() as session:
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    tile_xmin, tile_ymin, tile_xmax, tile_ymax = await get_bbox(latitude + dy * offset, longitude + dx * offset, offset)
                    tiles.append(await fetch_image(session, tile_xmin, tile_ymin, tile_xmax, tile_ymax))
        big_image = Image.new('RGB', (tile_size * 3, tile_size * 3))
        for i, tile_img in enumerate(tiles):
            row, col = divmod(i, 3)
            big_image.paste(tile_img, (col * tile_size, (2 - row) * tile_size))
        pixelated_img = big_image.resize((400, 400), resample=Image.NEAREST).convert('RGB')
        pixels = [list(pixel) for pixel in pixelated_img.getdata()]
        return web.json_response(pixels)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

app = web.Application()
app.router.add_post('/get_pixels_high', lambda r: get_pixels(r, 0.02))
app.router.add_post('/get_pixels_med', lambda r: get_pixels(r, 0.08))
app.router.add_post('/get_pixels_low', lambda r: get_pixels(r, 0.2))
app.router.add_post('/get_extra_tiles', get_extra_tiles)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)
