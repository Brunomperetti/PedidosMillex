import streamlit as st
import pandas as pd
# import gspread # Ya no es necesario para acceso público vía CSV
# from oauth2client.service_account import ServiceAccountCredentials # Ya no es necesario
from datetime import datetime

# Configurar página
st.set_page_config(page_title="Pedidos Millex", layout="wide", page_icon="📦")
st.title("📦 Seguimiento de Pedidos - Millex")

# --- Autenticación y Conexión ---
# La función conectar_google_sheets ya no es necesaria porque leeremos el CSV directamente
# @st.cache_resource
# def conectar_google_sheets():
#     scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#     creds = ServiceAccountCredentials.from_json_keyfile_name(
#         "mi-app-python-2025-04-24-abc123456.json", scope # Ya no se usa el JSON
#     )
#     client = gspread.authorize(creds)
#     return client.open_by_key("1B7sG6DqaCBfMN0OJOr_juEJ0zJXTo46lLHykpe-OaJk")

# --- Definición de Estados ---
ESTADOS_PEDIDO = {
    "Sin definir": "📥 Nuevo Pedido",
    "Pendiente de autorizacion": "⏳ Nuevo Pedido",
    "Leido": "📦 Armando pedido",
    "En espera de pedido en sucursal de transporte": "🛒Pedido armado",
    "Se entrego al transporte": "🚚 En transporte"
    # Considera añadir un estado "✅ Entregado" si existe en tus datos
}

ESTADOS_PAGO = {
    "Sin definir": "⏳ Pendiente de Pago",
    "Pendiente: El pago se encuentra pendiente de acreditacion": "📞 Contactando cliente",
    "El pago fue aprobado y acreditado": "💰 Pagado",
    "El pago fue rechazado. El usuario puede intentar nuevamente": "❌ Rechazado"
}

# --- Cargar Datos COMPLETOS (Modificado para leer CSV público) ---
@st.cache_data(ttl=300) # Cacheamos los datos por 5 minutos (300 segundos)
def cargar_datos():
    try:
        # Construye la URL para descargar la hoja específica como CSV
        spreadsheet_id = "1B7sG6DqaCBfMN0OJOr_juEJ0zJXTo46lLHykpe-OaJk"
        sheet_gid = "1856455950" # ID de la hoja específica dentro del spreadsheet
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_gid}"

        # Lee el archivo CSV directamente desde la URL usando pandas
        df = pd.read_csv(csv_url)

        # --- Mismo procesamiento de datos que tenías ---

        # Eliminar filas completamente vacías (importante después de leer CSV)
        df.replace('', pd.NA, inplace=True) # Reemplaza strings vacíos con NA de pandas
        df.dropna(how='all', inplace=True)  # Elimina filas donde *todos* los valores son NA

        # Asegurar que las columnas clave existan antes de procesarlas
        if 'Fecha' in df.columns:
             # Convertir a string antes de reemplazar, por si acaso pandas infiere otro tipo
            df['Fecha_limpia'] = df['Fecha'].astype(str).str.replace(',', ' ').str.strip()

            # Intentar parsear con el formato específico. dayfirst=True es importante para D/M/A
            df['Fecha_datetime'] = pd.to_datetime(
                df['Fecha_limpia'],
                dayfirst=True,
                format='%d/%m/%Y %H:%M:%S', # Asegúrate que este formato coincida EXACTAMENTE
                errors='coerce' # Si no puede parsear, pone NaT (Not a Time)
            )

            # Si hay fechas sin parsear, mostrar advertencia
            if df['Fecha_datetime'].isna().any():
                problematic_dates = df[df['Fecha_datetime'].isna()]['Fecha'].unique()
                st.warning(f"Advertencia: No se pudieron convertir {len(problematic_dates)} fechas al formato esperado (D/M/AAAA H:M:S). Ejemplos problemáticos: {problematic_dates[:3]}")

            # Mantener columna original para visualización si es necesario
            df['Fecha_original'] = df['Fecha']
        else:
            st.warning("La columna 'Fecha' no se encontró en la hoja de cálculo.")
            # Crear columnas placeholder si no existen para evitar errores posteriores
            df['Fecha_datetime'] = pd.NaT
            df['Fecha_original'] = ''

        # Validar existencia de otras columnas importantes antes de usarlas
        if 'Estado de Pedido' not in df.columns:
            st.warning("La columna 'Estado de Pedido' no se encontró.")
            df['Estado de Pedido'] = 'Sin definir' # Valor por defecto
        if 'Estado de Pago' not in df.columns:
            st.warning("La columna 'Estado de Pago' no se encontró.")
            df['Estado de Pago'] = 'Sin definir' # Valor por defecto
        if 'Código' not in df.columns:
            st.warning("La columna 'Código' no se encontró.")
            df['Código'] = '' # Valor por defecto
        if 'Cliente' not in df.columns:
            st.warning("La columna 'Cliente' no se encontró.")
            df['Cliente'] = 'N/A' # Valor por defecto
        if 'Total' not in df.columns:
            st.warning("La columna 'Total' no se encontró.")
            df['Total'] = 0 # Valor por defecto
        if 'Tipo' not in df.columns:
            st.warning("La columna 'Tipo' no se encontró.")
            df['Tipo'] = 'N/A' # Valor por defecto

        return df

    except pd.errors.EmptyDataError:
        st.error("Error: La hoja de cálculo parece estar vacía o no se pudo leer correctamente.")
        return pd.DataFrame()
    except Exception as e:
        # Muestra un error más detallado si falla la carga/lectura del CSV
        st.error(f"Error al cargar datos desde Google Sheets (CSV público): {str(e)}")
        return pd.DataFrame() # Devuelve un DataFrame vacío en caso de error

