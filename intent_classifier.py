from sentence_transformers import SentenceTransformer, util
from intents import INTENTS

INTENT_THRESHOLD = 0.60
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def detect_intent(text: str):
    model = get_model()
    user_emb = model.encode(text, convert_to_tensor=True)

    best_intent = None
    best_score = 0.0

    for intent, examples in INTENTS.items():
        example_embs = model.encode(examples, convert_to_tensor=True)
        score = util.cos_sim(user_emb, example_embs).max().item()

        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent, best_score
