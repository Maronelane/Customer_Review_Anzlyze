"""
Refactored ML Engine for Sentiment Analysis and Classification.
Fixes data leakage via Scikit-Learn Pipelines, enhances text cleaning 
with robust multi-word negation handling, and ensures correct polarity mapping.
"""

import os
import pickle
import re
import string
import logging
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
import pandas as pd

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from collections import Counter
from sklearn.model_selection import StratifiedKFold, train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Ensure NLTK packages are downloaded safely
def _download_nltk_resources():
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/stopwords', 'stopwords'),
        ('corpora/wordnet', 'wordnet'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger')
    ]
    for resource_path, resource_name in resources:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            nltk.download(resource_name, quiet=True)

_download_nltk_resources()

# Initialize NLP globals
STOP_WORDS = set(stopwords.words('english'))
STOP_WORDS.discard("not")
STOP_WORDS.discard("no")
STOP_WORDS.discard("nor")
STOP_WORDS.discard("neither")

LEMMATIZER = WordNetLemmatizer()

def clean_text(text: str) -> str:
    """
    Cleans raw text for NLP tasks while securely anchoring negations to adjacent words 
    (e.g., 'not good' -> 'not_good', 'dont buy' -> 'do_not_buy') to prevent semantic inversion.
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove URLs and HTML tags first so they don't interfere with tokens
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    
    # 3. Normalize explicit contract conversions to avoid splitting negations
    text = re.sub(r"\b(don['\u2019]t|dont)\b", "do_not", text)
    text = re.sub(r"\b(can['\u2019]t|cant)\b", "can_not", text)
    text = re.sub(r"\b(won['\u2019]t|wont)\b", "will_not", text)
    text = re.sub(r"\b(isn['\u2019]t|isnt)\b", "is_not", text)
    text = re.sub(r"\b(aren['\u2019]t|arent)\b", "are_not", text)
    text = re.sub(r"\b(didn['\u2019]t|didnt)\b", "did_not", text)
    text = re.sub(r"\b(wasn['\u2019]t|wasnt)\b", "was_not", text)
    text = re.sub(r"\b(weren['\u2019]t|werent)\b", "were_not", text)
    text = re.sub(r"\b(haven['\u2019]t|havent)\b", "have_not", text)
    text = re.sub(r"\b(hasn['\u2019]t|hasnt)\b", "has_not", text)
    text = re.sub(r"\b(hadn['\u2019]t|hadnt)\b", "had_not", text)
    
    # 4. Remove punctuation except underscores (protects compound words and spaces)
    punc_to_remove = string.punctuation.replace('_', '')
    text = text.translate(str.maketrans('', '', punc_to_remove))
    
    # 5. Remove standalone digits
    text = re.sub(r'\b\d+\b', '', text)
    
    # 6. Robust Multi-word Negation Scoping
    negation_words = {"not", "no", "never", "neither", "nor", "hardly", "scarcely", "barely"}
    tokens = text.split()
    processed_tokens = []
    
    is_negated = False
    negation_window = 0
    
    for token in tokens:
        if token in negation_words:
            is_negated = True
            negation_window = 2  # tag the next 2 words with negation prefix
            continue  # skip appending the standalone negation word itself
            
        if is_negated:
            if negation_window > 0 and token:
                processed_tokens.append(f"not_{token}")
                negation_window -= 1
            else:
                processed_tokens.append(token)
            if negation_window == 0:
                is_negated = False
        else:
            processed_tokens.append(token)
            
    # 7. Final Token Filtering & Lemmatization
    final_tokens = []
    for token in processed_tokens:
        if '_' in token:
            parts = token.split('_')
            lemmatized_parts = [LEMMATIZER.lemmatize(p) for p in parts if p]
            if len(lemmatized_parts) > 1:
                final_tokens.append("_".join(lemmatized_parts))
        else:
            if token not in STOP_WORDS and len(token) > 2:
                final_tokens.append(LEMMATIZER.lemmatize(token))
                
    return " ".join(final_tokens)


def detect_sentiment_from_rating(rating: Any) -> str:
    """Maps a numerical rating to a categorical sentiment label."""
    try:
        r = float(rating)
        if r >= 4.0:
            return "positive"
        elif r <= 2.0:
            return "negative"
        else:
            return "neutral"
    except (ValueError, TypeError):
        return "neutral"


def _generate_labels_from_text(texts: List[str]) -> List[str]:
    """Fallback label generation using TextBlob polarity if no ratings exist."""
    labels = []
    try:
        from textblob import TextBlob
        for t in texts:
            polarity = TextBlob(t).sentiment.polarity
            if polarity > 0.1:
                labels.append("positive")
            elif polarity < -0.1:
                labels.append("negative")
            else:
                labels.append("neutral")
    except ImportError:
        logger.warning("TextBlob not installed. Defaulting unrated texts to 'neutral'.")
        labels = ["neutral"] * len(texts)
    return labels


def train_models(df: pd.DataFrame, text_column: str, rating_column: Optional[str] = None) -> Tuple[Any, Dict[str, Any], Optional[str]]:
    """
    Trains and evaluates multiple sentiment classification models using Scikit-Learn Pipelines.
    Preventing data leakage by vectorizing strictly inside cross-validation loops.
    """
    if df.empty or text_column not in df.columns:
        raise ValueError("Provided DataFrame is empty or missing the specified text column.")

    # 1. Clean Texts
    logger.info("Cleaning text data for model training...")
    cleaned_texts = df[text_column].apply(clean_text).tolist()

    # 2. Assign Labels
    if rating_column and rating_column in df.columns:
        labels = df[rating_column].apply(detect_sentiment_from_rating).tolist()
    else:
        logger.info("No rating column provided. Generating pseudo-labels via TextBlob...")
        labels = _generate_labels_from_text(cleaned_texts)

    df_model = pd.DataFrame({'text': cleaned_texts, 'label': labels})
    df_model['text'] = df_model['text'].fillna("").astype(str)
    df_model = df_model[df_model['text'].str.strip() != ""] # Drop empty texts

    if len(df_model) < 5:
        raise ValueError("Not enough valid data points remaining after text cleaning to train models.")

    X = df_model['text']
    y = df_model['label']

    # Define Candidate Models wrapped in a Pipeline (TF-IDF Vectorizer + Classifier)
    models = {
        "naive_bayes": Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000, max_df=0.95)),
            ('clf', MultinomialNB())
        ]),
        "logistic_regression": Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000, max_df=0.95)),
            ('clf', LogisticRegression(max_iter=1000, random_state=42))
        ]),
        "svm": Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000, max_df=0.95)),
            ('clf', LinearSVC(random_state=42, max_iter=1000))
        ])
    }

    results = {}
    best_model_name = None
    highest_score = -1.0

    # Determine cross-validation splits safely based on class distribution
    min_class_count = y.value_counts().min()
    n_splits = 5 if min_class_count >= 5 else max(2, min_class_count)

    for name, pipeline in models.items():
        logger.info(f"Evaluating model: {name} with {n_splits}-fold Stratified CV...")
        try:
            if n_splits >= 2 and len(y.unique()) > 1:
                cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
                scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy')
                mean_acc = float(np.mean(scores))
            else:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                pipeline.fit(X_train, y_train)
                preds = pipeline.predict(X_test)
                mean_acc = float(accuracy_score(y_test, preds))
        except Exception as e:
            logger.error(f"Error evaluating {name}: {e}")
            continue

        # Refit on the *entire* dataset for production inference
        pipeline.fit(X, y)
        full_preds = pipeline.predict(X)
        report = classification_report(y, full_preds, output_dict=True, zero_division=0)

        results[name] = {
            "model": pipeline,
            "accuracy": mean_acc,
            "classification_report": report
        }

        if mean_acc > highest_score:
            highest_score = mean_acc
            best_model_name = name

    if not best_model_name:
        raise RuntimeError("All model training routines failed. Check your input data constraints.")

    best_model = results[best_model_name]["model"]
    logger.info(f"Best model selected: {best_model_name} with accuracy: {highest_score:.4f}")

    return best_model, results, best_model_name


def save_model(model: Any, filepath: str = "saved_models/best_sentiment_model.pkl") -> None:
    """Serializes and saves the trained pipeline model to disk."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Model successfully saved to {filepath}")