# --- Interfaz Principal ---
def main():
    df = cargar_datos()

    if df.empty:
        st.warning("No se encontraron datos o hubo un error al cargar. Verifica la URL de Google Sheets y su configuración de permisos (debe ser público).")
        return # Detiene la ejecución si no hay datos

    # Mostrar conteo real de pedidos
    st.markdown(f"**Total de pedidos cargados:** {len(df)}")

    # --- Sidebar con Filtros Simplificados ---
    with st.sidebar:
        st.header("Filtros")

        # Convertir estados a formato visual ANTES de crear los filtros
        # Usamos .astype(str).strip() para manejar posibles valores nulos o espacios
        if 'Estado de Pedido' in df.columns:
            df['Estado_Pedido_Visual'] = df['Estado de Pedido'].astype(str).str.strip().apply(
                lambda x: ESTADOS_PEDIDO.get(x, "❓ Desconocido: " + x)) # Mapea o indica si no existe
        else:
            df['Estado_Pedido_Visual'] = "❓ No disponible"

        if 'Estado de Pago' in df.columns:
             df['Estado_Pago_Visual'] = df['Estado de Pago'].astype(str).str.strip().apply(
                lambda x: ESTADOS_PAGO.get(x, "❓ Desconocido: " + x)) # Mapea o indica si no existe
        else:
            df['Estado_Pago_Visual'] = "❓ No disponible"


        # Filtros por estado (usando las opciones de los diccionarios)
        # Obtenemos las opciones únicas de los estados VISUALES presentes en los datos
        opciones_pedido_unicas = ["Todos"] + list(df['Estado_Pedido_Visual'].unique())
        filtro_pedido = st.selectbox("Estado del Pedido", opciones_pedido_unicas, index=0)

        opciones_pago_unicas = ["Todos"] + list(df['Estado_Pago_Visual'].unique())
        filtro_pago = st.selectbox("Estado del Pago", opciones_pago_unicas, index=0)

    # --- Aplicar Filtros ---
    df_filtrado = df.copy()

    # Aplicar filtros de estado (ya tenemos las columnas visuales)
    if filtro_pedido != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pedido_Visual'] == filtro_pedido]

    if filtro_pago != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pago_Visual'] == filtro_pago]

    # --- Mostrar Estadísticas ---
    st.subheader("📊 Resumen de Pedidos")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pedidos filtrados", len(df_filtrado))
    with col2:
        # Contar basados en el inicio del estado visual
        nuevos_pedidos = len(df_filtrado[df_filtrado['Estado_Pedido_Visual'].str.startswith(('⏳', '📥'))])
        st.metric("Nuevos pedidos", nuevos_pedidos)
    with col3:
        # Asegúrate de que "✅ Entregado" esté definido en ESTADOS_PEDIDO o ajusta aquí
        entregados = len(df_filtrado[df_filtrado['Estado_Pedido_Visual'] == "✅ Entregado"])
        st.metric("Entregados", entregados)

    # --- Mostrar Tabla de Pedidos COMPLETA ---
    st.subheader(f"📋 Listado de Pedidos ({len(df_filtrado)} registros)")

    # Ordenar por fecha descendente (si existe la columna parseada)
    if 'Fecha_datetime' in df_filtrado.columns and not df_filtrado['Fecha_datetime'].isna().all():
        df_filtrado = df_filtrado.sort_values('Fecha_datetime', ascending=False, na_position='last')
    elif 'Fecha_original' in df_filtrado.columns:
         # Ordenar por la fecha original como texto si no se pudo parsear
         df_filtrado = df_filtrado.sort_values('Fecha_original', ascending=False, na_position='last')


    # Definir columnas a mostrar (asegúrate que existan)
    columnas_mostrar_base = [
        'Código',
        'Fecha_original', # Mostrar la fecha original leída
        'Cliente',
        'Total',
        'Tipo',
        'Estado_Pago_Visual',
        'Estado_Pedido_Visual',
        'Confirmación', # Verifica si estas columnas existen en tu CSV
        'Reclamo',      # Verifica si estas columnas existen en tu CSV
        'factura'       # Verifica si estas columnas existen en tu CSV
    ]

    # Filtrar solo las columnas que realmente existen en el DataFrame
    columnas_existentes = [col for col in columnas_mostrar_base if col in df_filtrado.columns]

    # Si faltan columnas importantes, informa al usuario
    columnas_faltantes = [col for col in columnas_mostrar_base if col not in df_filtrado.columns]
    if columnas_faltantes:
        st.warning(f"Las siguientes columnas no se encontraron en los datos y no se mostrarán: {', '.join(columnas_faltantes)}")


    st.dataframe(
        df_filtrado[columnas_existentes], # Muestra solo las columnas existentes
        use_container_width=True,
        height=600,
        hide_index=True,
        # Configuración de columnas (adapta según las columnas existentes)
        column_config={
            "Fecha_original": st.column_config.TextColumn("Fecha"), # Renombrar para claridad
            "Total": st.column_config.NumberColumn("Total", format="$ %(value)d"), # Formato de moneda si aplica
            "Estado_Pago_Visual": st.column_config.TextColumn("Estado Pago"),
            "Estado_Pedido_Visual": st.column_config.TextColumn("Estado Pedido"),
            # Añade config para las otras columnas si es necesario
             "Confirmación": st.column_config.TextColumn("Confirmación"),
             "Reclamo": st.column_config.TextColumn("Reclamo"),
             "factura": st.column_config.TextColumn("Factura")
        }
    )

    # --- Botón de Refrescar ---
    if st.button("🔄 Refrescar Datos"):
        st.cache_data.clear() # Limpia la caché de datos
        st.rerun() # Vuelve a ejecutar el script desde el principio

if __name__ == "__main__":
    main()