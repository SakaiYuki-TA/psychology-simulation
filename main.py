import json
import os
import sys
from simulation import PanicSimulation
from visualization import plot_all

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _write_reasoning_log(results: list, path: str) -> None:
    lines = ["=" * 60, "エージェント行動ログ（フェーズ別）", "=" * 60]
    for phase in results:
        lines.append(f"\n■ フェーズ {phase['phase']}: {phase['name']}")
        if phase.get("event"):
            lines.append(f"  ⚠️  イベント: {phase['event']}")
        lines.append("-" * 50)
        for d in phase["decisions"]:
            edu_label = "教育あり" if d["psychology_educated"] else "教育なし"
            sp = d.get("self_preservation", 0.0)
            lines.append(f"\n  [{edu_label}] {d['agent_name']} (自己保存={sp:.2f})")
            lines.append(f"  アクション: {d['action']}")
            lines.append(f"  理由: {d['reasoning']}")
    lines.append("\n" + "=" * 60)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  保存: {path}")


def main():
    sim = PanicSimulation("config.yaml")
    results = sim.run()
    summary = sim.get_summary()

    edu = summary["educated"]
    non = summary["non_educated"]
    diff = edu["avg_cooperation"] - non["avg_cooperation"]

    print(f"\n{'='*60}")
    print("シミュレーション結果サマリー")
    print(f"{'='*60}")
    print(f"\n【心理学教育あり】")
    print(f"  平均協力行動率  : {edu['avg_cooperation']:.1%}")
    print(f"  平均パニック行動率: {edu['avg_panic']:.1%}")
    print(f"\n【心理学教育なし】")
    print(f"  平均協力行動率  : {non['avg_cooperation']:.1%}")
    print(f"  平均パニック行動率: {non['avg_panic']:.1%}")
    print(f"\n協力行動率の差: {diff:+.1%}（教育あり群）")
    print(f"{'='*60}")

    os.makedirs("output", exist_ok=True)
    with open("output/results.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)

    _write_reasoning_log(results, "output/reasoning_log.txt")

    print("\nグラフを生成中...")
    paths = plot_all(summary, results)
    for p in paths:
        print(f"  保存: {p}")

    print("\n完了。output/ フォルダを確認してください。")


if __name__ == "__main__":
    main()
