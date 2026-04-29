# price_tracker/app.py
import html as _html
import threading
from datetime import datetime, timedelta

import plotly.graph_objects as go
import streamlit as st

from database.repository import (
    add_product,
    deactivate_product,
    get_active_products,
    get_latest_price,
    get_price_history,
    get_price_stats,
    init_db,
    update_target_price,
)
from scheduler import check_product, start_scheduler

init_db()

# ── Scheduler em background ───────────────────────────────────────────────────

if "scheduler_started" not in st.session_state:
    st.session_state["scheduler_started"] = True
    threading.Thread(target=start_scheduler, daemon=True, name="scheduler-init").start()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Price Tracker",
    page_icon="🔔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global (fundo, sidebar, hide menu) ────────────────────────────────────

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 100%);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e2433 0%, #141824 100%);
    border-right: 1px solid #2d3748;
}
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constantes de estilo inline (st.html renderiza em iframe isolado) ─────────

_CARD     = ("background:linear-gradient(135deg,#1e2433 0%,#252d3d 100%);"
             "border:1px solid #2d3748;border-radius:16px;padding:24px;"
             "margin-bottom:4px;box-shadow:0 4px 24px rgba(0,0,0,0.3);")
_CARD_OUT = _CARD + "border-color:#4a5568;opacity:.75;"

_KPI = ("background:linear-gradient(135deg,#1e2433 0%,#252d3d 100%);"
        "border:1px solid #2d3748;border-radius:12px;padding:20px 16px;"
        "text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.25);")

_B = "display:inline-block;padding:3px 10px;border-radius:99px;font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;"
_BADGES = {
    "kabum":        _B + "background:#e64d2e22;color:#e64d2e;border:1px solid #e64d2e55;",
    "mercadolivre": _B + "background:#ffe60022;color:#d4ac00;border:1px solid #ffe60055;",
}
_BADGE_DEFAULT = _B + "background:#00b89422;color:#00b894;border:1px solid #00b89455;"

_PILL_DOWN = "background:#00b89422;color:#00b894;border:1px solid #00b89455;padding:3px 10px;border-radius:99px;font-size:.8rem;font-weight:600;"
_PILL_UP   = "background:#ff525222;color:#ff5252;border:1px solid #ff525255;padding:3px 10px;border-radius:99px;font-size:.8rem;font-weight:600;"
_PILL_SAME = "background:#8892a422;color:#8892a4;border:1px solid #8892a455;padding:3px 10px;border-radius:99px;font-size:.8rem;font-weight:600;"

STORE_COLORS = {
    "kabum":        "#e64d2e",
    "mercadolivre": "#d4ac00",
}


def _fmt(price: float) -> str:
    return f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _divider() -> None:
    st.html('<div style="height:1px;background:linear-gradient(90deg,transparent,#2d3748,transparent);margin:16px 0;"></div>')


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.html('<div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:4px;">🔔 Price Tracker</div>')
    st.caption("Monitoramento de preços em tempo real")
    _divider()

    st.markdown("**Monitorar novo produto**")

    with st.form("add_product_form", clear_on_submit=True):
        name         = st.text_input("Nome do produto", placeholder="Ex: RTX 4070 Super")
        url          = st.text_input("URL do produto", placeholder="Cole o link aqui...")
        store        = st.selectbox("Loja", ["kabum", "mercadolivre"])
        target_price = st.number_input(
            "Preço-alvo (R$)", min_value=0.0, format="%.2f",
            help="Você será notificado quando o preço cair abaixo deste valor",
        )
        submitted = st.form_submit_button("Adicionar produto", use_container_width=True)

        if submitted:
            if not name or not url:
                st.error("Nome e URL são obrigatórios.")
            else:
                product, criado = add_product(
                    name=name, url=url, store=store,
                    target_price=target_price or None,
                )
                if criado:
                    st.success(f"'{name}' adicionado!")
                    threading.Thread(
                        target=check_product, args=(product,),
                        daemon=True, name=f"check-{product.id}",
                    ).start()
                else:
                    st.warning("Produto já está sendo monitorado.")
                st.rerun()

    _divider()
    st.markdown("**Filtros**")
    filter_store = st.multiselect("Loja", ["kabum", "mercadolivre"], placeholder="Todas as lojas")
    sort_by = st.selectbox("Ordenar por", ["Nome", "Preço atual", "Variação", "Mais recente"])

