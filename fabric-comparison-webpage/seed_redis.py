# LOOPS THROUGH THE IMAGES FOLDER, EXTRACTS BOTH HSV AND LBP HISTOGRAMS AND STORES THEM AS FLAT
# BINARY FLOAT ARRAYS IN REDIS

# ALSO PRE-COMPUTES AN OPTIMIZED, DOWNSCALED JPEG OF EACH IMAGE TO MINIMIZE NETWORK OVERHEAD 
# WHEN SENDING VISUAL DATA TO THE AI LATER

import os
import cv2
import redis
import numpy as np
from skimage.feature import local_binary_pattern

# initializing Redis client connection
r = redis.Redis(host = "localhost", port = 6379, decode_responses = False)

# DIRECTORIES 
SOURCE_IMG_DIR = "images"
PROCESSED_DIR = "static/processed_pics" # where the processed copies will be stored

os.makedirs(PROCESSED_DIR, exist_ok = True)

# ONE TIME PREPROCESSING FUNCTION (OF THE DATASET OF IMAGES)
def preprocess_image_dataset():
    print("Starting optimized feature processing into Redis...")

    for filename in os.listdir(SOURCE_IMG_DIR):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):  # ignoring non images
            continue

        # extracting serial number from filename 
        serial_no = os.path.splitext(filename)[0] # splits filename into 2 parts, extracts name (se no.)
        # building file path 
        img_path = os.path.join(SOURCE_IMG_DIR, filename)

        # loading image into memory - OpenCV
        img_cv = cv2.imread(img_path)
        if img_cv is None:
            print(f"Could not read image: {filename}")
            continue

        # EXTRACTING COLOUR FEATURES (HSV)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        # this is the colour vector (2D array of float numbers)
        hist_hsv = cv2.calcHist([hsv], [0, 1], None, [180, 256], [0, 180, 0, 256])
        cv2.normalize(hist_hsv, hist_hsv, alpha = 0, beta = 1, norm_type = cv2.NORM_MINMAX)

        # EXTRACTING TEXTURE FEATURES (LBP)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        radius = 1
        n_points = 8 * radius
        lbp = local_binary_pattern(gray, n_points, radius, method = "uniform")
        n_bins = int(lbp.max() + 1)
        # this is the texture vector --> 1D array of float numbers 
        hist_lbp, _ = np.histogram(lbp.ravel(), bins = n_bins, range = (0, n_bins), density = True)


        # STORING RAW ARRAYS AS BINARY STRINGS IN REDIS 
        # ARRAYS --> FLOAT32
        r.set(f"curtain:color:{serial_no}", hist_hsv.astype(np.float32).tobytes())
        r.set(f"curtain:texture:{serial_no}", hist_lbp.astype(np.float32).tobytes())

        # downscaling to 224 x 224 to compress the image payload
        ai_processed = cv2.resize(img_cv, (224, 224), interpolation = cv2.INTER_AREA)
        processed_pics_path = os.path.join(PROCESSED_DIR, f"{serial_no}.jpg")
        cv2.imwrite(processed_pics_path, ai_processed, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

    print("Processing complete! Redis is fully loaded.")
    
if __name__ == "__main__":
    preprocess_image_dataset()

# precomputed embedding vectors --> arrays of numbers that represent the images 
