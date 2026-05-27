# Limpieza de archivo de Opiniones

Aplicación en Streamlit para limpiar archivos CSV o Excel descargados del sistema externo y generar un archivo compatible con la Google Sheet que alimenta BigQuery.

## Flujo operativo

1. Subir archivo original.
2. Procesar archivo.
3. Descargar CSV o Excel limpio.
4. Copiar filas limpias en Google Sheets.
5. BigQuery ejecuta el MERGE programado hacia `NativaOpiniones_BQ`.
6. Looker Studio se actualiza desde la tabla final.

## Archivos principales

- `app.py`: aplicación principal.
- `requirements.txt`: dependencias necesarias.
- `README.md`: documentación básica.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
