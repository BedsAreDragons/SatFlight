from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO
import json
from geopy.distance import geodesic

app = Flask(__name__)

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

def get_image(xmin, ymin, xmax, ymax):
    url = (
        'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
        'bbox={xmin},{ymin},{xmax},{ymax}'
        '&bboxSR=4326'
        '&size=800,800'
        '&imageSR=4326'
        '&format=png32'
        '&f=image'
    ).format(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

    response = requests.get(url, stream=True)

    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        return img
    else:
        raise Exception('Failed to retrieve the image')

@app.route('/get_pixels', methods=['POST'])
def get_pixels():
    try:
        data = request.get_json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        offset = 0.02  # Updated offset size

        xmin, ymin, xmax, ymax = get_bbox(latitude, longitude, offset)

        url = (
            'https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?'
            'bbox={xmin},{ymin},{xmax},{ymax}'
            '&bboxSR=4326'
            '&size=800,800'  # Fetch 800x800 image for better initial detail
            '&imageSR=4326'
            '&format=png32'
            '&f=image'
        ).format(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        img = Image.open(BytesIO(response.content))

        # Resize down to 400x400 to achieve pixelation
        pixelated_img = img.resize((400, 400), resample=Image.NEAREST)

        pixelated_img = pixelated_img.convert('RGB')

        pixel_data = list(pixelated_img.getdata())

        pixels = [list(pixel) for pixel in pixel_data]

        return jsonify(pixels), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_extra_tiles', methods=['POST'])
def get_extra_tiles():
    try:
        data = request.get_json()
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
                tile_img = get_image(tile_xmin, tile_ymin, tile_xmax, tile_ymax)
                tiles.append(tile_img)

        big_image = Image.new('RGB', (tile_size * 3, tile_size * 3))

        # Paste the tiles into the big image
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

        return jsonify(pixels), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
