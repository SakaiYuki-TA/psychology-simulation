import re
import os
import sys
import subprocess
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, FFMpegWriter

try:
    import japanize_matplotlib  # noqa: F401
except ImportError:
    plt.rcParams["font.family"] = ["MS Gothic", "Yu Gothic", "Meiryo", "DejaVu Sans"]

# imageio-ffmpeg で ffmpeg バイナリを自動取得
try:
    import imageio_ffmpeg
except ImportError:
    print("imageio-ffmpeg をインストールします...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"])
    import imageio_ffmpeg

plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()

# ─── 定数 ────────────────────────────────────────────────────────────────
FPS = 20
SECONDS_PER_PHASE = 3
FRAMES_PER_PHASE = FPS * SECONDS_PER_PHASE

ACTION_COLORS = {
    "COOPERATE": "#2196F3",
    "TEACH":     "#2196F3",
    "HOARD":     "#E53935",
    "ISOLATE":   "#FF9800",
    "PANIC":     "#212121",
}
NORMAL_BG = "#FFFFFF"
EVENT_BG  = "#FFECEC"

# 10 エージェントを 2行×5列 に配置（軸座標 0–1）
POSITIONS = [
    (0.1 + col * 0.2, 0.70 - row * 0.42)
    for row in range(2) for col in range(5)
]
RADIUS = 0.062


