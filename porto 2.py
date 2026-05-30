import tkinter as tk
from tkinter import ttk, messagebox
import os
from datetime import datetime

# --- VALIDACIÓN DE LIBRERÍAS CRÍTICAS ---
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


# --- BASE DE DATOS LOCAL (ARCHIVOS CSV) ---
if pd is not None:
    try:
        df_inventario = pd.read_csv("inventario.csv")
    except FileNotFoundError:
        df_inventario = pd.DataFrame(columns=["Codigo", "Producto", "Precio_Costo", "Precio_Venta", "Stock"])
        df_inventario.to_csv("inventario.csv", index=False)

    try:
        df_ventas = pd.read_csv("ventas.csv")
        if "Monto_Efectivo" not in df_ventas.columns:
            df_ventas = pd.DataFrame(columns=["Fecha", "Codigo", "Producto", "Monto_Efectivo", "Monto_Tarjeta", "Ganancia"])
            df_ventas.to_csv("ventas.csv", index=False)
    except FileNotFoundError:
        df_ventas = pd.DataFrame(columns=["Fecha", "Codigo", "Producto", "Monto_Efectivo", "Monto_Tarjeta", "Ganancia"])
        df_ventas.to_csv("ventas.csv", index=False)
else:
    df_inventario = None
    df_ventas = None

# Variables globales de negocio
total_caja_actual = 0.0
fondo_caja_efectivo = 1000.00  
efectivo_acumulado_cajero = 0.0 
tarjeta_acumulado_cuenta = 0.0
productos_en_carrito = [] 

# Componentes de control UI globales
btn_total_cobrar = None
entrada_scanner = None
tabla_caja = None
lbl_status = None
estilo = None
pestana_cobro = None
pestana_admin = None
menu_flotante = None
menu_desplegado = False


# --- FUNCIÓN PARA GENERAR BOTONES REDONDEADOS ---
def crear_imagen_boton_redondo(ancho, alto, radio, color_hex):
    if Image is None or ImageDraw is None:
        return None
    imagen = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(imagen)
    draw.rounded_rectangle((0, 0, ancho, alto), radius=radio, fill=color_hex)
    return ImageTk.PhotoImage(imagen)


