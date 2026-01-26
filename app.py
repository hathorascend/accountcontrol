import json
import calendar
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -----------------------
# Configuración y Constantes
# -----------------------
st.set_page_config(
    page_title="💳 Finanzas 2026",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_FILE = DATA_DIR / "operaciones.txt"

# -----------------------
# Estilos CSS Mejorados
# -----------------------
st.markdown("""
    <style>
    /* Variables de color */
    :root {
        --primary-color: #1f77b4;
        --success-color: #2ecc71;
        --warning-color: #f39c12;
        --danger-color: #e74c3c;
    }
    
    /* Métricas mejoradas */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 600;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 1rem;
    }
    
    /* Cards personalizados */
    .finance-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .alert-card {
        background: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .success-card {
        background: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    /* Tabs mejorados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: white;
    }
    
    /* Botones mejorados */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Data editor styling */
    [data-testid="stDataFrameResizable"] {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Ocultar índices de dataframes */
    .row_heading {
        display: none;
    }
    
    .blank {
        display: none;
    }
    
    /* Sidebar mejorado */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    /* Progress bar personalizado */
    .stProgress > div > div {
        background: linear-gradient(90deg, #2ecc71 0%, #27ae60 100%);
    }
    </style>
    """, unsafe_allow_html=True)

# -----------------------
# Utilidades
# -----------------------
def eur(x: float) -> str:
    """Formato moneda europea"""
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def log_op(action: str, detail: str) -> None:
    """Registro de auditoría simple"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}: {detail}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def get_status_emoji(gap: float) -> str:
    """Devuelve emoji según disponibilidad"""
    if gap >= 100:
        return "✅"
    elif gap >= 0:
        return "⚠️"
    else:
        return "🔴"

def get_month_progress() -> float:
    """Calcula el progreso del mes actual (0-1)"""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day / last_day

# -----------------------
# Lógica de Negocio (Clase Gestora)
# -----------------------
class FinanceManager:
    def __init__(self, year: int):
        self.year = year
        self.file_path = DATA_DIR / f"control_pagos_{year}.json"
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        if self.file_path.exists():
            try:
                return json.loads(self.file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                st.error(f"Error leyendo {self.file_path}. Iniciando vacío.")
        
        # Estructura inicial por defecto
        return {
            "year": self.year,
            "control_day": 29,
            "next_id": 1000,
            "balances": {
                "1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0
            },
            "accounts": [
                {"id": 1, "name": "BBVA – Ydaliz", "color": "#072146"},
                {"id": 2, "name": "BBVA – Moisés", "color": "#072146"},
                {"id": 3, "name": "Caixa – Conjunta", "color": "#0066b3"},
                {"id": 4, "name": "Santander – Ydaliz", "color": "#ec0000"},
                {"id": 5, "name": "Santander – Moisés", "color": "#ec0000"},
            ],
            "categories": [
                "Vivienda", "Transporte", "Alimentación", "Suscripciones", 
                "Seguros", "Educación", "Salud", "Ocio", "Otros"
            ],
            "template": [],
            "months": {}
        }

    def save(self):
        self.file_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_accounts(self) -> Dict[int, str]:
        return {a["id"]: a["name"] for a in self.data["accounts"]}

    def get_month_key(self, month: int) -> str:
        return f"{self.year:04d}-{month:02d}"

    def ensure_month_exists(self, month: int):
        key = self.get_month_key(month)
        if key in self.data["months"]:
            return

        # Generar mes desde plantilla
        items = []
        for t in self.data.get("template", []):
            # Filtro para anuales
            if t.get("type") == "sub_annual" and int(t.get("annual_month", 0)) != month:
                continue
            
            # Calcular fecha
            last_day = calendar.monthrange(self.year, month)[1]
            day = min(max(1, int(t.get("day", 1))), last_day)
            due_date = f"{self.year:04d}-{month:02d}-{day:02d}"

            items.append({
                "tid": int(t["id"]),
                "name": t["name"],
                "amount": float(t["amount"]),
                "account_id": int(t["account_id"]),
                "category": t.get("category", "Otros"),
                "due": due_date,
                "paid": False,
                "paid_date": None,
                "type": t["type"],
                "is_adhoc": False,
                "notes": ""
            })

        self.data["months"][key] = {
            "year": self.year, 
            "month": month, 
            "items": items
        }
        self.save()
        log_op("NEW_MONTH", f"Mes {key} generado.")

    def add_adhoc_expense(self, month: int, name: str, amount: float, day: int, 
                         account_id: int, category: str = "Otros", notes: str = ""):
        """Añade un gasto puntual solo a este mes"""
        key = self.get_month_key(month)
        self.ensure_month_exists(month)
        
        last_day = calendar.monthrange(self.year, month)[1]
        day_safe = min(max(1, day), last_day)
        
        new_id = self.data["next_id"]
        self.data["next_id"] += 1
        
        item = {
            "tid": new_id,
            "name": name,
            "amount": round(float(amount), 2),
            "account_id": int(account_id),
            "category": category,
            "due": f"{self.year:04d}-{month:02d}-{day_safe:02d}",
            "paid": False,
            "paid_date": None,
            "type": "adhoc",
            "is_adhoc": True,
            "notes": notes
        }
        
        self.data["months"][key]["items"].append(item)
        self.save()
        log_op("ADD_ADHOC", f"{name} ({amount}€) añadido a {key}")
        return True

    def delete_item(self, month: int, tid: int):
        """Elimina un item del mes"""
        key = self.get_month_key(month)
        if key in self.data["months"]:
            items = self.data["months"][key]["items"]
            self.data["months"][key]["items"] = [i for i in items if i["tid"] != tid]
            self.save()
            log_op("DELETE", f"Item {tid} eliminado de {key}")

    def update_balance(self, account_id: int, amount: float, operation: str):
        """operation: 'subtract' (pago) or 'add' (reembolso/ingreso)"""
        acc_str = str(account_id)
        current = float(self.data["balances"].get(acc_str, 0.0))
        if operation == 'subtract':
            self.data["balances"][acc_str] = round(current - amount, 2)
        else:
            self.data["balances"][acc_str] = round(current + amount, 2)
        self.save()

    def get_items_df(self, month: int) -> pd.DataFrame:
        key = self.get_month_key(month)
        if key not in self.data["months"]:
            return pd.DataFrame()
        
        items = self.data["months"][key]["items"]
        if not items:
            return pd.DataFrame()

        df = pd.DataFrame(items)
        # Enriquecer con nombres de cuenta
        acc_map = self.get_accounts()
        df["account_name"] = df["account_id"].map(acc_map)
        
        # Convertir fechas
        df["due"] = pd.to_datetime(df["due"])
        if "paid_date" in df.columns:
            df["paid_date"] = pd.to_datetime(df["paid_date"], errors='coerce')
        
        return df.sort_values("due")
    
    def get_category_summary(self, month: int) -> pd.DataFrame:
        """Resumen por categorías"""
        df = self.get_items_df(month)
        if df.empty:
            return pd.DataFrame()
        
        summary = df.groupby("category").agg({
            "amount": "sum",
            "paid": lambda x: (x == True).sum()
        }).reset_index()
        summary.columns = ["Categoría", "Total", "Pagados"]
        summary["Pendientes"] = summary.apply(lambda row: 
            len(df[(df["category"] == row["Categoría"]) & (~df["paid"])]), axis=1)
        return summary.sort_values("Total", ascending=False)

    def get_upcoming_payments(self, days: int = 7) -> pd.DataFrame:
        """Pagos próximos en los próximos N días"""
        today = date.today()
        month = today.month
        df = self.get_items_df(month)
        
        if df.empty:
            return pd.DataFrame()
        
        # Filtrar no pagados y próximos
        df_pending = df[~df["paid"]].copy()
        df_pending["days_until"] = (df_pending["due"] - pd.Timestamp(today)).dt.days
        
        upcoming = df_pending[df_pending["days_until"] <= days].copy()
        return upcoming.sort_values("days_until")

# -----------------------
# Componentes UI Reutilizables
# -----------------------

def render_quick_stats(manager: FinanceManager, selected_month: int):
    """Panel de estadísticas rápidas mejorado"""
    df_items = manager.get_items_df(selected_month)
    
    if df_items.empty:
        st.info("📝 No hay gastos registrados para este mes. ¡Comienza agregando tu primer gasto!")
        return
    
    total_month = df_items["amount"].sum()
    paid_month = df_items[df_items["paid"]]["amount"].sum()
    pending_month = total_month - paid_month
    progress = (paid_month / total_month) if total_month > 0 else 0
    
    # Métricas principales
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "💰 Total Mes", 
            eur(total_month),
            help="Suma total de gastos del mes"
        )
    
    with col2:
        st.metric(
            "✅ Pagado", 
            eur(paid_month),
            delta=f"{progress*100:.0f}%",
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            "⏳ Pendiente", 
            eur(pending_month),
            delta=f"{len(df_items[~df_items['paid']])} items",
            delta_color="inverse"
        )
    
    with col4:
        total_liquidity = sum(manager.data["balances"].values())
        deficit = total_liquidity - pending_month
        st.metric(
            "🏦 Liquidez Total",
            eur(total_liquidity),
            delta=eur(deficit) if deficit < 0 else f"+{eur(deficit)}",
            delta_color="normal" if deficit >= 0 else "inverse"
        )
    
    with col5:
        avg_per_day = total_month / calendar.monthrange(manager.year, selected_month)[1]
        st.metric(
            "📊 Promedio/Día",
            eur(avg_per_day),
            help="Gasto promedio diario del mes"
        )
    
    # Barra de progreso mejorada
    st.progress(progress, text=f"Progreso de pagos: {progress*100:.1f}% completado")
    
    # Alertas inteligentes
    upcoming = manager.get_upcoming_payments(7)
    if not upcoming.empty and len(upcoming) > 0:
        with st.expander(f"⚠️ Tienes {len(upcoming)} pagos próximos (7 días)", expanded=True):
            for _, row in upcoming.iterrows():
                days = int(row["days_until"])
                urgency = "🔴" if days <= 2 else "🟡" if days <= 5 else "🟢"
                st.write(f"{urgency} **{row['name']}** - {eur(row['amount'])} - {row['account_name']} - En {days} días")

def render_payment_manager(manager: FinanceManager, selected_month: int, auto_deduct: bool):
    """Gestor de pagos mejorado con filtros y búsqueda"""
    
    st.subheader("💳 Gestión de Pagos")
    
    df_items = manager.get_items_df(selected_month)
    
    if df_items.empty:
        st.warning("No hay items para mostrar")
        return
    
    # Filtros avanzados
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    
    with col_filter1:
        filter_status = st.selectbox(
            "Estado",
            ["Todos", "Pagados", "Pendientes"],
            key="filter_status"
        )
    
    with col_filter2:
        categories = ["Todas"] + sorted(df_items["category"].unique().tolist())
        filter_cat = st.selectbox("Categoría", categories, key="filter_cat")
    
    with col_filter3:
        accounts = ["Todas"] + sorted(df_items["account_name"].unique().tolist())
        filter_acc = st.selectbox("Cuenta", accounts, key="filter_acc")
    
    with col_filter4:
        search_term = st.text_input("🔍 Buscar", placeholder="Nombre del gasto...", key="search_box")
    
    # Aplicar filtros
    df_filtered = df_items.copy()
    
    if filter_status == "Pagados":
        df_filtered = df_filtered[df_filtered["paid"]]
    elif filter_status == "Pendientes":
        df_filtered = df_filtered[~df_filtered["paid"]]
    
    if filter_cat != "Todas":
        df_filtered = df_filtered[df_filtered["category"] == filter_cat]
    
    if filter_acc != "Todas":
        df_filtered = df_filtered[df_filtered["account_name"] == filter_acc]
    
    if search_term:
        df_filtered = df_filtered[df_filtered["name"].str.contains(search_term, case=False, na=False)]
    
    # Mostrar resumen de filtros
    st.caption(f"📋 Mostrando {len(df_filtered)} de {len(df_items)} gastos")
    
    if df_filtered.empty:
        st.info("No se encontraron resultados con los filtros aplicados")
        return
    
    # Editor de datos mejorado
    edited_df = st.data_editor(
        df_filtered,
        column_config={
            "paid": st.column_config.CheckboxColumn(
                "✓",
                help="Marcar como pagado",
                width="small"
            ),
            "name": st.column_config.TextColumn(
                "Concepto",
                width="medium",
                required=True
            ),
            "amount": st.column_config.NumberColumn(
                "Importe",
                format="%.2f €",
                width="small"
            ),
            "category": st.column_config.SelectboxColumn(
                "Categoría",
                options=manager.data.get("categories", []),
                width="small"
            ),
            "due": st.column_config.DateColumn(
                "Vencimiento",
                format="DD/MM/YYYY",
                width="small"
            ),
            "paid_date": st.column_config.DateColumn(
                "Fecha Pago",
                format="DD/MM/YYYY",
                width="small"
            ),
            "account_name": st.column_config.TextColumn(
                "Cuenta",
                width="medium"
            ),
            "notes": st.column_config.TextColumn(
                "Notas",
                width="medium"
            ),
            "is_adhoc": st.column_config.CheckboxColumn(
                "Puntual",
                help="Gasto no recurrente",
                width="small"
            ),
            "tid": None,
            "account_id": None,
            "type": None
        },
        hide_index=True,
        use_container_width=True,
        disabled=["account_name"],
        num_rows="dynamic",  # Permite añadir/eliminar filas
        key=f"editor_{selected_month}"
    )
    
    # Botones de acción
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    
    with col_btn1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            save_changes(manager, selected_month, df_items, edited_df, auto_deduct)
    
    with col_btn2:
        if st.button("✅ Marcar Todos Pagados", use_container_width=True):
            mark_all_paid(manager, selected_month, df_filtered, auto_deduct)
    
    with col_btn3:
        pending_count = len(df_filtered[~df_filtered["paid"]])
        if st.button(f"🗑️ Borrar Puntuales Pagados", use_container_width=True):
            delete_paid_adhoc(manager, selected_month, df_filtered)
    
    with col_btn4:
        if st.button("📥 Exportar a CSV", use_container_width=True):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                "Descargar CSV",
                csv,
                f"gastos_{selected_month:02d}_{manager.year}.csv",
                "text/csv"
            )

def save_changes(manager: FinanceManager, month: int, original_df: pd.DataFrame, 
                edited_df: pd.DataFrame, auto_deduct: bool):
    """Guarda cambios del editor"""
    changes_log = []
    key = manager.get_month_key(month)
    original_items = manager.data["months"][key]["items"]
    items_map = {i["tid"]: i for i in original_items}
    
    for index, row in edited_df.iterrows():
        tid = row["tid"]
        if tid in items_map:
            current_item = items_map[tid]
            
            # Detectar cambio de estado pagado
            was_paid = current_item["paid"]
            is_paid = row["paid"]
            
            if was_paid != is_paid:
                current_item["paid"] = is_paid
                current_item["paid_date"] = str(date.today()) if is_paid else None
                
                if auto_deduct:
                    op = 'subtract' if is_paid else 'add'
                    manager.update_balance(current_item["account_id"], current_item["amount"], op)
                    changes_log.append(f"{'✅ Pagado' if is_paid else '↩️ Revertido'}: {current_item['name']}")
            
            # Actualizar otros campos
            current_item["amount"] = float(row["amount"])
            current_item["due"] = str(row["due"])
            current_item["category"] = row.get("category", "Otros")
            current_item["notes"] = row.get("notes", "")
    
    manager.save()
    
    if changes_log:
        st.success(f"✅ {len(changes_log)} cambios guardados")
        for ch in changes_log:
            log_op("UPDATE", ch)
    else:
        st.info("No se detectaron cambios")
    
    st.rerun()

def mark_all_paid(manager: FinanceManager, month: int, df: pd.DataFrame, auto_deduct: bool):
    """Marca todos los items pendientes como pagados"""
    key = manager.get_month_key(month)
    items = manager.data["months"][key]["items"]
    items_map = {i["tid"]: i for i in items}
    
    count = 0
    for _, row in df[~df["paid"]].iterrows():
        tid = row["tid"]
        if tid in items_map:
            item = items_map[tid]
            item["paid"] = True
            item["paid_date"] = str(date.today())
            
            if auto_deduct:
                manager.update_balance(item["account_id"], item["amount"], 'subtract')
            
            count += 1
    
    manager.save()
    st.success(f"✅ {count} pagos marcados como completados")
    log_op("BULK_PAID", f"{count} items marcados en {key}")
    st.rerun()

def delete_paid_adhoc(manager: FinanceManager, month: int, df: pd.DataFrame):
    """Elimina gastos puntuales ya pagados"""
    key = manager.get_month_key(month)
    to_delete = df[(df["is_adhoc"]) & (df["paid"])]["tid"].tolist()
    
    if not to_delete:
        st.info("No hay gastos puntuales pagados para eliminar")
        return
    
    items = manager.data["months"][key]["items"]
    manager.data["months"][key]["items"] = [i for i in items if i["tid"] not in to_delete]
    manager.save()
    
    st.success(f"🗑️ {len(to_delete)} gastos puntuales eliminados")
    log_op("DELETE_ADHOC", f"{len(to_delete)} items borrados de {key}")
    st.rerun()

# -----------------------
# Interfaz Principal
# -----------------------

def main():
    # Inicializar session state
    if 'show_add_form' not in st.session_state:
        st.session_state.show_add_form = False
    
    # --- Sidebar: Configuración Global ---
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/money-bag.png", width=80)
        st.title("⚙️ Control")
        
        selected_year = st.selectbox(
            "Año Fiscal", 
            [2025, 2026, 2027], 
            index=1,
            key="year_selector"
        )
        
        # Inicializar Gestor
        manager = FinanceManager(selected_year)
        
        st.divider()
        
        # Selector de mes más intuitivo
        month_names = [calendar.month_name[i].capitalize() for i in range(1, 13)]
        current_month_idx = date.today().month - 1
        
        selected_month = st.selectbox(
            "Mes de Gestión", 
            list(range(1, 13)), 
            index=current_month_idx,
            format_func=lambda x: month_names[x-1],
            key="month_selector"
        )
        
        manager.ensure_month_exists(selected_month)
        
        st.divider()
        
        # Opciones de configuración
        st.subheader("🔧 Opciones")
        auto_deduct = st.checkbox(
            "Auto-descontar al pagar", 
            value=True,
            help="Descuenta automáticamente de la cuenta al marcar como pagado"
        )
        
        show_notifications = st.checkbox(
            "Notificaciones próximos pagos",
            value=True,
            help="Muestra alertas de pagos próximos"
        )
        
        st.divider()
        
        # Acciones rápidas
        st.subheader("📦 Backup")
        col_b1, col_b2 = st.columns(2)
        
        with col_b1:
            st.download_button(
                "💾 Descargar",
                data=json.dumps(manager.data, indent=2, ensure_ascii=False),
                file_name=f"backup_{selected_year}_{selected_month:02d}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col_b2:
            uploaded = st.file_uploader("📥 Restaurar", type=['json'], label_visibility="collapsed")
            if uploaded:
                try:
                    data = json.load(uploaded)
                    manager.data = data
                    manager.save()
                    st.success("✅ Restaurado")
                    st.rerun()
                except:
                    st.error("❌ Error")

    # --- Header Principal ---
    col_title, col_add_btn = st.columns([4, 1])
    
    with col_title:
        st.title(f"💳 {month_names[selected_month-1]} {selected_year}")
    
    with col_add_btn:
        if st.button("➕ Nuevo Gasto", type="primary", use_container_width=True):
            st.session_state.show_add_form = not st.session_state.show_add_form
    
    # Formulario de nuevo gasto (collapsible)
    if st.session_state.show_add_form:
        with st.container():
            st.markdown("### ➕ Agregar Gasto Extra")
            with st.form("add_adhoc", clear_on_submit=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    adhoc_name = st.text_input("Concepto *", placeholder="Ej: Cena, Reparación...")
                    adhoc_amount = st.number_input("Importe (€) *", min_value=0.01, step=10.0, value=50.0)
                
                with col_f2:
                    adhoc_cat = st.selectbox("Categoría", manager.data.get("categories", ["Otros"]))
                    adhoc_acc = st.selectbox(
                        "Cuenta *", 
                        manager.data["accounts"], 
                        format_func=lambda x: x["name"]
                    )
                
                with col_f3:
                    adhoc_day = st.number_input("Día", min_value=1, max_value=31, value=date.today().day)
                    adhoc_notes = st.text_input("Notas", placeholder="Opcional...")
                
                col_submit, col_cancel = st.columns([1, 1])
                
                with col_submit:
                    submitted = st.form_submit_button("💾 Guardar Gasto", type="primary", use_container_width=True)
                
                with col_cancel:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.show_add_form = False
                        st.rerun()
                
                if submitted and adhoc_name:
                    manager.add_adhoc_expense(
                        selected_month, 
                        adhoc_name, 
                        adhoc_amount, 
                        adhoc_day, 
                        adhoc_acc["id"],
                        adhoc_cat,
                        adhoc_notes
                    )
                    st.toast(f"✅ '{adhoc_name}' agregado correctamente!", icon="✅")
                    st.session_state.show_add_form = False
                    st.rerun()
            
            st.divider()
    
    # Dashboard de estadísticas
    render_quick_stats(manager, selected_month)
    
    st.divider()
    
    # --- Pestañas Principales ---
    tab_ops, tab_dash, tab_acc, tab_cat, tab_template = st.tabs([
        "📝 Operaciones", 
        "📊 Análisis", 
        "💰 Cuentas", 
        "📁 Categorías",
        "⚙️ Plantilla"
    ])

    # -----------------------
    # TAB 1: OPERACIONES
    # -----------------------
    with tab_ops:
        render_payment_manager(manager, selected_month, auto_deduct)

    # -----------------------
    # TAB 2: ANÁLISIS VISUAL
    # -----------------------
    with tab_dash:
        df_items = manager.get_items_df(selected_month)
        
        if df_items.empty:
            st.info("No hay datos para visualizar")
        else:
            # Gráficos mejorados
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("📊 Distribución por Cuenta")
                grp_acc = df_items.groupby("account_name")["amount"].sum().reset_index()
                fig_pie = px.pie(
                    grp_acc, 
                    values="amount", 
                    names="account_name",
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_g2:
                st.subheader("🏷️ Distribución por Categoría")
                grp_cat = df_items.groupby("category")["amount"].sum().reset_index()
                grp_cat = grp_cat.sort_values("amount", ascending=False).head(8)
                fig_cat = px.bar(
                    grp_cat,
                    x="amount",
                    y="category",
                    orientation='h',
                    color="amount",
                    color_continuous_scale="Blues"
                )
                fig_cat.update_layout(showlegend=False)
                st.plotly_chart(fig_cat, use_container_width=True)
            
            st.divider()
            
            # Timeline de pagos
            st.subheader("📅 Timeline del Mes")
            df_sorted = df_items.sort_values("due").copy()
            df_sorted["acumulado"] = df_sorted["amount"].cumsum()
            
            fig_timeline = go.Figure()
            
            # Línea acumulada
            fig_timeline.add_trace(go.Scatter(
                x=df_sorted["due"],
                y=df_sorted["acumulado"],
                mode='lines+markers',
                name='Acumulado',
                line=dict(color='#1f77b4', width=3),
                fill='tozeroy'
            ))
            
            # Marcar pagados vs pendientes
            paid_items = df_sorted[df_sorted["paid"]]
            pending_items = df_sorted[~df_sorted["paid"]]
            
            fig_timeline.add_trace(go.Scatter(
                x=paid_items["due"],
                y=paid_items["amount"],
                mode='markers',
                name='Pagados',
                marker=dict(size=12, color='green', symbol='circle')
            ))
            
            fig_timeline.add_trace(go.Scatter(
                x=pending_items["due"],
                y=pending_items["amount"],
                mode='markers',
                name='Pendientes',
                marker=dict(size=12, color='red', symbol='x')
            ))
            
            fig_timeline.update_layout(
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            # Comparativa Estado
            st.divider()
            st.subheader("✅ Estado de Pagos por Cuenta")
            
            status_data = []
            for acc_name in df_items["account_name"].unique():
                acc_items = df_items[df_items["account_name"] == acc_name]
                pagados = acc_items[acc_items["paid"]]["amount"].sum()
                pendientes = acc_items[~acc_items["paid"]]["amount"].sum()
                
                status_data.append({
                    "Cuenta": acc_name,
                    "Pagado": pagados,
                    "Pendiente": pendientes
                })
            
            df_status = pd.DataFrame(status_data)
            
            fig_status = go.Figure()
            fig_status.add_trace(go.Bar(
                name='Pagado',
                x=df_status["Cuenta"],
                y=df_status["Pagado"],
                marker_color='#2ecc71'
            ))
            fig_status.add_trace(go.Bar(
                name='Pendiente',
                x=df_status["Cuenta"],
                y=df_status["Pendiente"],
                marker_color='#e74c3c'
            ))
            
            fig_status.update_layout(barmode='stack', height=400)
            st.plotly_chart(fig_status, use_container_width=True)

    # -----------------------
    # TAB 3: CUENTAS
    # -----------------------
    with tab_acc:
        st.subheader("🏦 Estado de Tesorería")
        
        df_items = manager.get_items_df(selected_month)
        
        # Calcular necesidades por cuenta
        pending_by_acc = df_items[~df_items["paid"]].groupby("account_id")["amount"].sum().to_dict() if not df_items.empty else {}
        
        acc_data = []
        total_gap = 0
        total_balance = 0
        total_pending = 0
        
        for acc in manager.data["accounts"]:
            aid = str(acc["id"])
            bal = float(manager.data["balances"].get(aid, 0.0))
            need = pending_by_acc.get(acc["id"], 0.0)
            gap = bal - need
            
            status = get_status_emoji(gap)
            
            if gap < 0:
                total_gap += abs(gap)
            
            total_balance += bal
            total_pending += need
            
            acc_data.append({
                "": status,
                "Cuenta": acc["name"],
                "Saldo Actual": bal,
                "Pendiente": need,
                "Disponible": gap,
            })
        
        df_accs = pd.DataFrame(acc_data)
        
        # Alertas globales
        if total_gap > 0:
            st.markdown(f"""
            <div class="alert-card">
                <h4>⚠️ Atención: Déficit Detectado</h4>
                <p>Necesitas <strong>{eur(total_gap)}</strong> adicionales para cubrir todos los pagos pendientes.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            surplus = total_balance - total_pending
            st.markdown(f"""
            <div class="success-card">
                <h4>🎉 ¡Fondos Suficientes!</h4>
                <p>Todas las cuentas están cubiertas. Excedente: <strong>{eur(surplus)}</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Tabla de cuentas
        st.dataframe(
            df_accs,
            column_config={
                "": st.column_config.TextColumn("", width="small"),
                "Saldo Actual": st.column_config.ProgressColumn(
                    "Saldo",
                    format="%.2f €",
                    min_value=0,
                    max_value=df_accs["Saldo Actual"].max() if not df_accs.empty else 1000
                ),
                "Pendiente": st.column_config.NumberColumn(format="%.2f €"),
                "Disponible": st.column_config.NumberColumn(
                    format="%.2f €",
                ),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.divider()
        
        # Gráfico de saldos
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig_bal = px.bar(
                df_accs,
                x="Cuenta",
                y=["Saldo Actual", "Pendiente"],
                title="Comparativa Saldo vs Necesidades",
                barmode='group',
                color_discrete_map={"Saldo Actual": "#2ecc71", "Pendiente": "#e74c3c"}
            )
            st.plotly_chart(fig_bal, use_container_width=True)
        
        with col_chart2:
            # Disponible real
            fig_disp = px.bar(
                df_accs,
                x="Cuenta",
                y="Disponible",
                title="Disponibilidad Real por Cuenta",
                color="Disponible",
                color_continuous_scale=["red", "yellow", "green"],
                color_continuous_midpoint=0
            )
            st.plotly_chart(fig_disp, use_container_width=True)
        
        st.divider()
        
        # Ajuste manual de saldos
        with st.expander("🛠️ Ajustar Saldos Manualmente"):
            st.info("💡 Usa esto para sincronizar con tus saldos bancarios reales")
            
            with st.form("manual_balance"):
                cols = st.columns(len(manager.data["accounts"]))
                new_bals = {}
                
                for idx, acc in enumerate(manager.data["accounts"]):
                    with cols[idx]:
                        aid = str(acc["id"])
                        current_bal = float(manager.data["balances"].get(aid, 0.0))
                        val = st.number_input(
                            f"{acc['name']}", 
                            value=current_bal, 
                            step=50.0,
                            key=f"bal_{aid}"
                        )
                        new_bals[aid] = val
                
                if st.form_submit_button("💾 Actualizar Todos los Saldos", type="primary"):
                    manager.data["balances"] = {k: round(v, 2) for k, v in new_bals.items()}
                    manager.save()
                    st.success("✅ Saldos actualizados correctamente")
                    log_op("BALANCE_UPDATE", f"Saldos actualizados manualmente")
                    st.rerun()

    # -----------------------
    # TAB 4: CATEGORÍAS
    # -----------------------
    with tab_cat:
        st.subheader("📁 Análisis por Categorías")
        
        summary = manager.get_category_summary(selected_month)
        
        if summary.empty:
            st.info("No hay datos de categorías")
        else:
            # Métricas de categorías
            col_m1, col_m2, col_m3 = st.columns(3)
            
            with col_m1:
                st.metric("Categorías activas", len(summary))
            
            with col_m2:
                top_cat = summary.iloc[0]
                st.metric("Mayor gasto", top_cat["Categoría"], eur(top_cat["Total"]))
            
            with col_m3:
                avg_per_cat = summary["Total"].mean()
                st.metric("Promedio/Categoría", eur(avg_per_cat))
            
            st.divider()
            
            # Tabla detallada
            st.dataframe(
                summary,
                column_config={
                    "Total": st.column_config.ProgressColumn(
                        "Total",
                        format="%.2f €",
                        min_value=0,
                        max_value=summary["Total"].max()
                    ),
                    "Pagados": st.column_config.NumberColumn("Items Pagados"),
                    "Pendientes": st.column_config.NumberColumn("Items Pendientes"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.divider()
            
            # Treemap de categorías
            st.subheader("🗺️ Mapa de Gastos por Categoría")
            fig_tree = px.treemap(
                summary,
                path=['Categoría'],
                values='Total',
                color='Total',
                color_continuous_scale='RdYlGn_r',
                hover_data={'Total': ':,.2f'}
            )
            fig_tree.update_traces(textinfo="label+value+percent parent")
            st.plotly_chart(fig_tree, use_container_width=True)
            
            # Gestión de categorías
            st.divider()
            with st.expander("⚙️ Gestionar Categorías"):
                current_cats = manager.data.get("categories", [])
                
                col_cat1, col_cat2 = st.columns(2)
                
                with col_cat1:
                    st.write("**Categorías Actuales:**")
                    for cat in current_cats:
                        st.write(f"• {cat}")
                
                with col_cat2:
                    new_cat = st.text_input("Nueva Categoría")
                    if st.button("➕ Agregar Categoría"):
                        if new_cat and new_cat not in current_cats:
                            manager.data["categories"].append(new_cat)
                            manager.save()
                            st.success(f"✅ Categoría '{new_cat}' agregada")
                            st.rerun()

    # -----------------------
    # TAB 5: PLANTILLA
    # -----------------------
    with tab_template:
        st.subheader("⚙️ Plantilla de Gastos Recurrentes")
        st.info("💡 Los cambios aquí afectarán a los meses FUTUROS que generes, no al mes actual.")
        
        current_template = manager.data.get("template", [])
        
        if not current_template:
            st.warning("No hay gastos recurrentes configurados")
            df_template = pd.DataFrame(columns=[
                "id", "name", "amount", "account_id", "category", 
                "day", "type", "annual_month"
            ])
        else:
            df_template = pd.DataFrame(current_template)
        
        edited_template = st.data_editor(
            df_template,
            num_rows="dynamic",
            use_container_width=True,
            key="template_editor",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "name": st.column_config.TextColumn("Concepto", required=True),
                "amount": st.column_config.NumberColumn("Importe (€)", format="%.2f", required=True),
                "account_id": st.column_config.SelectboxColumn(
                    "Cuenta ID",
                    options=[a["id"] for a in manager.data["accounts"]],
                    required=True
                ),
                "category": st.column_config.SelectboxColumn(
                    "Categoría",
                    options=manager.data.get("categories", ["Otros"])
                ),
                "day": st.column_config.NumberColumn(
                    "Día del Mes",
                    min_value=1,
                    max_value=31,
                    required=True
                ),
                "type": st.column_config.SelectboxColumn(
                    "Tipo",
                    options=["fixed", "sub_monthly", "sub_annual"],
                    required=True
                ),
                "annual_month": st.column_config.NumberColumn(
                    "Mes (Si Anual)",
                    min_value=0,
                    max_value=12,
                    help="Solo para tipo 'sub_annual'. 0 = no aplica"
                ),
            }
        )
        
        col_save, col_reset = st.columns([1, 1])
        
        with col_save:
            if st.button("💾 Guardar Plantilla", type="primary", use_container_width=True):
                new_tpl = edited_template.to_dict(orient="records")
                
                # Limpiar y validar
                for item in new_tpl:
                    if pd.isna(item.get("id")):
                        item["id"] = manager.data["next_id"]
                        manager.data["next_id"] += 1
                    else:
                        item["id"] = int(item["id"])
                    
                    item["account_id"] = int(item["account_id"])
                    item["amount"] = float(item["amount"])
                    item["day"] = int(item["day"])
                    item["category"] = item.get("category", "Otros")
                    item["annual_month"] = int(item.get("annual_month", 0))
                
                manager.data["template"] = new_tpl
                manager.save()
                st.success("✅ Plantilla actualizada correctamente")
                log_op("TEMPLATE_UPDATE", f"{len(new_tpl)} items en plantilla")
                st.rerun()
        
        with col_reset:
            if st.button("🔄 Regenerar Mes Actual", use_container_width=True):
                if st.session_state.get('confirm_regenerate'):
                    # Eliminar mes actual y regenerar
                    key = manager.get_month_key(selected_month)
                    if key in manager.data["months"]:
                        del manager.data["months"][key]
                    manager.ensure_month_exists(selected_month)
                    st.success("✅ Mes regenerado desde plantilla")
                    st.session_state.confirm_regenerate = False
                    st.rerun()
                else:
                    st.session_state.confirm_regenerate = True
                    st.warning("⚠️ Esto eliminará todos los cambios del mes actual. Haz clic de nuevo para confirmar.")

if __name__ == "__main__":
    main()
