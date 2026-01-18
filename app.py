import json
import calendar
from pathlib import Path
from datetime import date, datetime

import streamlit as st

# -----------------------
# Config
# -----------------------
st.set_page_config(page_title="Control de Pagos 2026", layout="wide")

YEAR = 2026
CONTROL_DAY = 29  # fecha referencial de control

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATA_FILE = DATA_DIR / "control_pagos_streamlit_2026.json"
LOG_FILE = DATA_DIR / "operaciones.txt"

# -----------------------
# Modelo: Cuentas (5)
# -----------------------
ACCOUNTS = [
    {"id": 1, "name": "BBVA – Ydaliz"},
    {"id": 2, "name": "BBVA – Moisés"},
    {"id": 3, "name": "Caixa – Conjunta"},
    {"id": 4, "name": "Santander – Ydaliz"},
    {"id": 5, "name": "Santander – Moisés"},
]
ACC_BY_ID = {a["id"]: a["name"] for a in ACCOUNTS}

# -----------------------
# Plantilla: Gastos fijos + Suscripciones
# dia = día de cargo; si no existe en el mes, se ajusta al último día.
# type: fixed/sub_monthly/sub_annual
# annual_month: mes de cargo real (1-12) para anuales
# -----------------------
TEMPLATE_DEFAULT = [
    # --- Fijos ---
    {"id": 1, "name": "Cuota hipoteca", "amount": 533.66, "day": 5, "account_id": 4, "type": "fixed"},
    {"id": 2, "name": "Seguro hogar", "amount": 66.00, "day": 10, "account_id": 4, "type": "fixed"},
    {"id": 3, "name": "Seguro de vida", "amount": 52.00, "day": 10, "account_id": 3, "type": "fixed"},
    {"id": 4, "name": "Crédito coche", "amount": 258.00, "day": 15, "account_id": 1, "type": "fixed"},
    {"id": 5, "name": "Crédito complementario casa", "amount": 385.00, "day": 15, "account_id": 3, "type": "fixed"},
    {"id": 6, "name": "Cofidis", "amount": 145.00, "day": 20, "account_id": 1, "type": "fixed"},
    {"id": 7, "name": "IKEA Yda", "amount": 200.00, "day": 25, "account_id": 1, "type": "fixed"},
    {"id": 8, "name": "IKEA Moisés", "amount": 200.00, "day": 25, "account_id": 5, "type": "fixed"},
    {"id": 9, "name": "Vodafone", "amount": 15.00, "day": 8, "account_id": 1, "type": "fixed"},
    {"id": 10, "name": "Orange", "amount": 240.00, "day": 8, "account_id": 2, "type": "fixed"},
    {"id": 11, "name": "Carrefour", "amount": 100.00, "day": 12, "account_id": 1, "type": "fixed"},
    {"id": 12, "name": "Agua", "amount": 60.00, "day": 18, "account_id": 3, "type": "fixed"},
    {"id": 13, "name": "Luz", "amount": 120.00, "day": 18, "account_id": 3, "type": "fixed"},
    {"id": 14, "name": "Comida", "amount": 800.00, "day": 2, "account_id": 3, "type": "fixed"},
    {"id": 15, "name": "Curso inglés niño", "amount": 80.00, "day": 7, "account_id": 4, "type": "fixed"},
    {"id": 16, "name": "Karate", "amount": 50.00, "day": 7, "account_id": 4, "type": "fixed"},
    {"id": 17, "name": "Gasolina", "amount": 100.00, "day": 1, "account_id": 4, "type": "fixed"},

    # --- Suscripciones mensuales (todas cuenta 2) ---
    {"id": 101, "name": "ChatGPT Plus", "amount": 22.99, "day": 2, "account_id": 2, "type": "sub_monthly"},
    {"id": 102, "name": "Netflix", "amount": 16.00, "day": 2, "account_id": 2, "type": "sub_monthly"},
    {"id": 103, "name": "iCloud+ (2 TB)", "amount": 9.99, "day": 8, "account_id": 2, "type": "sub_monthly"},
    {"id": 104, "name": "PS Plus", "amount": 16.00, "day": 15, "account_id": 2, "type": "sub_monthly"},
    {"id": 105, "name": "Proton VPN Plus", "amount": 12.99, "day": 19, "account_id": 2, "type": "sub_monthly"},
    {"id": 106, "name": "X Premium", "amount": 4.00, "day": 27, "account_id": 2, "type": "sub_monthly"},
    {"id": 107, "name": "Roblox (niño)", "amount": 11.00, "day": 30, "account_id": 2, "type": "sub_monthly"},

    # --- Suscripciones anuales (pago real + prorrateo) ---
    {"id": 201, "name": "InShot Pro (Anual)", "amount": 15.99, "day": 8, "account_id": 2, "type": "sub_annual", "annual_month": 5},
    {"id": 202, "name": "Telegram Premium (Anual)", "amount": 33.99, "day": 25, "account_id": 2, "type": "sub_annual", "annual_month": 9},
]

