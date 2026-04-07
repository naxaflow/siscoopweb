import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SiscoopWeb - Planilla ASOPAGOS", layout="wide")
st.title("🧾 Generador de Planilla ASOPAGOS Colombia")

# ====================== PERIODO DE PAGO ======================
st.subheader("📅 Periodo de Pago")
col_a, col_m = st.columns([1, 1])
with col_a:
    año = st.selectbox("Año", list(range(2024, 2030)), index=2)
with col_m:
    mes = st.selectbox("Mes", list(range(1, 13)), index=datetime.today().month-1, format_func=lambda x: f"{x:02d}")

periodo = pd.to_datetime(f"{año}-{mes:02d}-01")

# ====================== RETIROS ======================
st.subheader("🚪 Retiros en este periodo")
hay_retiros = st.checkbox("Hay empleados que se retiran este mes", value=False)
if hay_retiros:
    ultimo_dia = periodo + pd.offsets.MonthEnd(0)
    fecha_retiro = st.date_input("Fecha de retiro", value=ultimo_dia)
    docs_retiro = st.text_area("Números de documento de los empleados que se retiran (uno por línea)", height=120, placeholder="12345678\n87654321\n...")
    retiros_set = {x.strip() for x in docs_retiro.splitlines() if x.strip()}
else:
    fecha_retiro = None
    retiros_set = set()

# ====================== CARGA DE ARCHIVO ======================
uploaded_file = st.file_uploader("Subir archivo Excel 'Detalle Pase'", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    # Limpiar filas basura
    df = df[~df.iloc[:, 0].astype(str).str.contains("FACTURA|SUBTOTAL|TOTAL|RESUMEN", na=False, case=False)]
    
    # ====================== RENOMBRAR COLUMNAS PARA QUE SEA FÁCIL ======================
    df.columns = [f"col_{i}" for i in range(len(df.columns))]
    
    st.subheader("🔍 Vista previa de tu Excel (con números de columna)")
    st.dataframe(df.head(12))
    
    # ====================== ASIGNAR COLUMNAS ======================
    st.subheader("📌 Asignar columnas del Excel")
    col_numero   = st.selectbox("Número de documento (cédula/NIT)", df.columns, index=1)
    col_nombre   = st.selectbox("Nombre / Razón Social", df.columns, index=2)
    col_eps      = st.selectbox("EPS", df.columns, index=6)
    col_ccf      = st.selectbox("Caja de Compensación (CCF)", df.columns, index=7)
    col_riesgo   = st.selectbox("Riesgo (R1, R2, R3...)", df.columns, index=8)
    col_N        = st.selectbox("Columna N (para pensión)", df.columns, index=9)
    col_salario  = st.selectbox("Salario", df.columns, index=10)
    col_pension  = st.selectbox("Pensión (base)", df.columns, index=11)
    col_salud    = st.selectbox("Salud", df.columns, index=12)
    col_arp      = st.selectbox("ARP", df.columns, index=13)
    
    # Aplicar los nombres reales
    df['numero']  = df[col_numero].astype(str).str.strip()
    df['nombre']  = df[col_nombre].astype(str).str.strip()
    df['eps']     = df[col_eps].astype(str).str.strip()
    df['ccf']     = df[col_ccf].astype(str).str.strip()
    df['riesgo']  = df[col_riesgo].astype(str).str.strip()
    
    # ====================== CONVERSIONES NUMÉRICAS ======================
    for c in [col_N, col_salario, col_pension, col_salud, col_arp]:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # ====================== FECHA DE INGRESO (columna F = col_5) ======================
    df['fecha_ingreso'] = pd.to_datetime(df['col_5'], errors='coerce')
    
    # ====================== MAPPING EPS / CCF ======================
    # (por ahora vacío – si tienes el mapping completo, pégalo aquí)
    eps_map = {}
    ccf_map = {}
    df['cod_eps'] = df['eps'].map(eps_map).fillna('999')
    df['cod_ccf'] = df['ccf'].map(ccf_map).fillna('999')
    
    # ====================== RISK MAP CORRECTO (el que me diste) ======================
    risk_map = {
        'R1': {'tasa': 0.00522, 'actividad': '1949101'},
        'R2': {'tasa': 0.01044, 'actividad': '2329001'},
        'R3': {'tasa': 0.02436, 'actividad': '3869201'},
        'R4': {'tasa': 0.0435,  'actividad': '4492301'},
        'R5': {'tasa': 0.0696,  'actividad': '5439003'},
    }
    df['riesgo'] = df['riesgo'].str.upper().fillna('R1')
    df['tasa_arp'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['tasa'])
    df['cod_actividad'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['actividad'])
    
    # ====================== PENSIÓN (N = 0 → sin pensión) ======================
    df['pension'] = df.apply(lambda row: 0 if row[col_N] == 0 else row[col_pension], axis=1)
    
    # ====================== GENERAR TXT ======================
    def generar_planilla_txt(df, periodo, fecha_retiro, retiros_set):
        lineas = []
        for _, row in df.iterrows():
            # Fecha ingreso solo si es del periodo actual
            if pd.notna(row['fecha_ingreso']) and row['fecha_ingreso'].to_period('M') == periodo.to_period('M'):
                fecha_ing_str = row['fecha_ingreso'].strftime('%Y%m%d')
            else:
                fecha_ing_str = ''
            
            # Fecha retiro solo para los marcados
            if fecha_retiro and str(row['numero']).strip() in retiros_set:
                fecha_ret_str = fecha_retiro.strftime('%Y%m%d')
            else:
                fecha_ret_str = ''
            
            linea = f"{row.get('tipo_doc','')},{row['numero']},{row['nombre']},{row['cod_eps']},{row['cod_ccf']},"
            linea += f"{row[col_salario]:.0f},{row['pension']:.0f},{row[col_salud]:.0f},{row['tasa_arp']:.5f},"
            linea += f"{row['cod_actividad']},{fecha_ing_str},{fecha_ret_str},30"
            lineas.append(linea)
        return "\n".join(lineas)
    
    txt_output = generar_planilla_txt(df, periodo, fecha_retiro, retiros_set)
    
    st.download_button(
        label="⬇️ Descargar Planilla TXT",
        data=txt_output,
        file_name=f"planilla_asopagos_{año}{mes:02d}.txt",
        mime="text/plain"
    )
    
    st.success(f"✅ Planilla generada para periodo {mes:02d}/{año}")
    st.dataframe(df.head(8))
