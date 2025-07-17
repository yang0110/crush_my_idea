import json 
from pymilvus import MilvusClient
from gme_encoder_class import GmeQwen2VL

encoder = GmeQwen2VL("Alibaba-NLP/gme-Qwen2-VL-2B-Instruct")
print('encoder', encoder)

milvus_client = MilvusClient(uri="./milvus_demo.db")
print(milvus_client)

with open("page_qa_pair.json", "r") as file:
    qa = json.load(file)

print(qa)

for k,v in qa.items():

    query_emb = encoder.get_text_embeddings(texts=[v]).flatten().numpy().tolist()
    # print('query_emb', len(query_emb))

    collection_name = "image_embedding_collection"
    # print("Searching in collection:", collection_name)
    search_results = milvus_client.search(
        collection_name=collection_name,
        data=[query_emb],
        output_fields=["image_path"],
        limit=5,  
        search_params={"metric_type": "COSINE", "params": {}},  # Search parameters
    )[0]
    # print("Search results:", search_results)
    sort_results = []
    for hit in search_results:
        # print(f"ID: {hit['id']}, Distance: {hit['distance']}, Image Path: {hit['entity']['image_path']}")
        sort_results.append(
            {
                "id": hit['id'],
                "score": hit['distance'],
                "image_path": hit['entity']['image_path']
            }
        )
    # print("sort results:", sort_results)
    sorted_results = sorted(sort_results, key=lambda x: x['score'], reverse=True)          
    topk = 1
    if len(sorted_results) >= topk:
        sorted_results = sorted_results[:topk]

    print('k=', k)
    print('v=', v)
    # print('sorted_results', sorted_results)
    for result in sorted_results:
        print(f"Score: {result['score']:.2f}, Image Path: {result['image_path']}")




