"""Gráficos das análises (imagens estáticas com matplotlib), com um padrão visual único.

Padrão adotado:
- o título diz a conclusão; o subtítulo diz o que está sendo medido e em que unidade;
- uma série = uma cor (azul); para destacar um grupo, ele fica azul e o resto, cinza;
- barras finas, com a ponta arredondada e a base reta, presa ao eixo;
- grade discreta (linha fina e sólida); textos em tons de cinza, nunca na cor da série;
- nunca dois eixos Y no mesmo gráfico;
- números no padrão brasileiro (1.234,5).
As cores foram conferidas com um validador de daltonismo e contraste; como o cinza tem
contraste baixo com o fundo, os gráficos trazem rótulos de valor e o notebook, a tabela.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch, Patch, PathPatch
from matplotlib.path import Path as ShapePath
from matplotlib.ticker import FuncFormatter, MultipleLocator

from src.config import DOCS_DIR

FIGURES_DIR = DOCS_DIR / "figures"

BLUE = "#2a78d6"  # a série, ou o grupo em destaque
GRAY = "#a8a79f"  # o que não está em destaque
TRACK = "#e9e8e2"  # trilho claro atrás de uma barra (ex.: o prazo prometido)
BAND = "#f1f0ec"  # faixa de fundo que marca um período
SURFACE = "#fcfcfb"  # fundo
INK = "#0b0b0b"  # títulos e números em destaque
INK_SECONDARY = "#52514e"  # subtítulos e rótulos de valor
INK_MUTED = "#898781"  # eixos e notas
GRID = "#e1e0d9"  # grade
AXIS = "#c3c2b7"  # linha de base

RADIUS = 0.035  # raio da ponta arredondada das barras, em polegadas
DPI = 200

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
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
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
    fig.savefig(path, dpi=DPI)
    return path


def _frame(
    title: str,
    subtitle: str,
    width: float,
    height: float,
    left: float = 0.9,
    bottom: float = 0.7,
    top: float = 1.1,
) -> tuple[Figure, Axes]:
    """Cria a figura com título, subtítulo e fonte. Margens em polegadas."""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.subplots_adjust(
        left=left / width,
        right=1 - 0.35 / width,
        top=1 - top / height,
        bottom=bottom / height,
    )
    x0 = 0.25 / width
    fig.text(
        x0,
        1 - 0.22 / height,
        title,
        fontsize=15,
        fontweight="semibold",
        color=INK,
        va="top",
    )
    fig.text(
        x0, 1 - 0.62 / height, subtitle, fontsize=10, color=INK_SECONDARY, va="top"
    )
    fig.text(x0, 0.14 / height, SOURCE, fontsize=7.5, color=INK_MUTED, va="bottom")
    return fig, ax


def _clean_axes(ax: Axes, grid_axis: str) -> None:
    """Grade só na direção dos valores, sem traços nos eixos e sem a linha da esquerda."""
    ax.tick_params(axis="both", length=0)
    ax.grid(True, axis=grid_axis)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)


def _rounded_bars(
    ax: Axes,
    positions: Sequence[float],
    lengths: Sequence[float],
    thickness: float,
    colors: Sequence[str],
    horizontal: bool = True,
    zorder: float = 2,
) -> None:
    """Barras com a ponta arredondada e a base reta, presa ao eixo.

    Os limites dos eixos precisam estar definidos antes: o raio é convertido de polegadas
    para as unidades de cada eixo, para o canto sair redondo e não achatado.
    """
    fig, box = ax.figure, ax.get_position()
    x_per_inch = abs(ax.get_xlim()[1] - ax.get_xlim()[0]) / (
        box.width * fig.get_figwidth()
    )
    y_per_inch = abs(ax.get_ylim()[1] - ax.get_ylim()[0]) / (
        box.height * fig.get_figheight()
    )
    along, across = (x_per_inch, y_per_inch) if horizontal else (y_per_inch, x_per_inch)
    kappa = 0.5523  # curva de Bézier que aproxima um quarto de círculo
    codes = [
        ShapePath.MOVETO,
        ShapePath.LINETO,
        *[ShapePath.CURVE4] * 3,
        ShapePath.LINETO,
    ]
    codes += [*[ShapePath.CURVE4] * 3, ShapePath.LINETO, ShapePath.CLOSEPOLY]

    for position, length, color in zip(positions, lengths, colors, strict=True):
        if length <= 0:
            continue
        r_along = min(RADIUS * along, length)
        r_across = min(RADIUS * across, thickness / 2)
        lo, hi = position - thickness / 2, position + thickness / 2
        k_along, k_across = kappa * r_along, kappa * r_across
        end = length
        points = [
            (0, lo),
            (end - r_along, lo),
            (end - r_along + k_along, lo),
            (end, lo + r_across - k_across),
            (end, lo + r_across),
            (end, hi - r_across),
            (end, hi - r_across + k_across),
            (end - r_along + k_along, hi),
            (end - r_along, hi),
            (0, hi),
            (0, lo),
        ]
        if not horizontal:
            points = [
                (across_value, along_value) for along_value, across_value in points
            ]
        shape = ShapePath(points, codes)
        ax.add_patch(PathPatch(shape, facecolor=color, edgecolor="none", zorder=zorder))


def monthly_revenue(
    df: pd.DataFrame, title: str, subtitle: str, peak_note: str = ""
) -> Figure:
    """Linha da receita mensal, com o pico e o último mês em destaque.

    As faixas de fundo marcam jan–ago de cada ano, os períodos que o título compara.
    """
    fig, ax = _frame(title, subtitle, width=10, height=5.4, left=0.7, top=1.2)
    data = df.reset_index(drop=True)
    revenue = data["revenue"]
    x = list(range(len(data)))
    last, peak = len(data) - 1, int(revenue.idxmax())
    y_top = revenue.max() * 1.35  # folga para os rótulos das faixas acima da grade
    ax.set_xlim(-0.5, last + 0.5)
    ax.set_ylim(0, y_top)

    for year, months in data[data["month"] <= 8].groupby("year"):
        start, end = months.index.min(), months.index.max()
        ax.axvspan(start - 0.5, end + 0.5, color=BAND, linewidth=0, zorder=0)
        ax.text(
            (start + end) / 2,
            y_top * 0.965,
            f"jan–ago/{year}: R$ {br(months['revenue'].sum() / 1e6, 2)} mi",
            ha="center",
            va="top",
            fontsize=9.5,
            color=INK_SECONDARY,
        )

    ax.plot(
        x,
        revenue,
        color=BLUE,
        linewidth=2.2,
        solid_capstyle="round",
        solid_joinstyle="round",
        zorder=2,
    )
    for i in (peak, last):
        ax.plot(
            i, revenue[i], "o", markersize=8, color=BLUE, mec=SURFACE, mew=2, zorder=3
        )
    peak_text = f"{peak_note}\n" if peak_note else ""
    for i, text in (
        (peak, f"{peak_text}R$ {br(revenue[peak] / 1000)} mil"),
        (last, f"R$ {br(revenue[last] / 1000)} mil"),
    ):
        ax.annotate(
            text,
            xy=(i, revenue[i]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            color=INK_SECONDARY,
        )

    labels = [
        f"{MONTHS[m - 1]}\n{y}" if (m == 1 or i == 0) else MONTHS[m - 1]
        for i, (y, m) in enumerate(zip(data["year"], data["month"], strict=True))
    ]
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: br(v / 1000)))
    ax.text(
        0,
        1.0,
        "R$ mil",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color=INK_MUTED,
    )
    _clean_axes(ax, "y")
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
    small_sample: int = 150,
) -> Figure:
    """Barras horizontais por UF (maior no topo), com uma região em destaque.

    Opcionalmente desenha atrás de cada barra um trilho claro até outro valor na mesma
    escala (ex.: o prazo prometido). UFs com menos de `small_sample` pedidos ganham um
    asterisco: a média delas é menos estável.
    """
    data = df.sort_values(value_col).reset_index(drop=True)
    rows, row_height = len(data), 0.3
    top, bottom = 1.45, 1.05  # em cima: título, subtítulo e legenda
    height = top + row_height * rows + bottom
    fig, ax = _frame(
        title, subtitle, width=10, height=height, left=0.7, bottom=bottom, top=top
    )
    y = list(range(rows))
    x_max = data[value_col].max()
    if marker_col:
        x_max = max(x_max, data[marker_col].max())
    ax.set_xlim(0, x_max * 1.1)
    ax.set_ylim(-0.6, rows - 0.4)

    handles = [
        Patch(color=BLUE, label=f"Região {highlight}"),
        Patch(color=GRAY, label="Demais regiões"),
    ]
    if marker_col:
        _rounded_bars(ax, y, data[marker_col], 0.58, [TRACK] * rows, zorder=1.5)
        handles.append(Patch(color=TRACK, label=marker_name))
    colors = [BLUE if region == highlight else GRAY for region in data["region"]]
    _rounded_bars(ax, y, data[value_col], 0.58, colors)
    for i, value in enumerate(data[value_col]):
        ax.text(
            value,
            i,
            f"  {value_label(value)}",
            va="center",
            fontsize=9,
            color=INK_SECONDARY,
            zorder=3,
        )

    small = data["orders"] < small_sample
    labels = [
        f"{s}*" if is_small else s
        for s, is_small in zip(data["state"], small, strict=True)
    ]
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", labelsize=10)
    ax.set_xlabel(xlabel)
    _clean_axes(ax, "x")
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.25 / 10, 1 - 1.02 / height),
        ncol=len(handles),
        fontsize=9.5,
        handlelength=1.1,
        handleheight=1.1,
        columnspacing=1.8,
        borderaxespad=0,
        borderpad=0,
    )
    if small.any():
        fig.text(
            0.25 / 10,
            0.45 / height,
            f"* Menos de {small_sample} pedidos: média menos estável.",
            fontsize=8,
            color=INK_MUTED,
        )
    return fig


def score_by_delay(df: pd.DataFrame, title: str, subtitle: str) -> Figure:
    """Colunas da nota média por faixa de atraso (escala de 1 a 5).

    Uma linha fina marca a nota de quem recebeu no prazo, para medir a queda de cada faixa.
    """
    fig, ax = _frame(title, subtitle, width=10, height=5.2, left=0.55, bottom=0.95)
    data = df.reset_index(drop=True)
    x = list(range(len(data)))
    ax.set_xlim(-0.6, len(data) - 0.4)
    ax.set_ylim(0, 5.3)
    _rounded_bars(ax, x, data["avg_score"], 0.36, [BLUE] * len(data), horizontal=False)
    for i, score in enumerate(data["avg_score"]):
        ax.text(
            i,
            score + 0.08,
            br(score, 2),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="semibold",
            color=INK,
        )

    on_time = data.loc[~data["is_late"], "avg_score"]
    if len(on_time) == 1:
        reference = on_time.iloc[0]
        # A linha começa na borda da coluna "no prazo" e segue até o fim do gráfico.
        ax.hlines(
            reference, 0.18, len(data) - 0.4, color=INK_MUTED, linewidth=0.8, zorder=1.5
        )
        ax.text(
            len(data) - 0.4,
            reference + 0.06,
            f"nota de quem recebeu no prazo ({br(reference, 2)})",
            ha="right",
            va="bottom",
            fontsize=8.5,
            color=INK_MUTED,
        )

    labels = [
        f"{label}\n{br(n)} pedidos"
        for label, n in zip(data["delay_label"], data["orders"], strict=True)
    ]
    ax.set_xticks(x, labels)
    ax.tick_params(axis="x", labelsize=10, pad=6)
    ax.yaxis.set_major_locator(MultipleLocator(1))
    _clean_axes(ax, "y")
    return fig


def repeat_customers(df: pd.DataFrame, title: str, subtitle: str) -> Figure:
    """Parte do todo em 100 quadrados (cada um = 1% dos clientes): 1 compra x 2 ou mais."""
    total = df["customers"].sum()
    breakdown = {row.purchases: row.customers for row in df.itertuples()}
    once = breakdown.get("1", 0)
    repeat = total - once
    three_or_more = repeat - breakdown.get("2", 0)
    repeat_cells = round(repeat / total * 100)

    width, height = 10, 4.4
    fig, ax = _frame(title, subtitle, width=width, height=height)
    side = 2.5  # quadrado de 10 x 10 células, em polegadas
    ax.set_position([0.25 / width, 0.62 / height, side / width, side / height])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")
    gap = 0.16
    for cell in range(100):
        row, col = divmod(cell, 10)
        ax.add_patch(
            FancyBboxPatch(
                (col + gap / 2, 9 - row + gap / 2),
                1 - gap,
                1 - gap,
                boxstyle="round,pad=0,rounding_size=0.14",
                facecolor=BLUE if cell < repeat_cells else GRAY,
                edgecolor="none",
            )
        )
    fig.text(
        0.25 / width,
        0.38 / height,
        f"Cada quadrado = 1% dos {br(total)} clientes",
        fontsize=8.5,
        color=INK_MUTED,
    )

    inches = fig.dpi_scale_trans
    blocks = [
        (
            BLUE,
            f"{br(repeat / total * 100, 1)}%",
            f"{br(repeat)} clientes compraram 2 vezes ou mais",
            f"{br(breakdown.get('2', 0))} com 2 compras e {br(three_or_more)} com 3 ou mais",
            3.1,
        ),
        (
            GRAY,
            f"{br(once / total * 100, 1)}%",
            f"{br(once)} clientes compraram uma vez só",
            "",
            1.8,
        ),
    ]
    for color, share, line, detail, y_top in blocks:
        fig.add_artist(
            FancyBboxPatch(
                (3.3, y_top - 0.24),  # centralizado com o número grande
                0.2,
                0.2,
                boxstyle="round,pad=0,rounding_size=0.03",
                facecolor=color,
                edgecolor="none",
                transform=inches,
            )
        )
        fig.text(
            3.65,
            y_top,
            share,
            transform=inches,
            fontsize=26,
            fontweight="semibold",
            color=INK,
            va="top",
        )
        fig.text(
            3.65,
            y_top - 0.42,
            line,
            transform=inches,
            fontsize=11.5,
            color=INK,
            va="top",
        )
        if detail:
            fig.text(
                3.65,
                y_top - 0.7,
                detail,
                transform=inches,
                fontsize=9.5,
                color=INK_SECONDARY,
                va="top",
            )
    return fig