# -----------------------
# Persistencia
# -----------------------
def log_op(action: str, detail: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}: {detail}\n"
    if LOG_FILE.exists():
        LOG_FILE.write_text(LOG_FILE.read_text(encoding="utf-8") + line, encoding="utf-8")
    else:
        LOG_FILE.write_text(line, encoding="utf-8")

def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data = {
        "year": YEAR,
        "control_day": CONTROL_DAY,
        "balances": {str(a["id"]): 0.0 for a in ACCOUNTS},
        "template": TEMPLATE_DEFAULT,
        "months": {},  # "YYYY-MM": {"items":[...]}
        "next_id": 300
    }
    save_data(data)
    log_op("INIT", f"Inicializado {YEAR} con {len(TEMPLATE_DEFAULT)} partidas")
    return data

def ym_key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"

def safe_date(y: int, m: int, d: int) -> str:
    last = calendar.monthrange(y, m)[1]
    dd = min(max(1, d), last)
    return f"{y:04d}-{m:02d}-{dd:02d}"

def ensure_month(data: dict, y: int, m: int) -> None:
    key = ym_key(y, m)
    if key in data["months"]:
        return

    items = []
    for t in data["template"]:
        # Anuales: solo se cargan en su mes real
        if t["type"] == "sub_annual":
            if int(t.get("annual_month", 0)) != m:
                continue

        items.append({
            "tid": t["id"],
            "name": t["name"],
            "amount": round(float(t["amount"]), 2),
            "account_id": int(t["account_id"]),
            "due": safe_date(y, m, int(t["day"])),
            "paid": False,
            "type": t["type"],
        })

    data["months"][key] = {"year": y, "month": m, "items": items}
    save_data(data)
    log_op("NEW_MONTH", f"Creado {key} con {len(items)} cargos (incluye anuales si aplica)")

def month_items(data: dict, key: str):
    return data["months"][key]["items"]

def calc_totals(items):
    total = sum(i["amount"] for i in items)
    pending = sum(i["amount"] for i in items if not i["paid"])
    return total, pending

def calc_by_account_pending(items):
    by = {}
    for i in items:
        if not i["paid"]:
            by[i["account_id"]] = by.get(i["account_id"], 0.0) + i["amount"]
    return by

def prorrated_monthly_cost(data: dict) -> float:
    # prorrateo global (solo anuales)
    annual = [t for t in data["template"] if t["type"] == "sub_annual"]
    return sum(float(t["amount"]) / 12.0 for t in annual)

def prorrated_by_account(data: dict):
    by = {}
    for t in data["template"]:
        if t["type"] == "sub_annual":
            acc = int(t["account_id"])
            by[acc] = by.get(acc, 0.0) + float(t["amount"]) / 12.0
    return by

def export_pending_txt(data: dict, key: str) -> Path:
    items = sorted([i for i in month_items(data, key) if not i["paid"]], key=lambda x: x["due"])
    lines = [f"Pendientes del mes {key} (corte día {data['control_day']})", "-" * 60]
    for i in items:
        lines.append(f"{i['due']} | {i['amount']:.2f}€ | {i['name']} | {ACC_BY_ID[i['account_id']]}")
    lines.append("-" * 60)
    lines.append(f"TOTAL PENDIENTE: {sum(i['amount'] for i in items):.2f}€")
    out = "\n".join(lines) + "\n"
    out_file = DATA_DIR / f"pendientes_{key}.txt"
    out_file.write_text(out, encoding="utf-8")
    log_op("EXPORT", f"{out_file.name} generado ({len(items)} items)")
    return out_file

# -----------------------
# App
# -----------------------
data = load_data()

# Mes por defecto = mes actual del sistema, pero año fijo 2026
default_month = date.today().month
selected_month = st.sidebar.selectbox("Mes", list(range(1, 13)), index=default_month - 1)
y = int(data["year"])
m = int(selected_month)
key = ym_key(y, m)
ensure_month(data, y, m)

items = month_items(data, key)
items_sorted = sorted(items, key=lambda x: x["due"])
total, pending = calc_totals(items_sorted)

st.title(f"Control de Pagos {y} — Mes {key}")
st.caption(f"Fecha referencial de control: día {data['control_day']}")

