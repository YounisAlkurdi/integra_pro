import numpy as np
import re

class DynamicsAnalyzer:
    """Analyzes Burstiness and Structural Variance (Research-Standard AI Detection)."""
    
    def __init__(self):
        pass

    def calculate_burstiness(self, text):
        """Measures variance of sentence lengths. AI is uniform, humans vary greatly."""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) < 2: return 0
        
        lens = [len(s.split()) for s in sentences]
        avg_len = np.mean(lens)
        std_dev = np.std(lens)
        
        # Burstiness = (Standard Deviation) / (Mean)
        return round(std_dev / avg_len if avg_len > 0 else 0, 3)

    def punctuation_density(self, text):
        """Measures misuse/uniformity of punctuation."""
        total_chars = len(text)
        if total_chars == 0: return 0
        punct_count = len(re.findall(r'[.,!?;:]', text))
        return round(punct_count / total_chars, 4)

    def analyze(self, text):
        burstiness = self.calculate_burstiness(text)
        return {
            "burstiness_score": burstiness,
            "sentence_variance": "Low (AI Indicator)" if burstiness < 0.3 else "High (Human typical)",
            "punctuation_density": self.punctuation_density(text)
        }
