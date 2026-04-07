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

# ====================== CARGA DE ARCHIVO ======================
uploaded_file = st.file_uploader("Subir archivo Excel 'Detalle Pase'", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    
    # Limpiar filas de títulos o totales
    df = df[~df.iloc[:, 0].astype(str).str.contains("FACTURA|SUBTOTAL|TOTAL|RESUMEN", na=False, case=False)]
    
    # ====================== CONVERSIONES SEGURAS ======================
    numeric_cols = ['N', 'salario', 'pension', 'salud', 'arp', 'caja']  
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # ====================== FECHA DE INGRESO desde COLUMNA F ======================
    # Columna F = índice 5 (0-based)
    df['fecha_ingreso'] = pd.to_datetime(df.iloc[:, 5], errors='coerce')
    
    # ====================== MAPPING EPS / CCF ======================
    # (tu mapping completo aquí - mantengo el mismo que ya tenías)
    eps_map = { ... }   # ← reemplaza con tu diccionario completo
    ccf_map = { ... }   # ← reemplaza con tu diccionario completo
    
    df['cod_eps'] = df['eps'].map(eps_map).fillna('999')
    df['cod_ccf'] = df['ccf'].map(ccf_map).fillna('999')
    
    # ====================== RISK MAP R1-R5 ======================
    risk_map = {
        'R1': {'tasa': 0.00522, 'actividad': '1949101'},
        'R2': {'tasa': 0.01044, 'actividad': '2329001'},
        'R3': {'tasa': 0.02436, 'actividad': '2329002'},
        'R4': {'tasa': 0.04440, 'actividad': '2329003'},
        'R5': {'tasa': 0.06960, 'actividad': '2329004'},
    }
    df['riesgo'] = df['riesgo'].str.upper().fillna('R1')
    df['tasa_arp'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['tasa'])
    df['cod_actividad'] = df['riesgo'].map(lambda r: risk_map.get(r, risk_map['R1'])['actividad'])
    
    # ====================== PENSIÓN (N = 0 → sin pensión) ======================
    df['pension'] = df.apply(lambda row: 0 if row['N'] == 0 else row['pension'], axis=1)
    
    # ====================== GENERAR TXT ======================
    def generar_planilla_txt(df, periodo):
        lineas = []
        for _, row in df.iterrows():
            # Solo poner fecha_ingreso si coincide con el periodo de pago
            if pd.notna(row['fecha_ingreso']) and row['fecha_ingreso'].to_period('M') == periodo.to_period('M'):
                fecha_ing_str = row['fecha_ingreso'].strftime('%Y%m%d')
            else:
                fecha_ing_str = ''
            
            # (aquí va tu formato exacto del TXT ASOPAGOS)
            linea = f"{row.get('tipo_doc','')},{row.get('numero','')},{row.get('nombre','')},{row['cod_eps']},{row['cod_ccf']},"
            linea += f"{row.get('salario',0):.0f},{row.get('pension',0):.0f},{row.get('salud',0):.0f},{row['tasa_arp']:.5f},"
            linea += f"{row['cod_actividad']},{fecha_ing_str},,"  # fecha_retiro vacío por ahora
            linea += f"30"  # días cotizados (ajusta si necesitas lógica más compleja)
            lineas.append(linea)
        return "\n".join(lineas)
    
    txt_output = generar_planilla_txt(df, periodo)
    
    # ====================== DESCARGA ======================
    st.download_button(
        label="⬇️ Descargar Planilla TXT",
        data=txt_output,
        file_name=f"planilla_asopagos_{año}{mes:02d}.txt",
        mime="text/plain"
    )
    
    st.success(f"✅ Planilla generada para periodo {mes:02d}/{año}")
    st.dataframe(df.head(10))  # vista previa
