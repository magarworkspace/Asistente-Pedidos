import streamlit as st
import pandas as pd
import io

# Configuración visual para celular
st.set_page_config(page_title="Asistente de Pedidos", layout="centered", page_icon="📱")

# Estilos personalizados (Botones estilizados)
st.markdown("""
    <style>
    div.stButton > button:first-child {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

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
    # Leer el archivo (funciona con Excel o CSV)
    if archivo_mes.name.endswith('.csv'):
        df = pd.read_csv(archivo_mes)
    else:
        df = pd.read_excel(archivo_mes)
    
    # Limpieza básica de nombres de columnas
    df.columns = df.columns.str.strip().str.upper()
    
    # Comprobar columnas obligatorias
    if 'ID PRODUCTO' in df.columns and 'DESCRIPCION' in df.columns:
        
        # Entrada del presupuesto de la semana
        presupuesto = st.number_input("💰 Ingresa el Presupuesto Semanal Neto:", min_value=0.0, value=50000.0, step=1000.0)
        
        # Crear categorías automáticas basadas en la primera palabra de la descripción
        df['CATEGORIA_INTERNA'] = df['DESCRIPCION'].apply(lambda x: str(x).split()[0].upper() if pd.notnull(x) else "VARIOS")
        categorias = sorted(df['CATEGORIA_INTERNA'].unique())
        
        # 2. INTERFAZ DE CAPTURA POR BOTONES
        st.write("### 🗂️ Categorías de Productos")
        cols = st.columns(3)
        for i, cat in enumerate(categorias):
            with cols[i % 3]:
                if st.button(cat, key=f"btn_{cat}"):
                    st.session_state['cat_actual'] = cat
        
        # Mostrar productos de la categoría seleccionada en ORDEN ALFABÉTICO
        if 'cat_actual' in st.session_state:
            cat_sel = st.session_state['cat_actual']
            st.write(f"### 🚗 Lista de: {cat_sel} (Orden Alfabético)")
            
            sub_df = df[df['CATEGORIA_INTERNA'] == cat_sel].sort_values(by='DESCRIPCION')
            
            for idx, row in sub_df.iterrows():
                id_p = str(int(row['ID PRODUCTO']))
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
            
            # 📬 FASE 4: NUEVO MENÚ DE ENVÍO MANUAL (A LOS DE ARRIBA)
            st.write("### 📤 Enviar Pedido Solicitado")
            correo_jefe = st.text_input("📝 Escribe el correo del destinatario (Jefe, Gerente o Proveedor):", placeholder="ejemplo@empresa.com")
            
            # Crear el archivo Excel en la memoria para descarga o envío inmediato
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_pedido.to_excel(writer, index=False, sheet_name='Pedido_Semanal')
            buffer.seek(0)
            
            if correo_jefe:
                if st.button("📧 ENVIAR CORREO COMPROBADO"):
                    st.success(f"¡Simulación de envío exitosa! El archivo con tus cantidades fue enviado al correo: {correo_jefe}")
            
            # Botón de respaldo para descargar o compartir directo por WhatsApp/Teams
            st.download_button(
                label="📥 DESCARGAR EXCEL FINAL (Para compartir por WhatsApp/Teams)",
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
                        st.success("¡Pedido borrado!")
                        st.rerun()
                with col_no:
                    if st.button("❌ NO, CANCELAR"):
                        st.session_state['confirmar_borrado'] = False
                        st.rerun()
        else:
            st.info("El carrito está vacío. Escanea o selecciona productos para empezar.")
    else:
        st.error("El archivo no tiene el formato correcto. Asegúrate de que incluya las columnas 'ID PRODUCTO' y 'DESCRIPCION'.")
