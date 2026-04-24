import re
from collections import Counter

class SyntacticAnalyzer:
    """Analyzes grammar ratios. Fallback to regex if spacy/pydantic v3.14 breaks."""
    
    def __init__(self):
        try:
            import spacy
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                import subprocess
                subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                self.nlp = spacy.load("en_core_web_sm")
            self.is_spacy = True
        except Exception as e:
            print(f"Syntactic (Spacy) Load Error: {e}. Falling back to Regex Heuristics.")
            self.nlp = None
            self.is_spacy = False

    def analyze(self, text):
        if self.is_spacy and self.nlp:
            try:
                doc = self.nlp(text)
                pos_counts = Counter([token.pos_ for token in doc])
                nouns = pos_counts.get("NOUN", 0) + pos_counts.get("PROPN", 0)
                pronouns = pos_counts.get("PRON", 0)
                total = sum(pos_counts.values()) or 1
                
                sub_clauses = len([token for token in doc if token.dep_ in ["advcl", "ccomp"]])
                
                return {
                    "noun_ratio": round(nouns / total, 3),
                    "pronoun_ratio": round(pronouns / total, 3),
                    "subordinate_clauses": sub_clauses,
                    "syntactic_complexity_score": round((sub_clauses / len(list(doc.sents))) if len(list(doc.sents)) > 0 else 0, 2)
                }
            except:
                pass
                
        nouns_approx = len(re.findall(r'\b[a-z]{3,}(tion|ment|ity|ness|ship|ance|ence)s?\b', text, re.I))
        pronouns_approx = len(re.findall(r'\b(I|me|my|mine|we|us|our|ours|you|your|yours|he|him|his|she|her|hers|it|its|they|them|their|theirs)\b', text, re.I))
        
        words = text.split()
        total = len(words) or 1
        return {
            "noun_ratio": round(nouns_approx / total, 3),
            "pronoun_ratio": round(pronouns_approx / total, 3),
            "subordinate_clauses": 0,
            "syntactic_complexity_score": 0.5
        }