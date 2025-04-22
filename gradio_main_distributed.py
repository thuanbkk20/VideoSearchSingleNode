import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from src.schemas.input import TaskInput
from src.model import MultimodalEmbeddingModel
from src.milvus import MilvusDatabase

# Load multiple DB URLs from environment
DB_URLs = os.environ.get("DB_URLs", "http://localhost:19530").split(",")

VIDEO_COLLECTION_NAME = os.environ.get("VIDEO_COLLECTION_NAME", "video_embedding")
TEXT_COLLECTION_NAME = os.environ.get("TEXT_COLLECTION_NAME", "text_embedding")

logger.info(f"Retrieving data from Milvus instances: {DB_URLs}")

model = MultimodalEmbeddingModel()
milvus_instances = [MilvusDatabase(url.strip()) for url in DB_URLs]

sample_videos = [
    "video-fetch-and-trim/videos/education_0.mp4",  # local
    "video-fetch-and-trim/videos/education_2.mp4",  # local
    "video-fetch-and-trim/videos/news & politics_0.mp4",  # local
    "video-fetch-and-trim/videos/news & politics_1.mp4",  # local
]


def main(video_url: str):
    input_ = TaskInput(
        video=video_url,
        text=None,
    )
    results = []

    def query_from_instance(milvus_instance, url):
        return url, model.retrieve_similarity_from_milvus(
            input_, milvus_instance, VIDEO_COLLECTION_NAME, TEXT_COLLECTION_NAME, limit=10
        )

    with ThreadPoolExecutor(max_workers=len(milvus_instances)) as executor:
        futures = [
            executor.submit(query_from_instance, m, url)
            for m, url in zip(milvus_instances, DB_URLs)
        ]
        for future in as_completed(futures):
            try:
                url, res = future.result()
                logger.info(f"Retrieved {len(res)} results from {url}")
                results.extend(res)
            except Exception as e:
                logger.error(f"Query failed from instance: {e}")

    return results


def init(n_videos: int):
    """Return list of trending videos"""
    results = []

    def fetch_from_instance(milvus_instance, url):
        return url, milvus_instance.query(
            collection_name=VIDEO_COLLECTION_NAME,
            limit=20,
            output_fields=["video"]
        )

    with ThreadPoolExecutor(max_workers=len(milvus_instances)) as executor:
        futures = [
            executor.submit(fetch_from_instance, m, url)
            for m, url in zip(milvus_instances, DB_URLs)
        ]
        for future in as_completed(futures):
            try:
                url, res = future.result()
                logger.info(f"Fetched {len(res)} videos from {url}")
                results.extend(res)
            except Exception as e:
                logger.error(f"Init query failed from instance: {e}")

    # Remove duplicates
    video_list = list(dict.fromkeys([r["video"] for r in results]))
    return video_list[:n_videos]
