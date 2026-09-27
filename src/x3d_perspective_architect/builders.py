from .models import PerspectiveModel
class PerspectiveBuilder:
    @classmethod
    def build(cls,d): return PerspectiveModel({"up_axis":"+Y","gravity_axis":"-Y"},{"type":d["type"]},{"anchor":d["scale_anchor"]},{"mode":d["navigation_mode"]},[])
