from dataclasses import dataclass, field
from typing import Callable
from community_projects.baiby_monitor.src.play_lullaby import play_mp3
from community_projects.baiby_monitor.src.baiby_telegram import send_telegram_message


@dataclass
class DetectionClass:
    function: Callable
    counter: int = field(default=0, init=False)
    argument: str = field(default="")
    is_activated: bool = field(default=False, init=False)

    def __post_init__(self):
        if self.function is None:
            raise ValueError("function must be provided")
    

class MatchHandler:
    _instance = None

    BEHAVIOR_DICT = {
        # Cry detection
        "Calm baby": None,
        "Crying baby": DetectionClass(function=send_telegram_message, argument="Baby is crying"),

        # Sleep detection
        "awaken baby": DetectionClass(function=play_mp3),
        "sleeping baby": None,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MatchHandler, cls).__new__(cls)
        return cls._instance

    def handle(self, label: str) -> None:
        detection_class = self.BEHAVIOR_DICT.get(label)
        if detection_class:
            detection_class.counter += 1
            if detection_class.counter >= 110 and detection_class.is_activated is False:
                print(f"\nDetected {label}\n")
                detection_class.function(detection_class.argument)
                detection_class.is_activated = True
                detection_class.counter = 0
