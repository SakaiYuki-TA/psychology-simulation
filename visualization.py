import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    import japanize_matplotlib  # noqa: F401
except ImportError:
    plt.rcParams["font.family"] = ["MS Gothic", "Yu Gothic", "Meiryo", "DejaVu Sans"]

ACTION_COLORS = {
    "COOPERATE": "#4CAF50",
    "TEACH": "#2196F3",
    "HOARD": "#9C27B0",
    "ISOLATE": "#FFC107",
    "PANIC": "#F44336",
}
ACTION_ORDER = ["COOPERATE", "TEACH", "HOARD", "ISOLATE", "PANIC"]


def _action_distribution(agents: list) -> dict:
    counts = {a: 0 for a in ACTION_ORDER}
    total = 0
    for agent in agents:
        for d in agent["decisions"]:
            counts[d["action"]] = counts.get(d["action"], 0) + 1
            total += 1
    return {k: v / max(total, 1) for k, v in counts.items()}


def _n_label(n: int | None) -> str:
    return f"（n={n}回の平均）" if n is not None else ""


def plot_all(summary: dict, results: list, output_dir: str = "output", n: int | None = None) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    paths.append(_plot_comparison(summary, output_dir, n))
    paths.append(_plot_phase_trend(results, output_dir, n))
    paths.append(_plot_action_distribution(summary, output_dir, n))
    return paths


def _plot_comparison(summary: dict, output_dir: str, n: int | None = None) -> str:
    edu = summary["educated"]
    non = summary["non_educated"]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.suptitle(
        f"心理学教育の有無による協力・パニック行動率の比較{_n_label(n)}",
        fontsize=13, fontweight="bold"
    )

    categories = ["心理学教育あり", "心理学教育なし"]
    coop  = [edu["avg_cooperation"], non["avg_cooperation"]]
    panic = [edu["avg_panic"],       non["avg_panic"]]
    x = np.arange(len(categories))
    w = 0.35

    # エラーバー（標準偏差）が含まれる場合は表示
    coop_err  = [edu.get("std_cooperation", 0), non.get("std_cooperation", 0)]
    panic_err = [edu.get("std_panic", 0),       non.get("std_panic", 0)]
    has_err = any(v > 0 for v in coop_err + panic_err)

    b1 = ax.bar(x - w / 2, coop, w, label="協力行動率", color="#2196F3", alpha=0.85,
                yerr=coop_err if has_err else None, capsize=4, error_kw={"elinewidth": 1.2})
    b2 = ax.bar(x + w / 2, panic, w, label="パニック行動率", color="#F44336", alpha=0.85,
                yerr=panic_err if has_err else None, capsize=4, error_kw={"elinewidth": 1.2})
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("比率")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend()
    ax.bar_label(b1, fmt="%.0f%%", labels=[f"{v:.0%}" for v in coop],  padding=5)
    ax.bar_label(b2, fmt="%.0f%%", labels=[f"{v:.0%}" for v in panic], padding=5)
    ax.grid(axis="y", alpha=0.3)

    path = os.path.join(output_dir, "01_comparison.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def _plot_phase_trend(results: list, output_dir: str, n: int | None = None) -> str:
    phase_names = [r["name"] for r in results]
    edu_coop, non_coop = [], []

    for phase in results:
        edu_d = [d for d in phase["decisions"] if d["psychology_educated"]]
        non_d = [d for d in phase["decisions"] if not d["psychology_educated"]]
        edu_coop.append(
            sum(1 for d in edu_d if d["action"] in {"COOPERATE", "TEACH"}) / max(len(edu_d), 1)
        )
        non_coop.append(
            sum(1 for d in non_d if d["action"] in {"COOPERATE", "TEACH"}) / max(len(non_d), 1)
        )

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(phase_names, edu_coop, "o-", color="#2196F3", lw=2, ms=8, label="心理学教育あり")
    ax.plot(phase_names, non_coop, "s-", color="#F44336", lw=2, ms=8, label="心理学教育なし")
    ax.fill_between(range(len(phase_names)), edu_coop, non_coop, alpha=0.08, color="gray")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("協力行動率")
    suffix = f"  {_n_label(n)}" if n else ""
    ax.set_title(f"フェーズ別 協力行動率の推移{suffix}")
    ax.set_xticks(range(len(phase_names)))
    ax.set_xticklabels(phase_names, rotation=15, ha="right")
    ax.legend()
    ax.grid(alpha=0.3)

    path = os.path.join(output_dir, "02_phase_trend.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def _plot_action_distribution(summary: dict, output_dir: str, n: int | None = None) -> str:
    groups = [
        ("心理学教育あり", summary["educated"]["agents"]),
        ("心理学教育なし", summary["non_educated"]["agents"]),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    suffix = f"  {_n_label(n)}" if n else ""
    fig.suptitle(f"行動タイプ分布{suffix}", fontsize=13, fontweight="bold")

    for ax, (group_name, agents) in zip(axes, groups):
        dist = _action_distribution(agents)
        colors = [ACTION_COLORS[a] for a in ACTION_ORDER]
        values = [dist[a] for a in ACTION_ORDER]
        non_zero = [(v, c, a) for v, c, a in zip(values, colors, ACTION_ORDER) if v > 0]
        if not non_zero:
            ax.text(0.5, 0.5, "データなし", ha="center", va="center")
            ax.set_title(group_name)
            continue
        nz_values, nz_colors, nz_labels = zip(*non_zero)
        ax.pie(
            nz_values,
            labels=nz_labels,
            colors=nz_colors,
            autopct=lambda p: f"{p:.0f}%" if p > 3 else "",
            startangle=90,
        )
        ax.set_title(group_name)

    handles = [mpatches.Patch(color=ACTION_COLORS[a], label=a) for a in ACTION_ORDER]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=9, bbox_to_anchor=(0.5, -0.02))

    path = os.path.join(output_dir, "03_action_distribution.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path
