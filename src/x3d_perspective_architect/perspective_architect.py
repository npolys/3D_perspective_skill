from .inference import PerspectiveInferenceEngine
from .builders import PerspectiveBuilder
class PerspectiveArchitect:
    def generate(self,r): return PerspectiveBuilder.build(PerspectiveInferenceEngine().infer(r.get("observer_type","HumanPerspective")))
