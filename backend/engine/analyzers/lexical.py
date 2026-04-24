import numpy as np
from scipy.stats import entropy
from collections import Counter
import re

class AdvancedLexicalAnalyzer:
    """Research-grade lexical analysis using Information Theory and Zipf's Law."""
    
    def __init__(self):
        pass

    def calculate_entropy(self, text):
        """Measures Shannon Entropy (Unpredictability/Randomness of language)."""
        words = re.findall(r'\w+', text.lower())
        if not words: return 0
        counts = Counter(words)
        probs = [count / len(words) for count in counts.values()]
        return round(entropy(probs, base=2), 3)

    def zipf_coefficient(self, text):
        """Calculates distance from Zipf's Law. AI follows this more strictly than humans."""
        words = re.findall(r'\w+', text.lower())
        if len(words) < 20: return 0
        
        counts = Counter(words)
        frequencies = sorted(counts.values(), reverse=True)
        ranks = np.arange(1, len(frequencies) + 1)
        
        # Log-log regression to find the slope (gamma)
        log_ranks = np.log(ranks)
        log_freqs = np.log(frequencies)
        
        # Linear fit: log(f) = -gamma * log(r) + C
        slope, _ = np.polyfit(log_ranks, log_freqs, 1)
        return round(abs(slope), 3)

    def MTLD(self, text):
        """Measure of Textual Lexical Diversity (Length-independent, research standard)."""
        words = re.findall(r'\w+', text.lower())
        if len(words) < 10: return 0
        
        def count_factors(word_list):
            factors = 0
            ttr_threshold = 0.72
            current_ttr = 1.0
            unique = set()
            count = 0
            
            for word in word_list:
                unique.add(word)
                count += 1
                current_ttr = len(unique) / count
                if current_ttr < ttr_threshold:
                    factors += 1
                    unique = set()
                    count = 0
            
            # Add partial factor
            if count > 0:
                factors += (1 - current_ttr) / (1 - ttr_threshold)
            return factors

        f1 = count_factors(words)
        f2 = count_factors(words[::-1])
        avg_factors = (f1 + f2) / 2
        return round(len(words) / avg_factors, 2) if avg_factors > 0 else 0

    def analyze(self, text):
        return {
            "shannon_entropy": self.calculate_entropy(text),
            "zipf_slope": self.zipf_coefficient(text),
            "mtld_diversity": self.MTLD(text),
            "complexity_index": "High" if self.calculate_entropy(text) > 4.5 else "Standard"
        }
