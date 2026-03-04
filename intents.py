# intents.py

from sentence_transformers import SentenceTransformer, util

# Load model ONCE
#model = SentenceTransformer("all-MiniLM-L6-v2")
_intent_model = None

def get_intent_model():
    global _intent_model
    if _intent_model is None:
        print("🔄 Loading intent model (one-time)...")
        _intent_model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            local_files_only=True
        )
    return _intent_model


# Confidence threshold
INTENT_THRESHOLD = 0.6

INTENTS = {
    "PLAY_MEDIA": [
        "i want to listen to something",
        "play music",
        "start a song",
        "put something on youtube",
        "play arijit singh",
        "i feel like listening to songs"
    ],

    "OPEN_APP": [
        "open chrome",
        "launch calculator",
        "start youtube",
        "open settings"
    ],

    "SEARCH": [
        "who is elon musk",
        "tell me about black holes",
        "what is artificial intelligence",
        "explain gravity"
    ],

    "SYSTEM_CONTROL": [
        "restart my system",
        "shutdown the laptop",
        "put the system to sleep"
    ],
    "MEDIA_CONTROL": [
        "pause youtube",
        "resume youtube",
        "mute video",
        "rewind video",
        "skip video",
        "fullscreen video"
  ],
}



def detect_intent(text: str):
    """
    Returns:
        (best_intent, confidence_score)
    """
    model = get_intent_model()

    text_embedding = model.encode(text, convert_to_tensor=True)

    best_intent = None
    best_score = 0.0

    for intent, examples in INTENTS.items():
        example_embeddings = model.encode(examples, convert_to_tensor=True)

        # cosine similarity
        similarity = util.cos_sim(text_embedding, example_embeddings)
        score = similarity.max().item()

        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent, best_score
