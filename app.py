import json
import calendar
from pathlib import Path
from datetime import date, datetime

import streamlit as st
import pandas as pd

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


def eur(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def log_op(action: str, detail: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}: {detail}\n"
    if LOG_FILE.exists():
        LOG_FILE.write_text(LOG_FILE.read_text(encoding="utf-8") + line, encoding="utf-8")
    else:
        LOG_FILE.write_text(line, encoding="utf-8")


def save_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_backup_schema(d: dict) -> None:
    required = ["year", "control_day", "balances", "template", "months"]
    for k in required:
        if k not in d:
            raise ValueError(f"Backup inválido: falta clave '{k}'")


def ym_key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def safe_date(y: int, m: int, d: int) -> str:
    last = calendar.monthrange(y, m)[1]
    dd = min(max(1, int(d)), last)
    return f"{y:04d}-{m:02d}-{dd:02d}"


# -----------------------
# Cuentas (5)
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
# Plantilla inicial (fijos + suscripciones)
# type: fixed / sub_monthly / sub_annual
# annual_month: mes de cargo real para anuales
# -----------------------
TEMPLATE_DEFAULT = [
    # Fijos
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

    # Suscripciones mensuales (todas cuenta 2)
    {"id": 101, "name": "ChatGPT Plus", "amount": 22.99, "day": 2, "account_id": 2, "type": "sub_monthly"},
    {"id": 102, "name": "Netflix", "amount": 16.00, "day": 2, "account_id": 2, "type": "sub_monthly"},
    {"id": 103, "name": "iCloud+ (2 TB)", "amount": 9.99, "day": 8, "account_id": 2, "type": "sub_monthly"},
    {"id": 104, "name": "PS Plus", "amount": 16.00, "day": 15, "account_id": 2, "type": "sub_monthly"},
    {"id": 105, "name": "Proton VPN Plus", "amount": 12.99, "day": 19, "account_id": 2, "type": "sub_monthly"},
    {"id": 106, "name": "X Premium", "amount": 4.00, "day": 27, "account_id": 2, "type": "sub_monthly"},
    {"id": 107, "name": "Roblox (niño)", "amount": 11.00, "day": 30, "account_id": 2, "type": "sub_monthly"},

    # Anuales (pago real + prorrateo)
    {"id": 201, "name": "InShot Pro (Anual)", "amount": 15.99, "day": 8, "account_id": 2, "type": "sub_annual", "annual_month": 5},
    {"id": 202, "name": "Telegram Premium (Anual)", "amount": 33.99, "day": 25, "account_id": 2, "type": "sub_annual", "annual_month": 9},
]


def load_data() -> dict:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    data = {
        "year": YEAR,
        "control_day": CONTROL_DAY,
        "balances": {str(a["id"]): 0.0 for a in ACCOUNTS},
        "template": TEMPLATE_DEFAULT,
        "months": {},
        "next_id": 1000,
    }
    save_data(data)
    log_op("INIT", f"Inicializado {YEAR} con {len(TEMPLATE_DEFAULT)} partidas")
    return data


def ensure_month(data: dict, y: int, m: int) -> None:
    key = ym_key(y, m)
    if key in data["months"]:
        return

    items = []
    for t in data["template"]:
        if t["type"] == "sub_annual" and int(t.get("annual_month", 0)) != m:
            continue

        items.append({
            "tid": int(t["id"]),
            "name": t["name"],
            "amount": round(float(t["amount"]), 2),
            "account_id": int(t["account_id"]),
            "due": safe_date(y, m, int(t["day"])),
            "paid": False,
            "type": t["type"],
        })

    data["months"][key] = {"year": y, "month": m, "items": items}
    save_data(data)
    log_op("NEW_MONTH", f"Creado {key} con {len(items)} cargos")


def month_items(data: dict, key: str):
    return data["months"][key]["items"]


def calc_totals(items):
    total = sum(i["amount"] for i in items)
    pending = sum(i["amount"] for i in items if not i["paid"])
    return total, pending


def need_by_account(items, only_pending=True):
    by = {}
    for i in items:
        if only_pending and i["paid"]:
            continue
        by[i["account_id"]] = by.get(i["account_id"], 0.0) + i["amount"]
    return by


def prorrated_by_account(data: dict):
    by = {}
    for t in data["template"]:
        if t["type"] == "sub_annual":
            acc = int(t["account_id"])
            by[acc] = by.get(acc, 0.0) + float(t["amount"]) / 12.0
    return by


def export_pending_txt(data: dict, key: str) -> Path:
    items = sorted([i for i in month_items(data, key) if not i["paid"]], key=lambda x: x["due"])
    lines = [f"Pendientes del mes {key} (corte día {data['control_day']})", "-" * 70]
    for i in items:
        lines.append(f"{i['due']} | {i['amount']:.2f}€ | {i['name']} | {ACC_BY_ID[i['account_id']]}")
    lines.append("-" * 70)
    lines.append(f"TOTAL PENDIENTE: {sum(i['amount'] for i in items):.2f}€")
    out = "\n".join(lines) + "\n"
    out_file = DATA_DIR / f"pendientes_{key}.txt"
    out_file.write_text(out, encoding="utf-8")
    log_op("EXPORT", f"{out_file.name} generado ({len(items)} items)")
    return out_file


def template_df(data: dict) -> pd.DataFrame:
    rows = []
    for t in data["template"]:
        rows.append({
            "id": int(t["id"]),
            "name": t["name"],
            "amount": float(t["amount"]),
            "day": int(t["day"]),
            "account_id": int(t["account_id"]),
            "account": ACC_BY_ID.get(int(t["account_id"]), ""),
            "type": t["type"],
            "annual_month": int(t.get("annual_month", 0)) if t["type"] == "sub_annual" else 0,
        })
    return pd.DataFrame(rows).sort_values(["type", "account_id", "day", "name"])


# -----------------------
# App
# -----------------------
data = load_data()
# Prorrateo anual por cuenta (necesario globalmente)

pr_by_acc = prorrated_by_account(data)
pr_global = sum(pr_by_acc.values())


# Sidebar: mes
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

# Toggle: auto-descuento
auto_deduct = st.sidebar.checkbox("Descontar saldo al marcar Pagado", value=True)
st.sidebar.caption("Si desmarcas un pago, el saldo se devuelve automáticamente.")

# Backup JSON
st.sidebar.subheader("Backup (JSON)")

# Export
export_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
st.sidebar.download_button(
    "Descargar backup JSON",
    data=export_bytes,
    file_name=f"backup_control_pagos_{data['year']}.json",
    mime="application/json",
)

# Import (solo bajo accion del usuario)
uploaded = st.sidebar.file_uploader("Seleccionar backup JSON", type=["json"])

if "last_import_sig" not in st.session_state:
    st.session_state["last_import_sig"] = None

if uploaded is not None:
    raw = uploaded.getvalue()
    sig = f"{uploaded.name}:{len(raw)}"  # firma simple
    st.sidebar.caption(f"Archivo listo: {uploaded.name} ({len(raw)} bytes)")

    do_import = st.sidebar.button("Importar ahora", type="primary")

    if do_import:
        try:
            incoming = json.loads(raw.decode("utf-8"))
            validate_backup_schema(incoming)

            # año fijo
            incoming["year"] = YEAR

            # marca para que sepas que SI cambió
            incoming.setdefault("meta", {})
            incoming["meta"]["last_import_ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            incoming["meta"]["last_import_file"] = uploaded.name

            save_data(incoming)
            log_op("IMPORT_JSON", f"Backup importado: {uploaded.name}")

            st.session_state["last_import_sig"] = sig
            st.sidebar.success("Backup importado. Recargando…")
            st.rerun()
            st.stop()

        except Exception as e:
            st.sidebar.error(f"No se pudo importar: {e}")


# Estado por cuenta
st.subheader("Estado por cuenta (meta del mes)")

balances = {k: float(v) for k, v in data["balances"].items()}
if any(v < 0 for v in balances.values()):
    st.warning("Hay cuentas con saldo negativo (por auto-descuento o ajustes).")

need_pending = need_by_account(items_sorted, only_pending=True)

rows = []
ok_global = True
sum_bal = 0.0
sum_need = 0.0
sum_deficit = 0.0

for a in ACCOUNTS:
    acc_id = a["id"]
    bal = float(balances.get(str(acc_id), 0.0))
    need = float(need_pending.get(acc_id, 0.0))
    deficit = max(0.0, need - bal)
    ok = deficit == 0.0
    ok_global = ok_global and ok

    sum_bal += bal
    sum_need += need
    sum_deficit += deficit

    rows.append({
        "Cuenta": a["name"],
        "Saldo actual": bal,
        "Pendiente en esta cuenta (mes)": need,
        "Falta para OK": deficit,
        "OK": "OK" if ok else "NO OK",
        "Prorrateo anuales / mes": float(pr_by_acc.get(acc_id, 0.0)),
        "Estructural (Pendiente + Prorrateo)": need + float(pr_by_acc.get(acc_id, 0.0)),
    })

df_accounts = pd.DataFrame(rows)
df_accounts = df_accounts[[
    "Cuenta", "Saldo actual", "Pendiente en esta cuenta (mes)", "Falta para OK", "OK",
    "Prorrateo anuales / mes", "Estructural (Pendiente + Prorrateo)"
]]

df_show = df_accounts.copy()
for col in [
    "Saldo actual", "Pendiente en esta cuenta (mes)", "Falta para OK",
    "Prorrateo anuales / mes", "Estructural (Pendiente + Prorrateo)"
]:
    df_show[col] = df_show[col].apply(eur)

cA, cB = st.columns([2, 1])
with cA:
    st.dataframe(df_show, use_container_width=True, hide_index=True)
with cB:
    st.metric("Suma saldos (5 cuentas)", eur(sum_bal))
    st.metric("Suma pendiente (real)", eur(sum_need))
    st.metric("Falta total para OK", eur(sum_deficit))
    st.markdown(f"**Estado global del mes:** {'🟢 OK' if ok_global else '🔴 NO OK'}")
    st.metric("Disponible para distribuir", eur(excess_total))
    st.metric("Falta total para OK", eur(deficit_total))
    st.markdown(f"**¿Redistribución suficiente?:** {'🟢 Sí' if can_redistribute else '🔴 No'}")


st.divider()
# --- Redistribución: excedentes vs déficits ---
excess_total = 0.0
deficit_total = 0.0
excess_by_acc = {}
deficit_by_acc = {}

for a in ACCOUNTS:
    acc_id = a["id"]
    bal = float(balances.get(str(acc_id), 0.0))
    need = float(need_pending.get(acc_id, 0.0))

    excess = max(0.0, bal - need)
    deficit = max(0.0, need - bal)

    excess_by_acc[acc_id] = excess
    deficit_by_acc[acc_id] = deficit

    excess_total += excess
    deficit_total += deficit

can_redistribute = excess_total >= deficit_total




# Actualizar saldos (permite negativos)
st.subheader("Actualizar saldos por cuenta")
with st.form("balances_form"):
    cols = st.columns(5)
    new_balances = {}
    for idx, a in enumerate(ACCOUNTS):
        with cols[idx]:
            new_balances[str(a["id"])] = st.number_input(
                a["name"],
                min_value=-1_000_000.0,  # permite negativos
                step=10.0,
                value=float(balances.get(str(a["id"]), 0.0)),
                format="%.2f",
            )
    save_bal = st.form_submit_button("Guardar saldos")

if save_bal:
    data["balances"] = {k: round(float(v), 2) for k, v in new_balances.items()}
    save_data(data)
    log_op("BALANCES", f"Saldos actualizados mes {key}")
    st.success("Saldos guardados.")
    st.rerun()

st.divider()

# Cargos del mes: marcar pagados y (opcional) descontar saldo
st.subheader("Cargos del mes (marca pagados)")
st.caption("Si activaste “Descontar saldo…”, al marcar Pagado se descuenta del saldo de la cuenta correspondiente.")

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
            st.write(eur(i["amount"]))
        with c4:
            st.write(i["type"])
        with c5:
            paid = st.checkbox("Pagado", value=bool(i["paid"]), key=f"paid_{key}_{i['tid']}_{i['due']}")
        edited.append((i["tid"], i["due"], paid))

    save_paid = st.form_submit_button("Guardar pagos")

if save_paid:
    changes = 0
    bal_changes = 0

    for tid, due, new_paid in edited:
        for it in items:
            if it["tid"] == tid and it["due"] == due:
                old_paid = bool(it["paid"])
                if old_paid != bool(new_paid):
                    it["paid"] = bool(new_paid)
                    changes += 1

                    if auto_deduct:
                        acc_k = str(it["account_id"])
                        amt = float(it["amount"])
                        if it["paid"] and not old_paid:
                            data["balances"][acc_k] = round(float(data["balances"].get(acc_k, 0.0)) - amt, 2)
                            bal_changes += 1
                            log_op("DEDUCT", f"{key} {it['name']} -{amt:.2f} ({ACC_BY_ID[it['account_id']]})")
                        elif (not it["paid"]) and old_paid:
                            data["balances"][acc_k] = round(float(data["balances"].get(acc_k, 0.0)) + amt, 2)
                            bal_changes += 1
                            log_op("REFUND", f"{key} {it['name']} +{amt:.2f} ({ACC_BY_ID[it['account_id']]})")
                break

    save_data(data)
    log_op("PAID_UPDATE", f"Mes {key}: {changes} cambios, {bal_changes} ajustes de saldo")
    st.success("Pagos (y saldos si aplica) actualizados.")
    st.rerun()

st.divider()

# Editor SOLO este mes
st.subheader("Editar cargos SOLO de este mes")
st.caption("Útil si este mes un importe cambió. No modifica la plantilla futura.")

with st.expander("Abrir editor del mes"):
    df_month = pd.DataFrame([{
        "tid": i["tid"],
        "name": i["name"],
        "amount": float(i["amount"]),
        "due": i["due"],
        "account_id": int(i["account_id"]),
        "paid": bool(i["paid"]),
        "type": i["type"],
    } for i in items_sorted])

    edited_df = st.data_editor(
        df_month,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "account_id": st.column_config.SelectboxColumn(
                "account_id",
                options=[a["id"] for a in ACCOUNTS],
                help="Cuenta por ID",
            ),
        },
        disabled=["tid", "type"],
        key=f"month_editor_{key}",
    )

    if st.button("Guardar cambios del mes"):
        by_tid_due = {(i["tid"], i["due"]): i for i in items}
        updated = 0
        for _, row in edited_df.iterrows():
            k2 = (int(row["tid"]), str(row["due"]))
            if k2 in by_tid_due:
                it = by_tid_due[k2]
                it["amount"] = round(float(row["amount"]), 2)
                it["account_id"] = int(row["account_id"])
                it["paid"] = bool(row["paid"])
                updated += 1
        save_data(data)
        log_op("EDIT_MONTH", f"{key}: editados {updated} items (solo mes)")
        st.success("Cambios del mes guardados.")
        st.rerun()

st.divider()

# Editor de plantilla
st.subheader("Editar PLANTILLA (gastos futuros)")
st.caption("Esto modifica lo que se cargará en meses FUTUROS. Los meses ya creados no se reescriben automáticamente.")

with st.expander("Abrir editor de plantilla"):
    df_t = template_df(data)
    edited_t = st.data_editor(
        df_t,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "type": st.column_config.SelectboxColumn("type", options=["fixed", "sub_monthly", "sub_annual"]),
            "account_id": st.column_config.SelectboxColumn("account_id", options=[a["id"] for a in ACCOUNTS]),
            "annual_month": st.column_config.SelectboxColumn(
                "annual_month",
                options=list(range(0, 13)),
                help="Solo para sub_annual (1-12). 0 si no aplica.",
            ),
        },
        disabled=["account"],
        key="template_editor",
    )

    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Guardar plantilla"):
            new_template = []
            for _, row in edited_t.iterrows():
                ttype = str(row["type"])
                ann_m = int(row["annual_month"])
                if ttype == "sub_annual" and not (1 <= ann_m <= 12):
                    st.error(f"El item {row['id']} es anual y necesita annual_month 1-12.")
                    st.stop()

                obj = {
                    "id": int(row["id"]),
                    "name": str(row["name"]).strip(),
                    "amount": round(float(row["amount"]), 2),
                    "day": int(row["day"]),
                    "account_id": int(row["account_id"]),
                    "type": ttype,
                }
                if ttype == "sub_annual":
                    obj["annual_month"] = ann_m
                new_template.append(obj)

            data["template"] = new_template
            save_data(data)
            log_op("SAVE_TEMPLATE", f"Plantilla guardada ({len(new_template)} items)")
            st.success("Plantilla guardada.")
            st.rerun()

    with c2:
        st.write("Añadir nuevo item")
        with st.form("add_template"):
            new_name = st.text_input("Nombre")
            new_amount = st.number_input("Importe", min_value=0.0, step=1.0, format="%.2f")
            new_day = st.number_input("Día (1-31)", min_value=1, max_value=31, step=1, value=10)
            new_type = st.selectbox("Tipo", ["fixed", "sub_monthly", "sub_annual"])
            new_account = st.selectbox("Cuenta", [a["id"] for a in ACCOUNTS], format_func=lambda x: ACC_BY_ID[x])
            new_ann_m = st.selectbox("Mes anual (si aplica)", list(range(0, 13)), index=0)
            add_btn = st.form_submit_button("Añadir a plantilla")

        if add_btn:
            if new_type == "sub_annual" and not (1 <= int(new_ann_m) <= 12):
                st.error("Para sub_annual debes elegir mes 1-12.")
                st.stop()

            new_id = int(data.get("next_id", 1000))
            data["next_id"] = new_id + 1
            obj = {
                "id": new_id,
                "name": new_name.strip(),
                "amount": round(float(new_amount), 2),
                "day": int(new_day),
                "account_id": int(new_account),
                "type": new_type,
            }
            if new_type == "sub_annual":
                obj["annual_month"] = int(new_ann_m)

            data["template"].append(obj)
            save_data(data)
            log_op("ADD_TEMPLATE", f"Agregado {new_id} {obj['name']} {obj['amount']:.2f}")
            st.success("Item añadido a plantilla.")
            st.rerun()

st.divider()

# Export pendientes
st.subheader("Exportar")
c1, c2 = st.columns([1, 3])
with c1:
    if st.button("Generar TXT de pendientes"):
        out = export_pending_txt(data, key)
        st.success(f"Generado: {out.name}")
        st.download_button("Descargar pendientes", data=out.read_bytes(), file_name=out.name)
with c2:
    st.write("Incluye fecha, importe, concepto y cuenta. Se registra en operaciones.txt.")

with st.expander("Nota importante sobre saldos"):
    st.write(
        "Los saldos son una referencia operativa. Si activas el auto-descuento, el sistema simula el efecto de pagar "
        "y te muestra la realidad interna. Si prefieres reflejar el banco 100%, desactiva el auto-descuento y actualiza "
        "saldos manualmente desde la app."
    )
