"""
RAG 测试 01: 下载并测试 Embedding 模型

支持模型:
- Qwen3-Embedding-0.6B (Qwen/Qwen3-Embedding-0.6B)
- all-MiniLM-L6-v2 (sentence-transformers/all-MiniLM-L6-v2)

运行方式:
    # 测试 Qwen 模型（默认）
    python scripts/rag/01_download_model.py

    # 测试 all-MiniLM-L6-v2
    python scripts/rag/01_download_model.py --model minilm
"""
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import sys
sys.path.insert(0, "/home/skdy/server/Aeris")

import argparse
import torch


# 模型配置
MODELS = {
    "qwen": {
        "name": "Qwen/Qwen3-Embedding-0.6B",
        "dir": "/home/skdy/server/Aeris/models/Qwen3-Embedding-0.6B",
        "use_sentence_transformer": False,
    },
    "minilm": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "dir": "/home/skdy/server/Aeris/models/all-MiniLM-L6-v2",
        "use_sentence_transformer": True,
    },
}


def test_qwen_model(model_name: str, model_dir: str):
    """测试 Qwen embedding 模型"""
    from transformers import AutoModel, AutoTokenizer

    print(f"正在加载模型: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        cache_dir=model_dir
    )
    print("✅ Tokenizer 加载成功")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = AutoModel.from_pretrained(
        model_name,
        trust_remote_code=True,
        cache_dir=model_dir
    ).to(device)
    print("✅ Model 加载成功")

    # 测试向量化
    test_text = "这是一个测试文本"
    inputs = tokenizer(test_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :]

    print(f"✅ 向量维度: {embedding.shape}")
    print(f"✅ 向量类型: {type(embedding)}, dtype: {embedding.dtype}")
    print(f"✅ 向量示例 (前5维): {embedding[0][:5].float().cpu().tolist()}")

    return embedding.shape[1]


def test_minilm_model(model_name: str, model_dir: str):
    """测试 all-MiniLM-L6-v2 模型"""
    from sentence_transformers import SentenceTransformer

    print(f"正在加载模型: {model_name}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"使用设备: {device}")

    model = SentenceTransformer(model_name, cache_folder=model_dir, device=device)
    print("✅ Model 加载成功")

    # 测试向量化
    test_text = "这是一个测试文本"
    embedding = model.encode(test_text)

    print(f"✅ 向量维度: {embedding.shape}")
    print(f"✅ 向量类型: {type(embedding)}, dtype: {embedding.dtype}")
    print(f"✅ 向量示例 (前5维): {embedding[:5].tolist()}")

    return embedding.shape[0]


def main():
    parser = argparse.ArgumentParser(description="测试 Embedding 模型")
    parser.add_argument(
        "--model",
        choices=["qwen", "minilm"],
        default="minilm",
        help="选择模型: qwen (Qwen3-Embedding-0.6B) 或 minilm (all-MiniLM-L6-v2)"
    )
    args = parser.parse_args()

    config = MODELS[args.model]
    model_name = config["name"]
    model_dir = config["dir"]

    print(f"\n{'='*50}")
    print(f"测试模型: {model_name}")
    print(f"缓存目录: {model_dir}")
    print(f"{'='*50}\n")

    if config["use_sentence_transformer"]:
        dim = test_minilm_model(model_name, model_dir)
    else:
        dim = test_qwen_model(model_name, model_dir)

    print(f"\n✅ 测试完成，向量维度: {dim}")


if __name__ == "__main__":
    main()
