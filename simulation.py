import time
import yaml
from typing import List, Dict, Optional
from agent import Agent
from claude_client import query_agent
from utils import parse_agent_response

try:
    from groq import RateLimitError as _GroqRateLimitError
except ImportError:
    _GroqRateLimitError = None

EVENT_FOOD_MISSING = "グループの食料の一部が原因不明で消えた。誰がやったかは不明。"


class PanicSimulation:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.agents = self._create_agents()
        self.phases = self.config["scenario"]["phases"]
        self.actions_desc = self.config["actions"]
        self.model = self.config["simulation"]["model"]
        self.temperature = self.config["simulation"]["temperature"]
        self.max_tokens = self.config["simulation"]["max_tokens"]
        self.results: List[Dict] = []

    def _create_agents(self) -> List[Agent]:
        agents = []
        edu_names = self.config["agents"]["psychology_educated"]["names"]
        non_names = self.config["agents"]["non_educated"]["names"]
        for i, name in enumerate(edu_names):
            agents.append(Agent(id=i, name=name, psychology_educated=True))
        for i, name in enumerate(non_names):
            agents.append(Agent(id=len(edu_names) + i, name=name, psychology_educated=False))
        return agents

    def _build_prompt(self, agent: Agent, phase_description: str) -> str:
        history = ", ".join(d["action"] for d in agent.decisions) or "なし"
        actions_list = "\n".join(f"- {k}: {v}" for k, v in self.actions_desc.items())
        personality = (
            f"善良さ: {agent.goodness:.2f} / 狡猾さ: {agent.cunning:.2f} / "
            f"感情的: {agent.emotional:.2f} / 論理的: {agent.logical:.2f} / "
            f"自己保存: {agent.self_preservation:.2f} / 依存性: {agent.dependency:.2f}"
        )
        return (
            f"【現在の状況】\n{phase_description}\n\n"
            f"あなたの性格パラメーター: {personality}\n"
            f"あなたの現在のストレスレベル: {agent.stress_level:.1f}/1.0\n"
            f"これまでの行動履歴: {history}\n\n"
            f"以下の5つのアクションから1つを選んでください：\n{actions_list}\n\n"
            "必ずこの形式で回答してください（他の文章は不要）：\n"
            "ACTION: [選択したアクション名（英語）]\n"
            "REASONING: [理由を1〜2文（日本語）]"
        )

    def _print_personality_table(self) -> None:
        print("\n--- エージェント性格パラメーター ---")
        header = f"  {'名前':10s} {'教育':6s} {'善良':5s} {'狡猾':5s} {'感情':5s} {'論理':5s} {'自己保存':8s} {'依存':5s}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for a in self.agents:
            edu = "あり" if a.psychology_educated else "なし"
            print(
                f"  {a.name:10s} {edu:6s} "
                f"{a.goodness:.2f}  {a.cunning:.2f}  {a.emotional:.2f}  "
                f"{a.logical:.2f}  {a.self_preservation:.2f}    {a.dependency:.2f}"
            )

    def run(self) -> List[Dict]:
        print(f"\n{'='*60}")
        print(f"シミュレーション開始: {self.config['scenario']['name']}")
        print(f"モデル: {self.model}")
        print(f"{'='*60}")
        self._print_personality_table()

        active_event: Optional[str] = None

        for phase in self.phases:
            current_event = active_event
            active_event = None

            phase_description = phase["description"]
            if current_event:
                phase_description = f"【イベント】{current_event}\n\n{phase_description}"
                print(f"\n⚠️  イベント発生: {current_event}")

            print(f"\n--- フェーズ {phase['id']}: {phase['name']} ---")
            print(f"{phase_description[:80]}...\n")

            phase_result: Dict = {
                "phase": phase["id"],
                "name": phase["name"],
                "event": current_event,
                "decisions": [],
            }

            for agent in self.agents:
                prompt = self._build_prompt(agent, phase_description)
                try:
                    raw = query_agent(
                        system_prompt=agent.get_system_prompt(),
                        user_message=prompt,
                        model=self.model,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                    action, reasoning = parse_agent_response(raw)
                except Exception as e:
                    # レート制限・致命的APIエラーは上位に再送出して統計ループを停止させる
                    if _GroqRateLimitError and isinstance(e, _GroqRateLimitError):
                        raise
                    msg = str(e).lower()
                    if any(kw in msg for kw in ("rate limit", "429", "too many requests", "rate_limit")):
                        raise
                    print(f"  [エラー] {agent.name}: {e}")
                    action, reasoning = "PANIC", "APIエラーのためデフォルト行動"

                agent.record_decision(phase["id"], action, reasoning)

                label = "教育あり" if agent.psychology_educated else "教育なし"
                print(f"  {agent.name:8s}({label}): {action}")
                print(f"    → {reasoning[:80]}")

                phase_result["decisions"].append({
                    "agent_name": agent.name,
                    "psychology_educated": agent.psychology_educated,
                    "action": action,
                    "reasoning": reasoning,
                    "self_preservation": agent.self_preservation,
                })
                time.sleep(0.5)

            # イベントトリガー判定: 自己保存>=0.7 かつ HOARD/ISOLATEを選んだエージェントがいれば発火
            if any(
                agent.self_preservation >= 0.7
                and agent.decisions[-1]["action"] in {"HOARD", "ISOLATE"}
                for agent in self.agents
            ):
                active_event = EVENT_FOOD_MISSING

            self.results.append(phase_result)

        return self.results

    def get_summary(self) -> Dict:
        edu = [a for a in self.agents if a.psychology_educated]
        non = [a for a in self.agents if not a.psychology_educated]

        def group_stats(agents: List[Agent]) -> Dict:
            return {
                "avg_cooperation": sum(a.cooperation_score for a in agents) / len(agents),
                "avg_panic": sum(a.panic_score for a in agents) / len(agents),
                "agents": [
                    {
                        "name": a.name,
                        "cooperation": a.cooperation_score,
                        "panic": a.panic_score,
                        "decisions": a.decisions,
                        "personality": {
                            "goodness": a.goodness,
                            "cunning": a.cunning,
                            "emotional": a.emotional,
                            "logical": a.logical,
                            "self_preservation": a.self_preservation,
                            "dependency": a.dependency,
                        },
                    }
                    for a in agents
                ],
            }

        return {
            "educated": group_stats(edu),
            "non_educated": group_stats(non),
        }
