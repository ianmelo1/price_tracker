# price_tracker/app.py
import threading
from scheduler import start_scheduler, check_prices
import streamlit as st
import plotly.graph_objects as go
from database.repository import (
    init_db,
    add_product,
    get_active_products,
    get_price_history,
    get_latest_price,
    update_target_price,
    deactivate_product,
)

init_db()

# ── Scheduler em background ───────────────────────────────────────────────────

def _start_scheduler_thread() -> None:
    """Inicia o scheduler em thread separada para não bloquear o Streamlit."""
    thread = threading.Thread(target=start_scheduler, daemon=True, name="scheduler")
    thread.start()

# garante que só sobe uma thread mesmo o Streamlit recarregando o script
if "scheduler_started" not in st.session_state:
    st.session_state["scheduler_started"] = True
    _start_scheduler_thread()

st.set_page_config(page_title="Price Tracker", page_icon="🔔", layout="wide")
st.title("🔔 Price Tracker")

# ── Sidebar: cadastro ─────────────────────────────────────────────────────────

st.sidebar.header("Monitorar novo produto")

with st.sidebar.form("add_product_form"):
    name         = st.text_input("Nome do produto")
    url          = st.text_input("URL do produto")
    store        = st.selectbox("Loja", ["kabum", "mercadolivre"])
    target_price = st.number_input("Preço-alvo (R$)", min_value=0.0, format="%.2f")
    submitted    = st.form_submit_button("Adicionar")

    if submitted:
        if not name or not url:
            st.sidebar.error("Nome e URL são obrigatórios.")
        else:
            _, criado = add_product(name=name, url=url, store=store, target_price=target_price or None)
            if criado:
                st.sidebar.success(f"'{name}' adicionado!")
            else:
                st.sidebar.warning("Esse produto já está sendo monitorado!")
            st.rerun()

# ── Produtos monitorados ──────────────────────────────────────────────────────

products = get_active_products()

if not products:
    st.info("Nenhum produto monitorado ainda. Adicione um produto na barra lateral.")
    st.stop()

for product in products:
    latest      = get_latest_price(product.id)
    history     = get_price_history(product.id, limit=100)

    current_price = latest.price if latest else None
    available     = latest.available if latest else None

    # -- cabeçalho do produto
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

    with col1:
        st.subheader(product.name)
        st.caption(f"{product.store.upper()} · {product.url}")

    with col2:
        if current_price:
            st.metric("Preço atual", f"R$ {current_price:.2f}")
        else:
            st.metric("Preço atual", "—")

    with col3:
        status = "✅ Em estoque" if available else "❌ Esgotado"
        st.metric("Status", status if latest else "—")

    with col4:
        new_target = st.number_input(
            "Preço-alvo (R$)",
            min_value=0.0,
            value=float(product.target_price or 0),
            format="%.2f",
            key=f"target_{product.id}",
        )
        if st.button("Salvar", key=f"save_{product.id}"):
            update_target_price(product.id, new_target)
            st.success("Atualizado!")
            st.rerun()

    # -- gráfico de histórico
    if history:
        prices = [h.price for h in reversed(history)]
        dates  = [h.captured_at for h in reversed(history)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=prices,
            mode="lines+markers",
            name="Preço",
            line=dict(color="#00b894", width=2),
        ))

        if product.target_price:
            fig.add_hline(
                y=product.target_price,
                line_dash="dash",
                line_color="#d63031",
                annotation_text=f"Alvo R$ {product.target_price:.2f}",
            )

        fig.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            height=250,
            xaxis_title="Data",
            yaxis_title="Preço (R$)",
            yaxis_tickprefix="R$ ",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Sem histórico de preços ainda.")

    # -- desativar produto
    with st.expander("Opções"):
        if st.button("🗑️ Parar de monitorar", key=f"deactivate_{product.id}"):
            deactivate_product(product.id)
            st.warning(f"'{product.name}' removido do monitoramento.")
            st.rerun()

    st.divider()