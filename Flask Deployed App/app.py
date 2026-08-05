import os
import csv
from flask import Flask, render_template, request
from PIL import Image
from torchvision import transforms
import torch

from CNN import CNN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
MODEL_PATHS = [
    os.path.join(PROJECT_ROOT, "plant_disease_model_1_latest.pt"),
    os.path.join(BASE_DIR, "plant_disease_model_1_latest.pt"),
    r"C:\Users\yugme\OneDrive\Desktop\Plant-Disease-Detection-main\Plant-Disease-Detection-main\plant_disease_model_1_latest.pt",
]
MODEL_PATH = next((path for path in MODEL_PATHS if os.path.exists(path)), None)

if MODEL_PATH is None:
    raise FileNotFoundError("The plant disease model file was not found.")

transform = transforms.Compose([
    transforms.Resize(255),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CNN(K=39).to(device)
checkpoint = torch.load(MODEL_PATH, map_location=device)

if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
    checkpoint = checkpoint["state_dict"]
if isinstance(checkpoint, dict) and "model" in checkpoint and isinstance(checkpoint["model"], dict):
    checkpoint = checkpoint["model"]

state_dict = {}
for key, value in checkpoint.items():
    state_dict[key.replace("module.", "").replace("model.", "")] = value

model.load_state_dict(state_dict)
model.eval()

disease_info = {'disease_name': [], 'description': [], 'Possible Steps': [], 'image_url': []}
with open('disease_info.csv', encoding='cp1252') as f:
    reader = csv.DictReader(f)
    for row in reader:
        disease_info['disease_name'].append(row['disease_name'])
        disease_info['description'].append(row['description'])
        disease_info['Possible Steps'].append(row['Possible Steps'])
        disease_info['image_url'].append(row['image_url'])

supplement_info = {'supplement name': [], 'supplement image': [], 'buy link': []}
with open('supplement_info.csv', encoding='cp1252') as f:
    reader = csv.DictReader(f)
    for row in reader:
        supplement_info['supplement name'].append(row['supplement name'])
        supplement_info['supplement image'].append(row['supplement image'])
        supplement_info['buy link'].append(row['buy link'])

def prediction(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        img_tensor = transform(img).unsqueeze(0).to(device)
        with torch.inference_mode():
            output = model(img_tensor)
            probabilities = torch.nn.functional.softmax(output, dim=1)
            confidence = probabilities.max().item() * 100
        pred = int(torch.argmax(output, dim=1).item())
        if 0 <= pred <= 38:
            return pred, round(confidence, 2)
        return 0, 0.0
    except Exception as e:
        print("Model prediction error:", e)
        return 0, 0.0

app = Flask(__name__)

@app.route('/')
def home_page():
    return render_template('home.html')

@app.route('/contact')
def contact():
    return render_template('contact-us.html')

@app.route('/index')
def ai_engine_page():
    return render_template('index.html')

@app.route('/mobile-device')
def mobile_device_detected_page():
    return render_template('mobile-device.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        image = request.files['image']
        filename = image.filename
        file_path = os.path.join('static/uploads', filename)
        image.save(file_path)
        print(file_path)
        pred, confidence = prediction(file_path)
        title = disease_info['disease_name'][pred]
        description = disease_info['description'][pred]
        prevent = disease_info['Possible Steps'][pred]
        image_url = disease_info['image_url'][pred]
        supplement_name = supplement_info['supplement name'][pred]
        supplement_image_url = supplement_info['supplement image'][pred]
        supplement_buy_link = supplement_info['buy link'][pred]
        return render_template('submit.html' , title = title , desc = description , prevent = prevent , 
                               image_url = image_url , pred = pred ,sname = supplement_name , simage = supplement_image_url , buy_link = supplement_buy_link, confidence=confidence)
    return redirect(url_for('ai_engine_page'))

@app.route('/market', methods=['GET', 'POST'])
def market():
    return render_template('market.html', supplement_image = supplement_info['supplement image'],
                           supplement_name = supplement_info['supplement name'], disease = disease_info['disease_name'], buy = supplement_info['buy link'])

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

if __name__ == '__main__':
    app.run(debug=True)
