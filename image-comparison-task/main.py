import os
from dotenv import load_dotenv
import base64
from mistralai.client import Mistral

load_dotenv()

#initializing Mistral Client 
apiKey = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"
client = Mistral(api_key = apiKey)

img1 = "fabric3.png"
img2 = "fabric4.jpg"

print("Encoding the images...")

# Reading and encoding the images 
with open(img1, "rb") as imgFile1:
    base64_img1 = base64.b64encode(imgFile1.read()).decode('utf-8')

with open(img2, "rb") as imgFile2:
    base64_img2 = base64.b64encode(imgFile2.read()).decode('utf-8')

print("Sending encoded images to Mistral AI for comparison...")


messages = [
    {
   "role": "user", "content": [
            {
                "type": "text", "text": (
                    "Analyze these two fabric images from Al Kilani Fabrics. "
                    "Compare them closely regarding their color and texture. "
                    "Based on the visual assessment, give an estimated similarity percentage (0-100%) "
                    "Keep the colour and texture similarity separate."
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

# Executing API call and printing the results
try:
    response = client.chat.complete(
        model = model,
        messages = messages
    )

    print("\n---- Mistral AI Test Results: -----")
    print(response.choices[0].message.content)
    print("----------------------\n")
    
except Exception as e:
    print("An error occurred during API call...")
