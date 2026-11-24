"""Gráficos das análises (imagens estáticas com matplotlib), com um padrão visual único.

Padrão adotado:
- o título diz a conclusão; o subtítulo diz o que está sendo medido;
- uma série = uma cor (azul); para destacar um grupo, ele fica azul e o resto, cinza;
- marcas finas, grade discreta (linha fina e sólida), textos em tons de cinza;
- nunca dois eixos Y no mesmo gráfico;
- números no padrão brasileiro (1.234,5).
As cores foram conferidas com um validador de daltonismo e contraste; como o cinza tem
contraste baixo com o fundo, os gráficos trazem rótulos de valor e o notebook, a tabela.
"""

from collections.abc import Callable
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

from src.config import DOCS_DIR

FIGURES_DIR = DOCS_DIR / "figures"

BLUE = "#2a78d6"  # a série, ou o grupo em destaque
GRAY = "#a8a79f"  # o que não está em destaque
SURFACE = "#fcfcfb"  # fundo
INK = "#0b0b0b"  # títulos e texto sobre o cinza
INK_SECONDARY = "#52514e"  # subtítulos e rótulos de valor
INK_MUTED = "#898781"  # eixos e notas
GRID = "#e1e0d9"  # grade
AXIS = "#c3c2b7"  # linha de base

MONTHS = [
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]
SOURCE = "Fonte: Brazilian E-Commerce Public Dataset by Olist (Kaggle), camada gold deste projeto"


def use_style() -> None:
    """Aplica o padrão visual a todos os gráficos."""
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
            "font.size": 10,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": INK_SECONDARY,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelcolor": INK_SECONDARY,
            "ytick.labelcolor": INK_SECONDARY,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "legend.frameon": False,
        }
    )


def br(number: float, decimals: int = 0) -> str:
    """Formata no padrão brasileiro: br(1234.5, 1) -> '1.234,5'."""
    text = f"{number:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def month_name(year_month: str) -> str:
    """'2017-11' -> 'nov/2017'."""
    year, month = year_month.split("-")
    return f"{MONTHS[int(month) - 1]}/{year}"


