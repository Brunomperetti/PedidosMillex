# [Configuración inicial igual...]

@st.cache_data(ttl=300)
def cargar_datos():
    try:
        # [URL y carga CSV igual...]
        
        # Procesamiento especial para Total
        if 'Total' in df.columns:
            # Convertir a string y limpiar
            df['Total'] = df['Total'].astype(str).str.replace(r'[^\d.]', '', regex=True)
            
            # Convertir a numérico
            df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0).round(2)
            
            # Verificar si hay valores negativos que no deberían existir
            df['Total'] = df['Total'].abs()
        
        # [Resto del procesamiento igual...]

# [En la función main, después de cargar los datos...]

    # Debug temporal (puedes quitarlo después)
    if 'Total' in df.columns:
        st.session_state['total_debug'] = {
            'min': df['Total'].min(),
            'max': df['Total'].max(),
            'mean': df['Total'].mean(),
            'sample_values': df['Total'].head(5).tolist()
        }
        st.write("Datos de depuración - Total:", st.session_state['total_debug'])
    
    # [Resto del código igual...]