# ─── ログ解析 ─────────────────────────────────────────────────────────────
def parse_log(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    phases: list = []
    cur_phase = None
    cur_dec   = None

    for raw in lines:
        line = raw.rstrip("\n")

        # ■ フェーズ N: name
        m = re.match(r"■ フェーズ (\d+): (.+)", line)
        if m:
            if cur_phase is not None:
                if cur_dec:
                    cur_phase["decisions"].append(cur_dec)
                    cur_dec = None
                phases.append(cur_phase)
            cur_phase = {"phase": int(m.group(1)), "name": m.group(2).strip(),
                         "event": None, "decisions": []}
            continue

        # イベント行（絵文字の有無にかかわらず）
        m = re.search(r"イベント: (.+)", line)
        if m and cur_phase:
            cur_phase["event"] = m.group(1).strip()
            continue

        # [教育あり/なし] 名前 (自己保存=x.xx)
        m = re.match(r"\s+\[(教育あり|教育なし)\] (.+?) \(自己保存=([\d.]+)\)", line)
        if m and cur_phase:
            if cur_dec:
                cur_phase["decisions"].append(cur_dec)
            cur_dec = {"educated": m.group(1) == "教育あり",
                       "name": m.group(2).strip(),
                       "self_preservation": float(m.group(3)),
                       "action": None, "reasoning": ""}
            continue

        m = re.match(r"\s+アクション: (\w+)", line)
        if m and cur_dec:
            cur_dec["action"] = m.group(1).strip()
            continue

        m = re.match(r"\s+理由: (.+)", line)
        if m and cur_dec:
            cur_dec["reasoning"] = m.group(1).strip()
            continue

    if cur_phase:
        if cur_dec:
            cur_phase["decisions"].append(cur_dec)
        phases.append(cur_phase)

    return phases


# ─── アニメーション生成 ───────────────────────────────────────────────────
def create_animation(phases: list, output_path: str = "output/simulation_animation.mp4"):
    total_frames = len(phases) * FRAMES_PER_PHASE

    fig = plt.figure(figsize=(16, 9), facecolor=NORMAL_BG)

    # 座標で各エリアを定義 [left, bottom, width, height]
    ax_title = fig.add_axes([0.00, 0.88, 1.00, 0.12])
    ax_left  = fig.add_axes([0.01, 0.22, 0.48, 0.65])
    ax_right = fig.add_axes([0.51, 0.22, 0.48, 0.65])
    ax_text  = fig.add_axes([0.01, 0.00, 0.98, 0.21])

    def setup_ax(ax, bg):
        ax.cla()
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_facecolor(bg)

    def draw_agents(ax, decisions, group_label, bg):
        setup_ax(ax, bg)
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDDDDD")
        ax.text(0.5, 0.97, group_label, ha="center", va="top",
                fontsize=13, fontweight="bold", transform=ax.transAxes,
                color="#333333")

        for i, d in enumerate(decisions[:10]):
            x, y = POSITIONS[i]
            action = d["action"] or "PANIC"
            color  = ACTION_COLORS.get(action, "#999999")

            ax.add_patch(plt.Circle((x, y), RADIUS, color=color, zorder=3, alpha=0.88))

            # 名前（円内）
            short = d["name"][:4]
            ax.text(x, y + 0.005, short, ha="center", va="center",
                    fontsize=7, color="white", fontweight="bold", zorder=4)

            # アクション名（円の下）
            ax.text(x, y - RADIUS - 0.035, action, ha="center", va="top",
                    fontsize=6.5, color=color, zorder=4)

    def draw_frame(frame: int):
        phase_idx      = frame // FRAMES_PER_PHASE
        frame_in_phase = frame % FRAMES_PER_PHASE
        phase = phases[phase_idx]
        bg    = EVENT_BG if phase["event"] else NORMAL_BG
        fig.patch.set_facecolor(bg)

        # タイトルエリア
        setup_ax(ax_title, bg)
        ax_title.text(0.5, 0.72,
                      f"フェーズ {phase['phase']}: {phase['name']}",
                      ha="center", va="center", fontsize=15, fontweight="bold",
                      color="#CC0000" if phase["event"] else "#111111",
                      transform=ax_title.transAxes)
        if phase["event"]:
            ax_title.text(0.5, 0.18,
                          f"⚠  {phase['event']}",
                          ha="center", va="center", fontsize=10,
                          color="#CC0000", transform=ax_title.transAxes)

        # エージェント描画
        edu = [d for d in phase["decisions"] if d["educated"]]
        non = [d for d in phase["decisions"] if not d["educated"]]
        draw_agents(ax_left,  edu, "心理学教育あり", bg)
        draw_agents(ax_right, non, "心理学教育なし", bg)

        # reasoning テキストエリア
        setup_ax(ax_text, bg)
        ax_text.axhline(y=0.97, color="#CCCCCC", linewidth=0.8)

        all_dec = edu + non
        if all_dec:
            n   = len(all_dec)
            idx = min((frame_in_phase * n) // FRAMES_PER_PHASE, n - 1)
            d   = all_dec[idx]
            edu_label = "教育あり" if d["educated"] else "教育なし"
            action    = d["action"] or "?"
            color     = ACTION_COLORS.get(action, "#999999")

            ax_text.text(0.01, 0.88,
                         f"[{edu_label}]  {d['name']}   →   {action}",
                         ha="left", va="top", fontsize=10, fontweight="bold",
                         color=color, transform=ax_text.transAxes)

            wrapped = "\n".join(textwrap.wrap(d["reasoning"], width=110))
            ax_text.text(0.01, 0.60, wrapped,
                         ha="left", va="top", fontsize=8.5, color="#333333",
                         transform=ax_text.transAxes)

        # 凡例
        legend_elems = [
            mpatches.Patch(color="#2196F3", label="COOPERATE / TEACH"),
            mpatches.Patch(color="#E53935", label="HOARD"),
            mpatches.Patch(color="#FF9800", label="ISOLATE"),
            mpatches.Patch(color="#212121", label="PANIC"),
        ]
        ax_text.legend(handles=legend_elems, loc="lower right", ncol=4,
                       fontsize=9, framealpha=0.9,
                       bbox_to_anchor=(0.995, 0.02))

    anim = FuncAnimation(fig, draw_frame, frames=total_frames,
                         interval=1000 / FPS, blit=False)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    print(f"動画を保存中... ({total_frames} フレーム, {FPS} fps)")
    writer = FFMpegWriter(fps=FPS, metadata={"title": "Simulation"}, bitrate=2500,
                          extra_args=["-vcodec", "libx264", "-pix_fmt", "yuv420p"])
    anim.save(output_path, writer=writer, dpi=120)
    plt.close(fig)
    print(f"保存完了: {output_path}")


# ─── エントリポイント ─────────────────────────────────────────────────────
if __name__ == "__main__":
    log_path = "output/reasoning_log.txt"
    if not os.path.exists(log_path):
        print(f"エラー: {log_path} が見つかりません。先に main.py を実行してください。")
        sys.exit(1)

    phases = parse_log(log_path)
    print(f"フェーズ数: {len(phases)}")
    for p in phases:
        edu_n = sum(1 for d in p["decisions"] if d["educated"])
        non_n = sum(1 for d in p["decisions"] if not d["educated"])
        print(f"  Phase {p['phase']}: {p['name']}  "
              f"教育あり={edu_n} 教育なし={non_n}  イベント={bool(p['event'])}")

    create_animation(phases)
