from openai import OpenAI
import base64
import os
import json
from tqdm import tqdm

def get_base64_data_uri_for_local_image(image_path):
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        return None
    extension = os.path.splitext(image_path)[1].lower()
    if extension == '.jpg' or extension == '.jpeg':
        mime_type = 'image/jpeg'
    elif extension == '.png':
        mime_type = 'image/png'
    elif extension == '.gif':
        mime_type = 'image/gif'
    elif extension == '.webp':
        mime_type = 'image/webp'
    else:
        print(f"Warning: Unknown image file extension '{extension}'. Defaulting to 'application/octet-stream'.")
        mime_type = 'application/octet-stream'

    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        print(f"Error encoding image '{image_path}': {e}")
        return None

openai_api_key = "EMPTY"
openai_api_base = "http://localhost:8000/v1"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)
print('client', client)

image_list = os.listdir('./pages/')

prompt = 'read the image and extract all text the content on the image'

page_summary_dict = {}
image_list = [os.path.join('./pages/', image) for image in os.listdir(os.path.join('./pages/'))]
for image_path in tqdm(image_list):
    print(f"Processing image: {image_path}")
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        continue
    image_data_uri = get_base64_data_uri_for_local_image(image_path)
    
    chat_response = client.chat.completions.create(
        model="Qwen/Qwen2.5-VL-7B-Instruct",
        messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_uri
                            }
                        }
                    ]
                }
            ],
        max_tokens=32768,
        temperature=0.6,
        top_p=0.95,
        extra_body={
            "top_k": 20,
        },
    )
    # print("Chat response:", chat_response)
    generated_content = chat_response.choices[0].message.content
    print("Extracted Content:")
    print(generated_content[:100] + "...")  # Print first 100 chars for brevity
    print(f"Length of generated content: {len(generated_content)} characters")
    # Save the generated content to the dictionary
    page_summary_dict[image_path] = generated_content
    print(len(page_summary_dict), "images processed so far.")

# Save the page summaries to a JSON file
with open("./page_content.json", "w") as file:
    json.dump(page_summary_dict, file, indent=4)
print("Page summaries saved to page_content.json")