# ── KPIs ──────────────────────────────────────────────────────────────────────

st.markdown("## Dashboard")

products = get_active_products()
if filter_store:
    products = [p for p in products if p.store in filter_store]

if not products:
    st.info("Nenhum produto monitorado ainda. Adicione um produto na barra lateral.")
    st.stop()

all_latest = [(p, get_latest_price(p.id), get_price_stats(p.id)) for p in products]

with_price   = [(p, l, s) for p, l, s in all_latest if l and l.price]
below_target = [(p, l, s) for p, l, s in with_price if p.target_price and l.price <= p.target_price]
price_drops  = [(p, l, s) for p, l, s in with_price if s["first_price"] and l.price < s["first_price"]]

avg_drop_pct = 0.0
if price_drops:
    drops = [(s["first_price"] - l.price) / s["first_price"] * 100 for _, l, s in price_drops]
    avg_drop_pct = sum(drops) / len(drops)

kpi_data = [
    (len(products),      "Produtos monitorados"),
    (len(below_target),  "Abaixo do alvo"),
    (len(price_drops),   "Com queda de preço"),
    (f"{avg_drop_pct:.1f}%", "Queda média"),
]
for col, (value, label) in zip(st.columns(4), kpi_data):
    with col:
        st.html(f"""
        <div style="{_KPI}">
          <div style="font-size:2rem;font-weight:700;color:#00b894;line-height:1;">{value}</div>
          <div style="font-size:.8rem;color:#8892a4;margin-top:6px;text-transform:uppercase;letter-spacing:.05em;">{label}</div>
        </div>""")

_divider()

# ── Ordenação ─────────────────────────────────────────────────────────────────


def sort_key(item):
    p, latest, stats = item
    if sort_by == "Nome":
        return p.name.lower()
    if sort_by == "Preço atual":
        return latest.price if (latest and latest.price) else float("inf")
    if sort_by == "Variação":
        if stats["first_price"] and latest and latest.price:
            return (latest.price - stats["first_price"]) / stats["first_price"]
        return 0
    if sort_by == "Mais recente":
        return latest.captured_at if latest else datetime.min
    return p.name.lower()


all_latest.sort(key=sort_key, reverse=(sort_by == "Mais recente"))

# ── Produtos ──────────────────────────────────────────────────────────────────

