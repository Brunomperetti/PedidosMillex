import streamlit as st
import pandas as pd
# import gspread # Ya no es necesario para acceso público vía CSV
# from oauth2client.service_account import ServiceAccountCredentials # Ya no es necesario
from datetime import datetime
import traceback # Añadir por si acaso para errores inesperados

# Configurar página
st.set_page_config(page_title="Pedidos Millex", layout="wide", page_icon="📦")
st.title("📦 Seguimiento de Pedidos - Millex")

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

# --- Cargar Datos COMPLETOS (Modificado para leer CSV público y corregir fechas) ---
@st.cache_data(ttl=300) # Cacheamos los datos por 5 minutos (300 segundos)
def cargar_datos():
    try:
        # Construye la URL para descargar la hoja específica como CSV
        spreadsheet_id = "1B7sG6DqaCBfMN0OJOr_juEJ0zJXTo46lLHykpe-OaJk"
        sheet_gid = "1856455950" # ID de la hoja específica dentro del spreadsheet
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_gid}"
        st.info(f"Cargando datos desde: {csv_url}") # Info para debugging

        # Lee el archivo CSV directamente desde la URL usando pandas
        # Especificar dtype para columnas potencialmente problemáticas
        try:
            df = pd.read_csv(csv_url, dtype={'Fecha': str, 'Código': str}) # Lee fecha y código como texto inicialmente
        except Exception as read_csv_error:
             st.error(f"Error al descargar o leer el CSV desde Google Sheets: {read_csv_error}")
             st.error(f"URL intentada: {csv_url}")
             # Intenta mostrar más detalles si es un error HTTP
             if hasattr(read_csv_error, 'code'):
                 st.error(f"Código de error HTTP: {read_csv_error.code}")
             if hasattr(read_csv_error, 'reason'):
                 st.error(f"Razón del error HTTP: {read_csv_error.reason}")
             return pd.DataFrame()


        st.success(f"Datos leídos, {len(df)} filas encontradas inicialmente.")

        # Eliminar filas completamente vacías (importante después de leer CSV)
        df.replace('', pd.NA, inplace=True) # Reemplaza strings vacíos con NA de pandas
        original_rows = len(df)
        df.dropna(how='all', inplace=True)  # Elimina filas donde *todos* los valores son NA
        if len(df) < original_rows:
            st.write(f"Nota: Se eliminaron {original_rows - len(df)} filas completamente vacías.")

        # --- Procesamiento de Fechas (Corregido) ---
        if 'Fecha' in df.columns:
            # Limpieza previa (opcional si pd.to_datetime ya maneja bien los formatos)
            # df['Fecha_limpia'] = df['Fecha'].astype(str).str.replace(',', ' ').str.strip() # Podrías necesitarla si hay comas extrañas

            # --- MODIFICACIÓN PRINCIPAL AQUÍ ---
            # Quita el parámetro 'format' y confía en la inferencia de pandas con dayfirst=True
            st.write("Intentando convertir columna 'Fecha' a datetime...")
            df['Fecha_datetime'] = pd.to_datetime(
                df['Fecha'], # Usar la columna original (leída como str)
                dayfirst=True, # Ayuda a interpretar D/M/AAAA
                errors='coerce' # Si falla, pone NaT
            )
            # --- FIN DE LA MODIFICACIÓN ---

            # Verificar cuántas fechas fallaron y mostrar advertencia si es necesario
            fechas_invalidas = df['Fecha_datetime'].isna()
            num_invalidas = fechas_invalidas.sum()

            if num_invalidas > 0:
                problematic_examples = df.loc[fechas_invalidas, 'Fecha'].unique()
                st.warning(
                    f"Advertencia: {num_invalidas} de {len(df)} entradas en la columna 'Fecha' "
                    f"no pudieron ser interpretadas como fechas/horas válidas. "
                    f"Ejemplos de valores problemáticos: {problematic_examples[:5]}" # Muestra hasta 5 ejemplos
                )
            else:
                 st.write("✅ Conversión de fechas realizada con éxito.")

            # Mantener columna original para visualización (ya la leímos como string)
            df['Fecha_original'] = df['Fecha']
        else:
            st.warning("La columna 'Fecha' no se encontró en la hoja de cálculo.")
            # Crear columnas placeholder si no existen para evitar errores posteriores
            df['Fecha_datetime'] = pd.NaT
            df['Fecha_original'] = ''

        # --- Validaciones de otras columnas (como las tenías) ---
        columnas_a_validar = {
            'Estado de Pedido': 'Sin definir',
            'Estado de Pago': 'Sin definir',
            'Código': '',
            'Cliente': 'N/A',
            'Total': 0,
            'Tipo': 'N/A',
            'Confirmación': '', # Añade las columnas opcionales aquí también
            'Reclamo': '',
            'factura': ''
        }
        for col, default_value in columnas_a_validar.items():
            if col not in df.columns:
                st.warning(f"La columna '{col}' no se encontró. Se creará con valor por defecto.")
                df[col] = default_value
            else:
                 # Opcional: Rellenar valores nulos en columnas existentes si es necesario
                 # df[col].fillna(default_value, inplace=True)
                 pass # O dejar los nulos si prefieres manejarlos después

        # Convertir 'Total' a numérico si existe, manejando errores
        if 'Total' in df.columns:
             # Limpiar formato de moneda antes de convertir (ejemplo: quitar '$' y '.')
             # Esto depende MUCHO de cómo esté formateado en el CSV
             # df['Total'] = df['Total'].astype(str).str.replace(r'[$.]', '', regex=True).str.replace(',', '.', regex=False) # Ejemplo limpieza
             df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0) # Convertir a número, poner 0 si falla


        st.success("Procesamiento inicial de datos completado.")
        return df

    except pd.errors.EmptyDataError:
        st.error("Error: La hoja de cálculo parece estar vacía o no se pudo leer correctamente después del encabezado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error inesperado al cargar o procesar datos: {str(e)}")
        st.error("--- Traceback ---")
        st.text(traceback.format_exc()) # Muestra el traceback en Streamlit
        st.error("-----------------")
        return pd.DataFrame() # Devuelve un DataFrame vacío en caso de error grave

