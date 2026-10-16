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
    # Leer el archivo detectando el formato
    if archivo_mes.name.endswith('.csv'):
        df = pd.read_csv(archivo_mes)
    else:
        df = pd.read_excel(archivo_mes)
    
    # Limpieza estándar de encabezados para evitar problemas de mayúsculas o espacios
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    # Forzar la búsqueda de las columnas correctas si vienen abajo de filas vacías
    if 'DESCRIPCION' not in df.columns:
        for i in range(min(15, len(df))):
            valores_fila = df.iloc[i].astype(str).str.strip().str.upper().tolist()
            if 'DESCRIPCION' in valores_fila or any('DESCRIP' in f for f in valores_fila):
                df.columns = df.iloc[i].astype(str).str.strip().str.upper()
                df = df.iloc[i+1:].reset_index(drop=True)
                break

    # Asegurar que limpiamos nombres de columnas clave tras el reajuste
    df.columns = df.columns.astype(str).str.strip().str.upper()

    # Comprobar columnas obligatorias de trabajo
    if 'ID PRODUCTO' in df.columns and 'DESCRIPCION' in df.columns:
        
        # Entrada del presupuesto de la semana
        presupuesto = st.number_input("💰 Ingresa el Presupuesto Semanal Neto:", min_value=0.0, value=50000.0, step=1000.0)
        
        # Limpiar filas donde falten los datos principales
        df = df.dropna(subset=['ID PRODUCTO', 'DESCRIPCION'])
        
        # Extractor inteligente de categorías compuestas corregido (Seguro contra números)
        def extraer_categoria_inteligente(texto):
            # Forzar a string y limpiar espacios
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

        df['CATEGORIA_INTERNA'] = df['DESCRIPCION'].apply(extraer_categoria_inteligente)
        
        # Filtro de seguridad para ignorar textos repetidos de cabeceras o totales del proveedor
        filtro_basura = ['ID', 'TOTAL', '***CAMBIO', 'LISTA', 'ID PRODUCTO', 'DESCRIPCION', 'CANTIDAD', 'STATUS', 'ID TIPO', 'PRECIO', 'MONTO', 'NAN', 'VARIOS']
        df = df[~df['CATEGORIA_INTERNA'].isin(filtro_basura)]
        
        # Obtener lista única de categorías ordenada alfabéticamente
        categorias = sorted([c for c in df['CATEGORIA_INTERNA'].unique() if str(c).strip()])
        
        # 2. INTERFAZ DE CAPTURA POR BOTONES
        st.write("### 🗂️ Categorías de Productos")
        if categorias:
            cols = st.columns(3)
            for i, cat in enumerate(categorias):
                with cols[i % 3]:
                    if st.button(f"📦 {cat}", key=f"btn_{cat}"):
                        st.session_state['cat_actual'] = cat
        else:
            st.info("Catálogo vacío o sin formato reconocido.")
        
        # Mostrar productos de la categoría seleccionada en ORDEN ALFABÉTICO
        if 'cat_actual' in st.session_state:
            cat_sel = st.session_state['cat_actual']
            st.write(f"### 🚗 Lista de: {cat_sel} (Orden Alfabético)")
            
            sub_df = df[df['CATEGORIA_INTERNA'] == cat_sel].sort_values(by='DESCRIPCION')
            
            for idx, row in sub_df.iterrows():
                try:
                    id_p = str(int(pd.to_numeric(row['ID PRODUCTO'])))
                except:
                    continue
                desc = row['DESCRIPCION']
                precio_uni = float(pd.to_numeric(row['PRECIO UNITARIO'], errors='coerce')) if 'PRECIO UNITARIO' in df.columns else 0.0
                if pd.isna(precio_uni): precio_uni = 0.0
                
                # Cuadro de captura de cantidad interactivo
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
                    "ID PRODUCTO": int(id_p),
                    "DESCRIPCION": datos['desc'],
                    "CANTIDAD": datos['cant'],
                    "PRECIO UNITARIO": datos['precio'],
                    "MONTO": subtotal_item
                })
            
            # CÁLCULO DE TU FÓRMULA EXACTA: (Total sin IVA + 16% IVA) - 22.13% Descuento
            con_iva = suma_sin_iva * 1.16
            descuento = con_iva * 0.2213
            total_real = con_iva - descuento
            
            # Mostrar tabla resumen
            df_pedido = pd.DataFrame(items_pedido)
            st.table(df_pedido)
            
            # Desglose numérico en pantalla
            st.write(f"**Suma total (Celda K8 sin IVA):** ${suma_sin_iva:,.2f}")
            st.write(f"**Total + IVA (16%):** ${con_iva:,.2f}")
            st.write(f"**Descuento aplicado (22.13%):** -${descuento:,.2f}")
            
            # Semáforo del presupuesto asignado
            if total_real <= presupuesto:
                st.success(f"🟢 **TOTAL REAL A PAGAR: ${total_real:,.2f}** (Dentro del presupuesto)")
            else:
                st.error(f"🔴 **TOTAL REAL A PAGAR: ${total_real:,.2f}** (¡Te pasaste por ${total_real - presupuesto:,.2f}!)")
            
            st.write("---")
            
            # 📤 FASE 4: MENÚ DE ENVÍO MANUAL
            st.write("### 📤 Enviar Pedido Solicitado")
            correo_jefe = st.text_input("📝 Escribe el correo del destinatario:", placeholder="ejemplo@empresa.com")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_pedido.to_excel(writer, index=False, sheet_name='Pedido_Semanal')
            buffer.seek(0)
            
            if correo_jefe and st.button("📧 ENVIAR CORREO COMPROBADO"):
                st.success(f"¡Simulación exitosa! Archivo empaquetado y enviado a: {correo_jefe}")
            
            st.download_button(
                label="📥 DESCARGAR EXCEL FINAL",
                data=buffer,
                file_name="pedido_semanal_final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.write("---")
            
            # 4. BOTÓN GENERAL DE CLEAR / BORRAR CON DOBLE CONFIRMACIÓN
            if not st.session_state['confirmar_borrado']:
                if st.button("🚨 CLEAR / BORRAR PEDIDO"):
                    st.session_state['confirmar_borrado'] = True
                    st.rerun()
            else:
                st.warning("⚠️ ¿Estás seguro de que deseas poner el archivo en blanco otra vez?")
                col_si, col_no = st.columns(2)
                with col_si:
                    if st.button("✅ SÍ, CONFIRMAR"):
                        st.session_state['pedido'] = {}
                        st.session_state['confirmar_borrado'] = False
                        st.rerun()
                with col_no:
                    if st.button("❌ NO, CANCELAR"):
                        st.session_state['confirmar_borrado'] = False
                        st.rerun()
        else:
            st.info("El carrito está vacío. Selecciona productos arriba para empezar.")
    else:
        st.error("No se encontraron las columnas 'ID PRODUCTO' y 'DESCRIPCION'. Revisa que el nombre esté bien escrito.")