def save_figure(fig: Figure, name: str) -> Path:
    """Salva o gráfico em docs/figures/<name>.png (usado pelo relatório em Markdown)."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=150)
    return path


def _frame(
    title: str,
    subtitle: str,
    width: float,
    height: float,
    left: float = 0.9,
    bottom: float = 0.7,
) -> tuple[Figure, Axes]:
    """Cria a figura com título, subtítulo e fonte. Margens em polegadas."""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(
        left=left / width,
        right=1 - 0.35 / width,
        top=1 - 1.05 / height,
        bottom=bottom / height,
    )
    x0 = 0.25 / width
    fig.text(
        x0,
        1 - 0.22 / height,
        title,
        fontsize=14,
        fontweight="semibold",
        color=INK,
        va="top",
    )
    fig.text(
        x0, 1 - 0.58 / height, subtitle, fontsize=9.5, color=INK_SECONDARY, va="top"
    )
    fig.text(x0, 0.12 / height, SOURCE, fontsize=7.5, color=INK_MUTED, va="bottom")
    return fig, ax


def monthly_revenue(
    df: pd.DataFrame, title: str, subtitle: str, peak_note: str = ""
) -> Figure:
    """Linha da receita mensal, com o pico e o último mês em destaque."""
    fig, ax = _frame(title, subtitle, width=10, height=5.2, left=1.15)
    x = list(range(len(df)))
    revenue = df["revenue"].reset_index(drop=True)

    ax.fill_between(x, revenue, color=BLUE, alpha=0.10, linewidth=0)
    ax.plot(
        x,
        revenue,
        color=BLUE,
        linewidth=2,
        solid_capstyle="round",
        solid_joinstyle="round",
    )

    peak, last = int(revenue.idxmax()), len(revenue) - 1
    for i in (peak, last):
        ax.plot(
            i, revenue[i], "o", markersize=8, color=BLUE, mec=SURFACE, mew=2, zorder=3
        )
    peak_text = f"{peak_note}\n" if peak_note else ""
    ax.annotate(
        f"{peak_text}R$ {br(revenue[peak] / 1000)} mil",
        xy=(peak, revenue[peak]),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        color=INK_SECONDARY,
    )
    ax.annotate(
        f"R$ {br(revenue[last] / 1000)} mil",
        xy=(last, revenue[last]),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        color=INK_SECONDARY,
    )

    labels = [
        f"{MONTHS[m - 1]}\n{y}" if (m == 1 or i == 0) else MONTHS[m - 1]
        for i, (y, m) in enumerate(zip(df["year"], df["month"], strict=True))
    ]
    ax.set_xticks(x, labels)
    ax.tick_params(axis="both", length=0)
    ax.set_xlim(-0.5, last + 0.5)
    ax.set_ylim(0, revenue.max() * 1.25)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"R$ {br(v / 1000)} mil"))
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    return fig


def state_bars(
    df: pd.DataFrame,
    value_col: str,
    value_label: Callable[[float], str],
    title: str,
    subtitle: str,
    xlabel: str,
    highlight: str = "Norte",
    marker_col: str | None = None,
    marker_name: str | None = None,
) -> Figure:
    """Barras horizontais por UF (maior no topo), com uma região em destaque.

    Opcionalmente desenha um marcador por UF (ex.: o prazo prometido), na mesma escala.
    O rótulo de cada UF traz o número de pedidos, para deixar visíveis as amostras pequenas.
    """
    data = df.sort_values(value_col).reset_index(drop=True)
    height = 1.05 + 0.27 * len(data) + 0.95
    fig, ax = _frame(title, subtitle, width=10, height=height, left=1.25, bottom=0.95)
    y = list(range(len(data)))

    colors = [BLUE if region == highlight else GRAY for region in data["region"]]
    ax.barh(y, data[value_col], height=0.62, color=colors, zorder=2)
    for i, value in enumerate(data[value_col]):
        ax.text(
            value,
            i,
            f"  {value_label(value)}",
            va="center",
            fontsize=8.5,
            color=INK_SECONDARY,
        )

    handles = [
        Patch(color=BLUE, label=f"Região {highlight}"),
        Patch(color=GRAY, label="Demais regiões"),
    ]
    x_max = data[value_col].max()
    if marker_col:
        ax.plot(data[marker_col], y, "|", color=INK, markersize=11, mew=2, zorder=3)
        handles.append(
            Line2D(
                [],
                [],
                marker="|",
                color=INK,
                linestyle="none",
                markersize=11,
                mew=2,
                label=marker_name,
            )
        )
        x_max = max(x_max, data[marker_col].max())

    ax.set_yticks(
        y,
        [f"{s} ({br(n)})" for s, n in zip(data["state"], data["orders"], strict=True)],
    )
    ax.set_xlim(0, x_max * 1.12)
    ax.set_ylim(-0.6, len(data) - 0.4)
    ax.set_xlabel(xlabel)
    ax.tick_params(axis="both", length=0)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.legend(handles=handles, loc="lower right", fontsize=9)
    fig.text(
        0.25 / 10,
        0.42 / height,
        "Entre parênteses: número de pedidos da UF.",
        fontsize=8,
        color=INK_MUTED,
    )
    return fig


def score_by_delay(df: pd.DataFrame, title: str, subtitle: str) -> Figure:
    """Colunas da nota média por faixa de atraso (escala de 1 a 5)."""
    fig, ax = _frame(title, subtitle, width=10, height=5.2, left=0.75, bottom=1.05)
    x = list(range(len(df)))
    ax.bar(x, df["avg_score"], width=0.38, color=BLUE, zorder=2)
    for i, score in enumerate(df["avg_score"]):
        ax.text(
            i,
            score + 0.08,
            br(score, 2),
            ha="center",
            va="bottom",
            fontsize=10,
            color=INK,
        )

    labels = [
        f"{label}\n{br(n)} pedidos"
        for label, n in zip(df["delay_label"], df["orders"], strict=True)
    ]
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 5.4)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.set_ylabel("nota média (1 a 5)")
    ax.tick_params(axis="both", length=0)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("atraso em relação ao dia prometido", labelpad=8)
    return fig


def repeat_customers(df: pd.DataFrame, title: str, subtitle: str) -> Figure:
    """Barra única dividida em partes (parte do todo): quem comprou 1 vez x 2 ou mais."""
    total = df["customers"].sum()
    once = df.loc[df["purchases"] == "1", "customers"].sum()
    repeat = total - once
    breakdown = {row.purchases: row.customers for row in df.itertuples()}
    more_than_two = total - breakdown.get("1", 0) - breakdown.get("2", 0)

    fig, ax = _frame(title, subtitle, width=10, height=3.0, left=0.25, bottom=1.0)
    gap = 0.002  # espaço da cor do fundo entre as partes
    ax.barh(0, once / total - gap, height=0.5, color=GRAY)
    ax.barh(0, repeat / total, left=once / total, height=0.5, color=BLUE)
    ax.text(
        0.012,
        0,
        f"1 compra: {br(once / total * 100, 1)}% ({br(once)} clientes)",
        va="center",
        fontsize=10,
        color=INK,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.5)
    ax.axis("off")
    handles = [
        Patch(color=GRAY, label="1 compra"),
        Patch(
            color=BLUE,
            label=(
                f"2 ou mais compras: {br(repeat / total * 100, 1)}% ({br(repeat)} clientes; "
                f"{br(breakdown.get('2', 0))} com 2 compras e {br(more_than_two)} com 3 ou mais)"
            ),
        ),
    ]
    ax.legend(
        handles=handles, loc="upper left", bbox_to_anchor=(0, -0.05), fontsize=9, ncol=1
    )
    return fig
