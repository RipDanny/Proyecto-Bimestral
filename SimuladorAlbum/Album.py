import tkinter as tk
from tkinter import ttk, messagebox
import threading
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec

# ─────────────────────── CONSTANTES ───────────────────────────────
TOTAL   = 980
PER_PACK = 7
COST    = 1.20
INIT_PACKS = TOTAL // PER_PACK   # 140

# ─────────────────────── PALETA ───────────────────────────────────
C = {
    "green":  "#1D9E75",
    "green2": "#0F6E56",
    "purple": "#534AB7",
    "coral":  "#D85A30",
    "amber":  "#BA7517",
    "bg":     "#F4F3EF",
    "panel":  "#ECEAE4",
    "card":   "#FFFFFF",
    "border": "#D3D1C7",
    "text":   "#2C2C2A",
    "muted":  "#888780",
    "done":   "#E1F5EE",
    "miss":   "#FAECE7",
}

# ─────────────────────── LÓGICA ───────────────────────────────────

def buy_packs(col, n):
    idx = np.random.randint(0, TOTAL, n * PER_PACK)
    np.add.at(col, idx, 1)

def get_missing(col):
    return int(np.sum(col == 0))

def get_dups(col):
    return int(np.sum(np.maximum(col - 1, 0)))

def exchange_round(parts):
    n = len(parts)
    swaps = 0
    changed = True

    while changed:
        changed = False

        for i in range(n):
            missing = np.where(parts[i] == 0)[0]

            for sticker in missing:
                for j in range(n):

                    if i == j:
                        continue

                    if parts[j][sticker] > 1:
                        parts[j][sticker] -= 1
                        parts[i][sticker] += 1

                        swaps += 1
                        changed = True
                        break

    return swaps
def analytical_prob(missing, dups_avail):
    if missing == 0: return 1.0
    if dups_avail == 0: return 0.0
    p = 1.0 - (1.0 - 1.0 / TOTAL) ** dups_avail
    return p ** missing

def simulate_one(n_part, max_rounds=None):
    parts = [np.zeros(TOTAL, dtype=np.int32) for _ in range(n_part)]
    for p in parts:
        buy_packs(p, INIT_PACKS)

    extra_total = 0
    rounds = []
    r = 0

    while True:
        r += 1
        swaps = exchange_round(parts)
        miss_before = [get_missing(p) for p in parts]
        extra = 0

        for p in parts:
            missing = get_missing(p)
            if missing == 0:
                continue

            packs_needed = max(1, int(np.ceil(missing / PER_PACK)))
            buy_packs(p, packs_needed)
            extra += packs_needed

        extra_total += extra
        miss_after = [get_missing(p) for p in parts]
        done = sum(1 for m in miss_after if m == 0)
        dups_avg = np.mean([get_dups(p) for p in parts])

        rounds.append({
            "r": r,
            "extra": extra,
            "swaps": swaps,
            "miss_before": miss_before,
            "miss_after": miss_after,
            "done": done,
            "dups_avg": dups_avg
        })

        if done == n_part or (max_rounds is not None and r >= max_rounds):
            break

        if r > 500:
            break

    final_miss = [get_missing(p) for p in parts]
    return {
        "extra": extra_total,
        "rounds": rounds,
        "final_miss": final_miss,
        "done": sum(1 for m in final_miss if m == 0)
    }

def simulate_many(n_part, reps, max_rounds, progress_cb=None):
    results = []
    for i in range(reps):
        results.append(simulate_one(n_part, max_rounds))
        if progress_cb:
            progress_cb(i + 1, reps)

    avg_extra  = np.mean([r["extra"] for r in results])
    avg_done   = np.mean([r["done"]  for r in results])
    avg_rounds = np.mean([len(r["rounds"]) for r in results])
    avg_cpp    = (INIT_PACKS + avg_extra / max(n_part,1)) * COST

    max_r = max(len(r["rounds"]) for r in results)
    round_avg = []
    for i in range(max_r):
        vals = [r["rounds"][i]["extra"] for r in results if i < len(r["rounds"])]
        round_avg.append(np.mean(vals) if vals else 0)

    return dict(n=n_part, reps=reps,
                avg_extra=avg_extra, avg_done=avg_done,
                avg_rounds=avg_rounds, avg_cpp=avg_cpp,
                round_avg=round_avg, raw=results)

def run_analysis(ns, reps, max_rounds, progress_cb=None):
    data = []
    for i, n in enumerate(ns):
        r = simulate_many(n, reps, max_rounds)
        data.append(r)
        if progress_cb:
            progress_cb(i + 1, len(ns), n)
    return data


