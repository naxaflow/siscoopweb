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
    docs_retiro = st.text_area(
        "Números de documento de los empleados que se retiran (uno por línea)",
        height=120,
        placeholder="12345678\n87654321\n..."
    )
    retiros_set = {x.strip() for x in docs_retiro.splitlines() if x.strip()}
else:
    fecha_retiro = None
    retiros_set = set()

# ====================== CARGA DE ARCHIVO ======================
uploaded_file = st.file_uploader("Subir archivo Excel 'Detalle Pase'", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    
    # Limpiar filas de títulos o totales
    df = df[~df.iloc[:, 0].astype(str).str.contains("FACTURA|SUBTOTAL|TOTAL|RESUMEN", na=False, case=False)]
    
    # ====================== DEBUG: COLUMNAS REALES ======================
    st.subheader("🔍 Columnas detectadas en tu Excel")
    st.write(list(df.columns))
    st.info("Copia aquí los nombres exactos de las columnas que corresponden a: eps, ccf, riesgo, numero, N (pensión), etc.")
    
    # ====================== CONVERSIONES SEGURAS ======================
    numeric_cols = ['N', 'salario', 'pension', 'salud', 'arp', 'caja']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # ====================== FECHA DE INGRESO (columna F) ======================
    if len(df.columns) > 5:
        df['fecha_ingreso'] = pd.to_datetime(df.iloc[:, 5], errors='coerce')
    else:
        df['fecha_ingreso'] = pd.NaT
    
    # ====================== MAPPING EPS / CCF ======================
    # (todavía con placeholders seguros)
    eps_map = { ... }   # ← tu mapping EPS completo
    ccf_map = { ... }   # ← tu mapping CCF completo
    
    df['cod_eps'] = df.get('eps', pd.Series(['999']*len(df))).map(eps_map).fillna('999')
    df['cod_ccf'] = df.get('ccf', pd.Series(['999']*len(df))).map(ccf_map).fillna('999')
    
    # ====================== RISK MAP R1-R5 (CORRECTO) ======================
    risk_map = {
        'R1': {'tasa': 0.00522, 'actividad': '1949101'},
        'R2': {'tasa': 0.01044, 'actividad': '2329001'},
        'R3': {'tasa': 0.02436, 'actividad': '3869201'},
        'R4': {'tasa': 0.0435,  'actividad': '4492301'},
        'R5': {'tasa': 0.0696,  'actividad': '5439003'},
    }
    
    riesgo_col = df.get('riesgo', pd.Series(['R1']*len(df)))
    df['riesgo'] = riesgo_col.str.upper().fillna('R1')
    df['tasa_arp'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['tasa'])
    df['cod_actividad'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['actividad'])
    
    # ====================== PENSIÓN (N = 0 → sin pensión) ======================
    if 'N' in df.columns:
        df['pension'] = df.apply(lambda row: 0 if row['N'] == 0 else row.get('pension', 0), axis=1)
    
    # ====================== GENERAR TXT ======================
    def generar_planilla_txt(df, periodo, fecha_retiro, retiros_set):
        lineas = []
        for _, row in df.iterrows():
            # Fecha ingreso solo si coincide con el periodo
            if pd.notna(row.get('fecha_ingreso')) and row['fecha_ingreso'].to_period('M') == periodo.to_period('M'):
                fecha_ing_str = row['fecha_ingreso'].strftime('%Y%m%d')
            else:
                fecha_ing_str = ''
            
            # Fecha retiro
            if fecha_retiro and str(row.get('numero', '')).strip() in retiros_set:
                fecha_ret_str = fecha_retiro.strftime('%Y%m%d')
            else:
                fecha_ret_str = ''
            
            linea = f"{row.get('tipo_doc','')},{row.get('numero','')},{row.get('nombre','')},{row.get('cod_eps','999')},{row.get('cod_ccf','999')},"
            linea += f"{row.get('salario',0):.0f},{row.get('pension',0):.0f},{row.get('salud',0):.0f},{row.get('tasa_arp',0):.5f},"
            linea += f"{row.get('cod_actividad','')},{fecha_ing_str},{fecha_ret_str},30"
            lineas.append(linea)
        return "\n".join(lineas)
    
    txt_output = generar_planilla_txt(df, periodo, fecha_retiro, retiros_set)
    
    # ====================== DESCARGA ======================
    st.download_button(
        label="⬇️ Descargar Planilla TXT",
        data=txt_output,
        file_name=f"planilla_asopagos_{año}{mes:02d}.txt",
        mime="text/plain"
    )
    
    st.success(f"✅ Planilla generada para periodo {mes:02d}/{año}")
    st.dataframe(df.head(10))