col1, col2, col3 = st.columns(3)
col1.metric("Total del mes (real)", f"{total:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("Falta por pagar (real)", f"{pending:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("Prorrateo anuales (planificación)", f"{prorrated_monthly_cost(data):,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

st.divider()

# --- Saldos por cuenta + OK/NO OK ---
st.subheader("Estado por cuenta (real del mes)")

balances = data["balances"]
need_by_acc = calc_by_account_pending(items_sorted)
pr_by_acc = prorrated_by_account(data)

rows = []
ok_global = True
sum_bal = 0.0
sum_need = 0.0

for a in ACCOUNTS:
    acc_id = a["id"]
    bal = float(balances.get(str(acc_id), 0.0))
    need = float(need_by_acc.get(acc_id, 0.0))
    pr = float(pr_by_acc.get(acc_id, 0.0))
    ok = bal >= need
    ok_global = ok_global and ok
    sum_bal += bal
    sum_need += need
    rows.append({
        "Cuenta": a["name"],
        "Saldo actual (€)": bal,
        "Necesario mes (€)": need,
        "OK mes": "OK" if ok else "NO OK",
        "Prorrateo anuales (€ / mes)": pr,
        "Estructural (Necesario+Prorrateo)": need + pr
    })

cA, cB = st.columns([2, 1])
with cA:
    st.dataframe(rows, use_container_width=True, hide_index=True)
with cB:
    st.metric("Suma saldos (5 cuentas)", f"{sum_bal:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Suma necesario (pendiente)", f"{sum_need:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
    st.markdown(f"**Estado global del mes:** {'🟢 OK' if ok_global else '🔴 NO OK'}")

st.divider()

# --- Editor de saldos ---
st.subheader("Actualizar saldos por cuenta")
with st.form("balances_form"):
    cols = st.columns(5)
    new_balances = {}
    for idx, a in enumerate(ACCOUNTS):
        with cols[idx]:
            new_balances[str(a["id"])] = st.number_input(
                a["name"],
                min_value=0.0,
                step=10.0,
                value=float(balances.get(str(a["id"]), 0.0)),
                format="%.2f"
            )
    save_bal = st.form_submit_button("Guardar saldos")

if save_bal:
    data["balances"] = {k: round(float(v), 2) for k, v in new_balances.items()}
    save_data(data)
    log_op("BALANCES", f"Actualizados saldos mes {key}")
    st.success("Saldos guardados.")
    st.rerun()

st.divider()

# --- Tabla de cargos del mes + marcar pagado ---
st.subheader("Cargos del mes (marca pagados)")
with st.form("paid_form"):
    edited = []
    for i in items_sorted:
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 2, 1])
        with c1:
            st.write(i["name"])
            st.caption(ACC_BY_ID[i["account_id"]])
        with c2:
            st.write(i["due"])
        with c3:
            st.write(f"{i['amount']:.2f} €".replace(".", ","))
        with c4:
            st.write(i["type"])
        with c5:
            paid = st.checkbox("Pagado", value=bool(i["paid"]), key=f"paid_{key}_{i['tid']}_{i['due']}")
        edited.append((i["tid"], i["due"], paid))

    save_paid = st.form_submit_button("Guardar pagos")

if save_paid:
    # aplica cambios
    changed = 0
    for tid, due, paid in edited:
        for it in items:
            if it["tid"] == tid and it["due"] == due:
                if bool(it["paid"]) != bool(paid):
                    it["paid"] = bool(paid)
                    changed += 1
    save_data(data)
    log_op("PAID_UPDATE", f"Mes {key}: {changed} cambios")
    st.success("Pagos actualizados.")
    st.rerun()

st.divider()

# --- Export pendientes ---
st.subheader("Exportar")
c1, c2 = st.columns([1, 3])
with c1:
    if st.button("Generar TXT de pendientes"):
        out = export_pending_txt(data, key)
        st.success(f"Generado: {out.name}")
        st.download_button("Descargar pendientes", data=out.read_bytes(), file_name=out.name)
with c2:
    st.write("El TXT incluye fecha, importe, concepto y cuenta. También queda registrado en operaciones.txt.")

# --- Notas rápidas (sin complicar la UI) ---
with st.expander("Notas de funcionamiento"):
    st.write(
        "- Año fijo 2026.\n"
        "- Suscripciones anuales: aparecen solo en su mes real, y además se prorratean en la sección de planificación.\n"
        "- Si un cargo cae en día inexistente (ej. 30 en febrero), se ajusta al último día del mes.\n"
        "- Corte de control: día 29 (referencial)."
    )
