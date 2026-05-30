import streamlit as st
import pandas as pd
import os
from datetime import datetime

# =========================================================================
# 🎨 1. CONFIGURACIÓN ESTÉTICA Y HOJA DE ESTILOS CSS (TU FORMATO ORIGINAL)
# =========================================================================
st.set_page_config(page_title="Sistema de Caja Registradora", layout="wide", initial_sidebar_state="expanded")

# Inyección de CSS para forzar el Modo Oscuro Industrial, tus fuentes y el comportamiento de los botones
st.markdown(
    """
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #121212;
        color: #E0E0E0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Títulos Principales en Neon/Blanco */
    h1 {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        border-bottom: 2px solid #29B6F6;
        padding-bottom: 10px;
    }
    
    /* Subtítulos */
    h2, h3, h4 {
        color: #29B6F6 !important;
        font-weight: 600 !important;
    }

    /* Estilo para los botones generales (Manteniendo tus contrastes) */
    div.stButton > button:first-child {
        background-color: #1E1E1E;
        color: #FFFFFF;
        border: 1px solid #424242;
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:first-child:hover {
        background-color: #29B6F6;
        color: #121212;
        border-color: #29B6F6;
    }

    /* Botón de Acción Principal (COBRAR / REGISTRAR) */
    div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #2E7D32 !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        box-shadow: 0px 4px 10px rgba(46, 125, 50, 0.3);
    }
    
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #388E3C !important;
        box-shadow: 0px 6px 15px rgba(56, 142, 60, 0.5);
    }

    /* Contenedores de Tarjetas y Secciones Mapeadas */
    div[data-testid="stForm"], div[data-testid="element-container"] .stContainer {
        background-color: #1E1E1E !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }

    /* Estilos de inputs de texto */
    .stTextInput col {
        color: #FFFFFF !important;
    }
    
    /* Formato de la tabla / Dataframe */
    .stDataFrame {
        background-color: #1E1E1E !important;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# ⚙️ 2. VALIDACIÓN DE LIBRERÍAS DE BACKEND (BLOQUES TRY-EXCEPT ORIGINALES)
# =========================================================================
try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None

try:
    from PIL import Image, ImageTk, ImageDraw
except ModuleNotFoundError:
    Image = None
    ImageTk = None
    ImageDraw = None

# =========================================================================
# 🗄️ 3. PERSISTENCIA DE CONTROL FINANCIERO Y BASE DE DATOS LOCAL
# =========================================================================
if pd is not None:
    if "df_inventario" not in st.session_state:
        try:
            st.session_state.df_inventario = pd.read_csv("inventario.csv")
        except FileNotFoundError:
            st.session_state.df_inventario = pd.DataFrame(columns=["Codigo", "Producto", "Precio_Costo", "Precio_Venta", "Stock"])
            st.session_state.df_inventario.to_csv("inventario.csv", index=False)

    if "df_ventas" not in st.session_state:
        try:
            st.session_state.df_ventas = pd.read_csv("ventas.csv")
            if "Monto_Efectivo" not in st.session_state.df_ventas.columns:
                st.session_state.df_ventas = pd.DataFrame(columns=["Fecha", "Codigo", "Producto", "Monto_Efectivo", "Monto_Tarjeta", "Ganancia"])
                st.session_state.df_ventas.to_csv("ventas.csv", index=False)
        except FileNotFoundError:
            st.session_state.df_ventas = pd.DataFrame(columns=["Fecha", "Codigo", "Producto", "Monto_Efectivo", "Monto_Tarjeta", "Ganancia"])
            st.session_state.df_ventas.to_csv("ventas.csv", index=False)
else:
    if "df_inventario" not in st.session_state: st.session_state.df_inventario = None
    if "df_ventas" not in st.session_state: st.session_state.df_ventas = None

# Mapeo exacto de tus variables globales a la memoria del Servidor Web
if "total_caja_actual" not in st.session_state: st.session_state.total_caja_actual = 0.0
if "fondo_caja_efectivo" not in st.session_state: st.session_state.fondo_caja_efectivo = 1000.00  
if "efectivo_acumulado_cajero" not in st.session_state: st.session_state.efectivo_acumulado_cajero = 0.0 
if "tarjeta_acumulado_cuenta" not in st.session_state: st.session_state.tarjeta_acumulado_cuenta = 0.0
if "productos_en_carrito" not in st.session_state: st.session_state.productos_en_carrito = [] 
if "string_buffer_teclas" not in st.session_state: st.session_state.string_buffer_teclas = ""
if "lbl_status" not in st.session_state: st.session_state.lbl_status = ("Esperando código de barras...", "info")
if "mostrar_pasarela" not in st.session_state: st.session_state.mostrar_pasarela = False
if "mostrar_cambio" not in st.session_state: st.session_state.mostrar_cambio = False
if "datos_cambio" not in st.session_state: st.session_state.datos_cambio = {}

# =========================================================================
# 🧠 4. FUNCIONES DE LÓGICA MATRICIAL Y CONTROL DE NEGOCIO (SIN CAMBIOS)
# =========================================================================
def escanear_producto(entrada_cruda):
    if pd is None or not entrada_cruda: return

    cantidad_a_llevar = 1
    codigo = entrada_cruda
    if "*" in entrada_cruda:
        parts = entrada_cruda.split("*", 1)
        if parts[0].isdigit() and parts[1]:
            cantidad_a_llevar = int(parts[0])
            codigo = parts[1].strip()

    df_inv = st.session_state.df_inventario
    producto_idx = df_inv[df_inv['Codigo'].astype(str) == codigo].index
    
    if len(producto_idx) > 0:
        idx = producto_idx[0]
        nombre = df_inv.loc[idx, 'Producto']
        p_costo = float(df_inv.loc[idx, 'Precio_Costo'])
        p_venta = float(df_inv.loc[idx, 'Precio_Venta'])
        stock_actual = int(df_inv.loc[idx, 'Stock'])
        
        if stock_actual >= cantidad_a_llevar:
            ganancia_unitaria = p_venta - p_costo
            df_inv.loc[idx, 'Stock'] = stock_actual - cantidad_a_llevar
            st.session_state.df_inventario = df_inv 
            
            texto_piezas = f"{cantidad_a_llevar} pza" if cantidad_a_llevar == 1 else f"{cantidad_a_llevar} pzas"
            monto_total_item = p_venta * cantidad_a_llevar
            
            row_id = len(st.session_state.productos_en_carrito)
            st.session_state.productos_en_carrito.append([row_id, codigo, nombre, p_venta, cantidad_a_llevar, ganancia_unitaria, idx])
            
            st.session_state.total_caja_actual += monto_total_item
            st.session_state.lbl_status = (f"✓ Agregado con éxito: {nombre} ({texto_piezas})", "success")
        else:
            st.session_state.lbl_status = (f"❌ ¡Sin Stock suficiente!: {nombre} solo tiene {stock_actual} unidades.", "error")
    else:
        st.session_state.lbl_status = (f"⚠️ Código [{codigo}] no mapeado en el inventario.", "warning")


def remover_item_por_id(item_a_borrar):
    for elemento in st.session_state.productos_en_carrito:
        row_id, codigo, nombre, p_venta, cant, ganancia_u, idx = elemento
        if row_id == item_a_borrar:
            st.session_state.df_inventario.loc[idx, 'Stock'] = int(st.session_state.df_inventario.loc[idx, 'Stock']) + cant
            st.session_state.total_caja_actual -= (p_venta * cant)
            if st.session_state.total_caja_actual < 0: st.session_state.total_caja_actual = 0.0
            
            st.session_state.productos_en_carrito.remove(elemento)
            st.session_state.lbl_status = (f"Eliminado del ticket actual: {nombre}", "error")
            return


def registrar_nueva_cuenta():
    st.session_state.total_caja_actual = 0.0
    st.session_state.productos_en_carrito = []
    st.session_state.efectivo_acumulado_cajero = 0.0
    st.session_state.tarjeta_acumulado_cuenta = 0.0
    st.session_state.string_buffer_teclas = ""
    st.session_state.lbl_status = ("Esperando código de barras...", "info")


def guardar_registro_venta_final(efectivo_final, tarjeta_final):
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    proporcion_efectivo = efectivo_final / st.session_state.total_caja_actual if st.session_state.total_caja_actual > 0 else 0.0
    proporcion_tarjeta = tarjeta_final / st.session_state.total_caja_actual if st.session_state.total_caja_actual > 0 else 0.0

    df_v = st.session_state.df_ventas
    for elemento in st.session_state.productos_en_carrito:
        row_id, codigo, nombre, p_venta, cant, ganancia_u, idx = elemento
        monto_item_total = p_venta * cant
        ganancia_total_item = ganancia_u * cant
        
        item_efectivo = monto_item_total * proporcion_efectivo
        item_tarjeta = monto_item_total * proporcion_tarjeta
        
        nueva_venta = pd.DataFrame([[fecha_hoy, codigo, nombre, item_efectivo, item_tarjeta, ganancia_total_item]], columns=df_v.columns)
        df_v = pd.concat([df_v, nueva_venta], ignore_index=True)
        
    st.session_state.df_ventas = df_v
    if st.session_state.df_inventario is not None: st.session_state.df_inventario.to_csv("inventario.csv", index=False)
    if st.session_state.df_ventas is not None: st.session_state.df_ventas.to_csv("ventas.csv", index=False)


# =========================================================================
# 🧭 5. MENU DE NAVEGACIÓN (SISTEMA INTEGRADO BARRA LATERAL)
# =========================================================================
opcion_pantalla = st.sidebar.radio("☰ MENÚ GENERAL", ["Terminal de Cobro", "Administración e Inventario"])

# =========================================================================
# 🛒 PANTALLA: TERMINAL DE COBRO DE ESCRITORIO
# =========================================================================
if opcion_pantalla == "Terminal de Cobro":
    
    # ─── PANTALLA SECUNDARIA: PANTALLA DE CAMBIO (FORMATO DE ALTO CONTRASTE) ───
    if st.session_state.mostrar_cambio:
        st.title("🧮 RESUMEN DE CAMBIO")
        st.balloons()
        
        dc = st.session_state.datos_cambio
        
        # Bloque de Devolución Física en Formato Negro Absoluto y Letra Neón
        st.markdown(
            f"""
            <div style="background-color: #000000; padding: 30px; border: 2px solid #2E7D32; border-radius: 10px; text-align: center; margin-bottom: 25px;">
                <h4 style="color: #A5D6A7 !important; margin: 0; font-size: 16px; text-transform: uppercase;">Cambio a devolver al cliente:</h4>
                <h1 style="color: #4CAF50 !important; font-size: 55px !important; margin: 10px 0; border: none; padding: 0; font-family: monospace;">
                    ${dc['cambio_monto']:.2f}
                </h1>
            </div>
            """, 
            unsafe_allow_html=True
        )
                
        # Tabla de desglose de cuentas
        with st.container():
            st.markdown("### Detalles de la Operación")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1: st.metric(label="Total Registrado", value=f"${dc['cuenta_total']:.2f}")
            with col_d2: st.metric(label="Efectivo Entregado", value=f"${dc['total_efectivo_recibido']:.2f}")
            with col_d3: st.metric(label="Monto por Tarjeta", value=f"${dc['total_tarjeta_recibido']:.2f}")
                
        st.write(" ")
        if st.button("CONCLUIR VENTA Y ABRIR NUEVA CUENTA", type="primary", use_container_width=True):
            registrar_nueva_cuenta()
            st.session_state.mostrar_cambio = False
            st.rerun()

    # ─── PANTALLA SECUNDARIA: PASARELA DE COBRO INTERMEDIA ───
    elif st.session_state.mostrar_pasarela:
        st.title("💱 PASARELA DE COBRO")
        cuenta_restante_dinamica = st.session_state.total_caja_actual - st.session_state.tarjeta_acumulado_cuenta
        
        # Panel superior de visualización rápida para cajas registradoras
        col_sup1, col_sup2 = st.columns(2)
        with col_sup1:
            st.metric(label="SALDO TOTAL A LIQUIDAR", value=f"${cuenta_restante_dinamica:.2f}")
        with col_sup2:
            st.metric(label="EFECTIVO SUMADO", value=f"${st.session_state.efectivo_acumulado_cajero:.2f}")
            
        col_pas_izq, col_pas_der = st.columns(2)
        
        # Rejilla (Grid) Fija de Billetes Rápidos (Tus valores exactos)
        with col_pas_izq:
            st.markdown("### Billetes Frecuentes")
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("$20 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 20; st.rerun()
                if st.button("$100 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 100; st.rerun()
                if st.button("$500 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 500; st.rerun()
            with cb2:
                if st.button("$50 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 50; st.rerun()
                if st.button("$200 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 200; st.rerun()
                if st.button("$1000 M.N.", use_container_width=True): st.session_state.efectivo_acumulado_cajero += 1000; st.rerun()
                
        # Entrada manual o Pad Numérico
        with col_pas_der:
            st.markdown("### Entrada Manual Efectivo")
            val_teclado = st.number_input("Introducir cantidad recibida:", min_value=0.0, value=float(st.session_state.efectivo_acumulado_cajero), step=5.0)
            if val_teclado != st.session_state.efectivo_acumulado_cajero:
                st.session_state.efectivo_acumulado_cajero = val_teclado
                st.rerun()
            if st.button("Borrar Cantidad (C)", use_container_width=True):
                st.session_state.efectivo_acumulado_cajero = 0.0
                st.rerun()
                
        st.markdown("---")
        # Acciones de pie de ventana (Botones inferiores de confirmación)
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            if st.button("⬅ Cancelar y Volver", use_container_width=True):
                st.session_state.mostrar_pasarela = False
                st.rerun()
        with col_p2:
            if st.button("💳 Liquidar con Tarjeta", use_container_width=True):
                st.session_state.tarjeta_acumulado_cuenta = st.session_state.total_caja_actual
                guardar_registro_venta_final(0.00, st.session_state.tarjeta_acumulado_cuenta)
                st.session_state.datos_cambio = {
                    "cambio_monto": 0.00, "total_efectivo_recibido": 0.00,
                    "total_tarjeta_recibido": st.session_state.tarjeta_acumulado_cuenta,
                    "cuenta_total": st.session_state.total_caja_actual
                }
                st.session_state.mostrar_pasarela = False
                st.session_state.mostrar_cambio = True
                st.rerun()
        with col_p3:
            if st.button("✅ EJECUTAR PAGO Y REGISTRAR", type="primary", use_container_width=True):
                if st.session_state.efectivo_acumulado_cajero < cuenta_restante_dinamica:
                    st.error("El dinero en efectivo es menor al saldo total de la venta.")
                else:
                    cambio = st.session_state.efectivo_acumulado_cajero - cuenta_restante_dinamica
                    efectivo_ingresado_neto = cuenta_restante_dinamica
                    st.session_state.fondo_caja_efectivo += efectivo_ingresado_neto
                    
                    guardar_registro_venta_final(efectivo_ingresado_neto, st.session_state.tarjeta_acumulado_cuenta)
                    st.session_state.datos_cambio = {
                        "cambio_monto": cambio, "total_efectivo_recibido": st.session_state.efectivo_acumulado_cajero,
                        "total_tarjeta_recibido": st.session_state.tarjeta_acumulado_cuenta,
                        "cuenta_total": st.session_state.total_caja_actual
                    }
                    st.session_state.mostrar_pasarela = False
                    st.session_state.mostrar_cambio = True
                    st.rerun()

    # ─── MÓDULO PRINCIPAL: CAJA REGISTRADORA ACTIVA ───
    else:
        st.title("🛒 Terminal de Cobro Activa")
        st.markdown(f"📦 **Fondo de Caja Fijo:** `${st.session_state.fondo_caja_efectivo:.2f}`")
        
        # Formulario del lector del escáner / Teclado manual
        with st.container():
            col_scan, col_reg = st.columns([4, 1])
            with col_scan:
                cod_scan = st.text_input("Ingresar código de barras (Ej: 5*CODIGO o Código directo):", key="main_scanner_box", placeholder="Listo para escanear...")
            with col_reg:
                st.write(" ") # Ajuste estético vertical de rejilla
                btn_reg = st.button("↵ Añadir", use_container_width=True)
                
            if (btn_reg or cod_scan != "") and cod_scan:
                escanear_producto(cod_scan)
                st.rerun()
                
            # Despliegue del Monitor de Estatus de Operación (Consola inferior del scanner)
            msg, tipo = st.session_state.lbl_status
            if tipo == "success": st.success(msg)
            elif tipo == "error": st.error(msg)
            elif tipo == "warning": st.warning(msg)
            else: st.info(msg)
            
        # Formato de la lista del Ticket actual (Treeview)
        st.markdown("### 🔥 Artículos en el Ticket Actual")
        if st.session_state.productos_en_carrito:
            
            # Formato de encabezado de tabla estilizado
            st.markdown(
                """
                <div style="background-color: #252525; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
                    <div style="display: flex; font-weight: bold; color: #29B6F6;">
                        <div style="flex: 1;">Acción</div>
                        <div style="flex: 1;">Cantidad</div>
                        <div style="flex: 4;">Descripción del Artículo</div>
                        <div style="flex: 2; text-align: right;">Total Parcial</div>
                    </div>
                </div>
                """, unsafe_allow_html=True
            )
            
            for item in st.session_state.productos_en_carrito:
                r_id, codigo, producto_nombre, p_venta, cantidad, ganancia, idx = item
                
                col_del, col_cant, col_desc, col_total = st.columns([1, 1, 4, 2])
                with col_del:
                    if st.button("❌", key=f"btn_trash_{r_id}"):
                        remover_item_por_id(r_id)
                        st.rerun()
                with col_cant: 
                    st.write(f"{cantidad} pza(s)")
                with col_desc: 
                    st.write(f"**{producto_nombre}** <span style='color:#757575;'>({codigo})</span>", unsafe_allow_html=True)
                with col_total: 
                    st.markdown(f"<div style='text-align: right; font-weight: bold;'>${(p_venta * cantidad):.2f}</div>", unsafe_allow_html=True)
                
            st.markdown("---")
            # Bloque de disparo de Cierre de Cuenta
            texto_total_boton = f"PROCESAR COBRO TOTAL  ➔  ${st.session_state.total_caja_actual:.2f}"
            if st.button(texto_total_boton, type="primary", use_container_width=True):
                if st.session_state.total_caja_actual == 0:
                    st.warning("No se puede cobrar un ticket en ceros.")
                else:
                    st.session_state.efectivo_acumulado_cajero = 0.0
                    st.session_state.tarjeta_acumulado_cuenta = 0.0
                    st.session_state.mostrar_pasarela = True
                    st.rerun()
        else:
            st.markdown("<div style='color: #757575; font-style: italic;'>Escanee códigos para ver los detalles del ticket...</div>", unsafe_allow_html=True)


# =========================================================================
# 📊 PANTALLA: ADMINISTRACIÓN GENERAL E INVENTARIOS
# =========================================================================
elif opcion_pantalla == "Administración e Inventario":
    st.title("📊 Panel de Control y Auditoría")
    
    # Formato de Fondo de Caja manual
    st.subheader("Modificar Fondo de Caja Efectivo")
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        val_fondo = st.number_input("Cantidad de efectivo en fondo:", value=float(st.session_state.fondo_caja_efectivo))
    with col_f2:
        st.write(" ")
        if st.button("Confirmar Ajuste", use_container_width=True):
            st.session_state.fondo_caja_efectivo = val_fondo
            st.success("Fondo monetario auditado y guardado.")
            
    # Render de Tablas de Control de Inventario
    st.subheader("📦 Base de Datos de Inventario (`inventario.csv`)")
    if st.session_state.df_inventario is not None:
        st.dataframe(st.session_state.df_inventario, use_container_width=True)
    else:
        st.error("No se localizó la base de datos de inventario.")
        
    # Análisis Estadístico de Ventas y Rendimiento
    st.subheader("📋 Historial de Ventas Ejecutadas (`ventas.csv`)")
    df_ventas_raw = st.session_state.df_ventas
    
    if df_ventas_raw is not None and not df_ventas_raw.empty:
        st.dataframe(df_ventas_raw, use_container_width=True)
        
        # Procesamiento matemático de fechas para métricas mensuales
        try:
            df_temporal = df_ventas_raw.copy()
            df_temporal['Fecha'] = pd.to_datetime(df_temporal['Fecha'], format='mixed', errors='coerce')
            df_temporal = df_temporal.dropna(subset=['Fecha'])
            
            if not df_temporal.empty:
                st.markdown("### 📈 Reporte de Ganancia Líquida Mensual")
                df_mensual = df_temporal.groupby(df_temporal['Fecha'].dt.to_period('M')).agg({
                    'Monto_Efectivo': 'sum', 'Monto_Tarjeta': 'sum', 'Ganancia': 'sum'
                }).reset_index()
                
                df_mensual['Fecha'] = df_mensual['Fecha'].astype(str)
                st.dataframe(df_mensual, use_container_width=True)
                
                # Despliegue de Gráfica Nativa de Alto Rendimiento
                if st.button("Desplegar Gráfica Histórica", type="primary", use_container_width=True):
                    st.write("#### Ganancias Mensuales Consolidadas")
                    st.bar_chart(data=df_mensual, x='Fecha', y='Ganancia')
        except Exception as e:
            st.error(f"Error en auditoría analítica de tiempos: {e}")
    else:
        st.info("Aún no se registran movimientos financieros en las tablas.")