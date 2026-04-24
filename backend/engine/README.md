# Integra AI NLP Engine

This is a modular, professional NLP engine designed to analyze candidate speech in real-time. It uses academic metrics to assess speech patterns and detect potential AI-generated responses.

## Structure

- `main.py`: FastAPI server serving as the bridge between Frontend and NLP Analyzers.
- `analyzers/`:
    - `lexical.py`: Type-Token Ratio (TTR), Vocabulary Richness, and N-Grams analysis.
    - `syntactic.py`: Part-of-Speech (POS) analysis (Noun vs Pronoun ratios) and Syntactic Complexity.
    - `readability.py`: Flesch-Kincaid Grade level and Reading Ease scores.
    - `semantic.py`: Vector Space Modeling using TF-IDF and Cosine Similarity to check question-answer alignment.

## How to run

1. Ensure Python 3.9+ is installed.
2. The initial setup (requirements and SpaCy models) is handled automatically.
3. Run the engine:
   ```powershell
   cd nlp_engine
   .\venv\Scripts\python main.py
   ```
4. The engine runs on `http://localhost:8000`.

## Academic Concepts Applied
- **Lexical Diversity (TTR)**: Measures the ratio of unique words to total words.
- **Syntactic Complexity**: Analyzes the depth of subordinate clauses.
- **Stylometric Fingerprinting**: Checks for AI-typical noun-heavy structures.
