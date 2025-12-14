import json
import sys
from pathlib import Path
from collections import defaultdict

from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def load_company_inputs(company_dir: str) -> dict:
    p = Path(company_dir)
    inputs_path = p / "input_payload.json"
    if not inputs_path.exists():
        raise FileNotFoundError(f"inputs.json not found at: {inputs_path}")
    return json.loads(inputs_path.read_text(encoding="utf-8"))


def embed_queries(queries, model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        queries,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    return embeddings


def choose_num_clusters(n_queries, min_clusters=4, max_clusters=20, target_cluster_size=3):
    if n_queries <= 0:
        return 0
    estimated = max(1, n_queries // target_cluster_size)
    k = max(min_clusters, min(max_clusters, estimated))
    k = min(k, n_queries)
    return k


def cluster_queries(embeddings, n_clusters, random_state=42):
    kmeans = MiniBatchKMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        batch_size=256,
        n_init="auto",
    )
    labels = kmeans.fit_predict(embeddings)
    return labels


def extract_cluster_keywords(queries, labels, top_n=5):
    cluster_to_texts = defaultdict(list)
    for q, label in zip(queries, labels):
        cluster_to_texts[label].append(q)

    cluster_keywords = {}
    for label, texts in cluster_to_texts.items():
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000,
        )
        X = vectorizer.fit_transform(texts)
        mean_tfidf = X.mean(axis=0).A1
        feature_names = vectorizer.get_feature_names_out()
        top_idx = mean_tfidf.argsort()[::-1][:top_n]
        cluster_keywords[label] = [feature_names[i] for i in top_idx]
    return cluster_keywords


def build_theme_names(cluster_keywords, default_prefix="Theme"):
    theme_names = {}
    for label, keywords in cluster_keywords.items():
        theme_names[label] = ", ".join(keywords[:3]) if keywords else f"{default_prefix} {label}"
    return theme_names


def main(company_dir: str):
    cfg = load_company_inputs(company_dir)

    keywords = cfg.get("keywords", [])
    if not keywords:
        raise ValueError("inputs.json missing 'keywords' list")

    keyword_ids = [k["keyword_id"] for k in keywords]
    queries = [k["keyword"] for k in keywords]

    print(f"Total queries: {len(queries)}")

    embeddings = embed_queries(queries)

    k = choose_num_clusters(
        n_queries=len(queries),
        min_clusters=4,
        max_clusters=10,
        target_cluster_size=3,
    )
    print(f"Chosen number of clusters: {k}")

    labels = cluster_queries(embeddings, n_clusters=k)

    cluster_items = defaultdict(list)
    for kid, q, label in zip(keyword_ids, queries, labels):
        cluster_items[int(label)].append({"keyword_id": kid, "keyword": q})

    cluster_keywords = extract_cluster_keywords(queries, labels, top_n=5)
    theme_names = build_theme_names(cluster_keywords)

    result = {"k": int(k), "clusters": []}

    for label in sorted(cluster_items.keys()):
        items = cluster_items[label]
        ids = [x["keyword_id"] for x in items]
        result["clusters"].append(
            {
                "cluster_id": int(label),
                "theme": theme_names.get(label, f"Theme {label}"),
                "keywords": cluster_keywords.get(label, []),
                "ids": ids,
                "items": items,
            }
        )

    print("\nClustered themes")
    for c in result["clusters"]:
        print(f"\nCluster {c['cluster_id']}  ids: {', '.join(c['ids'])}  theme: {c['theme']}")
        if c["keywords"]:
            print("  keywords:", ", ".join(c["keywords"]))
        for it in c["items"]:
            print(f"   - {it['keyword_id']}: {it['keyword']}")

    out_path = Path(company_dir) / "clusters.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1])
