"""Dashboard das análises (Streamlit). Rode a partir da raiz do repositório, depois do pipeline:

    python -m streamlit run app/dashboard.py

Usa as mesmas consultas de sql/analysis/ que o notebook, então os números são idênticos.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # permite importar src/ mesmo rodando de outra pasta

from src.analysis import run_query
from src.charts import BLUE, GRAY, br, month_name
from src.config import DB_PATH

st.set_page_config(page_title="Olist: análises", page_icon="📦", layout="wide")


@st.cache_data
def _load(name: str, db_version: float) -> pd.DataFrame:
    return run_query(name)


def query(name: str) -> pd.DataFrame:
    """Consulta com cache; a data do arquivo do banco renova o cache após um novo pipeline."""
    return _load(name, DB_PATH.stat().st_mtime)


def layout(fig: go.Figure, height: int) -> go.Figure:
    """Padrão visual dos gráficos: números em pt-BR, grade discreta, sem enfeites."""
    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        separators=",.",
        hoverlabel={"align": "left"},
        legend={"orientation": "h", "y": -0.15},
        bargap=0.35,
    )
    return fig


def state_chart(
    df: pd.DataFrame, value: str, hover: str, marker: str | None = None
) -> go.Figure:
    """Barras horizontais por UF (maior no topo), com a região Norte em destaque."""
    data = df.sort_values(value)
    fig = go.Figure()
    for is_north, name, color in [
        (True, "Região Norte", BLUE),
        (False, "Demais regiões", GRAY),
    ]:
        part = data[(data["region"] == "Norte") == is_north]
        fig.add_bar(
            x=part[value],
            y=part["state"],
            orientation="h",
            name=name,
            marker_color=color,
            customdata=part,
            hovertemplate=hover + "<extra></extra>",
        )
    if marker:
        fig.add_scatter(
            x=data[marker],
            y=data["state"],
            mode="markers",
            name="Prazo prometido (média)",
            marker={
                "symbol": "line-ns-open",
                "size": 14,
                "line": {"width": 2},
                "color": "#777777",
            },
            hovertemplate="%{y}: prometido %{x:.1f} dias<extra></extra>",
        )
    fig.update_yaxes(categoryorder="array", categoryarray=data["state"].tolist())
    return layout(fig, height=110 + 24 * len(data))


def weighted_mean(rows: pd.DataFrame, column: str) -> float:
    return (rows[column] * rows["orders"]).sum() / rows["orders"].sum()


# ---------------------------------------------------------------------------- cabeçalho
st.title("Olist: o que os dados de 2016–2018 dizem")
st.caption(
    "Camada gold do pipeline deste repositório. Receita = itens de pedidos entregues (sem frete); "
    "atraso comparado por data; cliente = `customer_unique_id`. Premissas completas no README."
)

if not DB_PATH.exists():
    st.error(
        "O Data Warehouse ainda não existe. Rode primeiro: `python -m src.pipeline`"
    )
    st.stop()

kpi = query("kpis").iloc[0]
cols = st.columns(6)
cols[0].metric("Receita", f"R$ {br(kpi['revenue'] / 1e6, 2)} mi")
cols[1].metric("Pedidos entregues", br(kpi["orders"]))
cols[2].metric("Ticket médio", f"R$ {br(kpi['revenue'] / kpi['orders'], 2)}")
cols[3].metric("Prazo médio de entrega", f"{br(kpi['avg_delivery_days'], 1)} dias")
cols[4].metric("Pedidos atrasados", f"{br(kpi['late_share'] * 100, 1)}%")
cols[5].metric("Nota média", br(kpi["avg_score"], 2))

sales_tab, logistics_tab, satisfaction_tab, finance_tab, customers_tab = st.tabs(
    ["Vendas", "Logística", "Satisfação", "Financeiro", "Clientes"]
)

# ---------------------------------------------------------------------------- vendas
with sales_tab:
    st.subheader("Como a receita total varia mês a mês?")
    q1 = query("q1_monthly_revenue")
    q1["label"] = q1["year_month"].map(month_name)
    start, end = st.select_slider(
        "Período",
        options=q1["label"].tolist(),
        value=(q1["label"].iloc[0], q1["label"].iloc[-1]),
    )
    period = q1.iloc[
        q1.index[q1["label"] == start][0] : q1.index[q1["label"] == end][0] + 1
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Receita no período", f"R$ {br(period['revenue'].sum() / 1e6, 2)} mi")
    c2.metric("Pedidos no período", br(period["orders"].sum()))
    c3.metric(
        "Ticket médio", f"R$ {br(period['revenue'].sum() / period['orders'].sum(), 2)}"
    )

    fig = go.Figure(
        go.Scatter(
            x=period["label"],
            y=period["revenue"],
            mode="lines+markers",
            line={"color": BLUE, "width": 2},
            marker={"size": 7, "color": BLUE},
            fill="tozeroy",
            fillcolor="rgba(42, 120, 214, 0.10)",
            customdata=period[["orders", "avg_ticket"]],
            hovertemplate=(
                "<b>%{x}</b><br>Receita: R$ %{y:,.0f}<br>Pedidos: %{customdata[0]:,}"
                "<br>Ticket médio: R$ %{customdata[1]:,.2f}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title="R$", rangemode="tozero")
    st.plotly_chart(layout(fig, height=420), width="stretch")
    peak = period.loc[period["revenue"].idxmax()]
    black_friday = ", mês da Black Friday" if peak["month"] == 11 else ""
    st.caption(
        f"Pico do período em {peak['label']}{black_friday}. "
        "Os meses das pontas do dataset, com poucos pedidos, ficam de fora."
    )
    with st.expander("Ver tabela"):
        st.dataframe(period.drop(columns="label"), hide_index=True)

# ---------------------------------------------------------------------------- logística
with logistics_tab:
    st.subheader("Qual o tempo médio de entrega, em dias, por estado?")
    q2 = query("q2_delivery_time_by_state")
    regions = sorted(q2["region"].unique())
    chosen = st.multiselect("Regiões", regions, default=regions, key="regions_delivery")
    view = q2[q2["region"].isin(chosen)]
    if view.empty:
        st.info("Escolha ao menos uma região.")
    else:
        hover = (
            "<b>%{customdata[0]}</b> (%{customdata[1]})<br>Prazo médio: %{x:.1f} dias"
            "<br>Mediana: %{customdata[4]:.0f} dias<br>Pedidos: %{customdata[2]:,}"
            "<br>Atrasados: %{customdata[6]:.1%}"
        )
        st.plotly_chart(
            state_chart(view, "avg_delivery_days", hover, marker="avg_promised_days"),
            width="stretch",
        )
        q2["late_orders"] = q2["late_share"] * q2["orders"]
        by_region = q2.groupby("region")[["late_orders", "orders"]].sum()
        late_by_region = by_region["late_orders"] / by_region["orders"]
        national = q2["late_orders"].sum() / q2["orders"].sum()
        small = q2.loc[q2["orders"] < 150, "state"].tolist()
        st.caption(
            f"Pedidos atrasados: Norte {br(late_by_region['Norte'] * 100, 1)}%, "
            f"Nordeste {br(late_by_region['Nordeste'] * 100, 1)}%, Brasil {br(national * 100, 1)}%. "
            f"Poucos pedidos (menos de 150) em: {', '.join(small)}."
        )
        with st.expander("Ver tabela"):
            st.dataframe(view, hide_index=True)

# ---------------------------------------------------------------------------- satisfação
with satisfaction_tab:
    st.subheader("Pedidos atrasados têm nota média menor que os entregues no prazo?")
    q3 = query("q3_review_score_by_delay")
    on_time, late = q3[~q3["is_late"]], q3[q3["is_late"]]
    c1, c2 = st.columns(2)
    c1.metric("Nota média no prazo", br(weighted_mean(on_time, "avg_score"), 2))
    c2.metric("Nota média dos atrasados", br(weighted_mean(late, "avg_score"), 2))

    fig = go.Figure(
        go.Bar(
            x=q3["delay_label"],
            y=q3["avg_score"],
            marker_color=BLUE,
            text=[br(v, 2) for v in q3["avg_score"]],
            textposition="outside",
            customdata=q3[["orders", "share_score_1", "share_score_5"]],
            hovertemplate=(
                "<b>%{x}</b><br>Nota média: %{y:.2f}<br>Pedidos: %{customdata[0]:,}"
                "<br>Nota 1: %{customdata[1]:.1%}<br>Nota 5: %{customdata[2]:.1%}<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title="nota média (1 a 5)", range=[0, 5.4])
    fig.update_xaxes(title="atraso em relação ao dia prometido")
    st.plotly_chart(layout(fig, height=420), width="stretch")
    st.caption("Associação observada, não prova de causa.")
    with st.expander("Ver tabela"):
        st.dataframe(q3, hide_index=True)

# ---------------------------------------------------------------------------- financeiro
with finance_tab:
    st.subheader("Qual o valor médio do frete por estado do cliente?")
    q4 = query("q4_freight_by_state")
    chosen = st.multiselect("Regiões", regions, default=regions, key="regions_freight")
    view = q4[q4["region"].isin(chosen)]
    if view.empty:
        st.info("Escolha ao menos uma região.")
    else:
        hover = (
            "<b>%{customdata[0]}</b> (%{customdata[1]})<br>Frete médio: R$ %{x:.2f}"
            "<br>Peso no valor dos itens: %{customdata[4]:.1%}<br>Pedidos: %{customdata[2]:,}"
        )
        st.plotly_chart(state_chart(view, "avg_freight", hover), width="stretch")
        st.caption("Frete por pedido (soma do frete dos itens), em pedidos entregues.")
        with st.expander("Ver tabela"):
            st.dataframe(view, hide_index=True)

# ---------------------------------------------------------------------------- clientes
with customers_tab:
    st.subheader("Qual a porcentagem de clientes que compraram mais de uma vez?")
    q5 = query("q5_repeat_customers")
    total = q5["customers"].sum()
    repeat = total - q5.loc[q5["purchases"] == "1", "customers"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Compraram mais de uma vez", f"{br(repeat / total * 100, 1)}%")
    c2.metric(
        "Em dias diferentes",
        f"{br(q5['customers_on_2plus_days'].sum() / total * 100, 1)}%",
    )
    c3.metric("Clientes com pedido entregue", br(total))

    fig = go.Figure()
    for name, value, color in [
        ("1 compra", total - repeat, GRAY),
        ("2 ou mais", repeat, BLUE),
    ]:
        fig.add_bar(
            x=[value / total],
            y=["clientes"],
            orientation="h",
            name=name,
            marker_color=color,
            hovertemplate=f"{name}: %{{x:.1%}} ({br(value)} clientes)<extra></extra>",
        )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%", range=[0, 1])
    fig.update_yaxes(visible=False)
    st.plotly_chart(layout(fig, height=200), width="stretch")
    st.caption(
        "Clientes únicos (`customer_unique_id`). Com `customer_id`, que muda a cada pedido, "
        "a recompra daria 0%."
    )
    with st.expander("Ver tabela"):
        st.dataframe(q5, hide_index=True)
