from .inference import PerspectiveInferenceEngine
class PerspectiveArchitect:
    def generate(self, request):
      return PerspectiveInferenceEngine().infer(request.get("observer_type","HumanPerspective"))