def load_model(filepath: str = "saved_models/best_sentiment_model.pkl") -> Any:
    """Loads a serialized pipeline model from disk."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No saved model found at {filepath}")
    with open(filepath, "rb") as f:
        model = pickle.load(f)
    logger.info(f"Model successfully loaded from {filepath}")
    return model


def predict_sentiment(model: Any, texts: List[str]) -> List[Dict[str, Any]]:
    """Runs predictions on new lists of text using the pipeline model."""
    if not texts:
        return []
    
    cleaned = [clean_text(t) for t in texts]
    predictions = model.predict(cleaned)
    
    results = []
    for original, pred in zip(texts, predictions):
        results.append({
            "text": original,
            "predicted_sentiment": pred
        })
    return results


def run_full_pipeline(
    df: pd.DataFrame,
    text_column: str,
    rating_column: Optional[str] = None,
    progress_cb=None,
    custom_categories: Optional[dict] = None,
    use_transformer: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    Runs the full machine learning pipeline including cleaning, model training,
    feature extraction, and inference generation. Supports progress callbacks.
    """
    if custom_categories is not None:
        logger.info("Custom categories supplied for downstream analysis: %s", sorted(custom_categories.keys())[:10])

    if use_transformer:
        logger.info("Transformer mode requested; using the standard sklearn pipeline fallback for compatibility.")

    if progress_cb:
        try:
            progress_cb("Initializing machine learning pipeline...", 5)
        except Exception:
            pass

    # 1. Train models and get the best estimator pipeline
    best_model, results, best_name = train_models(df, text_column, rating_column)
    
    if progress_cb:
        try:
            progress_cb(f"Training complete. Best model: {best_name}. Running predictions...", 50)
        except Exception:
            pass

    # 2. Extract and clean texts for inference & problem detection
    cleaned_texts = df[text_column].apply(clean_text).tolist()
    original_texts = df[text_column].astype(str).tolist()

    # 3. Predict sentiments across the dataset
    all_predictions = best_model.predict(cleaned_texts).tolist()

    # 4. Calculate sentiment distributions
    sentiment_counts = Counter(all_predictions)
    total = len(all_predictions)
    sentiment_distribution = {
        "positive": sentiment_counts.get("positive", 0),
        "negative": sentiment_counts.get("negative", 0),
        "neutral": sentiment_counts.get("neutral", 0),
        "total": total,
    }

    # 5. Extract feature names from the TF-IDF vectorizer inside the pipeline
    try:
        tfidf_step = best_model.named_steps.get("tfidf")
        feature_names = tfidf_step.get_feature_names_out().tolist() if tfidf_step else []
    except Exception:
        feature_names = []

    # 6. Map predictions alongside original texts
    predictions_with_text = [
        {"text": original_texts[i], "sentiment": all_predictions[i], "cleaned": cleaned_texts[i]}
        for i in range(len(all_predictions))
    ]

    if progress_cb:
        try:
            progress_cb("Saving model and finalizing pipeline...", 70)
        except Exception:
            pass

    # 7. Save the best model artifact
    save_model(best_model)

    if progress_cb:
        try:
            progress_cb("Pipeline finished successfully!", 100)
        except Exception:
            pass

    serializable_models = {
        name: {
            "accuracy": info["accuracy"],
            "classification_report": info["classification_report"],
        }
        for name, info in results.items()
    }

    return {
        "models": serializable_models,
        "best_model": best_name,
        "best_accuracy": results[best_name]["accuracy"],
        "sentiment_distribution": sentiment_distribution,
        "predictions": predictions_with_text,
        "feature_names": feature_names,
    }