for p, latest, stats in all_latest:
    current_price   = latest.price if latest else None
    is_out_of_stock = latest is not None and not latest.available
    store_color     = STORE_COLORS.get(p.store, "#00b894")
    chart_color     = "#4a5568" if is_out_of_stock else store_color

    # Variação desde o primeiro registro
    variation_span = ""
    if not is_out_of_stock and stats["first_price"] and current_price:
        delta_pct = (current_price - stats["first_price"]) / stats["first_price"] * 100
        if delta_pct < -0.5:
            variation_span = f'<span style="{_PILL_DOWN}">&#9660; {abs(delta_pct):.1f}%</span>'
        elif delta_pct > 0.5:
            variation_span = f'<span style="{_PILL_UP}">&#9650; {delta_pct:.1f}%</span>'
        else:
            variation_span = f'<span style="{_PILL_SAME}">= est&#225;vel</span>'

    esgotado_span = ""
    if is_out_of_stock:
        esgotado_span = (
            '<span style="margin-left:8px;background:#ff525222;color:#ff5252;'
            'border:1px solid #ff525255;padding:3px 10px;border-radius:99px;'
            'font-size:.75rem;font-weight:600;">ESGOTADO &middot; rastreamento pausado</span>'
        )

    badge_style = _BADGES.get(p.store, _BADGE_DEFAULT)
    card_style  = _CARD_OUT if is_out_of_stock else _CARD
    name_color  = "#8892a4" if is_out_of_stock else "#e2e8f0"
    price_color = "#4a5568" if is_out_of_stock else store_color
    price_html  = _fmt(current_price) if current_price else "&#8212;"
    url_display = _html.escape(p.url[:80] + ("…" if len(p.url) > 80 else ""))

    st.html(f"""
    <div style="{card_style}">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="{badge_style}">{_html.escape(p.store)}</span>
          {esgotado_span}
          <div style="font-size:1.15rem;font-weight:700;color:{name_color};margin-top:6px;">{_html.escape(p.name)}</div>
          <div style="font-size:.75rem;color:#4a5568;margin-top:2px;word-break:break-all;">{url_display}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:1.8rem;font-weight:800;color:{price_color};">{price_html}</div>
          <div style="margin-top:4px;">{variation_span}</div>
        </div>
      </div>
    </div>""")

    if is_out_of_stock:
        history = get_price_history(p.id, limit=500)
        if history:
            prices_all = list(reversed([h.price for h in history]))
            dates_all  = list(reversed([h.captured_at for h in history]))
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates_all, y=prices_all,
                mode="lines", name="Preço",
                line=dict(color="#4a5568", width=2),
                fill="tozeroy", fillcolor="rgba(74,85,104,0.06)",
                hovertemplate="<b>%{x|%d/%m %H:%M}</b><br>R$ %{y:,.2f}<extra></extra>",
            ))
            fig.update_layout(
                height=200, margin=dict(l=0, r=0, t=8, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#4a5568"),
                xaxis=dict(showgrid=False, zeroline=False, color="#4a5568", tickformat="%d/%m"),
                yaxis=dict(showgrid=True, gridcolor="#1e2433", zeroline=False, color="#4a5568", tickprefix="R$ "),
                showlegend=False, hovermode="x unified",
            )
            st.plotly_chart(fig, width="stretch")

        col_del, _ = st.columns([1, 3])
        with col_del:
            if st.button("🗑️ Remover produto", key=f"deact_{p.id}", use_container_width=True):
                deactivate_product(p.id)
                st.rerun()

        _divider()
        continue

    # -- métricas
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Mínimo histórico", _fmt(stats["min"]) if stats["min"] else "—")
    with m2:
        st.metric("Máximo histórico", _fmt(stats["max"]) if stats["max"] else "—")
    with m3:
        st.metric("Média histórica", _fmt(stats["avg"]) if stats["avg"] else "—")
    with m4:
        if p.target_price and current_price:
            gap = current_price - p.target_price
            if gap <= 0:
                st.metric("vs Alvo", _fmt(abs(gap)), delta="Abaixo do alvo!", delta_color="normal")
            else:
                st.metric("vs Alvo", _fmt(gap), delta=f"Faltam {_fmt(gap)}", delta_color="inverse")
        else:
            st.metric("vs Alvo", "—")

    # -- gráfico
    history = get_price_history(p.id, limit=500)

    if history:
        prices_raw = list(reversed([h.price for h in history]))
        dates_raw  = list(reversed([h.captured_at for h in history]))

        period_col, _ = st.columns([2, 5])
        with period_col:
            period = st.radio(
                "Período", ["7d", "30d", "90d", "Tudo"],
                horizontal=True, key=f"period_{p.id}",
                label_visibility="collapsed",
            )

        now    = datetime.now()
        cutoff = {"7d": now - timedelta(days=7), "30d": now - timedelta(days=30), "90d": now - timedelta(days=90)}.get(period)

        if cutoff:
            pairs  = [(d, pr) for d, pr in zip(dates_raw, prices_raw) if d >= cutoff]
            dates  = [x[0] for x in pairs]
            prices = [x[1] for x in pairs]
        else:
            dates, prices = dates_raw, prices_raw

        if not prices:
            st.caption("Sem dados no período selecionado.")
        else:
            fig = go.Figure()
            r, g, b = int(chart_color[1:3], 16), int(chart_color[3:5], 16), int(chart_color[5:7], 16)

            fig.add_trace(go.Scatter(
                x=dates, y=prices, mode="lines", name="Preço",
                line=dict(color=chart_color, width=2.5),
                fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.08)",
                hovertemplate="<b>%{x|%d/%m %H:%M}</b><br>R$ %{y:,.2f}<extra></extra>",
            ))

            if len(prices) >= 4:
                window = max(3, len(prices) // 5)
                ma = [sum(prices[max(0, i - window + 1):i + 1]) / min(i + 1, window) for i in range(len(prices))]
                fig.add_trace(go.Scatter(
                    x=dates, y=ma, mode="lines", name=f"Média móvel ({window})",
                    line=dict(color="#8892a4", width=1.5, dash="dot"),
                    hovertemplate="<b>Média móvel</b><br>R$ %{y:,.2f}<extra></extra>",
                ))

            min_val, max_val = min(prices), max(prices)
            min_idx, max_idx = prices.index(min_val), prices.index(max_val)

            fig.add_trace(go.Scatter(
                x=[dates[min_idx]], y=[min_val], mode="markers+text", name="Mínimo",
                marker=dict(color="#00b894", size=10, symbol="triangle-up"),
                text=[_fmt(min_val)], textposition="top center",
                textfont=dict(color="#00b894", size=11),
                hovertemplate="<b>Mínimo</b><br>R$ %{y:,.2f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=[dates[max_idx]], y=[max_val], mode="markers+text", name="Máximo",
                marker=dict(color="#ff5252", size=10, symbol="triangle-down"),
                text=[_fmt(max_val)], textposition="bottom center",
                textfont=dict(color="#ff5252", size=11),
                hovertemplate="<b>Máximo</b><br>R$ %{y:,.2f}<extra></extra>",
            ))

            if p.target_price:
                fig.add_hline(
                    y=p.target_price, line_dash="dash",
                    line_color="#d63031", line_width=1.5,
                    annotation_text=f"Alvo {_fmt(p.target_price)}",
                    annotation_font_color="#d63031",
                )

            fig.update_layout(
                height=300, margin=dict(l=0, r=0, t=16, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8892a4", family="Inter, sans-serif"),
                xaxis=dict(showgrid=False, zeroline=False, color="#8892a4", tickformat="%d/%m"),
                yaxis=dict(showgrid=True, gridcolor="#2d3748", zeroline=False, color="#8892a4", tickprefix="R$ "),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                            bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
                hovermode="x unified",
            )
            st.plotly_chart(fig, width="stretch")
    else:
        st.caption("Sem histórico de preços ainda.")

    # -- ações
    with st.expander("Configurar / Ações"):
        ac1, ac2 = st.columns(2)
        with ac1:
            new_target = st.number_input(
                "Novo preço-alvo (R$)", min_value=0.0,
                value=float(p.target_price or 0), format="%.2f",
                key=f"target_{p.id}",
            )
            if st.button("Salvar alvo", key=f"save_{p.id}", use_container_width=True):
                update_target_price(p.id, new_target or None)
                st.success("Preço-alvo atualizado!")
                st.rerun()
        with ac2:
            if st.button("🔄 Verificar agora", key=f"check_{p.id}", use_container_width=True):
                with st.spinner("Buscando preço..."):
                    check_product(p)
                st.rerun()
            if st.button("🗑️ Parar monitoramento", key=f"deact_{p.id}", use_container_width=True):
                deactivate_product(p.id)
                st.warning(f"'{p.name}' removido do monitoramento.")
                st.rerun()

    _divider()
