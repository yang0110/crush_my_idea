import torch
from gme_encoder_class import GmeQwen2VL
import os
from tqdm import tqdm
from glob import glob
import numpy as np
import pandas as pd
from pymilvus import MilvusClient
os.environ["TOKENIZERS_PARALLELISM"] = "false"

folder_list = os.listdir('./pages')
print(f"Found {len(folder_list)} folders in './pages'")
image_list = []
for folder in folder_list:
    images = os.listdir(os.path.join('./pages', folder))
    for image in images:
        if image.endswith('.jpg') or image.endswith('.png'):
            image_list.append(os.path.join('./pages', folder, image))

print(f"Total images found: {len(image_list)}")

# Initialize the GmeQwen2VL encoder for mm embedding tasks
encoder = GmeQwen2VL("Alibaba-NLP/gme-Qwen2-VL-2B-Instruct")
print('encoder', encoder)

image_emb_dict = {}
for image_path in tqdm(image_list):
    print('image_path', image_path)
    image_emb_dict[image_path] = encoder.get_image_embeddings(images=[image_path]).flatten().numpy().tolist()
    print("Number of encoded images:", len(image_emb_dict))

# --- create database --- 
dim = len(list(image_emb_dict.values())[0])
print('dim', dim)

# Initialize Milvus client
milvus_client = MilvusClient(uri="./milvus_demo.db")

# Create collections for image embeddings
collection_name = "image_embedding_collection"
if milvus_client.has_collection(collection_name=collection_name):
    milvus_client.drop_collection(collection_name=collection_name)

milvus_client.create_collection(
    collection_name=collection_name,
    dimension=dim,
    auto_id=True,
    enable_dynamic_field=True,
    consistency_level="Strong"
)
milvus_client.insert(
    collection_name=collection_name,
    data=[{"image_path": k, "vector": v} for k, v in image_emb_dict.items()],
)
