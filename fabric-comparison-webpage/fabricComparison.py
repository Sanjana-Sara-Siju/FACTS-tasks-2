# RECEIVES UPLOADED IMAGE, PROCESSES IT, LOOPS THROUGH REDIS TO FIND BEST COLOUR AND 
# TEXTURE MATCH SEPARATELY 

import cv2
import redis
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from skimage.feature import local_binary_pattern
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI() # initializing the web server 

# initializing Redis
# connecting the running WSL Linux database
r = redis.Redis(host = "localhost", port = 6379, decode_responses = False)

# opens local /static/ folder to the Internet so the browser can load the .jpg thumbnails via URLs
# this means if the browser is asking for anything starting with /static/, look inside the physical 
# /static/ folder on the computer and hand the file 
app.mount("/static", StaticFiles(directory = "static"), name = "static")

# because FastAPI is sharing the /static/ folder, each image has their own local URL


# When someone visits 127.0.0.1:8000, this reads the index.html file and sends the webpage to 
# their browser
@app.get("/", response_class = HTMLResponse)
async def serve_home():
    with open("static/index.html", "r") as f:
        return f.read()
    

@app.post("/search")
async def search_fabrics(file: UploadFile = File(...)):
    # reads the incoming upload stream directly into memory
    contents = await file.read()
    # instead of saving user's upload to hard drive (slow), this converts the raw binary data 
    # directly into a readable OpenCV image matrix in my RAM
    nparr = np.frombuffer(contents, np.uint8)
    query_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # processsing uploaded image's color (HSV)
    hsv = cv2.cvtColor(query_img, cv2.COLOR_BGR2HSV)
    q_color = cv2.calcHist([hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
    cv2.normalize(q_color, q_color, alpha = 0, beta = 1, norm_type = cv2.NORM_MINMAX)
    
    # processing uploaded image's texture (LBP)
    gray = cv2.cvtColor(query_img, cv2.COLOR_BGR2GRAY)
    lbp = local_binary_pattern(gray, 8, 1, method = "uniform")
    n_bins = int(lbp.max() + 1)
    q_texture, _ = np.histogram(lbp.ravel(), bins = n_bins, range = (0, n_bins), density = True)
    q_texture = q_texture.astype(np.float32)

    # blank dictionaries to keep track of the highest score as the server sweeps through database
    best_color_match = {"serial": "N/A", "score": -1.0}
    best_texture_match = {"serial": "N/A", "score": -1.0}
    
    # telling Redis to find every single color vector stored in its memory
    for key in r.scan_iter("curtain:color:*"):
        serial_no = key.decode("utf-8").split(":")[-1]
        db_bytes = r.get(key) # pulls raw binary math for a specific curtain
        # reconstructing the exact original matrix shape from raw bytes
        db_color = np.frombuffer(db_bytes, dtype = np.float32).reshape(180, 256)
        
        # compares user's upload against database item
        score = cv2.compareHist(q_color, db_color, cv2.HISTCMP_CORREL)
        # If this curtain scores higher than previous best, it overwrites the dictionary to 
        # become new best
        if score > best_color_match["score"]:
            best_color_match = {"serial": serial_no, "score": score}

    # telling Redis to find every single texture vector stored in its memory
    for key in r.scan_iter("curtain:texture:*"):
        serial_no = key.decode("utf-8").split(":")[-1]
        db_bytes = r.get(key)
        db_texture = np.frombuffer(db_bytes, dtype = np.float32)
        
        # same comparison for texture 
        score = cosine_similarity([q_texture], [db_texture])[0][0]
        if score > best_texture_match["score"]:
            best_texture_match = {"serial": serial_no, "score": score}

    return {
        # these are the winning serial nos 
        # this is a JSON dictionary
        "color_match_serial": best_color_match["serial"],
        "color_match_confidence": f"{max(0, best_color_match['score']) * 100:.2f}%",
        "texture_match_serial": best_texture_match["serial"],
        "texture_match_confidence": f"{max(0, best_texture_match['score']) * 100:.2f}%"
    }


