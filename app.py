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

# ====================== INGRESOS Y RETIROS MANUALES ======================
st.subheader("📥 Ingresos en este periodo (manual)")
hay_ingresos = st.checkbox("Hay empleados que ingresan este mes", value=False)
if hay_ingresos:
    fecha_ingreso_manual = st.date_input("Fecha de ingreso", value=periodo)
    docs_ingreso = st.text_area("Números de documento que INGRESAN (uno por línea)", height=120, placeholder="")
    ingresos_set = {x.strip() for x in docs_ingreso.splitlines() if x.strip()}
else:
    fecha_ingreso_manual = None
    ingresos_set = set()

st.subheader("🚪 Retiros en este periodo (manual)")
hay_retiros = st.checkbox("Hay empleados que se retiran este mes", value=False)
if hay_retiros:
    ultimo_dia = periodo + pd.offsets.MonthEnd(0)
    fecha_retiro_manual = st.date_input("Fecha de retiro", value=ultimo_dia)
    docs_retiro = st.text_area("Números de documento que SE RETIRAN (uno por línea)", height=120, placeholder="")
    retiros_set = {x.strip() for x in docs_retiro.splitlines() if x.strip()}
else:
    fecha_retiro_manual = None
    retiros_set = set()

# ====================== CARGA Y LIMPIEZA ======================
uploaded_file = st.file_uploader("Subir archivo Excel 'Detalle Pase' (hoja detalle.rpt)", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str, header=None)
    df = df[pd.to_numeric(df.iloc[:, 0], errors='coerce').notna()]   # solo filas de empleados
    df.columns = [f"col_{i}" for i in range(len(df.columns))]

    st.success(f"✅ Archivo limpiado correctamente: {len(df)} empleados")
    st.dataframe(df.head(10))

    # ====================== SELECTORES DE COLUMNAS ======================
    st.subheader("📌 Selecciona las columnas correctas")
    col_numero  = st.selectbox("Número de documento", df.columns, index=1)
    col_nombre  = st.selectbox("Nombre del afiliado", df.columns, index=2)
    col_eps     = st.selectbox("EPS", df.columns, index=6)
    col_ccf     = st.selectbox("Caja de Compensación", df.columns, index=12)
    col_riesgo  = st.selectbox("Riesgo (R1-R5)", df.columns, index=len(df.columns)-1)
    col_N       = st.selectbox("Columna N (pensión)", df.columns, index=9)
    col_salario = st.selectbox("Salario / IBC (V/r. Factura)", df.columns, index=17)
    col_pension = st.selectbox("Valor Pensión", df.columns, index=11)
    col_salud   = st.selectbox("Valor Salud", df.columns, index=7)

    # Aplicar columnas
    df['numero'] = df[col_numero].astype(str).str.strip().str.replace(',', '')
    df['nombre'] = df[col_nombre].astype(str).str.strip()
    df['eps']    = df[col_eps].astype(str).str.strip()
    df['ccf']    = df[col_ccf].astype(str).str.strip()
    df['riesgo'] = df[col_riesgo].astype(str).str.strip()

    # Conversiones numéricas
    for c in [col_N, col_salario, col_pension, col_salud]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # ====================== MAPPINGS ======================
    eps_map = {'Nueva EPS': '050', 'SANITAS S.A.': '053', 'ASMET SALUD': '054', 'Positiva': '058', 'MALLAMAS': '059', '': '999'}
    ccf_map = {'CCF32': '32', 'CCF13': '13', '': '00'}
    df['cod_eps'] = df['eps'].map(eps_map).fillna('999')
    df['cod_ccf'] = df['ccf'].map(ccf_map).fillna('00')

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

    df['pension'] = df.apply(lambda row: 0 if row[col_N] == 0 else row[col_pension], axis=1)

    # ====================== GENERAR TXT ======================
    def generar_planilla_txt(df, periodo, fecha_ingreso_manual, ingresos_set, fecha_retiro_manual, retiros_set):
        lineas = []
        for _, row in df.iterrows():
            fecha_ing_str = fecha_ingreso_manual.strftime('%Y%m%d') if fecha_ingreso_manual and str(row['numero']).strip() in ingresos_set else ''
            fecha_ret_str = fecha_retiro_manual.strftime('%Y%m%d') if fecha_retiro_manual and str(row['numero']).strip() in retiros_set else ''
            
            # tipo_doc queda vacío (como en tu archivo original)
            linea = f",{row['numero']},{row['nombre']},{row['cod_eps']},{row['cod_ccf']},"
            linea += f"{row[col_salario]:.0f},{row['pension']:.0f},{row[col_salud]:.0f},{row['tasa_arp']:.5f},"
            linea += f"{row['cod_actividad']},{fecha_ing_str},{fecha_ret_str},30"
            lineas.append(linea)
        return "\n".join(lineas)

    txt_output = generar_planilla_txt(df, periodo, fecha_ingreso_manual, ingresos_set, fecha_retiro_manual, retiros_set)

    st.download_button(
        label="⬇️ Descargar Planilla TXT",
        data=txt_output,
        file_name=f"planilla_asopagos_{año}{mes:02d}.txt",
        mime="text/plain"
    )

    st.success(f"✅ Planilla generada ({len(df)} empleados)")
