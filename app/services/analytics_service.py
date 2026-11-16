"""
Data Analytics & Machine Learning Service Module
Implements:
1. Linear Regression (Cuaca historis & tren tutupan awan/suhu)
2. Clustering (K-Means pengelompokan kondisi cuaca/observasi)
3. Sentiment Analysis (Analisis tanggapan teks publik seputar astronomi)
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans

def train_weather_trend_regression(historical_data: list):
    """
    Fits linear regression on historical weather data to estimate trend.
    """
    if not historical_data:
        return None
    
    df = pd.DataFrame(historical_data)
    # Features e.g. day index, Target: temperature or cloud cover
    X = np.arange(len(df)).reshape(-1, 1)
    y = df['value'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    return {
        'slope': float(model.coef_[0]),
        'intercept': float(model.intercept_)
    }

def cluster_observation_conditions(features_list: list, n_clusters: int = 3):
    """
    Applies K-Means clustering to observation condition records
    (e.g., [cloud_cover, humidity, rain_prob]).
    """
    if len(features_list) < n_clusters:
        return []
    
    X = np.array(features_list)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    labels = kmeans.fit_predict(X)
    
    return {
        'labels': labels.tolist(),
        'cluster_centers': kmeans.cluster_centers_.tolist()
    }

def analyze_sentiment(text: str) -> dict:
    """
    Rule/Lexicon-based or simple classifier placeholder for sentiment analysis
    on astronomy public comments.
    """
    positive_words = {'menakjubkan', 'indah', 'keren', 'kagum', 'luar biasa', 'terang', 'jelas', 'suka', 'antusias'}
    negative_words = {'kecewa', 'mendung', 'gelap', 'buruk', 'gagal', 'hujan', 'sayang', 'tertutup awan'}
    
    words = text.lower().split()
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    
    if pos_count > neg_count:
        sentiment = 'Positif'
        score = 0.5 + min(0.5, pos_count * 0.1)
    elif neg_count > pos_count:
        sentiment = 'Negatif'
        score = -(0.5 + min(0.5, neg_count * 0.1))
    else:
        sentiment = 'Netral'
        score = 0.0
        
    return {
        'text': text,
        'sentiment': sentiment,
        'polarity_score': round(score, 2)
    }
