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
        
        # Limpieza
        df = df.dropna(subset=[df.columns[0]]).reset_index(drop=True)
        df = df[~df.iloc[:, 0].astype(str).str.contains("F3|FACTURA|Subtotales|Subtotales>>>|Vlr Total", case=False, na=False)]
        df = df.fillna(0)

        # Mapping COMPLETO de EPS/CCF (de tu imagen)
        eps_map = {
            "COMFENALCO VALLE": "CCF56", "EPS-S COMF HUILA": "CCF2", "SANITAS S.A.": "EPS005",
            "ALIANSALUD EPS S.A.": "EPS001", "COLMEDICA E.P.S.": "EPS001", "SALUD TOTAL E.P.S.": "EPS002",
            "CAFESALUD E.P.S. S.A.": "EPS003", "MIN002": "MIN002", "COMPENSAR E.P.S": "EPS008",
            "COMPENSAR-EPS": "EPS008", "EPS SURA": "EPS010", "SUSALUD E.P.S.": "EPS010",
            "SALUDCOOP E.P.S.": "EPS013", "HUMANAVIR E.P.S.": "EPS014", "COOMEVA E.P.S.": "EPS016",
            "FAMISANAR LTDA": "EPS017", "S.O.S": "EPS018", "CRUZ BLANCA E.P.S. S.A.": "EPS023",
            "SALUDVIDA": "EPS033", "Nueva EPS": "EPS037", "golden group eps": "EPS039",
            "COOSALUD": "EPS042", "MEDIMAS E.P.S. S.A.": "EPS044", "MEDIMAS SUBSIDIADA": "EPS045",
            "CAFESALUD SUBSIDIADA": "EPSC02", "EPS-S CONVIDA": "EPSC3", "CAPITAL SALUD EPSS SA": "EPSC3",
            "ASOCIACION INDIGENAS DEL CAUCA": "EPSIC3", "CAFESALUD SUBSIDIADA": "EPSS09",
            "EPS-S EMSSANAR": "ESSC18", "COOSALUD": "ESSC24", "COMPARTA EPS": "ESSC33",
            "Asmet Salud EPS": "ESSC62", "EPS ECOOPSOS S.A.S": "ESSC91", "MIN002 - ADRES": "MIN002"
        }

        # Riesgo → Tasa ARP + Código Actividad
        risk_map = {
            "R1": {"tasa": 0.00522, "actividad": "1949101"},
            "R2": {"tasa": 0.01044, "actividad": "2329001"},
            "R3": {"tasa": 0.02436, "actividad": "3869201"},
            "R4": {"tasa": 0.04350, "actividad": "4492301"},
            "R5": {"tasa": 0.06960, "actividad": "5439003"}
        }

        st.success(f"✅ {len(df)} afiliados válidos cargados")

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

                    eps_name = str(row.iloc[6]).strip()
                    eps = eps_map.get(eps_name, "EPS037")
                    ccf = str(row.iloc[12]).strip() if pd.notna(row.iloc[12]) else "CCF32"

                    vlr_pension = pd.to_numeric(row.iloc[10], errors='coerce').fillna(0).astype(int)
                    vlr_arp     = pd.to_numeric(row.iloc[8],  errors='coerce').fillna(0).astype(int)
                    vlr_caja    = pd.to_numeric(row.iloc[12], errors='coerce').fillna(0).astype(int)

                    # Riesgo columna Y (índice 24)
                    riesgo = str(row.iloc[24]).strip().upper()
                    risk_info = risk_map.get(riesgo, {"tasa": 0.00522, "actividad": "1949101"})
                    tasa_arp = risk_info["tasa"]
                    actividad = risk_info["actividad"]

                    ibc = round(vlr_pension / 0.16) if vlr_pension > 0 else salario_min
                    ibc = max(ibc, salario_min)

                    ibc_str = f"{int(ibc):09d}"
                    pen_str = f"{int(vlr_pension):012d}"
                    arp_str = f"{int(vlr_arp):012d}"
                    caja_str = f"{int(vlr_caja):012d}"
                    tasa_str = f"{tasa_arp:.5f}"

                    aportes = f"3030303000{ibc_str}F00{ibc_str}001{ibc_str}001{ibc_str}0000001000.16000000{pen_str}000000000000000000000000{pen_str}000000000000000000000000000000000.04000000" \
                              f"057000000000000               000000000               0000000000.{tasa_str}000000000{arp_str}00.040000000001000.000000000000000.000000000000000.000000000000000.00000000000000"

                    linea = f"02{seq}CC{num_doc:<15}{tipo_cot:>4}  {municipio:5}{ap1}{ap2}{nom1}{nom2}00230301      {eps.ljust(10)}{ccf.ljust(10)}{aportes}                  S14-4  1                                                                                                                                                       000000000000          {actividad}"
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
