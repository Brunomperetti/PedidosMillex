import streamlit as st
import pandas as pd
from datetime import datetime
import traceback

# Configurar página
st.set_page_config(page_title="Pedidos Millex", layout="wide", page_icon="📦")
st.title("📦 Seguimiento de Pedidos - Millex")

# --- Definición de Estados ---
ESTADOS_PEDIDO = {
    "Sin definir": "📥 Nuevo Pedido",
    "Pendiente de autorizacion": "⏳ Nuevo Pedido",
    "Leido": "📦 Armando pedido",
    "En local comercial": "🛒 Pedido armado",
    "En espera de pedido en sucursal de transporte": "🛒 Pedido armado",
    "Se entrego al transporte": "🚚 En transporte"
}

ESTADOS_PAGO = {
    "Sin definir": "⏳ Pendiente de Pago",
    "Pendiente: El pago se encuentra pendiente de acreditacion": "📞 Pago Solicitado",
    "El pago fue aprobado y acreditado": "💰 Pagado",
    "El pago fue rechazado. El usuario puede intentar nuevamente": "❌ Rechazado"
}

# --- Cargar Datos COMPLETOS (Optimizado) ---
@st.cache_data(ttl=300)
def cargar_datos():
    try:
        # URL de los datos
        spreadsheet_id = "1B7sG6DqaCBfMN0OJOr_juEJ0zJXTo46lLHykpe-OaJk"
        sheet_gid = "1856455950"
        csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={sheet_gid}"
        
        # Leer el CSV
        df = pd.read_csv(csv_url, dtype={'Fecha': str, 'Código': str})
        
        # Eliminar filas completamente vacías
        df.replace('', pd.NA, inplace=True)
        df.dropna(how='all', inplace=True)
        
        # --- Procesamiento de Fechas Mejorado ---
        if 'Fecha' in df.columns:
            # Primero intentamos con el formato exacto
            df['Fecha_datetime'] = pd.to_datetime(
                df['Fecha'].str.replace(',', ''),  # Eliminamos la coma
                format='%d/%m/%Y %H:%M:%S',
                errors='coerce'
            )
            
            # Si hay fechas inválidas, intentamos otro método
            if df['Fecha_datetime'].isna().any():
                # Intentamos parsear sin especificar formato exacto
                df['Fecha_datetime'] = pd.to_datetime(
                    df['Fecha'],
                    dayfirst=True,
                    errors='coerce'
                )
            
            # Mantener columna original para visualización
            df['Fecha_original'] = df['Fecha']
        else:
            df['Fecha_datetime'] = pd.NaT
            df['Fecha_original'] = ''
        
        # --- Validaciones de otras columnas ---
        columnas_a_validar = {
            'Estado de Pedido': 'Sin definir',
            'Estado de Pago': 'Sin definir',
            'Código': '',
            'Cliente': 'N/A',
            'Total': 0,
            'Tipo': 'N/A',
            'Confirmación': '',
            'Reclamo': '',
            'factura': ''
        }
        
        for col, default_value in columnas_a_validar.items():
            if col not in df.columns:
                df[col] = default_value
        
        # Convertir 'Total' a numérico
        if 'Total' in df.columns:
            df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
        
        return df

    except Exception as e:
        st.error(f"Error al cargar los datos: {str(e)}")
        return pd.DataFrame()

# --- Interfaz Principal ---
def main():
    # Mostrar spinner mientras se cargan los datos
    with st.spinner('Cargando datos...'):
        df = cargar_datos()
    
    if df.empty:
        st.warning("No se pudieron cargar los datos. Por favor, intente más tarde.")
        if st.button("🔄 Reintentar Carga"):
            st.cache_data.clear()
            st.rerun()
        return
    
    # Mostrar conteo real de pedidos
    st.markdown(f"**Total de pedidos cargados:** {len(df)}")
    
    # --- Preprocesamiento para visualización ---
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
    
    # --- Sidebar con Filtros ---
    with st.sidebar:
        st.header("Filtros")
        
        opciones_pedido_unicas = ["Todos"] + sorted(df['Estado_Pedido_Visual'].unique().tolist())
        filtro_pedido = st.selectbox("Estado del Pedido", opciones_pedido_unicas, index=0)
        
        opciones_pago_unicas = ["Todos"] + sorted(df['Estado_Pago_Visual'].unique().tolist())
        filtro_pago = st.selectbox("Estado del Pago", opciones_pago_unicas, index=0)
    
    # --- Aplicar Filtros ---
    df_filtrado = df.copy()
    
    if filtro_pedido != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pedido_Visual'] == filtro_pedido]
    
    if filtro_pago != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Estado_Pago_Visual'] == filtro_pago]
    
    # --- Mostrar Estadísticas ---
    st.subheader("📊 Resumen de Pedidos")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pedidos Mostrados", len(df_filtrado))
    with col2:
        nuevos_pedidos = df_filtrado['Estado_Pedido_Visual'].str.startswith(('⏳', '📥')).sum()
        st.metric("Nuevos pedidos", nuevos_pedidos)
    with col3:
        entregados = (df_filtrado['Estado_Pedido_Visual'] == "🚚 En transporte").sum()
        st.metric("En transporte", entregados)
    
    # --- Mostrar Tabla de Pedidos ---
    st.subheader(f"📋 Listado de Pedidos ({len(df_filtrado)} registros)")
    
    # Ordenar por fecha
    if 'Fecha_datetime' in df_filtrado.columns and not df_filtrado['Fecha_datetime'].isna().all():
        df_filtrado_ordenado = df_filtrado.sort_values('Fecha_datetime', ascending=False, na_position='last')
    else:
        df_filtrado_ordenado = df_filtrado
    
    # Columnas a mostrar
    columnas_mostrar = [
        'Código', 'Fecha_original', 'Cliente', 'Total', 
        'Tipo', 'Estado_Pago_Visual', 'Estado_Pedido_Visual',
        'Confirmación', 'Reclamo', 'factura'
    ]
    
    # Configuración de columnas
    config_columnas = {
        "Fecha_original": st.column_config.TextColumn("Fecha"),
        "Total": st.column_config.NumberColumn("Total ($)", format="$ %.2f"),
        "Estado_Pago_Visual": st.column_config.TextColumn("Estado Pago"),
        "Estado_Pedido_Visual": st.column_config.TextColumn("Estado Pedido"),
        "Código": st.column_config.TextColumn("Código"),
        "Cliente": st.column_config.TextColumn("Cliente"),
        "Tipo": st.column_config.TextColumn("Tipo"),
        "Confirmación": st.column_config.TextColumn("Confirmación"),
        "Reclamo": st.column_config.TextColumn("Reclamo"),
        "factura": st.column_config.TextColumn("Factura")
    }
    
    # Filtrar columnas existentes
    columnas_existentes = [col for col in columnas_mostrar if col in df_filtrado_ordenado.columns]
    config_columnas_filtrada = {k: v for k, v in config_columnas.items() if k in columnas_existentes}
    
    # Mostrar dataframe
    st.dataframe(
        df_filtrado_ordenado[columnas_existentes],
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config=config_columnas_filtrada
    )
    
    # --- Botón de Refrescar ---
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refrescar Datos"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()
