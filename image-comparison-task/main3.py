# APPROACH 3 - USING OPENCV (HSV AND LBP) + ViT + MISTRAL
import os
import cv2
import base64 
import torch
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from mistralai.client import Mistral
from skimage.feature import local_binary_pattern
from transformers import ViTImageProcessor, ViTModel
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
#initializing Mistral Client 
apiKey = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"
client = Mistral(api_key = apiKey)

# loading Hugging Face ViT model
processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
vit_model = ViTModel.from_pretrained('google/vit-base-patch16-224')

img1_path = "fabric1.jpg"
img2_path = "fabric2.jpg"

print(f"\nAnalyzing {img1_path} and {img2_path}...")

# HUGGING FACE ViT (as in main2.py)

image1 = Image.open(img1_path).convert("RGB") #opens image and forces into standard RGB format
inputs1 = processor(images = image1, return_tensors = "pt") #resizes image to 224x224 pixels and converts into a mathematical grid (tensor)
with torch.no_grad(): 
    outputs1 = vit_model(**inputs1) 
embedding_1 = outputs1.pooler_output.numpy() 


image2 = Image.open(img2_path).convert("RGB")
inputs2 = processor(images = image2, return_tensors = "pt")
with torch.no_grad():
    outputs2 = vit_model(**inputs2)
embedding_2 = outputs2.pooler_output.numpy()

# cosine similarity comparison
similarity_score = cosine_similarity(embedding_1, embedding_2)[0][0] # 1st row, 1st element
vit_percentage = max(0, similarity_score) * 100


# OPENCV HSV HISTOGRAM

img1_cv = cv2.imread(img1_path) #default colour space of OpenCV is BGR 
img2_cv = cv2.imread(img2_path)

# converting to hue, saturation and value colour space 
hsv1 = cv2.cvtColor(img1_cv, cv2.COLOR_BGR2HSV)
hsv2 = cv2.cvtColor(img2_cv, cv2.COLOR_BGR2HSV)

# calculating 2D histogram for Hue (0-180) and Saturation (0-255)
# often ignore Value (brightness) to handle lighting changes
hist_hsv1 = cv2.calcHist([hsv1], [0, 1], None, [180, 256], [0, 180, 0, 256])
# normalizing the images if their sizes are different
cv2.normalize(hist_hsv1, hist_hsv1, alpha = 0, beta = 1, norm_type = cv2.NORM_MINMAX)

hist_hsv2 = cv2.calcHist([hsv2], [0, 1], None, [180, 256], [0, 180, 0, 256])
cv2.normalize(hist_hsv2, hist_hsv2, alpha = 0, beta = 1, norm_type = cv2.NORM_MINMAX)

# comparing histograms using Correlation
hsv_sim = cv2.compareHist(hist_hsv1, hist_hsv2, cv2.HISTCMP_CORREL)
hsv_percentage = max(0, hsv_sim) * 100  # if score is -ve, it gets converted to 0


# LBP

# converting to grayscale to ignore color completely
gray1 = cv2.cvtColor(img1_cv, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(img2_cv, cv2.COLOR_BGR2GRAY)

radius = 1
n_points = 8 * radius

# generating Local Binary Pattern maps
lbp1 = local_binary_pattern(gray1, n_points, radius, method = "uniform")
lbp2 = local_binary_pattern(gray2, n_points, radius, method = "uniform")

# converting the maps into 1D histograms to compare them
n_bins = int(lbp1.max() + 1)
hist_lbp1, _ = np.histogram(lbp1.ravel(), bins = n_bins, range = (0, n_bins), density = True)
hist_lbp2, _ = np.histogram(lbp2.ravel(), bins = n_bins, range = (0, n_bins), density = True)

lbp_sim = cosine_similarity([hist_lbp1], [hist_lbp2])[0][0]
lbp_percentage = max(0, lbp_sim) * 100

# FINAL WEIGHTED CALCULATION
# (I'm taking 40% ViT, 30% HSV and 30% LBP)

final_score = (vit_percentage * 0.40) + (hsv_percentage * 0.30) + (lbp_percentage * 0.30)

print(f"ViT Semantic Similarity: {vit_percentage:.2f}%\n")
print(f"HSV Color Similarity:    {hsv_percentage:.2f}%\n")
print(f"LBP Texture Similarity:  {lbp_percentage:.2f}%\n")
print(f"FINAL WEIGHTED SCORE:   {final_score:.2f}%\n")


print("Encoding the images...")

# Reading and encoding the images 
with open(img1_path, "rb") as imgFile1:
    base64_img1 = base64.b64encode(imgFile1.read()).decode('utf-8')

with open(img2_path, "rb") as imgFile2:
    base64_img2 = base64.b64encode(imgFile2.read()).decode('utf-8')

print("Sending encoded images to Mistral AI...")


# MISTRAL AI ANALYSIS
print("\nFinal summary by Mistral AI.... ")

messages = [
    {
        "role": "user", "content": [
            {
                "type": "text", "text": (
                    "You are an AI assistant for Al Kilani Fabrics. "
            "I am providing you with 2 fabric images and our system just compared them and calculated the following:\n"
            f"- Pure Color Similarity (HSV): {hsv_percentage:.2f}%\n"
            f"- Pure Texture Similarity (LBP): {lbp_percentage:.2f}%\n"
            f"- Overall Semantic Structure (ViT): {vit_percentage:.2f}%\n"
            f"- FINAL WEIGHTED SCORE: {final_score:.2f}%\n\n"
            "Our strict threshold to recommend a fabric as an alternative option is 70%. "
            "Write a brief summary if it passes the threshold. "
            "Then specifically mention where the strengths or weaknesses lie (e.g. :'The colors are almost a perfect match, but the texture is completely different')."
            "Briefly describe the actual color and texture of the 2 fabrics based on the images."
            "Highlight the final weighted score and the final recommendation in bold."
                )
            },
            {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{base64_img1}"
            },
            {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{base64_img2}"
            }
        ]
    }
]


try:
    response = client.chat.complete(
        model = model,
        messages = messages
    )

    print("\n---- Mistral AI Final Assessment -----\n")
    print(response.choices[0].message.content)
    print("--------------------------------------\n")
    
except Exception as e:
    print("An error occurred during the API call...")

