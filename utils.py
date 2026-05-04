import re

VALID_ACTIONS = {"COOPERATE", "TEACH", "HOARD", "ISOLATE", "PANIC"}

_ALIAS_MAP = {
    "HELP": "COOPERATE",
    "CALM": "COOPERATE",
    "ASSIST": "COOPERATE",
    "EVACUATE": "ISOLATE",
    "FLEE": "ISOLATE",
    "ESCAPE": "ISOLATE",
}

_KEYWORD_MAP = {
    "COOPERATE": ["協力", "cooperate", "助け", "救助", "救う", "連れ", "落ち着", "calm", "声かけ", "誘導", "冷静", "安心"],
    "TEACH": ["教え", "teach", "伝える", "知識", "技術", "指導"],
    "HOARD": ["独占", "hoard", "確保", "自分だけ", "押しのけ"],
    "ISOLATE": ["単独", "isolate", "避難", "evacuate", "脱出", "逃げる", "一人"],
    "PANIC": ["パニック", "panic", "我先", "必死", "混乱"],
}


def parse_agent_response(response: str) -> tuple[str, str]:
    """LLM レスポンスから (action, reasoning) を抽出する。"""
    action: str | None = None
    reasoning = ""

    # ACTION: XXX 形式を探す
    match = re.search(r"ACTION\s*[:：]\s*([A-Z]+)", response, re.IGNORECASE)
    if match:
        candidate = match.group(1).upper()
        if candidate in VALID_ACTIONS:
            action = candidate
        elif candidate in _ALIAS_MAP:
            action = _ALIAS_MAP[candidate]
        else:
            action = "PANIC"

    # REASONING: ... 形式を探す
    r_match = re.search(r"REASONING\s*[:：]\s*(.+)", response, re.DOTALL | re.IGNORECASE)
    if r_match:
        reasoning = r_match.group(1).strip()[:200]

    # アクションが取れなかった場合はキーワードで推定
    if action is None:
        text = response.upper()
        for act, keywords in _KEYWORD_MAP.items():
            if any(kw.upper() in text for kw in keywords):
                action = act
                break
        if action is None:
            action = "PANIC"

    if not reasoning:
        reasoning = response.strip()[:200]

    return action, reasoning
