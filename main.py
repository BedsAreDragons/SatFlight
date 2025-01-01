from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO
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
            '&size=400,400'
            '&imageSR=4326'
            '&format=png32'
            '&f=image'
        ).format(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)

        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        img = Image.open(BytesIO(response.content))

        small = img.resize((800, 800), resample=Image.BILINEAR)
        pixelated_img = small.resize(img.size, Image.NEAREST)

        pixelated_img = pixelated_img.convert('RGB')

        pixel_data = list(pixelated_img.getdata())

        pixels = [list(pixel) for pixel in pixel_data]

        return jsonify(pixels), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
