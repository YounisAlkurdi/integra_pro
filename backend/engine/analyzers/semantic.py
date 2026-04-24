from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SemanticAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()

    def calculate_similarity(self, text1, text2):
        if not text1 or not text2:
            return 0
        try:
            tfidf = self.vectorizer.fit_transform([text1, text2])
            return cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        except:
            return 0

    def analyze(self, answer, context_question=""):
        similarity = self.calculate_similarity(answer, context_question)
        
        return {
            "question_alignment_score": round(similarity, 3),
            "ai_prompt_behavior": "High" if similarity > 0.8 else "Normal"
        }
