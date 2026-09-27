from .observer_registry import OBSERVERS
class PerspectiveInferenceEngine:
    def infer(self,t):
        d=dict(OBSERVERS[t]); d["type"]=t; return d
