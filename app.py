import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SiscoopWeb - Planilla ASOPAGOS", layout="wide")
st.title("🧾 Generador de Planilla ASOPAGOS Colombia")

# ====================== SELECTORES MANUALES INGRESO / RETIRO ======================
st.subheader("📅 Selector Manual de Ingreso y Retiro")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    fecha_ingreso_global = st.date_input("Fecha de Ingreso (global)", datetime.today())
with col2:
    fecha_retiro_global = st.date_input("Fecha de Retiro (opcional - global)", None)
with col3:
    aplicar_por_empleado = st.checkbox("Aplicar por empleado (usar columnas del Excel)", value=False)

# ====================== CARGA DE ARCHIVO ======================
uploaded_file = st.file_uploader("Subir archivo Excel 'Detalle Pase'", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)  # leer todo como string primero
    
    # Limpiar filas de títulos / subtotales (ej. "FACTURA PITALITO")
    df = df[~df.iloc[:, 0].astype(str).str.contains("FACTURA|SUBTOTAL|TOTAL|RESUMEN", na=False, case=False)]
    
    # ====================== CONVERSIONES SEGURAS (evita el error int/fillna) ======================
    numeric_cols = ['N', 'salario', 'pension', 'salud', 'arp', 'caja']  # ajusta según tus columnas reales
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # ====================== MAPPING EPS / CCF (ya tenías completo) ======================
    eps_map = { ... }   # ← tu mapping completo que ya tenías
    ccf_map = { ... }   # ← tu mapping completo que ya tenías
    # (mantengo el mismo que te pasé antes)
    
    df['cod_eps'] = df['eps'].map(eps_map).fillna('999')   # fallback
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
    
    # ====================== PENSIÓN (Columna N = 0 → sin pensión) ======================
    df['pension'] = df.apply(lambda row: 0 if row['N'] == 0 else row['pension'], axis=1)
    
    # ====================== APLICAR FECHAS INGRESO / RETIRO ======================
    if not aplicar_por_empleado:
        df['fecha_ingreso'] = fecha_ingreso_global
        df['fecha_retiro'] = fecha_retiro_global if fecha_retiro_global else pd.NaT
    # si está marcado "por empleado" se respetan las columnas del Excel (si existen)
    
    # Calcular días cotizados (ejemplo)
    df['dias_cotizados'] = 30  # valor por defecto mensual
    mask_retiro = df['fecha_retiro'].notna()
    if mask_retiro.any():
        df.loc[mask_retiro, 'dias_cotizados'] = (
            df.loc[mask_retiro, 'fecha_retiro'] - df.loc[mask_retiro, 'fecha_ingreso']
        ).dt.days
    
    # ====================== GENERAR TXT (lógica ASOPAGOS) ======================
    def generar_planilla_txt(df):
        lineas = []
        for _, row in df.iterrows():
            # formato según especificación ASOPAGOS / PILA
            linea = f"{row['tipo_doc']},{row['numero']},{row['nombre']},{row['cod_eps']},{row['cod_ccf']},"
            linea += f"{row['salario']:.0f},{row['pension']:.0f},{row['salud']:.0f},{row['tasa_arp']:.5f},"
            linea += f"{row['cod_actividad']},{row['fecha_ingreso'].strftime('%Y%m%d') if pd.notna(row['fecha_ingreso']) else ''},"
            linea += f"{row['fecha_retiro'].strftime('%Y%m%d') if pd.notna(row['fecha_retiro']) else ''},"
            linea += f"{int(row['dias_cotizados'])}"
            lineas.append(linea)
        return "\n".join(lineas)
    
    txt_output = generar_planilla_txt(df)
    
    # ====================== DESCARGA ======================
    st.download_button(
        label="⬇️ Descargar Planilla TXT",
        data=txt_output,
        file_name=f"planilla_asopagos_{datetime.today().strftime('%Y%m%d')}.txt",
        mime="text/plain"
    )
    
    st.success("✅ Planilla generada correctamente")
    st.dataframe(df.head(10))  # vista previa
