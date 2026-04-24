"""
evaluate.py  —  NLP Project Evaluation Script
ضعه في نفس مجلد main.py وشغّله مباشرة
"""

import sys
import os
import json
import time
import warnings
warnings.filterwarnings("ignore")

# ── إضافة مسار المشروع ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── استيراد الـ Analyzers ────────────────────────────────────────
from lexical    import AdvancedLexicalAnalyzer
from syntactic  import SyntacticAnalyzer
from readability import DynamicsAnalyzer
from semantic   import SemanticAnalyzer
from neural     import NeuralDetector


# ═══════════════════════════════════════════════════════════════
#  نفس دوال التسجيل من main.py  (نسخ حرفي)
# ═══════════════════════════════════════════════════════════════

def score_lexical(res):
    entropy = res.get("shannon_entropy", 4.5)
    return round(min(max((entropy - 3.5) / (5.5 - 3.5), 0.0), 1.0), 4)

def score_dynamics(res):
    burst = res.get("burstiness_score", 0.5)
    return round(1.0 - min(burst / 0.5, 1.0), 4)

def score_syntactic(res):
    pronoun_ratio = res.get("pronoun_ratio", 0.08)
    return round(1.0 - min(pronoun_ratio / 0.15, 1.0), 4)

def score_semantic(res):
    alignment = res.get("question_alignment_score", 0.0)
    return round(min(alignment, 1.0), 4)

def calculate_ai_score(lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res):
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

    if neural_label == "Fake":
        adjustment = 0.15 * neural_conf
    elif neural_label == "Real":
        adjustment = -0.10 * neural_conf
    else:
        adjustment = 0.0

    return round(min(max(statistical_score + adjustment, 0.01), 0.99), 2)


# ═══════════════════════════════════════════════════════════════
#  تحميل HC3 Dataset
# ═══════════════════════════════════════════════════════════════

def load_hc3(max_samples=200):
    """
    يحمّل dataset AI vs Human من HuggingFace
    """
    print("📦 جاري تحميل dataset ...")
    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ مكتبة datasets غير موجودة — شغّل: pip install datasets")
        sys.exit(1)

    ds = load_dataset("andythetechnerd03/AI-human-text", split="train")

    texts, labels = [], []

    for item in ds:
        text = item.get("text", "")
        label = item.get("generated", 0)  # 0=human, 1=AI
        if text and len(text.split()) >= 20:
            if label == 0 and labels.count(0) < max_samples:
                texts.append(text)
                labels.append(0)
            elif label == 1 and labels.count(1) < max_samples:
                texts.append(text)
                labels.append(1)
        if labels.count(0) >= max_samples and labels.count(1) >= max_samples:
            break

    print(f"✅ محمّل: {labels.count(0)} نص بشري  |  {labels.count(1)} نص AI\n")
    return texts, labels



# ═══════════════════════════════════════════════════════════════
#  تشغيل التقييم
# ═══════════════════════════════════════════════════════════════

def run_evaluation():
    texts, true_labels = load_hc3(max_samples=200)

    print("🔧 تهيئة الـ Analyzers ...")
    lexical   = AdvancedLexicalAnalyzer()
    syntactic = SyntacticAnalyzer()
    dynamics  = DynamicsAnalyzer()
    semantic  = SemanticAnalyzer()
    neural    = NeuralDetector()
    print()

    predictions = []
    scores_list = []
    start_total = time.time()

    for i, text in enumerate(texts):
        neural_res   = {"ai_label": "Untested", "confidence": 0.5}
        if neural.online:
            try:
                r = neural.pipe(text[:1500])[0]
                neural_res = {"ai_label": r["label"], "confidence": round(r["score"], 4)}
            except:
                pass

        lexical_res   = lexical.analyze(text)
        dynamics_res  = dynamics.analyze(text)
        syntactic_res = syntactic.analyze(text)
        semantic_res  = semantic.analyze(text, "")

        score = calculate_ai_score(
            lexical_res, dynamics_res, syntactic_res, semantic_res, neural_res
        )

        pred = 1 if score >= 0.65 else 0
        predictions.append(pred)
        scores_list.append(score)

        # Progress
        if (i + 1) % 50 == 0:
            elapsed = time.time() - start_total
            print(f"  [{i+1}/{len(texts)}] — {elapsed:.1f}s")

    total_time = time.time() - start_total

    # ── حساب المقاييس يدوياً (بدون sklearn) ──────────────────────
    TP = sum(1 for p, t in zip(predictions, true_labels) if p == 1 and t == 1)
    TN = sum(1 for p, t in zip(predictions, true_labels) if p == 0 and t == 0)
    FP = sum(1 for p, t in zip(predictions, true_labels) if p == 1 and t == 0)
    FN = sum(1 for p, t in zip(predictions, true_labels) if p == 0 and t == 1)

    accuracy  = (TP + TN) / len(true_labels)
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall    = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # ── عرض النتائج ───────────────────────────────────────────────
    print("\n" + "═" * 50)
    print("  📊  نتائج التقييم  —  HC3 Dataset")
    print("═" * 50)
    print(f"  Accuracy   : {accuracy:.1%}")
    print(f"  Precision  : {precision:.1%}   (من اللي قال AI، كم صح؟)")
    print(f"  Recall     : {recall:.1%}   (من الـ AI الحقيقية، كم اكتشف؟)")
    print(f"  F1 Score   : {f1:.1%}")
    print("─" * 50)
    print(f"  TP={TP}  TN={TN}  FP={FP}  FN={FN}")
    print(f"  العينة     : {len(true_labels)} نص  ({len(true_labels)//2} بشري + {len(true_labels)//2} AI)")
    print(f"  الوقت      : {total_time:.1f}s  ({total_time/len(true_labels)*1000:.0f}ms/نص)")
    print(f"  Neural     : {'ONLINE ✅' if neural.online else 'OFFLINE ⚠️  (statistical only)'}")
    print("═" * 50)

    # ── حفظ النتائج ───────────────────────────────────────────────
    results = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {"TP": TP, "TN": TN, "FP": FP, "FN": FN},
        "samples": len(true_labels),
        "neural_online": neural.online,
        "latency_ms_per_sample": round(total_time / len(true_labels) * 1000, 1)
    }

    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 النتائج محفوظة في: evaluation_results.json")
    print("    ← هذا الملف هو اللي تعرضه في المناقشة\n")

    return results


if __name__ == "__main__":
    run_evaluation()