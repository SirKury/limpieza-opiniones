import streamlit as st
import pandas as pd
import io
import unicodedata
from datetime import datetime

st.set_page_config(
    page_title="Limpieza de CSV - Opiniones",
    page_icon="📄",
    layout="wide"
)

EXPECTED_COLUMNS = [
    "marca_temporal",
    "numero_de_codigo",
    "hora_recepcion_de_caso",
    "tipo_de_opinion",
    "institucion",
    "establecimiento",
    "nombre_completo_paciente",
    "dui_del_paciente",
    "telefono",
    "correo_electronico",
    "opinion_del_paciente",
    "opinion_del_paciente_en_el_sitio",
    "pasa_a_direccion_respectiva",
    "tecnico_que_toma_el_caso",
    "nombre_del_recurso_reportado",
    "respuesta_tecnica_dimes",
    "atestado_sis",
    "informacion_verificable",
    "resolucion_del_caso_por_direccion",
    "fecha_de_cita_por_direccion",
    "atestados_direccion_comprobante",
    "resolucion_de_caso_por_isss",
    "seguimiento_de_caso",
    "solo_dimes",
    "caso_fraudulento"
]

RENAME_MAP = {
    "nombre_completo_del_paciente": "nombre_completo_paciente",
    "fecha_de_cita_direccion": "fecha_de_cita_por_direccion"
}

COLUMNS_TO_DROP = [
    "minsal",
    "solicitud_de_anonimato_segun_sitio",
    "archivo_adjunto_paciente",
    "establecimiento_estandarizado"
]


def normalize_column_name(col: str) -> str:
    col = str(col).strip().lower()
    col = unicodedata.normalize("NFD", col)
    col = "".join(ch for ch in col if unicodedata.category(ch) != "Mn")
    col = col.replace("/", "_").replace("-", "_").replace(" ", "_")
    col = "".join(ch for ch in col if ch.isalnum() or ch == "_")

    while "__" in col:
        col = col.replace("__", "_")

    return col.strip("_")


def normalize_datetime_latam(series: pd.Series) -> pd.Series:
    """
    Convierte fechas al formato final:
    día/mes/año hora:minuto:segundo

    Corrige casos donde el archivo original viene como:
    mes/día/año hora:minuto:segundo

    Ejemplo:
    06/02/2026 17:15:53  ->  02/06/2026 17:15:53
    """

    dt = pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=False
    )

    return dt.dt.strftime("%d/%m/%Y %H:%M:%S")
    # Devuelve el formato requerido: dd/mm/yyyy HH:MM:SS
    return dt.dt.strftime("%d/%m/%Y %H:%M:%S")

def read_uploaded_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        try:
            return pd.read_csv(uploaded_file, dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, dtype=str, encoding="latin1")

    if file_name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file, dtype=str)

    raise ValueError("Formato no permitido. Use CSV o XLSX.")


