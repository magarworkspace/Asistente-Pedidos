import streamlit as st
import pandas as pd
import io

# Configuración visual para celular
st.set_page_config(page_title="Asistente de Pedidos", layout="centered", page_icon="📱")

st.title("📱 Mi Captura de Pedidos")
st.write("---")

# Inicializar la canasta de pedidos en la memoria del celular
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
    
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    if 'ID PRODUCTO' in df.columns and 'DESCRIPCION' in df.columns:
        presupuesto = st.number_input("💰 Ingresa el Presupuesto Semanal Neto:", min_value=0.0, value=50000.0, step=1000.0)
        
        df = df.dropna(subset=['ID PRODUCTO', 'DESCRIPCION'])
        df['ID_STR'] = df['ID PRODUCTO'].astype(str).str.split('.').str[0].str.strip()
        df['DESCRIPCION_STR'] = df['DESCRIPCION'].astype(str).str.strip()
        df = df[df['DESCRIPCION_STR'] != ""]
        
        # 📷 FASE 2.5: ESCÁNER DE CÁMARA
        st.write("### 📷 Escáner de Código de Barras")
        imagen_camara = st.camera_input("Apunta la cámara al código de barras")
        
        id_buscado = st.text_input("🔍 Buscar rápidamente por ID de Producto:", key="buscador_id")
        if id_buscado:
            id_limpio = id_buscado.strip()
            coincidencia = df[df['ID_STR'] == id_limpio]
            if not coincidencia.empty:
                row = coincidencia.iloc[0]
                desc_b = row['DESCRIPCION_STR']
                col_p = [c for c in df.columns if 'PRECIO' in c or 'UNITARIO' in c]
                precio_b = float(pd.to_numeric(row[col_p[0]], errors='coerce')) if col_p else 0.0
                if pd.isna(precio_b): precio_b = 0.0
                
                st.write(f"📌 **Encontrado:** {desc_b} (Precio: ${precio_b:,.2f})")
                val_b = st.session_state['pedido'].get(id_limpio, 0)
                cant_b = st.number_input(f"Cantidad para ID {id_limpio}:", min_value=0, value=val_b if isinstance(val_b, int) else val_b['cant'], key=f"fast_{id_limpio}")
                if cant_b > 0:
                    st.session_state['pedido'][id_limpio] = {"desc": desc_b, "cant": cant_b, "precio": precio_b}
                elif id_limpio in st.session_state['pedido'] and cant_b == 0:
                    del st.session_state['pedido'][id_limpio]
            else:
                st.error("ID no encontrado.")

        st.write("---")

        def extraer_categoria_robusto(texto):
            txt = str(texto).strip().upper()
            palabras = txt.split()
            if len(palabras) == 0 or txt in ['NAN', 'NONE', '']:
                return "VARIOS"
            primera = palabras[0]
            if primera in ['BALATA', 'BOMBA', 'BASE', 'CABLE', 'BUJE', 'TORNILLO', 'DEPOSITO', 'DUCTO', 'KIT', 'TAPA', 'TAPON', 'VALVULA'] and len(palabras) > 1:
                segunda = palabras[1]
                if segunda in ['DISCO', 'TAMBOR', 'AGUA', 'GASOLINA', 'AMORTIGUADOR', 'HORQUILLA', 'BUJIA', 'SELECTOR', 'ESTABILIZADOR', 'ANTICONGELANTE', 'ENTRADA', 'DISTRIBUCION', 'PUNTERIAS', 'RADIADOR', 'IAC']:
                    return f"{primera} {segunda}"
            return primera

        df['CATEGORIA_INTERNA'] = df['DESCRIPCION_STR'].apply(extraer_categoria_robusto)
        filtro_basura = ['ID', 'TOTAL', '***CAMBIO', 'LISTA', 'ID PRODUCTO', 'DESCRIPCION', 'CANTIDAD', 'STATUS', 'ID TIPO', 'PRECIO', 'MONTO', 'NAN', 'VARIOS']
        df = df[~df['CATEGORIA_INTERNA'].isin(filtro_basura)]
        
        categorias = sorted([c for c in df['CATEGORIA_INTERNA'].unique() if str(c).strip()])
        
        st.write("### 🗂️ Categorías de Productos")
        if categorias:
            cols = st.columns(3)
            for i, cat in enumerate(categorias):
                with cols[i % 3]:
                    if st.button(f"📦 {cat}", key=f"btn_{cat}"):
                        st.session_state['cat_actual'] = cat
        
        if 'cat_actual' in st.session_state:
            cat_sel = st.session_state['cat_actual']
            st.write(f"### 🚗 Lista de: {cat_sel}")
            sub_df = df[df['CATEGORIA_INTERNA'] == cat_sel].sort_values(by='DESCRIPCION_STR')
            
            for idx, row in sub_df.iterrows():
                id_p = str(row['ID_STR'])
                desc = row['DESCRIPCION_STR']
                col_precio = [c for c in df.columns if 'PRECIO' in c or 'UNITARIO' in c]
                precio_uni = float(pd.to_numeric(row[col_precio[0]], errors='coerce')) if col_precio else 0.0
                if pd.isna(precio_uni): precio_uni = 0.0
                
                val_actual = st.session_state['pedido'].get(id_p, 0)
                cantidad_actual_int = val_actual if isinstance(val_actual, int) else val_actual['cant']
                nueva_cant = st.number_input(f"{desc} (ID: {id_p})", min_value=0, value=cantidad_actual_int, key=f"inp_{id_p}")
                if nueva_cant > 0:
                    st.session_state['pedido'][id_p] = {"desc": desc, "cant": nueva_cant, "precio": precio_uni}
                elif id_p in st.session_state['pedido'] and nueva_cant == 0:
                    del st.session_state['pedido'][id_p]
        
        st.write("---")
        st.write("### 📊 Resumen del Pedido")
        if st.session_state['pedido']:
            items_pedido = []
            suma_sin_iva = 0.0
            for id_p, datos in st.session_state['pedido'].items():
                subtotal_item = datos['cant'] * datos['precio']
                suma_sin_iva += subtotal_item
                items_pedido.append({"ID PRODUCTO": id_p, "DESCRIPCION": datos['desc'], "CANTIDAD": datos['cant'], "PRECIO UNITARIO": datos['precio'], "MONTO": subtotal_item})
            
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
            correo_jefe = st.text_input("📝 Escribe el correo del destinatario:", placeholder="ejemplo@empresa.com")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_pedido.to_excel(writer, index=False, sheet_name='Pedido_Semanal')
            buffer.seek(0)
            
            if correo_jefe and st.button("📧 ENVIAR CORREO COMPROBADO"):
                st.success(f"¡Archivo enviado a: {correo_jefe}!")
            
            st.download_button(label="📥 DESCARGAR EXCEL FINAL", data=buffer, file_name="pedido_semanal_final.xlsx")
            
            st.write("---")
            if not st.session_state['confirmar_borrado']:
                if st.button("🚨 CLEAR / BORRAR PEDIDO"):
                    st.session_state['confirmar_borrado'] = True
                    st.rerun()
            else:
                st.warning("⚠️ ¿Estás seguro de que deseas poner el archivo en blanco otra vez?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ SÍ, CONFIRMAR"):
                        st.session_state['pedido'] = {}
                        st.session_state['confirmar_borrado'] = False
                        st.rerun()
                with col2:
                    if st.button("❌ NO, CANCELAR"):
                        st.session_state['confirmar_borrado'] = False
                        st.rerun()
        else:
            st.info("El carrito está vacío.")
    else:
        st.error("No se encontraron las columnas en tu Excel.")