# ─────────────────────── APP TKINTER ──────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Álbum Mundial FIFA México-Canadá-USA 2026")
        self.configure(bg=C["bg"])
        self.minsize(1100, 720)
        self.resizable(True, True)

        self._sim_result = None
        self._analysis_data = None
        self._running = False

        self._build_ui()
        self._draw_prob_tab()

    # ── Layout principal ──────────────────────────────────────────
    def _build_ui(self):
        # Cabecera
        hdr = tk.Frame(self, bg=C["green"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚽  Álbum Mundial FIFA 2026  —  Simulador de Intercambio de Cromos",
                 bg=C["green"], fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=18, pady=12)
        tk.Label(hdr, text="980 figuritas  ·  7/funda  ·  $1.20/funda",
                 bg=C["green"], fg="#9FE1CB",
                 font=("Segoe UI", 10)).pack(side="right", padx=18)

        # Panel izquierdo (controles)
        left = tk.Frame(self, bg=C["panel"], width=240)
        left.pack(side="left", fill="y", padx=0, pady=0)
        left.pack_propagate(False)
        self._build_controls(left)

        # Panel derecho (tabs)
        right = tk.Frame(self, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._build_tabs(right)

    def _section(self, parent, title):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", padx=12, pady=(10, 2))
        tk.Label(f, text=title.upper(), bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        sep = tk.Frame(parent, bg=C["border"], height=1)
        sep.pack(fill="x", padx=12, pady=(0, 6))
        return parent

    def _slider_row(self, parent, label, from_, to, init, step=1):
        row = tk.Frame(parent, bg=C["panel"])
        row.pack(fill="x", padx=14, pady=3)
        tk.Label(row, text=label, bg=C["panel"], fg=C["text"],
                 font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
        var = tk.IntVar(value=init)
        val_lbl = tk.Label(row, textvariable=var, bg=C["panel"], fg=C["green"],
                           font=("Segoe UI", 9, "bold"), width=4)
        val_lbl.pack(side="right")
        sl = ttk.Scale(row, from_=from_, to=to, variable=var,
                       orient="horizontal", length=110,
                       command=lambda v, vv=var: vv.set(round(float(v))))
        sl.pack(side="right", padx=4)
        return var

    def _metric_card(self, parent, label, init_val="—"):
        f = tk.Frame(parent, bg=C["card"], relief="flat",
                     highlightbackground=C["border"], highlightthickness=1)
        f.pack(fill="x", padx=12, pady=3)
        tk.Label(f, text=label, bg=C["card"], fg=C["muted"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(6,0))
        var = tk.StringVar(value=init_val)
        tk.Label(f, textvariable=var, bg=C["card"], fg=C["text"],
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(0,6))
        return var

    def _build_controls(self, parent):
        tk.Label(parent, text="PARÁMETROS", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14,2))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=12, pady=(0,6))

        self.v_n    = self._slider_row(parent, "Participantes", 1, 50, 5)
        self.v_reps = self._slider_row(parent, "Repeticiones",  1, 30, 8)
        self.v_rnd  = self._slider_row(parent, "Rondas máx",   3, 20, 12)

        # Botones
        btn_f = tk.Frame(parent, bg=C["panel"])
        btn_f.pack(fill="x", padx=12, pady=10)

        self.btn_sim = tk.Button(btn_f, text="▶  Simular",
                                 bg=C["green"], fg="white",
                                 activebackground=C["green2"], activeforeground="white",
                                 font=("Segoe UI", 10, "bold"),
                                 relief="flat", bd=0, padx=8, pady=7, cursor="hand2",
                                 command=self._on_simulate)
        self.btn_sim.pack(fill="x", pady=(0,6))

        self.btn_all = tk.Button(btn_f, text="📊  Analizar i=1..50",
                                 bg=C["purple"], fg="white",
                                 activebackground="#3C3489", activeforeground="white",
                                 font=("Segoe UI", 10, "bold"),
                                 relief="flat", bd=0, padx=8, pady=7, cursor="hand2",
                                 command=self._on_analyze)
        self.btn_all.pack(fill="x")

        # Barra de progreso
        tk.Label(parent, text="PROGRESO", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(14,2))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=12, pady=(0,6))
        self.progress = ttk.Progressbar(parent, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=12, pady=(0,4))
        self.lbl_status = tk.Label(parent, text="Listo", bg=C["panel"], fg=C["muted"],
                                   font=("Segoe UI", 8))
        self.lbl_status.pack(anchor="w", padx=14)

        # Métricas
        tk.Label(parent, text="RESULTADOS", bg=C["panel"], fg=C["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(16,2))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=12, pady=(0,6))
        self.mv_extra  = self._metric_card(parent, "Fundas extra promedio")
        self.mv_cpp    = self._metric_card(parent, "Costo total / persona")
        self.mv_done   = self._metric_card(parent, "Álbumes completados")
        self.mv_rounds = self._metric_card(parent, "Rondas promedio")

    def _build_tabs(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Segoe UI", 10), padding=[12,5])

        self.tab_sim  = tk.Frame(nb, bg=C["bg"])
        self.tab_ana  = tk.Frame(nb, bg=C["bg"])
        self.tab_prob = tk.Frame(nb, bg=C["bg"])

        nb.add(self.tab_sim, text="  Simulación  ")
        nb.add(self.tab_ana, text="  Análisis  ")
        nb.add(self.tab_prob, text="  Probabilidades  ")

        # Figuras matplotlib por tab
        self.fig_sim, self.ax_sim_bars, self.ax_sim_miss = self._make_fig_2(self.tab_sim)
        self.fig_ana, self.ax_ana_extra, self.ax_ana_cost = self._make_fig_2(self.tab_ana)
        self.fig_prob, self.ax_prob = self._make_fig_1(self.tab_prob)

    def _make_fig_2(self, parent):
        fig = Figure(figsize=(8, 5), facecolor=C["bg"])
        fig.subplots_adjust(hspace=0.45, left=0.1, right=0.97, top=0.92, bottom=0.1)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)
        for ax in (ax1, ax2):
            ax.set_facecolor(C["panel"])
            for sp in ax.spines.values(): sp.set_color(C["border"])
            ax.tick_params(colors=C["muted"], labelsize=8)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return fig, ax1, ax2

    def _make_fig_1(self, parent):
        fig = Figure(figsize=(8, 5), facecolor=C["bg"])
        fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.1)
        ax = fig.add_subplot(111)
        ax.set_facecolor(C["panel"])
        for sp in ax.spines.values(): sp.set_color(C["border"])
        ax.tick_params(colors=C["muted"], labelsize=8)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return fig, ax

    # ── Acciones ──────────────────────────────────────────────────
    def _set_buttons(self, state):
        self.btn_sim.config(state=state)
        self.btn_all.config(state=state)

    def _on_simulate(self):
        if self._running: return
        n    = self.v_n.get()
        reps = self.v_reps.get()
        rnds = self.v_rnd.get()
        self._running = True
        self._set_buttons("disabled")
        self.lbl_status.config(text="Simulando...")
        self.progress["value"] = 0

        def run():
            def cb(i, total):
                pct = i / total * 100
                self.progress["value"] = pct
                self.lbl_status.config(text=f"Rep {i}/{total}")
                self.update_idletasks()
            res = simulate_many(n, reps, rnds, progress_cb=cb)
            self._sim_result = res
            self.after(0, self._finish_sim)

        threading.Thread(target=run, daemon=True).start()

    def _finish_sim(self):
        r = self._sim_result
        n = r["n"]
        self.mv_extra.set(f"{r['avg_extra']:.1f} fundas")
        self.mv_cpp.set(f"${r['avg_cpp']:.2f}")
       # self.mv_done.set(f"{r['avg_done']:.1f} / {n}")
        self.mv_done.set(f"{int(r['avg_done'])} / {n}")
        self.mv_rounds.set(f"{r['avg_rounds']:.1f}")
        self.progress["value"] = 100
        self.lbl_status.config(text="✓ Completado")
        self._draw_sim_tab(r)
        self._running = False
        self._set_buttons("normal")

    def _on_analyze(self):
        if self._running: return
        reps = self.v_reps.get()
        rnds = self.v_rnd.get()
        ns = list(range(1, 11)) + [12,15,18,20,25,30,35,40,45,50]
        self._running = True
        self._set_buttons("disabled")
        self.lbl_status.config(text="Analizando...")
        self.progress["value"] = 0

        def run():
            def cb(i, total, n_val):
                pct = i / total * 100
                self.progress["value"] = pct
                self.lbl_status.config(text=f"n={n_val} ({i}/{total})")
                self.update_idletasks()
            data = run_analysis(ns, reps, rnds, progress_cb=cb)
            self._analysis_data = data
            self.after(0, self._finish_analysis)

        threading.Thread(target=run, daemon=True).start()

    def _finish_analysis(self):
        self._draw_ana_tab(self._analysis_data)
        self.progress["value"] = 100
        self.lbl_status.config(text="✓ Análisis completo")
        self._running = False
        self._set_buttons("normal")

    # ── Gráficos ──────────────────────────────────────────────────
    def _style_ax(self, ax):
        ax.set_facecolor(C["panel"])
        for sp in ax.spines.values(): sp.set_color(C["border"])
        ax.tick_params(colors=C["muted"], labelsize=8)
        ax.grid(alpha=0.3, zorder=1)

    def _draw_sim_tab(self, r):
        # Fundas extra por ronda
        ax = self.ax_sim_bars
        ax.cla(); self._style_ax(ax)
        rounds = list(range(1, len(r["round_avg"]) + 1))
        ax.bar(rounds, r["round_avg"], color=C["green"], alpha=0.85, width=0.6, zorder=2)
        ax.set_title(f"Fundas adicionales por ronda  (n={r['n']}, {r['reps']} repeticiones)",
                     color=C["text"], fontsize=9, pad=4)
        ax.set_xlabel("Ronda", fontsize=8, color=C["muted"])
        ax.set_ylabel("Fundas extra", fontsize=8, color=C["muted"])

        # Cromos faltantes última rep
        ax2 = self.ax_sim_miss
        ax2.cla(); self._style_ax(ax2)
        last = r["raw"][-1]
        fm = last["final_miss"]
        n = r["n"]
        cols = [C["green"] if m == 0 else C["coral"] for m in fm]
        bars = ax2.bar(range(1, n+1), fm, color=cols, alpha=0.85, width=0.7, zorder=2)
        for bar, val in zip(bars, fm):
            if val > 0:
                ax2.text(bar.get_x() + bar.get_width()/2,
                         bar.get_height() + 0.3, str(val),
                         ha="center", va="bottom", fontsize=7, color=C["text"])
        ax2.set_title("Cromos faltantes finales — última simulación",
                      color=C["text"], fontsize=9, pad=4)
        ax2.set_xlabel("Participante", fontsize=8, color=C["muted"])
        ax2.set_ylabel("Faltantes", fontsize=8, color=C["muted"])
        self.fig_sim.canvas.draw()

    def _draw_ana_tab(self, data):
        ns    = [d["n"]      for d in data]
        extra = [d["avg_extra"] for d in data]
        cpp   = [d["avg_cpp"]   for d in data]

        ax1 = self.ax_ana_extra
        ax1.cla(); self._style_ax(ax1)
        ax1.plot(ns, extra, color=C["green"], linewidth=2, marker="o", markersize=4, zorder=3)
        ax1.fill_between(ns, extra, alpha=0.1, color=C["green"])
        ax1.set_title("Fundas extra totales promedio vs número de participantes",
                      color=C["text"], fontsize=9, pad=4)
        ax1.set_xlabel("Participantes (n)", fontsize=8, color=C["muted"])
        ax1.set_ylabel("Fundas extra", fontsize=8, color=C["muted"])

        ax2 = self.ax_ana_cost
        ax2.cla(); self._style_ax(ax2)
        ax2.plot(ns, cpp, color=C["purple"], linewidth=2, marker="s", markersize=4, zorder=3)
        ax2.fill_between(ns, cpp, alpha=0.1, color=C["purple"])
        ax2.axhline(168, color=C["coral"], linewidth=1, linestyle="--",
                    alpha=0.8, label="Mínimo ideal $168")
        ax2.set_title("Costo total por persona vs número de participantes",
                      color=C["text"], fontsize=9, pad=4)
        ax2.set_xlabel("Participantes (n)", fontsize=8, color=C["muted"])
        ax2.set_ylabel("Costo ($)", fontsize=8, color=C["muted"])
        ax2.legend(fontsize=8)
        self.fig_ana.canvas.draw()

    def _draw_prob_tab(self):
        ax = self.ax_prob
        ax.cla(); self._style_ax(ax)
        mv = np.arange(0, 301, 5)
        scenarios = [
            (100,  C["coral"],  "D=100"),
            (300,  C["amber"],  "D=300"),
            (700,  C["green"],  "D=700"),
            (1500, C["purple"], "D=1500"),
            (3000, "#D4537E",   "D=3000"),
        ]
        for dups, col, lbl in scenarios:
            probs = [analytical_prob(m, dups) * 100 for m in mv]
            ax.plot(mv, probs, color=col, linewidth=2, label=lbl)

        ax.axhline(50, color=C["muted"], linewidth=0.7, linestyle=":", alpha=0.7)
        ax.set_title(
            "Probabilidad analítica de completar el álbum en una ronda\n"
            "P(m, D) = (1 − (1−1/980)^D)^m",
            color=C["text"], fontsize=9, pad=4)
        ax.set_xlabel("Cromos faltantes (m)", fontsize=8, color=C["muted"])
        ax.set_ylabel("P(completar) %", fontsize=8, color=C["muted"])
        ax.set_ylim(0, 105)
        ax.legend(fontsize=9, framealpha=0.85)
        self.fig_prob.canvas.draw()


# ─────────────────────── ENTRADA ──────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