def clean_dataframe(df: pd.DataFrame):
    original_rows = len(df)
    original_columns = list(df.columns)

    # Normalizar nombres de columnas
    df.columns = [normalize_column_name(c) for c in df.columns]

    # Renombrar columnas conocidas
    df.rename(columns=RENAME_MAP, inplace=True)

    # Eliminar columnas no necesarias
    df.drop(columns=[c for c in COLUMNS_TO_DROP if c in df.columns], inplace=True)

    # Agregar columnas faltantes
    missing_columns = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    for col in missing_columns:
        df[col] = pd.NA

    # Detectar columnas extra antes de ordenar
    extra_columns = [c for c in df.columns if c not in EXPECTED_COLUMNS]

    # Ordenar columnas finales
    df = df[EXPECTED_COLUMNS]

    # Limpiar espacios en blanco
    for col in df.columns:
        df[col] = df[col].astype("string").str.strip()

    # Convertir fechas al formato día/mes/año hora:minuto:segundo
    date_columns = [
        "marca_temporal",
        "hora_recepcion_de_caso",
        "fecha_de_cita_por_direccion"
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = normalize_datetime_latam(df[col])

    # Reemplazar valores vacíos o inválidos
    df = df.replace({
        "nan": pd.NA,
        "NaN": pd.NA,
        "None": pd.NA,
        "none": pd.NA,
        "NaT": pd.NA,
        "": pd.NA
    })

    # Eliminar filas sin número de código
    before_filter = len(df)
    df = df[df["numero_de_codigo"].notna()]
    df = df[df["numero_de_codigo"].astype(str).str.strip() != ""]
    removed_without_code = before_filter - len(df)

    # Detectar códigos duplicados
    duplicated_codes = df["numero_de_codigo"].astype(str).str.strip().str.upper().duplicated().sum()

    summary = {
        "filas_originales": original_rows,
        "filas_finales": len(df),
        "filas_sin_codigo_eliminadas": removed_without_code,
        "columnas_originales": len(original_columns),
        "columnas_finales": len(df.columns),
        "columnas_faltantes_agregadas": missing_columns,
        "columnas_extra_detectadas": extra_columns,
        "codigos_duplicados_detectados": int(duplicated_codes)
    }

    return df, summary


def dataframe_to_csv_bytes(df: pd.DataFrame):
    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue().encode("utf-8-sig")


def dataframe_to_excel_bytes(df: pd.DataFrame):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Opiniones_limpio")
    return output.getvalue()


st.title("📄 Limpieza de archivo para Opiniones")
st.caption("Herramienta para generar archivo limpio compatible con Google Sheets, BigQuery y Looker Studio.")

st.markdown(
    """
    ### Instrucciones
    
    1. Suba el archivo original descargado del sistema.
    2. Presione **Procesar archivo**.
    3. Descargue el archivo limpio.
    4. Copie las filas limpias en la Google Sheet desde la fila 2.
    5. No modifique los encabezados de la Google Sheet.
    """
)

uploaded_file = st.file_uploader(
    "Subir archivo original",
    type=["csv", "xlsx"]
)

if uploaded_file is not None:
    try:
        df_original = read_uploaded_file(uploaded_file)

        st.success("Archivo recibido correctamente.")

        col1, col2, col3 = st.columns(3)
        col1.metric("Filas originales", f"{len(df_original):,}")
        col2.metric("Columnas originales", f"{len(df_original.columns):,}")
        col3.metric("Archivo", uploaded_file.name)

        with st.expander("Vista previa del archivo original"):
            st.dataframe(df_original.head(20), use_container_width=True)

        if st.button("Procesar archivo", type="primary"):
            df_clean, summary = clean_dataframe(df_original.copy())

            st.success("Archivo procesado correctamente.")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Filas finales", f"{summary['filas_finales']:,}")
            c2.metric("Columnas finales", f"{summary['columnas_finales']:,}")
            c3.metric("Sin código eliminadas", f"{summary['filas_sin_codigo_eliminadas']:,}")
            c4.metric("Códigos duplicados", f"{summary['codigos_duplicados_detectados']:,}")

            if summary["columnas_faltantes_agregadas"]:
                st.warning("Columnas faltantes agregadas vacías:")
                st.write(summary["columnas_faltantes_agregadas"])

            if summary["columnas_extra_detectadas"]:
                st.info("Columnas extra detectadas y excluidas del archivo final:")
                st.write(summary["columnas_extra_detectadas"])

            st.subheader("Vista previa del archivo limpio")
            st.dataframe(df_clean.head(50), use_container_width=True)

            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

            csv_bytes = dataframe_to_csv_bytes(df_clean)
            excel_bytes = dataframe_to_excel_bytes(df_clean)

            st.download_button(
                label="⬇️ Descargar CSV limpio",
                data=csv_bytes,
                file_name=f"opiniones_limpio_{fecha}.csv",
                mime="text/csv"
            )

            st.download_button(
                label="⬇️ Descargar Excel limpio",
                data=excel_bytes,
                file_name=f"opiniones_limpio_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.info(
                """
                Recomendación operativa:
                
                - Abra el archivo limpio.
                - Copie únicamente las filas de datos.
                - Pegue en la Google Sheet desde la fila 2.
                - Verifique que no haya dejado filas antiguas mezcladas.
                - Realice este proceso antes de la hora programada de BigQuery.
                """
            )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
else:
    st.info("Suba un archivo CSV o Excel para comenzar.")
