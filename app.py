import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SiscoopWeb", page_icon="🚀", layout="centered")
st.title("🚀 SiscoopWeb - Generador Planilla ASOPAGOS")
st.subheader("Sube tu 'detalle pase.xlsx' y genera el TXT en un clic")

uploaded_file = st.file_uploader("Selecciona tu archivo detalle pase.xlsx / detalle.xls", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="detalle.rpt", header=9)
        df = df.dropna(subset=[df.columns[0]]).reset_index(drop=True)
        df = df.fillna(0)

        # Conversión ultra segura de valores numéricos
        vlr_pension = pd.to_numeric(df.iloc[:, 10], errors='coerce').fillna(0).astype(int)
        vlr_arp     = pd.to_numeric(df.iloc[:, 8],  errors='coerce').fillna(0).astype(int)
        vlr_caja    = pd.to_numeric(df.iloc[:, 12], errors='coerce').fillna(0).astype(int)

        st.success(f"✅ {len(df)} afiliados cargados correctamente")

        col1, col2 = st.columns(2)
        with col1:
            nit = st.text_input("NIT Empresa", "900452062")
            periodo = st.text_input("Periodo", "2026-032026-04")
        with col2:
            municipio = st.text_input("Municipio DANE", "41001")
            tipo_cot = st.selectbox("Tipo cotizante default", ["0100", "0103", "0104"], index=0)
            salario_min = st.number_input("Salario mínimo 2026", value=1750905)

        if st.button("🔥 GENERAR PLANILLA TXT", type="primary", use_container_width=True):
            with st.spinner("Generando archivo..."):
                lines = []
                header = f"0110001SION UCE                                                                                                                                                                                                NI{nit}       4E                    SCCF01     CCF01                                   14-4  {periodo}                    000470000014281000105"
                lines.append(header)

                for idx, row in df.iterrows():
                    seq = f"{idx+1:05d}"
                    num_doc = str(row.iloc[1]).strip()
                    nombre_completo = str(row.iloc[2]).strip()
                    partes = nombre_completo.split()
                    ap1 = (partes[0] if len(partes) > 0 else "").ljust(20)
                    ap2 = (partes[1] if len(partes) > 1 else "").ljust(20)
                    nom1 = (partes[2] if len(partes) > 2 else "").ljust(20)
                    nom2 = (" ".join(partes[3:]) if len(partes) > 3 else "").ljust(20)

                    eps = {"Nueva EPS": "EPS037", "SANITAS S.A.": "EPS005", "ASMET SALUD": "ESSC62", "MALLAMAS": "EPSIC5"}.get(str(row.iloc[6]).strip(), "EPS037")
                    ccf = str(row.iloc[12]).strip() if pd.notna(row.iloc[12]) else "CCF32"

                    p = vlr_pension.iloc[idx]
                    a = vlr_arp.iloc[idx]
                    c = vlr_caja.iloc[idx]

                    ibc = round(p / 0.16) if p > 0 else salario_min
                    ibc = max(ibc, salario_min)
                    tasa_arp = round(a / ibc, 5) if ibc > 0 else 0.00522

                    ibc_str = f"{int(ibc):09d}"
                    pen_str = f"{int(p):012d}"
                    arp_str = f"{int(a):012d}"
                    caja_str = f"{int(c):012d}"
                    tasa_str = f"{tasa_arp:.5f}"

                    aportes = f"3030303000{ibc_str}F00{ibc_str}001{ibc_str}001{ibc_str}0000001000.16000000{pen_str}000000000000000000000000{pen_str}000000000000000000000000000000000.04000000" \
                              f"057000000000000               000000000               0000000000.{tasa_str}000000000{arp_str}00.040000000001000.000000000000000.000000000000000.000000000000000.00000000000000"

                    linea = f"02{seq}CC{num_doc:<15}{tipo_cot:>4}  {municipio:5}{ap1}{ap2}{nom1}{nom2}00230301      {eps.ljust(10)}{ccf.ljust(10)}{aportes}                  S14-4  1                                                                                                                                                       000000000000          1949101"
                    linea = linea[:693].ljust(693)
                    lines.append(linea)

                txt_content = "\n".join(lines)
                st.download_button(
                    label="📥 DESCARGAR PLANILLA TXT",
                    data=txt_content,
                    file_name=f"planilla_asopagos_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                st.success("✅ ¡Planilla generada correctamente!")

    except Exception as e:
        st.error(f"Error: {str(e)}")

st.caption("SiscoopWeb © 2026 - Generador Planilla ASOPAGOS")
