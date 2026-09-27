from dataclasses import dataclass
@dataclass
class PerspectiveModel:
    world_frame:dict
    observer:dict
    scale_model:dict
    navigation_model:dict
    viewpoints:list
