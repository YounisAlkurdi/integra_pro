from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from analyzers.lexical import AdvancedLexicalAnalyzer
from analyzers.syntactic import SyntacticAnalyzer
from analyzers.readability import DynamicsAnalyzer
from analyzers.semantic import SemanticAnalyzer
from analyzers.neural import NeuralDetector
import uvicorn
import asyncio
import time

app = FastAPI(title="SOTA AI Detector Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

lexical  = AdvancedLexicalAnalyzer()
syntactic = SyntacticAnalyzer()
dynamics  = DynamicsAnalyzer()
semantic  = SemanticAnalyzer()
neural    = NeuralDetector()

# ─────────────────────────────────────────────
# NORMALIZERS  →  كل واحد بيرجع قيمة بين 0 و 1
# 0 = Human,  1 = AI
# ─────────────────────────────────────────────

def score_lexical(res: dict) -> float:
    entropy = res.get("shannon_entropy", 4.5)
    # Human: 3.5-4.7   AI: 4.9+
    score = (entropy - 3.5) / (5.5 - 3.5)
    return round(min(max(score, 0.0), 1.0), 4)

def score_dynamics(res: dict) -> float:
    burst = res.get("burstiness_score", 0.5)
    # Human: > 0.4   AI: < 0.2
    # نعكس القيمة لأن burstiness منخفض = AI
    score = 1.0 - min(burst / 0.5, 1.0)
    return round(score, 4)

def score_syntactic(res: dict) -> float:
    # نسبة الضمائر منخفضة = AI (الـ AI قليلاً ما يستخدم I/we/you)
    pronoun_ratio = res.get("pronoun_ratio", 0.08)
    score = 1.0 - min(pronoun_ratio / 0.15, 1.0)
    return round(score, 4)

def score_semantic(res: dict) -> float:
    # AI بيجاوب بنفس كلمات السؤال بشكل واضح
    alignment = res.get("question_alignment_score", 0.0)
    return round(min(alignment, 1.0), 4)

def calculate_ai_score(
    lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res
) -> float:

    scores = {
        "lexical":   score_lexical(lexical_res),
        "dynamics":  score_dynamics(dynamics_res),
        "syntactic": score_syntactic(syntactic_res),
        "semantic":  score_semantic(semantic_res),
    }

    # الأوزان الأساسية (بدون neural)
    weights = {
        "lexical":   0.40,
        "dynamics":  0.30,
        "syntactic": 0.20,
        "semantic":  0.10,
    }

    statistical_score = sum(scores[k] * weights[k] for k in weights)

    # Neural كـ تعديل إضافي مش كعامل أساسي
    neural_label = neural_res.get("ai_label", "Untested")
    neural_conf  = neural_res.get("confidence", 0.5)

    if neural_label == "Fake":
        # لو neural قال AI، نضيف 15% من ثقته
        adjustment = 0.15 * neural_conf
    elif neural_label == "Real":
        # لو neural قال Human، نطرح 10% من ثقته
        adjustment = -0.10 * neural_conf
    else:
        adjustment = 0.0

    final_score = statistical_score + adjustment
    return round(min(max(final_score, 0.01), 0.99), 2)


@app.get("/")
async def root():
    return {"status": "Research-Grade NLP Engine Online", "active_neural": neural.online}


@app.post("/analyze")
async def analyze_text(
    text: str = Body(..., embed=True),
    question: str = Body("", embed=True)
):
    if not text.strip():
        return {"error": "Empty text"}

    word_count = len(text.split())
    if word_count < 10:
        return {
            "overall_ai_probability": 0.05,
            "verdict": "Too Short To Analyze"
        }

    start_time = time.time()

    tasks = [
        asyncio.create_task(neural.predict_async(text)),
        asyncio.to_thread(lexical.analyze, text),
        asyncio.to_thread(dynamics.analyze, text),
        asyncio.to_thread(syntactic.analyze, text),
        asyncio.to_thread(semantic.analyze, text, question),
    ]

    neural_res, lexical_res, dynamics_res, syntactic_res, semantic_res = \
        await asyncio.gather(*tasks)

    overall_prob = calculate_ai_score(
        lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res
    )

    if overall_prob > 0.75:
        verdict = "High AI Probability"
    elif overall_prob < 0.35:
        verdict = "Human Typical"
    else:
        verdict = "Mixed Signals"

    latency = round(time.time() - start_time, 3)

    return {
        "overall_ai_probability": overall_prob,
        "verdict": verdict,
        "performance": {
            "latency_ms": latency * 1000,
            "system": "Hybrid-Forensic-V3"
        },
        "component_scores": {
            "lexical":   score_lexical(lexical_res),
            "dynamics":  score_dynamics(dynamics_res),
            "syntactic": score_syntactic(syntactic_res),
            "semantic":  score_semantic(semantic_res),
        },
        "neural": neural_res,
        "statistical": {
            "lexical":   lexical_res,
            "dynamics":  dynamics_res,
            "syntactic": syntactic_res,
            "semantic":  semantic_res,
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
