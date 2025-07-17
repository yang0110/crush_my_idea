# --- call bedrock for reasoning ---
import boto3
import json
import base64
import os

# Replace with your desired AWS region
model_id = "anthropic.claude-3-sonnet-20240229-v1:0" # Claude 3 Sonnet or Opus
region_name = 'us-east-1' 
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=region_name
)

# Encode the image to base64
image_list = os.listdir('./pages/MuZero/')
print(image_list)
# image_path = sorted_results[0]['image_path']
# print('image_path', image_path)
result_dict = {}
for image_path in image_list:
    with open(os.path.join('./pages/MuZero/', image_path), "rb") as image_file:
        image_bytes = image_file.read()
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt_text = f'first, read the image. Second, summary the content in the image.'
    print('prompt_text=', prompt_text)

    messages_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",  # Or image/png, image/webp, image/gif
                "data": encoded_image,
            },
        },
        {"type": "text", "text": prompt_text},
    ]

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": messages_content
            }
        ]
    }

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        response_body = json.loads(response.get("body").read())
        if response_body and response_body.get("content"):
            generated_text = ""
            for content_block in response_body["content"]:
                if content_block.get("type") == "text":
                    generated_text += content_block["text"]
            print("Bedrock Generated Text:")
            print(generated_text)
        else:
            print("No content found in the model response.")

    except Exception as e:
        print(f"Error invoking model with image: {e}")
    result_dict[image_path] = generated_text

with open("page_qa_pair.json", "w") as file:
    json.dump(result_dict, file)