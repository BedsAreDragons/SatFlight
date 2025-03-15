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

async def process_terrain_request(latitude, longitude, offset):
    try:
        xmin, ymin, xmax, ymax = await get_bbox(latitude, longitude, offset)
        async with ClientSession() as session:
            img = await fetch_image(session, xmin, ymin, xmax, ymax)
        pixelated_img = img.resize((400, 400), resample=Image.NEAREST).convert('RGB')
        pixels = [list(pixel) for pixel in pixelated_img.getdata()]
        return pixels
    except Exception as e:
        raise Exception(f"Error processing terrain request: {str(e)}")

# New route to handle POST requests for loading terrain
async def load_terrain(request):
    try:
        data = await request.json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        offset = float(data.get('offset', 0.02))  # Default offset if not provided

        print(f"Processing terrain for coordinates: ({latitude}, {longitude})")
        pixels = await process_terrain_request(latitude, longitude, offset)

        return web.json_response({
            'status': 'success',
            'pixels': pixels
        })
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

# Web server setup
app = web.Application()
app.router.add_post('/load_terrain', load_terrain)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=5000)
