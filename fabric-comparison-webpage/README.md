# AI Visual Search Engine
A service built to perform real time visual similarity searches on fabric inventory. By transitioning from heavy deep-learning models to optimized mathematical vector mapping, this engine reduces search latency from several seconds down to milliseconds.

## Key Features
- Searches are executed in milliseconds by comparing mathematical vectors stored in memory, rather than relying on heavy AI inference APIs.
- Separates the heavy offline image processing (batch ingestion) from the live web server, ensuring instant server boot times and zero latency for the end user.
- Evaluates uploads based on two distinct metrics:
Color: Extracted using OpenCV HSV (Hue, Saturation, Value) histograms.

Texture: Extracted using Local Binary Patterns (LBP) via scikit-image.
- Uses standard URL routing and native JavaScript URL.createObjectURL() to display images dynamically, preventing massive network payloads and allowing browser caching.
- A modern frontend built with Bootstrap 5, incorporating Al Kilani's official brand colors.

## Tech Stack 
**Frontend:**
- HTML5 & CSS3
- Bootstrap 5 (UI Framework & Grid System)
- JavaScript (Asynchronous Fetch API & DOM Manipulation)

**Backend and API:**
- Python 3
- FastAPI 
- Uvicorn 

**Computer Vision & Math:**
- OpenCV (Image decoding, color space conversion, histogram correlation)
- Scikit-Image (LBP texture mapping)
- NumPy (Matrix operations & Cosine Similarity)

**Infrastructure & Database:**
- Redis (In-memory data store for vector caching)
- Windows Subsystem for Linux (WSL / Ubuntu)


## System Architecture 
This project is split into two distinct operational phases to maximize performance:

1. The Ingestion Pipeline (seed_redis.py)
An offline batch-processing script run by the database administrator whenever new inventory is added.
- Scans the raw /images/ directory.
- Mathematically extracts HSV and LBP features for every fabric.
- Converts these features into raw binary byte arrays and stores them in Redis RAM.
- Generates optimized 224x224 JPEG thumbnails and saves them to /static/processed_pics/ for high speed web delivery.

2. The Live Search Server (fabricComparison.py)
A  FastAPI server dedicated entirely to serving user requests.
- Intercepts user image uploads as raw byte streams directly into RAM.
- Extracts the HSV and LBP vectors of the uploaded sample.
- Sweeps the Redis cache by utilizing Cosine Similarity and Histogram Correlation to find the closest matching vectors.
- Returns a lightweight JSON payload containing the winning serial numbers and confidence percentages.


## How to run locally?
1. Boot the database (WSL)
Open your Ubuntu/WSL terminal and start the Redis server:

sudo service redis-server start

2. Open your Python environment terminal and populate the Redis cache:

python seed_redis.py

3. Start the web server
Boot the application:

python -m uvicorn fabricComparison:app --reload

4. Access the portal
Open a web browser and navigate to:

http://127.0.0.1:8000

