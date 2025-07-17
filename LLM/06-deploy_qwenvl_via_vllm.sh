# conda create -n vlm_env python=3.10 -y
# conda activate vlm_env
# python=3.10
# pip install "vllm>=0.8.5"
# pip install openai
vllm serve "Qwen/Qwen2.5-VL-7B-Instruct" --tensor-parallel-size 2