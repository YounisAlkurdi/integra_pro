import asyncio
import time
from engine.analyzers.lexical import AdvancedLexicalAnalyzer
from engine.analyzers.syntactic import SyntacticAnalyzer
from engine.analyzers.readability import DynamicsAnalyzer
from engine.analyzers.semantic import SemanticAnalyzer
from engine.analyzers.neural import NeuralDetector

# --- Singleton AI Analyzers ---
print("🧠 Forensic Service: Initializing Neural & Linguistic Models...")
lexical  = AdvancedLexicalAnalyzer()
syntactic = SyntacticAnalyzer()
dynamics  = DynamicsAnalyzer()
semantic  = SemanticAnalyzer()
neural    = NeuralDetector()

def score_lexical(res: dict) -> float:
    entropy = res.get("shannon_entropy", 4.5)
    score = (entropy - 3.5) / (5.5 - 3.5)
    return round(min(max(score, 0.0), 1.0), 4)

def score_dynamics(res: dict) -> float:
    burst = res.get("burstiness_score", 0.5)
    score = 1.0 - min(burst / 0.5, 1.0)
    return round(score, 4)

def score_syntactic(res: dict) -> float:
    pronoun_ratio = res.get("pronoun_ratio", 0.08)
    score = 1.0 - min(pronoun_ratio / 0.15, 1.0)
    return round(score, 4)

def score_semantic(res: dict) -> float:
    alignment = res.get("question_alignment_score", 0.0)
    return round(min(alignment, 1.0), 4)

def calculate_ai_score(lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res) -> float:
    scores = {
        "lexical":   score_lexical(lexical_res),
        "dynamics":  score_dynamics(dynamics_res),
        "syntactic": score_syntactic(syntactic_res),
        "semantic":  score_semantic(semantic_res),
    }
    weights = {"lexical": 0.40, "dynamics": 0.30, "syntactic": 0.20, "semantic": 0.10}
    statistical_score = sum(scores[k] * weights[k] for k in weights)

    neural_label = neural_res.get("ai_label", "Untested")
    neural_conf  = neural_res.get("confidence", 0.5)

    adjustment = 0.15 * neural_conf if neural_label == "Fake" else (-0.10 * neural_conf if neural_label == "Real" else 0.0)
    
    final_score = statistical_score + adjustment
    return round(min(max(final_score, 0.01), 0.99), 2)

async def perform_forensic_analysis(text: str, question: str = ""):
    """
    Unified entry point for forensic text analysis.
    Shared between the main API and the standalone forensic engine.
    """
    if not text.strip():
        return {"error": "Empty text provided"}

    start_time = time.time()
    
    # Run all analyzers in parallel
    tasks = [
        asyncio.create_task(neural.predict_async(text)),
        asyncio.to_thread(lexical.analyze, text),
        asyncio.to_thread(dynamics.analyze, text),
        asyncio.to_thread(syntactic.analyze, text),
        asyncio.to_thread(semantic.analyze, text, question),
    ]

    neural_res, lexical_res, dynamics_res, syntactic_res, semantic_res = await asyncio.gather(*tasks)

    overall_prob = calculate_ai_score(lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res)
    latency = round(time.time() - start_time, 3)

    return {
        "overall_ai_probability": overall_prob,
        "verdict": "High AI Probability" if overall_prob > 0.75 else ("Human Typical" if overall_prob < 0.35 else "Mixed Signals"),
        "performance": {"latency_ms": latency * 1000},
        "component_scores": {
            "lexical": score_lexical(lexical_res),
            "dynamics": score_dynamics(dynamics_res),
            "syntactic": score_syntactic(syntactic_res),
            "semantic": score_semantic(semantic_res),
        },
        "neural": neural_res,
        "statistical_details": {
            "lexical": lexical_res,
            "dynamics": dynamics_res,
            "syntactic": syntactic_res,
            "semantic": semantic_res
        }
    }