# --- Interfaz Principal ---
def main():
    df = cargar_datos()

    if df.empty:
        st.warning("No se pudieron cargar los datos para mostrar. Verifica los mensajes de error anteriores.")
        # Podrías añadir un botón para reintentar la carga aquí
        if st.button("🔄 Reintentar Carga"):
             st.cache_data.clear()
             st.rerun()
        return # Detiene la ejecución si no hay datos

    # Mostrar conteo real de pedidos
    st.markdown(f"**Total de pedidos cargados:** {len(df)}")

    # --- Sidebar con Filtros Simplificados ---
    with st.sidebar:
        st.header("Filtros")

        # Crear columnas visuales DESPUÉS de cargar y ANTES de filtrar/mostrar
        # Usamos .fillna('').astype(str).strip() para manejo robusto
        if 'Estado de Pedido' in df.columns:
            df['Estado_Pedido_Visual'] = df['Estado de Pedido'].fillna('').astype(str).str.strip().apply(
                lambda x: ESTADOS_PEDIDO.get(x, f"❓ {x}" if x else "❓ Vacío")
            )
        else:
            df['Estado_Pedido_Visual'] = "❓ No disponible"

        if 'Estado de Pago' in df.columns:
            df['Estado_Pago_Visual'] = df['Estado de Pago'].fillna('').astype(str).str.strip().apply(
                 lambda x: ESTADOS_PAGO.get(x, f"❓ {x}" if x else "❓ Vacío")
            )
        else:
            df['Estado_Pago_Visual'] = "❓ No disponible"


        # Filtros usando las opciones únicas de los estados VISUALES
        opciones_pedido_unicas = ["Todos"] + sorted(list(df['Estado_Pedido_Visual'].unique()))
        filtro_pedido = st.selectbox("Estado del Pedido", opciones_pedido_unicas, index=0)

        opciones_pago_unicas = ["Todos"] + sorted(list(df['Estado_Pago_Visual'].unique()))
        filtro_pago = st.selectbox("Estado del Pago", opciones_pago_unicas, index=0)

    # --- Aplicar Filtros ---
    # Importante: Filtrar ANTES de calcular métricas o mostrar tabla
    df_filtrado = df.copy() # Copiar después de añadir columnas visuales

    if filtro_pedido != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pedido_Visual'] == filtro_pedido]

    if filtro_pago != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pago_Visual'] == filtro_pago]

    # --- Mostrar Estadísticas (basadas en df_filtrado) ---
    st.subheader("📊 Resumen de Pedidos (Filtrados)")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pedidos Mostrados", len(df_filtrado)) # Ahora refleja los filtros
    with col2:
        # Contar basados en el inicio del estado visual EN LOS DATOS FILTRADOS
        nuevos_pedidos = df_filtrado['Estado_Pedido_Visual'].str.startswith(('⏳', '📥')).sum()
        st.metric("Nuevos pedidos", nuevos_pedidos)
    with col3:
        # Asegúrate de que "✅ Entregado" esté definido en ESTADOS_PEDIDO o ajusta aquí
        entregados = (df_filtrado['Estado_Pedido_Visual'] == "🚚 En transporte").sum() # Ejemplo, ajusta al estado final real
        st.metric("En transporte", entregados) # O "Entregados" si tienes ese estado


    # --- Mostrar Tabla de Pedidos (basada en df_filtrado) ---
    st.subheader(f"📋 Listado de Pedidos ({len(df_filtrado)} registros)")

    # Ordenar df_filtrado por fecha descendente
    if 'Fecha_datetime' in df_filtrado.columns and not df_filtrado['Fecha_datetime'].isna().all():
        df_filtrado_ordenado = df_filtrado.sort_values('Fecha_datetime', ascending=False, na_position='last')
    elif 'Fecha_original' in df_filtrado.columns:
         # Ordenar por la fecha original como texto si no se pudo parsear bien
         df_filtrado_ordenado = df_filtrado.sort_values('Fecha_original', ascending=False, na_position='last')
    else:
         df_filtrado_ordenado = df_filtrado # No ordenar si no hay columna de fecha


    # Definir columnas a mostrar (verifica que existan en df_filtrado_ordenado)
    columnas_mostrar_base = [
        'Código',
        'Fecha_original', # Mostrar la fecha original leída
        'Cliente',
        'Total',
        'Tipo',
        'Estado_Pago_Visual',
        'Estado_Pedido_Visual',
        'Confirmación',
        'Reclamo',
        'factura'
    ]

    # Filtrar solo las columnas que realmente existen en el DataFrame ordenado
    columnas_existentes = [col for col in columnas_mostrar_base if col in df_filtrado_ordenado.columns]

    # Si faltan columnas importantes, informa al usuario (ya se hizo en cargar_datos)
    # columnas_faltantes = [col for col in columnas_mostrar_base if col not in df_filtrado_ordenado.columns]
    # if columnas_faltantes:
    #     st.warning(f"Columnas no encontradas para mostrar: {', '.join(columnas_faltantes)}")


    # Configuración de columnas para st.dataframe
    # Crear dinámicamente basado en columnas existentes
    config_columnas = {
        "Fecha_original": st.column_config.TextColumn("Fecha"),
        "Total": st.column_config.NumberColumn("Total ($)", # Añadir símbolo moneda
                                               format="$ %.2f", # Mostrar 2 decimales
                                               help="Monto total del pedido"),
        "Estado_Pago_Visual": st.column_config.TextColumn("Estado Pago"),
        "Estado_Pedido_Visual": st.column_config.TextColumn("Estado Pedido"),
        "Código": st.column_config.TextColumn("Código"),
        "Cliente": st.column_config.TextColumn("Cliente"),
        "Tipo": st.column_config.TextColumn("Tipo"),
        "Confirmación": st.column_config.TextColumn("Confirmación"),
        "Reclamo": st.column_config.TextColumn("Reclamo"),
        "factura": st.column_config.TextColumn("Factura")
    }
    # Filtrar config_columnas para que solo incluya las columnas existentes
    config_columnas_filtrada = {k: v for k, v in config_columnas.items() if k in columnas_existentes}


    st.dataframe(
        df_filtrado_ordenado[columnas_existentes], # Muestra solo las columnas existentes
        use_container_width=True,
        height=600, # Ajusta la altura según necesidad
        hide_index=True,
        column_config=config_columnas_filtrada # Usar config filtrada
    )

    # --- Botón de Refrescar ---
    st.sidebar.markdown("---") # Separador en sidebar
    if st.sidebar.button("🔄 Refrescar Datos"):
        st.cache_data.clear() # Limpia la caché de datos
        st.info("Caché limpiada. Recargando datos...")
        st.rerun() # Vuelve a ejecutar el script desde el principio

if __name__ == "__main__":
    main()
