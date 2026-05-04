import random
from dataclasses import dataclass, field
from typing import List

COOPERATIVE = {"COOPERATE", "TEACH"}
UNCOOPERATIVE = {"HOARD", "ISOLATE", "PANIC"}


@dataclass
class Agent:
    id: int
    name: str
    psychology_educated: bool
    stress_level: float = 0.3
    decisions: List[dict] = field(default_factory=list)
    goodness: float = field(default_factory=lambda: round(random.random(), 2))
    cunning: float = field(default_factory=lambda: round(random.random(), 2))
    emotional: float = field(default_factory=lambda: round(random.random(), 2))
    logical: float = field(default_factory=lambda: round(random.random(), 2))
    self_preservation: float = field(default_factory=lambda: round(random.random(), 2))
    dependency: float = field(default_factory=lambda: round(random.random(), 2))

    def get_system_prompt(self) -> str:
        edu_text = (
            "あなたは小学5年生から義務教育+高校・大学の教育の一環で、心理学教育を受けてきた人物です。"
            "集団心理、感情のコントロール方法、意思決定のメカニズムについてを学んでいます。"
        ) if self.psychology_educated else "あなたは特別な心理学教育を受けていない一般人です。"
        personality = (
            f"あなたの性格特性（0.0〜1.0、高いほどその傾向が強い）:\n"
            f"  善良さ={self.goodness:.2f}, 狡猾さ={self.cunning:.2f}, "
            f"感情的={self.emotional:.2f}, 論理的={self.logical:.2f}, "
            f"自己保存={self.self_preservation:.2f}, 依存性={self.dependency:.2f}\n"
            "これらの特性を反映した行動・判断をしてください。"
        )
        return f"{edu_text}\n\n{personality}"

    def record_decision(self, phase_id: int, action: str, reasoning: str) -> None:
        self.decisions.append({"phase": phase_id, "action": action, "reasoning": reasoning})

    @property
    def cooperation_score(self) -> float:
        if not self.decisions:
            return 0.0
        return sum(1 for d in self.decisions if d["action"] in COOPERATIVE) / len(self.decisions)

    @property
    def panic_score(self) -> float:
        if not self.decisions:
            return 0.0
        return sum(1 for d in self.decisions if d["action"] in UNCOOPERATIVE) / len(self.decisions)
