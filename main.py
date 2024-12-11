from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/get_pixels', methods=['POST'])
def get_pixels():
    try:
        data = request.get_json()
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
        offset = 0.005

        xmin = longitude - offset
        ymin = latitude - offset
        xmax = longitude + offset
        ymax = latitude + offset

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
