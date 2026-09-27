class PerspectiveInferenceEngine:
    def infer(self, observer_type):
        if observer_type=="HumanPerspective":
            return {"scale":"HumanScale","navigation":"WALK"}
        return {}
