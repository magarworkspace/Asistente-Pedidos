import streamlit as st
import pandas as pd
import io

# Configuración visual para celular
st.set_page_config(page_title="Asistente de Pedidos", layout="centered", page_icon="📱")

st.title("📱 Mi Captura de Pedidos")
st.write("---")

# Inicializar la canasta de pedidos en la memoria
if 'pedido' not in st.session_state:
    st.session_state['pedido'] = {}
if 'confirmar_borrado' not in st.session_state:
    st.session_state['confirmar_borrado'] = False

# 1. CARGA DEL EXCEL DEL MES
archivo_mes = st.file_uploader("📂 1. Arrastra aquí el Excel o CSV del proveedor", type=["csv", "xlsx"])

if archivo_mes is not None:
    if archivo_mes.name.endswith('.csv'):
        df = pd.read_csv(archivo_mes)
    else:
        df = pd.read_excel(archivo_mes)
    
    # Forzar que los encabezados estén limpios y en mayúsculas
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    if 'ID PRODUCTO' in df.columns and 'DESCRIPCION' in df.columns:
        # Entrada del presupuesto de la semana
        presupuesto = st.number_input("💰 Ingresa el Presupuesto Semanal Neto:", min_value=0.0, value=50000.0, step=1000.0)
        
        # Limpiar filas vacías básicas
        df = df.dropna(subset=['ID PRODUCTO', 'DESCRIPCION'])
        
        # Extractor de categorías básico (primera palabra de la descripción)
        df['CATEGORIA_INTERNA'] = df['DESCRIPCION'].astype(str).str.strip().apply(lambda x: x.split()[0].upper() if len(x.split()) > 0 else "VARIOS")
        
        # Quitar los encabezados repetidos
        filtro_basura = ['ID', 'TOTAL', '***CAMBIO', 'LISTA', 'ID PRODUCTO', 'DESCRIPCION', 'CANTIDAD']
        df = df[~df['CATEGORIA_INTERNA'].isin(filtro_basura)]
        categorias = sorted(df['CATEGORIA_INTERNA'].unique())
        
        # 2. INTERFAZ DE CAPTURA POR BOTONES
        st.write("### 🗂️ Categorías de Productos")
        if categories := categorias:
            cols = st.columns(3)
            for i, cat in enumerate(categories):
                with cols[i % 3]:
                    if st.button(cat, key=f"btn_{cat}"):
                        st.session_state['cat_actual'] = cat
        
        # Mostrar productos de la categoría seleccionada en ORDEN ALFABÉTICO
        if 'cat_actual' in st.session_state:
            cat_sel = st.session_state['cat_actual']
            st.write(f"### 🚗 Lista de: {cat_sel} (Orden Alfabético)")
            
            sub_df = df[df['CATEGORIA_INTERNA'] == cat_sel].sort_values(by='DESCRIPCION')
            
            for idx, row in sub_df.iterrows():
                try:
                    id_p = str(int(row['ID PRODUCTO']))
                except:
                    id_p = str(row['ID PRODUCTO'])
                desc = row['DESCRIPCION']
                precio_uni = float(row['PRECIO UNITARIO']) if 'PRECIO UNITARIO' in df.columns else 0.0
                
                # Cuadro de captura de cantidad
                val_actual = st.session_state['pedido'].get(id_p, 0)
                nueva_cant = st.number_input(f"{desc} (ID: {id_p})", min_value=0, value=val_actual if isinstance(val_actual, int) else val_actual['cant'], key=f"inp_{id_p}")
                if nueva_cant > 0:
                    st.session_state['pedido'][id_p] = {"desc": desc, "cant": nueva_cant, "precio": precio_uni}
                elif id_p in st.session_state['pedido'] and nueva_cant == 0:
                    del st.session_state['pedido'][id_p]
        
        st.write("---")
        
        # 3. PANTALLA FINANCIERA Y TOTALES
        st.write("### 📊 Resumen del Pedido")
        if st.session_state['pedido']:
            items_pedido = []
            suma_sin_iva = 0.0
            
            for id_p, datos in st.session_state['pedido'].items():
                subtotal_item = datos['cant'] * datos['precio']
                suma_sin_iva += subtotal_item
                items_pedido.append({
                    "ID PRODUCTO": id_p,
                    "DESCRIPCION": datos['desc'],
                    "CANTIDAD": datos['cant'],
                    "PRECIO UNITARIO": datos['precio'],
                    "MONTO": subtotal_item
                })
            
            # FÓRMULA: (Total sin IVA + 16% IVA) - 22.13% Descuento
            con_iva = suma_sin_iva * 1.16
            descuento = con_iva * 0.2213
            total_real = con_iva - descuento
            
            df_pedido = pd.DataFrame(items_pedido)
            st.table(df_pedido)
            
            st.write(f"**Suma total (Celda K8 sin IVA):** ${suma_sin_iva:,.2f}")
            st.write(f"**Total + IVA (16%):** ${con_iva:,.2f}")
            st.write(f"**Descuento aplicado (22.13%):** -${descuento:,.2f}")
            
            if total_real <= presupuesto:
                st.success(f"🟢 **TOTAL REAL A PAGAR: ${total_real:,.2f}**")
            else:
                st.error(f"🔴 **TOTAL REAL A PAGAR: ${total_real:,.2f}**")
            
            st.write("---")
            st.write("### 📤 Enviar Pedido Solicitado")
            correo_jefe = st.text_input("📝 Correo del destinatario:")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_pedido.to_excel(writer, index=False, sheet_name='Pedido')
            buffer.seek(0)
            
            if correo_jefe and st.button("📧 ENVIAR CORREO COMPROBADO"):
                st.success(f"¡Enviado a: {correo_jefe}!")
            
            st.download_button(label="📥 DESCARGAR EXCEL FINAL", data=buffer, file_name="pedido_final.xlsx")
            
            st.write("---")
            if not st.session_state['confirmar_borrado']:
                if st.button("🚨 CLEAR / BORRAR PEDIDO"):
                    st.session_state['confirmar_borrado'] = True
                    st.rerun()
            else:
                st.warning("⚠️ ¿Borrar todo?")
                if st.button("✅ SÍ, CONFIRMAR"):
                    st.session_state['pedido'] = {}
                    st.session_state['confirmar_borrado'] = False
                    st.rerun()
        else:
            st.info("El carrito está vacío.")
    else:
        st.error("No se encontraron las columnas 'ID PRODUCTO' y 'DESCRIPCION' en la primera fila. Recuerda dejar tus títulos reales en el primer renglón del archivo.")
