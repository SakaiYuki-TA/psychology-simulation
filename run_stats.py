"""30回シミュレーションを繰り返して統計を取る。"""
import json
import os
import subprocess
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from main import _write_reasoning_log
from simulation import PanicSimulation
from visualization import plot_all

MAX_RUNS = 30

try:
    from groq import RateLimitError as _GroqRateLimitError
except ImportError:
    _GroqRateLimitError = None


def _is_rate_limit(e: Exception) -> bool:
    if _GroqRateLimitError and isinstance(e, _GroqRateLimitError):
        return True
    msg = str(e).lower()
    return any(kw in msg for kw in ("rate limit", "429", "too many requests", "rate_limit"))


def run_stats():
    all_edu_coop:  list[float] = []
    all_edu_panic: list[float] = []
    all_non_coop:  list[float] = []
    all_non_panic: list[float] = []

    first_results  = None
    first_summary  = None

    print(f"\n{'='*60}")
    print(f"統計シミュレーション開始（最大 {MAX_RUNS} 回）")
    print(f"{'='*60}")

    for run_idx in range(MAX_RUNS):
        print(f"\n▶ 実行 {run_idx + 1} / {MAX_RUNS}")

        try:
            sim     = PanicSimulation("config.yaml")
            results = sim.run()
            summary = sim.get_summary()
        except Exception as e:
            if _is_rate_limit(e):
                print(f"\n[レート制限エラー] {e}")
            else:
                print(f"\n[APIエラー] {e}")
            print(f"完了した回数 n={run_idx} で統計を出力します。")
            break

        edu = summary["educated"]
        non = summary["non_educated"]

        all_edu_coop.append(edu["avg_cooperation"])
        all_edu_panic.append(edu["avg_panic"])
        all_non_coop.append(non["avg_cooperation"])
        all_non_panic.append(non["avg_panic"])

        print(f"  教育あり: 協力={edu['avg_cooperation']:.1%}  パニック={edu['avg_panic']:.1%}")
        print(f"  教育なし: 協力={non['avg_cooperation']:.1%}  パニック={non['avg_panic']:.1%}")

        # 1回目のみ reasoning_log と first_summary を保存
        if run_idx == 0:
            first_results = results
            first_summary = summary
            os.makedirs("output", exist_ok=True)
            _write_reasoning_log(results, "output/reasoning_log.txt")
            print("  ✓ reasoning_log.txt を保存しました（1回目）")

    n = len(all_edu_coop)
    if n == 0:
        print("1回もシミュレーションが完了しませんでした。終了します。")
        return

    # ─── 統計集計 ──────────────────────────────────────────────
    avg_edu_coop  = float(np.mean(all_edu_coop))
    avg_edu_panic = float(np.mean(all_edu_panic))
    avg_non_coop  = float(np.mean(all_non_coop))
    avg_non_panic = float(np.mean(all_non_panic))
    std_edu_coop  = float(np.std(all_edu_coop))
    std_edu_panic = float(np.std(all_edu_panic))
    std_non_coop  = float(np.std(all_non_coop))
    std_non_panic = float(np.std(all_non_panic))

    print(f"\n{'='*60}")
    print(f"統計結果  n={n} 回")
    print(f"{'='*60}")
    print(f"\n【心理学教育あり】")
    print(f"  協力行動率   平均: {avg_edu_coop:.1%}  SD: {std_edu_coop:.1%}")
    print(f"  パニック行動率 平均: {avg_edu_panic:.1%}  SD: {std_edu_panic:.1%}")
    print(f"\n【心理学教育なし】")
    print(f"  協力行動率   平均: {avg_non_coop:.1%}  SD: {std_non_coop:.1%}")
    print(f"  パニック行動率 平均: {avg_non_panic:.1%}  SD: {std_non_panic:.1%}")
    diff = avg_edu_coop - avg_non_coop
    print(f"\n協力行動率の差: {diff:+.1%}（教育あり群）")
    print(f"{'='*60}")

    # グラフ用サマリー（first_summary の agents を流用）
    avg_summary = {
        "n": n,
        "educated": {
            "avg_cooperation":  avg_edu_coop,
            "avg_panic":        avg_edu_panic,
            "std_cooperation":  std_edu_coop,
            "std_panic":        std_edu_panic,
            "agents": first_summary["educated"]["agents"],
        },
        "non_educated": {
            "avg_cooperation":  avg_non_coop,
            "avg_panic":        avg_non_panic,
            "std_cooperation":  std_non_coop,
            "std_panic":        std_non_panic,
            "agents": first_summary["non_educated"]["agents"],
        },
        "all_runs": {
            "edu_coop":  all_edu_coop,
            "edu_panic": all_edu_panic,
            "non_coop":  all_non_coop,
            "non_panic": all_non_panic,
        },
    }

    with open("output/stats_results.json", "w", encoding="utf-8") as f:
        json.dump(avg_summary, f, ensure_ascii=False, indent=2)
    print("\n  ✓ stats_results.json を保存しました")

    print("\nグラフを生成中...")
    paths = plot_all(avg_summary, first_results, n=n)
    for p in paths:
        print(f"  保存: {p}")

    # ─── animate.py を実行 ─────────────────────────────────────
    print("\nanimate.py を実行中...")
    subprocess.run([sys.executable, "animate.py"], check=True)

    print("\n統計シミュレーション完了。")


if __name__ == "__main__":
    run_stats()
