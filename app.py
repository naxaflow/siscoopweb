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
    df = df[~df.iloc[:, 0].astype(str).str.contains("FACTURA|SUBTOTAL|TOTAL|RESUMEN", na=False, case=False)]
    
    # Renombrar columnas para trabajar fácilmente
    df.columns = [f"col_{i}" for i in range(len(df.columns))]
    
    # ====================== MAPPING EPS (oficial ASOPAGOS) ======================
    eps_map = {
        'Nueva EPS': '050',
        'SANITAS S.A.': '053',
        'ASMET SALUD': '054',
        'Positiva': '058',
        'MALLAMAS': '059',
        'COLPATRIA ARL': '999',   # ARP no es EPS
        '': '999'
    }
    
    # ====================== MAPPING CCF (oficial ASOPAGOS) ======================
    ccf_map = {
        'CCF32': '32',
        'CCF13': '13',
        '0': '00',
        '': '00'
    }
    
    # ====================== ASIGNACIÓN AUTOMÁTICA DE COLUMNAS (según tu archivo) ======================
    df['numero'] = df['col_1'].astype(str).str.strip().str.replace(',', '')
    df['nombre'] = df['col_2'].astype(str).str.strip()
    df['eps']    = df['col_6'].astype(str).str.strip()
    df['ccf']    = df['col_12'].astype(str).str.strip()
    df['riesgo'] = df[df.columns[-1]].astype(str).str.strip()   # última columna = R1/R2/R3...
    
    # ====================== CONVERSIONES NUMÉRICAS ======================
    for c in ['col_9', 'col_17', 'col_11', 'col_7']:   # N, Salario, Pensión, Salud
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    # ====================== FECHA INGRESO ======================
    df['fecha_ingreso'] = pd.to_datetime(df['col_5'], errors='coerce')
    
    # ====================== APLICAR MAPPINGS ======================
    df['cod_eps'] = df['eps'].map(eps_map).fillna('999')
    df['cod_ccf'] = df['ccf'].map(ccf_map).fillna('00')
    
    # ====================== RISK MAP (CORRECTO) ======================
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
    
    # ====================== PENSIÓN (Columna N = 0 → sin pensión) ======================
    df['pension'] = df.apply(lambda row: 0 if row['col_9'] == 0 else row['col_11'], axis=1)
    
    # ====================== GENERAR TXT ======================
    def generar_planilla_txt(df, periodo, fecha_retiro, retiros_set):
        lineas = []
        for _, row in df.iterrows():
            fecha_ing_str = row['fecha_ingreso'].strftime('%Y%m%d') if pd.notna(row['fecha_ingreso']) and row['fecha_ingreso'].to_period('M') == periodo.to_period('M') else ''
            fecha_ret_str = fecha_retiro.strftime('%Y%m%d') if fecha_retiro and str(row['numero']).strip() in retiros_set else ''
            
            linea = f"{row.get('tipo_doc','')},{row['numero']},{row['nombre']},{row['cod_eps']},{row['cod_ccf']},"
            linea += f"{row['col_17']:.0f},{row['pension']:.0f},{row['col_7']:.0f},{row['tasa_arp']:.5f},"
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
    
    st.success(f"✅ Planilla generada correctamente para {mes:02d}/{año}")
    st.dataframe(df.head(8))
