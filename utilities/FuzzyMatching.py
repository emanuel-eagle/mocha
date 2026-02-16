from rapidfuzz import fuzz

class FuzzyMatching:

    def __init__(self):
        self.threshold = 60 # default value
        self.items = None

    def set_items(self, items):
        self.items = items
    
    def set_threshold(self, threshold):
        self.threshold = threshold

    def fuzzy_search(self, query):
        if self.items is None:
            raise ValueError("Items not set. Call set_items() before searching.")
        q = query.lower()
        results = []
        if isinstance(self.items, dict):
            for key, value in self.items.items():
                key_score = fuzz.partial_ratio(q, str(key).lower())
                val_score = fuzz.partial_ratio(q, str(value).lower())
                best = max(key_score, val_score)
                if best >= self.threshold:
                    results.append((key, best))
        else:
            for item in self.items:
                score = fuzz.partial_ratio(q, str(item).lower())
                if score >= self.threshold:
                    results.append((item, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return [match for match, _ in results]