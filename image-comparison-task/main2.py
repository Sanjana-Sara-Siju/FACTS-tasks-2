# APPROACH 2 - USING HUGGING FACE ViT MODEL + MISTRAL

import os
import torch
from PIL import Image
from dotenv import load_dotenv
from mistralai.client import Mistral
from transformers import ViTImageProcessor, ViTModel  # to analyze the images
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

#initializing Mistral Client 
apiKey = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"
client = Mistral(api_key = apiKey)

# loading Hugging Face ViT model
processor = ViTImageProcessor.from_pretrained('google/vit-base-patch16-224')
vit_model = ViTModel.from_pretrained('google/vit-base-patch16-224')

img1_path = "fabric3.png"
img2_path = "fabric4.jpg"

print(f"\nAnalyzing {img1_path} and {img2_path} with Hugging Face...")

# EXTRACTING FEATURES FOR IMG 1
image1 = Image.open(img1_path).convert("RGB")
inputs1 = processor(images = image1, return_tensors = "pt") # returning PyTorch tensors
with torch.no_grad(): # disables gradient calculation so uses less memory 
    outputs1 = vit_model(**inputs1) # passing processed image into ViT, inputs1 unpacks the dictionary
embedding_1 = outputs1.pooler_output.numpy() # extracting image embedding from model output
                                             # converting PyTorch tensor into numpy array
                                             # the conversion is because scikit learn expects numpy arrays

# EXTRACTING FEATURES FOR IMG 2
image2 = Image.open(img2_path).convert("RGB")
inputs2 = processor(images = image2, return_tensors = "pt")
with torch.no_grad():
    outputs2 = vit_model(**inputs2)
embedding_2 = outputs2.pooler_output.numpy()

# COSINE SIMILARITY COMPARISON ON BOTH EMBEDDING ARRAYS
similarity_score = cosine_similarity(embedding_1, embedding_2)[0][0] # 1st row, 1st element
similarity_percentage = similarity_score * 100

print(f"-> Calculated ViT Similarity: {similarity_percentage:.2f}%")

# MISTRAL AI REPORT
print("\nFinal summary by Mistral AI.... ")

messages = [
    {
        "role": "user", "content": (
            "You are an AI assistant for Al Kilani Fabrics. "
            "Our automated vision system just compared two fabrics and calculated a "
            f"mathematical similarity score of {similarity_percentage:.2f}%. "
            "Our threshold to recommend a fabric as the next recommended option is 70%. "
            "Write a brief summary stating if this is an acceptable substitute based on"
            "the score, and what a score like this implies about "
            "their visual characteristics (texture and color)."
        )
    }
]


try:
    response = client.chat.complete(
        model = model,
        messages = messages
    )

    print("\n---- Mistral AI Final Assessment -----")
    print(response.choices[0].message.content)
    print("--------------------------------------\n")
    
except Exception as e:
    print("An error occurred during the API call...")