# --- FUNCIÓN DE CENTRADO ---
def centrar_ventana(ventana, ancho_v, alto_v):
    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()
    x = (pantalla_ancho // 2) - (ancho_v // 2)
    y = (pantalla_alto // 2) - (alto_v // 2)
    ventana.geometry(f"{ancho_v}x{alto_v}+{x}+{y}")


# --- CONTROLADOR DE NAVEGACIÓN ---
def mostrar_pantalla(pantalla_objetivo):
    pestana_cobro.pack_forget()
    pestana_admin.pack_forget()
    pantalla_objetivo.pack(fill="both", expand=True, padx=10, pady=10)
    if pantalla_objetivo == pestana_cobro and entrada_scanner is not None:
        entrada_scanner.focus_set()


def determinar_posicion_menu_dinamico():
    global menu_flotante, menu_desplegado
    if menu_desplegado:
        menu_flotante.place_forget()
        menu_desplegado = False
    else:
        menu_flotante.place(x=0, y=45, width=320, height=190)
        menu_flotante.lift()
        menu_desplegado = True


# --- CONTROLADOR DE ARTÍCULOS ---
def escanear_producto(event=None):
    global df_inventario, total_caja_actual, productos_en_carrito, btn_total_cobrar
    if pd is None or entrada_scanner is None: return

    entrada_cruda = entrada_scanner.get().strip()
    entrada_scanner.delete(0, tk.END)
    if not entrada_cruda: return

    cantidad_a_llevar = 1
    codigo = entrada_cruda
    if "*" in entrada_cruda:
        parts = entrada_cruda.split("*", 1)
        if parts[0].isdigit() and parts[1]:
            cantidad_a_llevar = int(parts[0])
            codigo = parts[1].strip()

    producto_idx = df_inventario[df_inventario['Codigo'].astype(str) == codigo].index
    
    if len(producto_idx) > 0:
        idx = producto_idx[0]
        nombre = df_inventario.loc[idx, 'Producto']
        p_costo = float(df_inventario.loc[idx, 'Precio_Costo'])
        p_venta = float(df_inventario.loc[idx, 'Precio_Venta'])
        stock_actual = int(df_inventario.loc[idx, 'Stock'])
        
        if stock_actual >= cantidad_a_llevar:
            ganancia_unitaria = p_venta - p_costo
            df_inventario.loc[idx, 'Stock'] = stock_actual - cantidad_a_llevar
            
            texto_piezas = f"{cantidad_a_llevar} pza" if cantidad_a_llevar == 1 else f"{cantidad_a_llevar} pzas"
            monto_total_item = p_venta * cantidad_a_llevar
            
            num_elementos = len(tabla_caja.get_children())
            tag_fila = "par" if num_elementos % 2 == 0 else "impar"
            
            row_id = tabla_caja.insert("", "end", values=["❌", texto_piezas, nombre, f"${monto_total_item:.2f}"], tags=(tag_fila,))
            productos_en_carrito.append([row_id, codigo, nombre, p_venta, cantidad_a_llevar, ganancia_unitaria, idx])
            
            total_caja_actual += monto_total_item
            if btn_total_cobrar is not None:
                btn_total_cobrar.config(text=f"COBRAR CUENTA  •  TOTAL: ${total_caja_actual:.2f}\n(Presione aquí para abrir pasarela de efectivo)")
            if lbl_status is not None:
                lbl_status.config(text=f"Agregado: {nombre} ({texto_piezas})", fg="#2ed573")
        else:
            if lbl_status is not None:
                lbl_status.config(text=f"¡Error!: {nombre} solo tiene {stock_actual} unidades.", fg="#ff4757")
    else:
        if lbl_status is not None:
            lbl_status.config(text=f"El código [{codigo}] no está registrado.", fg="#ffa502")


def detectar_clic_tabla(event):
    if tabla_caja is None: return
    region = tabla_caja.identify_region(event.x, event.y)
    if region == "cell":
        column = tabla_caja.identify_column(event.x)
        item_id = tabla_caja.identify_row(event.y)
        if column == "#1" and item_id:
            remover_item_por_id(item_id)


def remover_item_por_id(item_a_borrar):
    global total_caja_actual, productos_en_carrito, df_inventario, btn_total_cobrar
    for elemento in productos_en_carrito:
        row_id, codigo, nombre, p_venta, cant, ganancia_u, idx = elemento
        if row_id == item_a_borrar:
            df_inventario.loc[idx, 'Stock'] = int(df_inventario.loc[idx, 'Stock']) + cant
            total_caja_actual -= (p_venta * cant)
            if total_caja_actual < 0: total_caja_actual = 0.0
            
            tabla_caja.delete(item_a_borrar)
            productos_en_carrito.remove(elemento)
            
            for i, child in enumerate(tabla_caja.get_children()):
                tag_actual = "par" if i % 2 == 0 else "impar"
                tabla_caja.item(child, tags=(tag_actual,))
            
            if btn_total_cobrar is not None:
                btn_total_cobrar.config(text=f"COBRAR CUENTA  •  TOTAL: ${total_caja_actual:.2f}\n(Presione aquí para abrir pasarela de efectivo)")
            if lbl_status is not None:
                lbl_status.config(text=f"Retirado del ticket: {nombre}", fg="#ff4757")
            return


def registrar_nueva_cuenta():
    global total_caja_actual, productos_en_carrito, btn_total_cobrar
    if tabla_caja is not None:
        for row in tabla_caja.get_children():
            tabla_caja.delete(row)
    total_caja_actual = 0.0
    productos_en_carrito = []
    if btn_total_cobrar is not None:
        btn_total_cobrar.config(text="COBRAR CUENTA  •  TOTAL: $0.00\n(Presione aquí para abrir pasarela de efectivo)")
    if lbl_status is not None:
        lbl_status.config(text="Esperando código...", fg="#747d8c")


def ajustar_fondo_manual():
    global fondo_caja_efectivo
    try:
        nuevo_monto = float(entrada_ajuste_fondo.get().strip())
        fondo_caja_efectivo = nuevo_monto
        lbl_fondo_dinero.config(text=f"${fondo_caja_efectivo:.2f}")
        entrada_ajuste_fondo.delete(0, tk.END)
        messagebox.showinfo("Fondo Updated", "Fondo de caja actualizado con éxito.")
    except ValueError:
        messagebox.showerror("Error", "Cantidad inválida.")


def actualizar_tablas_admin():
    if pd is None: return
    try:
        for row in tabla_inv.get_children():
            tabla_inv.delete(row)
        for row in tabla_ganancias.get_children():
            tabla_ganancias.delete(row)
        for _, fila in df_inventario.iterrows():
            tabla_inv.insert("", "end", values=list(fila))
            
        if not df_ventas.empty:
            fechas_parseadas = pd.to_datetime(df_ventas['Fecha'], format='mixed', errors='coerce')
            df_temporal = df_ventas.copy()
            df_temporal['Fecha'] = fechas_parseadas
            df_temporal = df_temporal.dropna(subset=['Fecha'])
            
            if not df_temporal.empty:
                df_mensual = df_temporal.groupby(df_temporal['Fecha'].dt.to_period('M')).agg({
                    'Monto_Efectivo': 'sum',
                    'Monto_Tarjeta': 'sum',
                    'Ganancia': 'sum'
                }).reset_index()
                
                for _, fila in df_mensual.iterrows():
                    tabla_ganancias.insert("", "end", values=[
                        str(fila['Fecha']), 
                        f"${fila['Monto_Efectivo']:.2f}", 
                        f"${fila['Monto_Tarjeta']:.2f}", 
                        f"${fila['Ganancia']:.2f}"
                    ])
    except NameError:
        pass


def generar_grafica():
    if plt is None or pd is None or df_ventas.empty: return
    fechas_parseadas = pd.to_datetime(df_ventas['Fecha'], format='mixed', errors='coerce')
    df_temporal = df_ventas.copy()
    df_temporal['Fecha'] = fechas_parseadas
    df_temporal = df_temporal.dropna(subset=['Fecha'])
    
    if df_temporal.empty:
        messagebox.showwarning("Sin datos", "No hay registros válidos para la gráfica.")
        return
        
    df_mensual = df_temporal.groupby(df_temporal['Fecha'].dt.strftime('%B %Y')).agg({'Ganancia': 'sum'})
    plt.figure(figsize=(8, 5))
    plt.bar(df_mensual.index, df_mensual['Ganancia'], color='#1e90ff', edgecolor='black')
    plt.tight_layout()
    plt.show()


# =========================================================================
# 📌 PASARELA DE COBRO 
# =========================================================================
def abrir_ventana_cobro():
    global total_caja_actual, efectivo_acumulado_cajero, tarjeta_acumulado_cuenta
    
    if total_caja_actual == 0:
        messagebox.showwarning("Caja Vacía", "No hay productos marcados para cobrar.")
        return
        
    efectivo_acumulado_cajero = 0.0
    tarjeta_acumulado_cuenta = 0.0
    cuenta_restante_dinamica = total_caja_actual
    
    win_pago = tk.Toplevel(root)
    win_pago.title("PASARELA DE COBRO")
    centrar_ventana(win_pago, 980, 480) 
    win_pago.configure(bg="#2f3542") 
    win_pago.resizable(False, False)
    win_pago.transient(root)
    win_pago.grab_set()

    # PANEL SUPERIOR COMPARTIDO
    frame_cantidades_superior = tk.Frame(win_pago, bg="#1e222b", height=85)
    frame_cantidades_superior.pack(side="top", fill="x", padx=12, pady=10)
    frame_cantidades_superior.pack_propagate(False)

    f_total_izq = tk.Frame(frame_cantidades_superior, bg="#1e222b")
    f_total_izq.pack(side="left", expand=True, fill="both", pady=5)
    lbl_titulo_izq = tk.Label(f_total_izq, text="TOTAL POR LIQUIDAR", font=('Segoe UI', 12, 'bold'), fg="#a4b0be", bg="#1e222b")
    lbl_titulo_izq.pack(pady=(2,0))
    lbl_monto_restante_arriba = tk.Label(f_total_izq, text=f"${cuenta_restante_dinamica:.2f}", font=('Segoe UI', 24, 'bold'), fg="#2ed573", bg="#1e222b")
    lbl_monto_restante_arriba.pack()

    f_acumulado_der = tk.Frame(frame_cantidades_superior, bg="#1e222b")
    f_acumulado_der.pack(side="right", expand=True, fill="both", pady=5)
    tk.Label(f_acumulado_der, text="EFECTIVO RECIBIDO (ACUMULADO)", font=('Segoe UI', 12, 'bold'), fg="#a4b0be", bg="#1e222b").pack(pady=(2,0))
    lbl_monto_recibido_arriba = tk.Label(f_acumulado_der, text="$0.00", font=('Segoe UI', 24, 'bold'), fg="#1e90ff", bg="#1e222b")
    lbl_monto_recibido_arriba.pack()

    # CUERPO CENTRAL
    frame_cuerpo_central = tk.Frame(win_pago, bg="#2f3542")
    frame_cuerpo_central.pack(fill="both", expand=True, padx=12, pady=5) 

    # LADO IZQUIERDO: GRID DE BILLETES
    frame_billetes_grid = tk.Frame(frame_cuerpo_central, bg="#2f3542")
    frame_billetes_grid.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    for r in range(3): frame_billetes_grid.rowconfigure(r, weight=1)
    for c in range(2): frame_billetes_grid.columnconfigure(c, weight=1)

    billetes_config = [
        {"archivo": "b20.jpg", "alternativo": "20.jpg", "valor": 20, "color": "#74b9ff", "text": "$20", "row": 0, "col": 0},
        {"archivo": "b50.jpg", "alternativo": "50.jpg", "valor": 50, "color": "#dfe4ea", "text": "$50", "row": 0, "col": 1},
        {"archivo": "b100.jpg", "alternativo": "100.jpg", "valor": 100, "color": "#ff7675", "text": "$100", "row": 1, "col": 0},
        {"archivo": "b200.jpg", "alternativo": "200.jpg", "valor": 200, "color": "#55efc4", "text": "$200", "row": 1, "col": 1},
        {"archivo": "b500.jpg", "alternativo": "500.jpg", "valor": 500, "color": "#ffeaa7", "text": "$500", "row": 2, "col": 0},
        {"archivo": "b1000.jpg", "alternativo": "1000.jpg", "valor": 1000, "color": "#a55eea", "text": "$1000", "row": 2, "col": 1}
    ]

    def presionar_billete_modal(valor):
        global efectivo_acumulado_cajero
        efectivo_acumulado_cajero += valor
        lbl_monto_recibido_arriba.config(text=f"${efectivo_acumulado_cajero:.2f}")

    ruta_carpeta_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_imagenes = os.path.join(ruta_carpeta_actual, "imagenes")

    for b in billetes_config:
        ruta_img = os.path.join(ruta_imagenes, b["archivo"])
        if not os.path.exists(ruta_img):
            ruta_img = os.path.join(ruta_imagenes, b["alternativo"])

        if Image is not None and os.path.exists(ruta_img):
            try:
                img_o = Image.open(ruta_img)
                img_r = img_o.resize((190, 85), Image.Resampling.LANCZOS)
                img_tk = ImageTk.PhotoImage(img_r)
                btn = tk.Button(frame_billetes_grid, image=img_tk, bd=0, highlightthickness=0, relief="flat", bg="#2f3542", activebackground="#2f3542", cursor="hand2", command=lambda v=b["valor"]: presionar_billete_modal(v))
                btn.image = img_tk
            except Exception:
                btn = tk.Button(frame_billetes_grid, text=b["text"], font=('Segoe UI', 14, 'bold'), bg=b["color"], fg="#2f3542", bd=0, highlightthickness=0, relief="flat", cursor="hand2", command=lambda v=b["valor"]: presionar_billete_modal(v))
        else:
            btn = tk.Button(frame_billetes_grid, text=b["text"], font=('Segoe UI', 14, 'bold'), bg=b["color"], fg="#2f3542", bd=0, highlightthickness=0, relief="flat", cursor="hand2", command=lambda v=b["valor"]: presionar_billete_modal(v))
        
        btn.grid(row=b["row"], column=b["col"], padx=4, pady=3, sticky="nsew")

    # LADO DERECHO: PAD NUMÉRICO
    frame_derecha_teclas = tk.Frame(frame_cuerpo_central, bg="#2f3542")
    frame_derecha_teclas.pack(side="right", fill="both", expand=False, padx=(10, 0))

    lbl_tecleando_en_vivo = tk.Label(frame_derecha_teclas, text="$0.00", font=('Segoe UI', 11, 'italic'), fg="#a4b0be", bg="#2f3542", anchor="e")
    lbl_tecleando_en_vivo.pack(fill="x", pady=(0, 2))

    grid_teclado_num = tk.Frame(frame_derecha_teclas, bg="#2f3542")
    grid_teclado_num.pack(fill="both", expand=True)
    
    for i in range(5): grid_teclado_num.rowconfigure(i, weight=1)
    for i in range(3): grid_teclado_num.columnconfigure(i, weight=1)

    string_buffer_teclas = ""

    def presionar_tecla_chica(valor):
        global efectivo_acumulado_cajero
        nonlocal string_buffer_teclas
        if valor == "C": 
            string_buffer_teclas = ""
            efectivo_acumulado_cajero = 0.0
            lbl_monto_recibido_arriba.config(text="$0.00")
        elif valor == ".":
            if "." not in string_buffer_teclas: 
                string_buffer_teclas += "."
        else: 
            string_buffer_teclas += str(valor)
        
        if string_buffer_teclas:
            lbl_tecleando_en_vivo.config(text=f"${float(string_buffer_teclas) if string_buffer_teclas != '.' else 0.0:.2f}")
        else:
            lbl_tecleando_en_vivo.config(text="$0.00")

    def funcion_enter_sumar_chica():
        global efectivo_acumulado_cajero
        nonlocal string_buffer_teclas
        try:
            if string_buffer_teclas:
                monto_ingresado = float(string_buffer_teclas)
                efectivo_acumulado_cajero += monto_ingresado
                lbl_monto_recibido_arriba.config(text=f"${efectivo_acumulado_cajero:.2f}")
                string_buffer_teclas = "" 
                lbl_tecleando_en_vivo.config(text="$0.00") 
        except ValueError:
            messagebox.showerror("Error", "Monto no válido")

    botones_num = [
        ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
        ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
        ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
        ('C', 3, 0), ('0', 3, 1), ('.', 3, 2)
    ]

    for (t, r, c) in botones_num:
        color_fondo = "#ff4757" if t == "C" else "#3d4452"
        b_num = tk.Button(grid_teclado_num, text=t, font=('Segoe UI', 14, 'bold'), bg=color_fondo, fg="white", bd=0, relief="flat", width=6, height=1, cursor="hand2", command=lambda v=t: presionar_tecla_chica(v))
        b_num.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")

    b_horizontal_enter = tk.Button(grid_teclado_num, text="ENTER   ↵", font=('Segoe UI', 12, 'bold'), bg="#1e90ff", fg="white", bd=0, relief="flat", height=1, cursor="hand2", command=funcion_enter_sumar_chica)
    b_horizontal_enter.grid(row=4, column=0, columnspan=3, padx=3, pady=5, sticky="nsew")

    # PIE DE ACCIONES DE LA PASARELA
    frame_pie_acciones = tk.Frame(win_pago, bg="#2f3542")
    frame_pie_acciones.pack(fill="x", side="bottom", padx=12, pady=(10, 15))

    def guardar_registro_venta_final(efectivo_final, tarjeta_final):
        global df_ventas, productos_en_carrito, df_inventario, total_caja_actual
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        proporcion_efectivo = efectivo_final / total_caja_actual if total_caja_actual > 0 else 0.0
        proporcion_tarjeta = tarjeta_final / total_caja_actual if total_caja_actual > 0 else 0.0

        for r_id, codigo, nombre, p_venta, cant, ganancia_u, idx in productos_en_carrito:
            monto_item_total = p_venta * cant
            ganancia_total_item = ganancia_u * cant
            
            item_efectivo = monto_item_total * proporcion_efectivo
            item_tarjeta = monto_item_total * proporcion_tarjeta
            
            nueva_venta = pd.DataFrame([[fecha_hoy, codigo, nombre, item_efectivo, item_tarjeta, ganancia_total_item]], columns=df_ventas.columns)
            df_ventas = pd.concat([df_ventas, nueva_venta], ignore_index=True)
            
        if df_inventario is not None: df_inventario.to_csv("inventario.csv", index=False)
        if df_ventas is not None: df_ventas.to_csv("ventas.csv", index=False)

    def ejecutar_pago_final():
        global total_caja_actual, fondo_caja_efectivo, efectivo_acumulado_cajero, tarjeta_acumulado_cuenta
        nonlocal cuenta_restante_dinamica
        
        if string_buffer_teclas:
            try: efectivo_acumulado_cajero += float(string_buffer_teclas)
            except ValueError: pass

        if efectivo_acumulado_cajero < cuenta_restante_dinamica:
            messagebox.showerror("Efectivo Insuficiente", f"El efectivo acumulado (${efectivo_acumulado_cajero:.2f}) no cubre el restante de la cuenta (${cuenta_restante_dinamica:.2f}).")
            return
            
        cambio = efectivo_acumulado_cajero - cuenta_restante_dinamica
        efectivo_ingresado_neto = cuenta_restante_dinamica
        fondo_caja_efectivo += efectivo_ingresado_neto
        lbl_fondo_dinero.config(text=f"${fondo_caja_efectivo:.2f}")
        
        guardar_registro_venta_final(efectivo_ingresado_neto, tarjeta_acumulado_cuenta)
        win_pago.destroy()
        
        mostrar_pantalla_cambio(cambio, efectivo_acumulado_cajero, tarjeta_acumulado_cuenta, total_caja_actual)
        registrar_nueva_cuenta()
        actualizar_tablas_admin()

    def ejecutar_pago_tarjeta():
        global total_caja_actual, tarjeta_acumulado_cuenta, efectivo_acumulado_cajero
        nonlocal cuenta_restante_dinamica, string_buffer_teclas
        
        monto_tarjeta = 0.0
        if string_buffer_teclas:
            try:
                monto_tarjeta = float(string_buffer_teclas)
            except ValueError:
                messagebox.showerror("Error", "Cantidad no válida.")
                return
        
        if monto_tarjeta == 0.0:
            tarjeta_acumulado_cuenta += cuenta_restante_dinamica
            guardar_registro_venta_final(efectivo_acumulado_cajero, tarjeta_acumulado_cuenta)
            win_pago.destroy()
            mostrar_pantalla_cambio(0.00, 0.00, tarjeta_acumulado_cuenta, total_caja_actual)
            registrar_nueva_cuenta()
            actualizar_tablas_admin()
            return

        if monto_tarjeta < cuenta_restante_dinamica:
            cuenta_restante_dinamica -= monto_tarjeta
            tarjeta_acumulado_cuenta += monto_tarjeta
            string_buffer_teclas = "" 
            lbl_tecleando_en_vivo.config(text="$0.00")
            lbl_monto_restante_arriba.config(text=f"${cuenta_restante_dinamica:.2f}")
            return

        if monto_tarjeta >= cuenta_restante_dinamica:
            tarjeta_acumulado_cuenta += cuenta_restante_dinamica
            guardar_registro_venta_final(efectivo_acumulado_cajero, tarjeta_acumulado_cuenta)
            win_pago.destroy()
            mostrar_pantalla_cambio(0.00, 0.00, tarjeta_acumulado_cuenta, total_caja_actual)
            registrar_nueva_cuenta()
            actualizar_tablas_admin()

    img_btn_regresar = crear_imagen_boton_redondo(110, 50, 5, "#747d8c") 
    img_btn_tarjeta = crear_imagen_boton_redondo(260, 50, 5, "#2471a3")  
    img_btn_registrar = crear_imagen_boton_redondo(460, 50, 5, "#2ed573") 

    btn_regresar = tk.Button(frame_pie_acciones, text="⬅ Volver", font=('Segoe UI', 11, 'bold'), fg="white", bd=0, highlightthickness=0, compound="center", cursor="hand2", command=win_pago.destroy)
    if img_btn_regresar:
        btn_regresar.config(image=img_btn_regresar, bg="#2f3542", activebackground="#2f3542")
        btn_regresar.image = img_btn_regresar
    else:
        btn_regresar.config(bg="#747d8c", width=10, height=2)
    btn_regresar.pack(side="left", padx=5)
    
    btn_tarjeta = tk.Button(frame_pie_acciones, text="💳 Pago con Tarjeta", font=('Segoe UI', 13, 'bold'), fg="white", bd=0, highlightthickness=0, compound="center", cursor="hand2", command=ejecutar_pago_tarjeta)
    if img_btn_tarjeta:
        btn_tarjeta.config(image=img_btn_tarjeta, bg="#2f3542", activebackground="#2f3542")
        btn_tarjeta.image = img_btn_tarjeta
    else:
        btn_tarjeta.config(bg="#2471a3", width=24, height=2)
    btn_tarjeta.pack(side="left", padx=5)
    
    btn_registrar = tk.Button(frame_pie_acciones, text="✅ REGISTRAR VENTA Y COMPLETAR COBRO", font=('Segoe UI', 13, 'bold'), fg="white", bd=0, highlightthickness=0, compound="center", cursor="hand2", command=ejecutar_pago_final)
    if img_btn_registrar:
        btn_registrar.config(image=img_btn_registrar, bg="#2f3542", activebackground="#2f3542")
        btn_registrar.image = img_btn_registrar
    else:
        btn_registrar.config(bg="#2ed573", height=2, padx=15)
    btn_registrar.pack(side="right", padx=5)


# =========================================================================
# 📌 PANTALLA DE CAMBIO (CAMBIO ARRIBA, DESGLOSE ABAJO Y COLORES AJUSTADOS)
# =========================================================================
def mostrar_pantalla_cambio(cambio_monto, total_efectivo_recibido, total_tarjeta_recibido, cuenta_total):
    ventana_cambio = tk.Toplevel(root)
    ventana_cambio.title("RESUMEN DE COBRO & CAMBIO")
    centrar_ventana(ventana_cambio, 520, 420)
    ventana_cambio.configure(bg="#2f3542")
    ventana_cambio.resizable(False, False)
    ventana_cambio.transient(root)
    ventana_cambio.grab_set()
    
    tk.Label(ventana_cambio, text="¡COBRO EXITOSO!", font=('Segoe UI', 15, 'bold'), fg="#2ed573", bg="#2f3542").pack(pady=(15, 5))
    
    # 1. BLOQUE SUPERIOR: CAMBIO (Sombreado más oscuro y números en blanco)
    frame_cambio_superior = tk.Frame(ventana_cambio, bg="#16181c", bd=1, relief="solid")
    frame_cambio_superior.pack(fill="x", padx=30, pady=(10, 5), ipady=10)
    
    if cambio_monto > 0.005:
        tk.Label(frame_cambio_superior, text="CAMBIO A DEVOLVER FISICAMENTE:", font=('Segoe UI', 11, 'bold'), fg="#a4b0be", bg="#16181c").pack(pady=(5, 0))
        lbl_cambio_grande = tk.Label(frame_cambio_superior, text=f"${cambio_monto:.2f}", font=('Segoe UI', 38, 'bold'), fg="#ffffff", bg="#16181c")
        lbl_cambio_grande.pack()
    else:
        lbl_cambio_grande = tk.Label(frame_cambio_superior, text="Cuenta Liquidada Sin Cambio", font=('Segoe UI', 14, 'bold', 'italic'), fg="#ffffff", bg="#16181c")
        lbl_cambio_grande.pack(pady=15)
        
    # 2. BLOQUE INFERIOR: DESGLOSE (Sombreado intermedio, textos inclinados y números en blanco)
    frame_ticket_desglose = tk.Frame(ventana_cambio, bg="#22252a", bd=1, relief="solid")
    frame_ticket_desglose.pack(fill="x", padx=30, pady=(10, 10), ipady=8)
    
    # Fila de Total de la cuenta
    f_row_total = tk.Frame(frame_ticket_desglose, bg="#22252a")
    f_row_total.pack(fill="x", padx=25, pady=4)
    tk.Label(f_row_total, text="Total de la Cuenta:", font=('Segoe UI', 12, 'italic'), fg="#ffffff", bg="#22252a").pack(side="left")
    tk.Label(f_row_total, text=f"${cuenta_total:.2f}", font=('Segoe UI', 12, 'bold'), fg="#ffffff", bg="#22252a").pack(side="right")
    
    # Fila de Tarjeta (Si aplica)
    if total_tarjeta_recibido > 0.005:
        f_row_tarjeta = tk.Frame(frame_ticket_desglose, bg="#22252a")
        f_row_tarjeta.pack(fill="x", padx=25, pady=3)
        tk.Label(f_row_tarjeta, text="Registrado en Tarjeta:", font=('Segoe UI', 12, 'italic'), fg="#ced6e0", bg="#22252a").pack(side="left")
        tk.Label(f_row_tarjeta, text=f"${total_tarjeta_recibido:.2f}", font=('Segoe UI', 12, 'bold'), fg="#ffffff", bg="#22252a").pack(side="right")
        
    # Fila de Efectivo (Si aplica)
    if total_efectivo_recibido > 0.005:
        f_row_efectivo = tk.Frame(frame_ticket_desglose, bg="#22252a")
        f_row_efectivo.pack(fill="x", padx=25, pady=3)
        tk.Label(f_row_efectivo, text="Efectivo Recibido:", font=('Segoe UI', 12, 'italic'), fg="#ced6e0", bg="#22252a").pack(side="left")
        tk.Label(f_row_efectivo, text=f"${total_efectivo_recibido:.2f}", font=('Segoe UI', 12, 'bold'), fg="#ffffff", bg="#22252a").pack(side="right")
    
    # Botón Finalizar
    tk.Button(ventana_cambio, text="FINALIZAR OPERACIÓN", font=('Segoe UI', 11, 'bold'), bg="#747d8c", fg="white", bd=0, padx=30, pady=9, cursor="hand2", command=ventana_cambio.destroy).pack(side="bottom", pady=15)


# --- ADAPTADOR DE RESOLUCIÓN PROTEGIDO ---
def cambiar_dimensiones_interfaz(event):
    if btn_total_cobrar is None or entrada_scanner is None or estilo is None: 
        return
    try:
        ancho = root.winfo_width()
        if ancho > 1400:  
            estilo.configure("Treeview", font=('Segoe UI', 13), rowheight=38)
            estilo.configure("Treeview.Heading", font=('Segoe UI', 12, 'bold'))
            btn_total_cobrar.config(font=('Segoe UI', 24, 'bold'))
            entrada_scanner.config(font=('Segoe UI', 18))
        else:  
            estilo.configure("Treeview", font=('Segoe UI', 11), rowheight=32)
            estilo.configure("Treeview.Heading", font=('Segoe UI', 11, 'bold'))
            btn_total_cobrar.config(font=('Segoe UI', 18, 'bold'))
            entrada_scanner.config(font=('Segoe UI', 13))
    except Exception:
        pass


# --- INTERFAZ PRINCIPAL ---
root = tk.Tk()
root.title("Sistema de Caja Registradora")
root.geometry("1150x750")
root.configure(bg="#f1f2f6")

root.bind("<Configure>", cambiar_dimensiones_interfaz)

# CONFIGURACIÓN DE ESTILOS GLOBALES CORRECTA (SOLUCIÓN DEL ERROR PADX)
estilo = ttk.Style()
estilo.theme_use("clam")

# Aplicamos padding interno a las celdas y cabeceras globalmente usando ttk.Style
estilo.configure("Treeview", padding=[10, 5, 10, 5])
estilo.configure("Treeview.Heading", padding=[10, 5, 10, 5])

# BARRA DE NAVEGACIÓN SUPERIOR FIJA
frame_barra_superior_fija = tk.Frame(root, bg="#2f3542", height=45)
frame_barra_superior_fija.pack(side="top", fill="x")
frame_barra_superior_fija.pack_propagate(False)

btn_menu_barras = tk.Button(
    frame_barra_superior_fija, text="☰  Menú de Sistema", font=('Segoe UI', 11, 'bold'), bg="#2f3542", fg="white", 
    activebackground="#57606f", activeforeground="white", bd=0, relief="flat", padx=15, cursor="hand2",
    command=determinar_posicion_menu_dinamico
)
btn_menu_barras.pack(side="left", fill="y")


# CONTENEDOR DE PANTALLAS
contenedor_principal = tk.Frame(root, bg="#f1f2f6")
contenedor_principal.pack(fill="both", expand=True)

pestana_cobro = tk.Frame(contenedor_principal, bg="#f1f2f6")
pestana_admin = tk.Frame(contenedor_principal, bg="#f1f2f6")


# =========================================================================
# 📌 PANTALLA: TERMINAL DE COBRO 
# =========================================================================
pestana_cobro.rowconfigure(1, weight=1) 
pestana_cobro.columnconfigure(0, weight=1)

frame_scanner = ttk.LabelFrame(pestana_cobro, text=" Panel de Entrada ")
frame_scanner.grid(row=0, column=0, sticky="ew", padx=15, pady=10, ipady=8)

tk.Label(frame_scanner, text="Escanea o ingresa un código:", font=('Segoe UI', 11), bg="#f1f2f6").pack(side="left", padx=15, pady=5)
entrada_scanner = tk.Entry(frame_scanner, font=('Segoe UI', 13), width=25, bg="#ffffff", bd=2, relief="groove")
entrada_scanner.pack(side="left", padx=5, pady=5)
entrada_scanner.bind('<Return>', escanear_producto)

tk.Button(frame_scanner, text="↵ Registrar", font=('Segoe UI', 10, 'bold'), bg="#747d8c", fg="white", bd=0, padx=12, pady=4, command=escanear_producto, cursor="hand2").pack(side="left", padx=5)

lbl_status = tk.Label(frame_scanner, text="Esperando código...", font=('Segoe UI', 11, 'italic'), fg="#747d8c")
lbl_status.pack(side="left", padx=15, pady=5)


# TICKET / LISTA DE COMPRAS
frame_ticket = ttk.LabelFrame(pestana_cobro, text=" Lista de Compra Actual ")
frame_ticket.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)

tabla_caja = ttk.Treeview(frame_ticket, columns=["Eliminar", "Cantidad", "Producto", "Precio"], show="headings")
tabla_caja.heading("Eliminar", text="Quitar", anchor="center")
tabla_caja.heading("Cantidad", text="Cantidad", anchor="center")
tabla_caja.heading("Producto", text="Descripción del Producto", anchor="center")
tabla_caja.heading("Precio", text="Precio de Venta", anchor="center")

# LÍNEA CORREGIDA: Eliminado el 'padx' que causaba el TclError catastrófico
tabla_caja.column("Eliminar", width=100, anchor="center")
tabla_caja.column("Cantidad", width=120, anchor="center") 
tabla_caja.column("Producto", width=650, anchor="w")
tabla_caja.column("Precio", width=180, anchor="center")

tabla_caja.tag_configure("par", background="#ffffff")
tabla_caja.tag_configure("impar", background="#e9eaec") 

tabla_caja.pack(fill="both", expand=True, padx=10, pady=10)
tabla_caja.bind("<Button-1>", detectar_clic_tabla)

frame_inferior_control = tk.Frame(pestana_cobro, bg="#f1f2f6")
frame_inferior_control.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
frame_inferior_control.columnconfigure(0, weight=1)

btn_total_cobrar = tk.Button(
    frame_inferior_control, 
    text="COBRAR CUENTA  •  TOTAL: $0.00\n(Presione aquí para abrir pasarela de efectivo)", 
    font=('Segoe UI', 18, 'bold'), 
    bg="#2ed573", fg="#ffffff", activebackground="#26af5f", activeforeground="#ffffff",
    bd=0, pady=22, cursor="hand2", command=abrir_ventana_cobro
)
btn_total_cobrar.grid(row=0, column=0, sticky="ew")


# =========================================================================
# ☰ MENU DESPLEGABLE
# =========================================================================
menu_flotante = tk.Frame(root, bg="#22252a", bd=1, relief="solid")

lbl_tit_menu = tk.Label(menu_flotante, text="MENÚ DE SISTEMA", font=('Segoe UI', 10, 'bold'), bg="#16181c", fg="#95a5a6", pady=8, bd=1, relief="solid")
lbl_tit_menu.pack(fill="x")

def comando_navegar(pantalla):
    determinar_posicion_menu_dinamico() 
    mostrar_pantalla(pantalla)

opciones_menu = [
    ("🛒  Terminal de Cobro (Caja)", lambda: comando_navegar(pestana_cobro)),
    ("⚙️  Administración e Inventario", lambda: comando_navegar(pestana_admin)),
    ("📊  Reportes Rápidos", lambda: [determinar_posicion_menu_dinamico(), generar_grafica()]),
    ("❌  Cerrar Opciones", determinar_posicion_menu_dinamico)
]

for texto, cmd in opciones_menu:
    btn_opc = tk.Button(
        menu_flotante, text=texto, font=('Segoe UI', 11), bg="#22252a", fg="white",
        activebackground="#1e90ff", activeforeground="white", bd=0, anchor="w", padx=20, pady=10, cursor="hand2", command=cmd
    )
    btn_opc.pack(fill="x")


# =========================================================================
# 📌 PANTALLA: ADMINISTRACIÓN E INVENTARIO
# =========================================================================
pestana_admin.rowconfigure(0, weight=1)
pestana_admin.columnconfigure(0, weight=1)

notebook_interna = ttk.Notebook(pestana_admin)
notebook_interna.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

sub_arqueo = ttk.Frame(notebook_interna)
notebook_interna.add(sub_arqueo, text="  💵 Registro de Efectivo ")
frame_fondo = ttk.LabelFrame(sub_arqueo, text=" Balance de la Gaveta ")
frame_fondo.pack(padx=20, pady=20, fill="x", ipady=10)
lbl_fondo_dinero = tk.Label(frame_fondo, text=f"${fondo_caja_efectivo:.2f}", font=('Segoe UI', 28, 'bold'), fg="#1e90ff")
lbl_fondo_dinero.pack(anchor="w", padx=15, pady=5)

frame_ajuste = ttk.LabelFrame(sub_arqueo, text=" Ajustar Caja ")
frame_ajuste.pack(padx=20, pady=10, fill="x", ipady=10)
entrada_ajuste_fondo = tk.Entry(frame_ajuste, font=('Segoe UI', 12), width=15)
entrada_ajuste_fondo.pack(side="left", padx=15, pady=10)
tk.Button(frame_ajuste, text="Actualizar Dinero Físico", font=('Segoe UI', 11, 'bold'), bg="#747d8c", fg="white", bd=0, padx=15, pady=5, command=ajustar_fondo_manual, cursor="hand2").pack(side="left", pady=10)

sub_inv = ttk.Frame(notebook_interna)
notebook_interna.add(sub_inv, text=" Stock Real & Costos de Proveedor ")
if pd is not None:
    tabla_inv = ttk.Treeview(sub_inv, columns=list(df_inventario.columns), show="headings")
    for col in df_inventario.columns:
        tabla_inv.heading(col, text=col, anchor="center")
        tabla_inv.column(col, width=140, anchor="center")
    tabla_inv.pack(fill="both", expand=True, padx=5, pady=5)

sub_ganancias = ttk.Frame(notebook_interna)
notebook_interna.add(sub_ganancias, text=" Historial de Ventas & Ganancias ")
tabla_ganancias = ttk.Treeview(sub_ganancias, columns=["Mes", "Efectivo Total", "Tarjeta Total", "Ganancia Total Neta"], show="headings")
tabla_ganancias.heading("Mes", text="Mes", anchor="center")
tabla_ganancias.heading("Efectivo Total", text="Venta Efectivo", anchor="center")
tabla_ganancias.heading("Tarjeta Total", text="Venta Tarjeta", anchor="center")
tabla_ganancias.heading("Ganancia Total Neta", text="Ganancia Neta Consolidada", anchor="center")

tabla_ganancias.column("Mes", anchor="center", width=120)
tabla_ganancias.column("Efectivo Total", anchor="center", width=150)
tabla_ganancias.column("Tarjeta Total", anchor="center", width=150)
tabla_ganancias.column("Ganancia Total Neta", anchor="center", width=200)
tabla_ganancias.pack(fill="both", expand=True, padx=5, pady=5)

btn_grafica = tk.Button(pestana_admin, text="📊 Generar Gráfica de Ganancias del Mes", font=('Segoe UI', 11, 'bold'), bg="#1e90ff", fg="white", activebackground="#1071d1", padx=15, pady=8, bd=0, cursor="hand2", command=generar_grafica)
btn_grafica.grid(row=1, column=0, pady=10, sticky="e", padx=15)


# --- INICIALIZACIÓN ---
mostrar_pantalla(pestana_cobro)

if pd is not None:
    if df_inventario.empty:
        productos_prueba = [
            ["7501055300074", "Refresco de Botella 600ml", 12.00, 18.00, 50],
            ["7501000111205", "Papas Fritas Crujientes", 10.50, 16.00, 40],
            ["7501031301439", "Galletas de Chispas", 14.00, 22.00, 30]
        ]
        df_inventario = pd.DataFrame(productos_prueba, columns=df_inventario.columns)
        df_inventario.to_csv("inventario.csv", index=False)
    actualizar_tablas_admin()

root.mainloop()
