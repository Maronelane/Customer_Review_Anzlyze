import inspect
import json

import pandas as pd

from db import _safe_for_mongo
from ml_engine import clean_text, detect_sentiment_from_rating, run_full_pipeline


def test_clean_text():
    raw = "This is NOT good!! Check http://example.com"
    cleaned = clean_text(raw)
    assert "http" not in cleaned
    assert "not_good" in cleaned # verifying our negation logic


def test_sentiment_detection():
    assert detect_sentiment_from_rating(5) == "positive"
    assert detect_sentiment_from_rating(1) == "negative"
    assert detect_sentiment_from_rating(3) == "neutral"


def test_run_full_pipeline_api_matches_app_calls():
    params = inspect.signature(run_full_pipeline).parameters
    assert "custom_categories" in params
    assert "use_transformer" in params


def test_ml_results_are_serializable_for_mongo():
    df = pd.DataFrame({
        "text": [
            "I love this product",
            "This is awful",
            "It is okay",
            "Great quality and fast shipping",
            "Terrible experience",
            "The item is average",
        ],
        "rating": [5, 1, 3, 5, 1, 3],
    })

    results = run_full_pipeline(df, "text", "rating")
    safe = _safe_for_mongo(results["models"])
    json.dumps(safe)
    assert all("model" not in str(key) for key in safe)
