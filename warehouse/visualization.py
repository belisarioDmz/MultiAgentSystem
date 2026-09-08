"""Visualización del almacén con matplotlib.

- draw_frame(ax, model): dibuja el estado actual del modelo en un eje. Es la
  base reutilizada tanto por la vista estática como por la animación.
- visualize_warehouse(model): vista estática (una figura, un frame).
- animate_simulation(model, steps): animación con FuncAnimation que avanza la
  simulación y redibuja en cada frame.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.animation import FuncAnimation


def draw_frame(ax, model):
    """Dibuja el estado actual del modelo sobre el eje `ax` (lo limpia antes).

    Se usa tanto para la vista estática como para cada frame de la animación.
    """
    ax.clear()
    environment = model.environment

    # Capa transitable de fondo. Transponer (.T) para orientar X horizontal.
    walkable_data = environment.walkable_layer.data.T
    ax.imshow(
        walkable_data,
        cmap="Greens",
        origin="lower",  # (0,0) abajo a la izquierda
        extent=(-0.5, environment.width - 0.5, -0.5, environment.height - 0.5),
        alpha=0.25,
    )

    # Racks
    for rack in environment.racks:
        for x, y in rack.cells:
            ax.add_patch(
                Rectangle(
                    (x - 0.5, y - 0.5), 1, 1,
                    facecolor="dimgray", edgecolor="black", linewidth=1,
                )
            )
        xs = [x for x, y in rack.cells]
        ys = [y for x, y in rack.cells]
        ax.text(
            sum(xs) / len(xs), sum(ys) / len(ys), f"R{rack.id}",
            ha="center", va="center", fontsize=11, fontweight="bold",
            color="white",
        )

    # Entradas (inbound)
    entry_x = [x for x, y in environment.product_entries]
    entry_y = [y for x, y in environment.product_entries]
    ax.scatter(entry_x, entry_y, s=150, marker=">", label="Receiving Dock")

    # Salidas (truck dock)
    exit_x = [x for x, y in environment.product_exits]
    exit_y = [y for x, y in environment.product_exits]
    ax.scatter(exit_x, exit_y, s=150, marker="<", label="Truck Dock")

    # Estaciones de carga
    charge_x = [x for x, y in environment.charging_stations]
    charge_y = [y for x, y in environment.charging_stations]
    ax.scatter(charge_x, charge_y, s=180, marker="o", label="Charging Station")

    # Pallets (productos) que NO están siendo transportados (los transportados
    # se dibujan junto a su AGV para no duplicar el marcador).
    pallet_drawn = False
    carried_ids = {
        agv.carried_product.id
        for agv in getattr(model, "agvs", [])
        if getattr(agv, "carried_product", None) is not None
    }
    for product in getattr(environment, "products", []):
        #No dibujar: sin posición, cargado por un AGV, o ya despachado
        #(delivered -> salió del almacén, no debe seguir apareciendo).
        if product.position is None or product.id in carried_ids:
            continue
        if product.status == "delivered":
            continue
        x, y = product.position
        ax.add_patch(
            Rectangle(
                (x - 0.3, y - 0.3), 0.6, 0.6,
                facecolor="orange", edgecolor="black", linewidth=1, zorder=5,
                label="Pallet" if not pallet_drawn else None,
            )
        )
        ax.text(
            x, y + 0.45, product.id, ha="center", va="bottom",
            fontsize=7, fontweight="bold", color="darkorange", zorder=6,
        )
        pallet_drawn = True

    # AGVs
    agv_drawn = False
    for agv in getattr(model, "agvs", []):
        if agv.position is None:
            continue
        x, y = agv.position
        # Color según estado: cargando -> verde, con pallet -> naranja borde.
        facecolor = "seagreen" if agv.status == "charging" else "royalblue"
        ax.add_patch(
            Circle(
                (x, y), 0.4,
                facecolor=facecolor, edgecolor="black", linewidth=1, zorder=7,
                label="AGV" if not agv_drawn else None,
            )
        )
        ax.text(
            x, y, str(agv.unique_id), ha="center", va="center",
            fontsize=8, fontweight="bold", color="white", zorder=8,
        )
        # Si carga un pallet, dibujar un cuadrito encima del AGV.
        if getattr(agv, "carried_product", None) is not None:
            ax.add_patch(
                Rectangle(
                    (x - 0.18, y + 0.12), 0.36, 0.28,
                    facecolor="orange", edgecolor="black", linewidth=0.8,
                    zorder=9,
                )
            )
        # batería y estado debajo del AGV
        ax.text(
            x, y - 0.55, f"{agv.battery}%·{agv.status[:4]}",
            ha="center", va="top", fontsize=6, color="navy", zorder=8,
        )
        agv_drawn = True

    # Grid y ejes
    ax.set_xticks(range(environment.width))
    ax.set_yticks(range(environment.height))
    ax.grid(True, linewidth=0.5, alpha=0.35)
    ax.set_xlim(-0.5, environment.width - 0.5)
    ax.set_ylim(-0.5, environment.height - 0.5)
    ax.set_aspect("equal")

    # Título con métricas de la simulación
    completed = sum(
        1 for m in model.mission_manager.missions if m.status == "completed"
    ) if hasattr(model, "mission_manager") else 0
    total = len(model.mission_manager.missions) if hasattr(model, "mission_manager") else 0
    ax.set_title(
        f"Warehouse — step {getattr(model, 'steps_taken', 0)} — "
        f"misiones {completed}/{total}",
        fontsize=15, fontweight="bold",
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    # Leyenda (añade el rack como parche manual)
    handles, labels = ax.get_legend_handles_labels()
    rack_legend = Rectangle((0, 0), 1, 1, facecolor="dimgray", edgecolor="black")
    handles.insert(0, rack_legend)
    labels.insert(0, "Rack")
    ax.legend(
        handles, labels, loc="upper center",
        bbox_to_anchor=(0.5, -0.06), ncol=3,
    )


def visualize_warehouse(model):
    """Vista estática: dibuja el estado actual del modelo en una figura."""
    fig, ax = plt.subplots(figsize=(10, 10))
    draw_frame(ax, model)
    plt.tight_layout()
    plt.show()


def animate_simulation(model, steps=120, interval=400):
    """Anima la simulación avanzando `steps` pasos.

    Cada frame avanza la simulación un step (model.step()) y redibuja el
    estado. `interval` es el tiempo entre frames en milisegundos. Se muestra
    en ventana interactiva (decisión: por ahora solo ventana).

    Devuelve el objeto FuncAnimation (hay que mantener una referencia viva
    mientras se muestra, si no matplotlib puede descartarlo).
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    def update(frame):
        # Frame 0 muestra el estado inicial; a partir de ahí se avanza.
        if frame > 0:
            model.step()
        draw_frame(ax, model)
        return ax.patches

    anim = FuncAnimation(
        fig, update, frames=steps + 1, interval=interval, repeat=False,
    )
    plt.tight_layout()
    plt.show()
    return anim


def plot_results(model, titulo=""):
    """Panel de resultados en una sola figura: tabla arriba + gráficas abajo.

    - Tabla: por AGV -> misiones completadas, distancia, batería y estado final;
      más una fila de totales. Reemplaza a la tabla de texto de la terminal.
    - Gráficas de barras: misiones completadas y distancia por AGV.

    Usa los datos finales que ya guarda cada AGV (`completed_missions` y
    `distance_traveled`). Útil para el análisis de desempeño / comparación.
    """
    agvs = sorted(model.agvs, key=lambda a: a.unique_id)
    ids = [f"AGV{a.unique_id}" for a in agvs]
    misiones = [a.completed_missions for a in agvs]
    distancias = [a.distance_traveled for a in agvs]

    total_completadas = sum(
        1 for m in model.mission_manager.missions if m.status == "completed"
    )
    total_misiones = len(model.mission_manager.missions)

    kpis = model.kpis()

    # Layout dinámico según el número de AGVs: más AGVs = tabla más alta, para
    # que las filas no se apretujen contra el título ni la franja de KPIs.
    n_agvs = len(agvs)
    tabla_ratio = 0.6 + 0.18 * n_agvs          # crece con el número de AGVs
    fig_height = 7 + 0.35 * n_agvs             # figura más alta si hay más filas

    # Figura con 3 filas: 0 = franja de KPIs, 1 = tabla, 2 = gráficas de barras.
    fig = plt.figure(figsize=(12, fig_height))
    gs = fig.add_gridspec(
        3, 2, height_ratios=[0.5, tabla_ratio, 1.4], hspace=0.55, wspace=0.25
    )

    # --- Franja de KPIs (fila 0, ancho completo) ---
    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis("off")

    ct = kpis["completion_time_min"]
    ct_txt = f"{ct:.1f} min" if ct is not None else "no completado"
    tarjetas = [
        ("Tiempo de completado", ct_txt),
        ("Throughput", f"{kpis['throughput_per_min']:.2f} mis/min"),
        ("T. medio misión", f"{kpis['avg_mission_time_min']:.2f} min"),
        ("Distancia/misión", f"{kpis['dist_per_mission']:.1f} celdas"),
        ("Desbalance carga", f"{kpis['load_imbalance']:.2f}"),
        ("Utilización flota", f"{kpis['utilization'] * 100:.0f}%"),
    ]
    n = len(tarjetas)
    for i, (label, value) in enumerate(tarjetas):
        cx = (i + 0.5) / n  # centro horizontal de cada tarjeta
        ax_kpi.text(cx, 0.68, value, ha="center", va="center",
                    fontsize=15, fontweight="bold", color="#1A237E",
                    transform=ax_kpi.transAxes)
        ax_kpi.text(cx, 0.28, label, ha="center", va="center",
                    fontsize=9, color="#455A64", transform=ax_kpi.transAxes)
    ax_kpi.set_title("KPIs", fontsize=12, fontweight="bold", loc="left")

    # --- Tabla (fila 1, abarca las dos columnas) ---
    ax_tabla = fig.add_subplot(gs[1, :])
    ax_tabla.axis("off")

    col_labels = ["AGV", "Misiones", "Distancia", "Batería", "Estado"]
    filas = []
    for a in agvs:
        filas.append([
            str(a.unique_id),
            str(a.completed_missions),
            str(a.distance_traveled),
            f"{a.battery}%",
            a.status,
        ])
    # Fila de totales
    filas.append([
        "TOTAL",
        f"{total_completadas}/{total_misiones}",
        str(sum(distancias)),
        "",
        "",
    ])

    tabla = ax_tabla.table(
        cellText=filas,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(10)
    tabla.scale(1, 1.3)

    # Color sobrio: encabezado azul, filas alternas gris claro, totales resaltada.
    header_color = "#37474F"   # gris azulado oscuro
    row_a = "#ECEFF1"          # gris muy claro
    row_b = "#FFFFFF"          # blanco
    total_color = "#CFD8DC"    # gris para la fila de totales
    n_cols = len(col_labels)
    n_filas = len(filas)
    for (r, c), cell in tabla.get_celld().items():
        cell.set_edgecolor("#B0BEC5")
        if r == 0:  # encabezado
            cell.set_facecolor(header_color)
            cell.set_text_props(color="white", fontweight="bold")
        elif r == n_filas:  # última fila = totales
            cell.set_facecolor(total_color)
            cell.set_text_props(fontweight="bold")
        else:
            cell.set_facecolor(row_a if r % 2 else row_b)

    sim_min = model.steps_taken * getattr(model, "seconds_per_step", 1.0) / 60.0
    ax_tabla.set_title(
        f"Resultados — {sim_min:.1f} min simulados ({model.steps_taken} steps)",
        fontsize=13, fontweight="bold", pad=4,
    )

    # --- Gráfica 1: misiones por AGV (fila inferior izquierda) ---
    ax1 = fig.add_subplot(gs[2, 0])
    bars1 = ax1.bar(ids, misiones, color="royalblue", edgecolor="black")
    ax1.set_title("Misiones completadas por AGV")
    ax1.set_ylabel("Misiones completadas")
    ax1.set_xlabel("AGV")
    ax1.bar_label(bars1)
    ax1.set_yticks(range(0, max(misiones + [1]) + 1))

    # --- Gráfica 2: distancia por AGV (fila inferior derecha) ---
    ax2 = fig.add_subplot(gs[2, 1])
    bars2 = ax2.bar(ids, distancias, color="seagreen", edgecolor="black")
    ax2.set_title("Distancia recorrida por AGV")
    ax2.set_ylabel("Distancia (celdas)")
    ax2.set_xlabel("AGV")
    ax2.bar_label(bars2)

    if titulo:
        fig.suptitle(titulo, fontsize=15, fontweight="bold")

    plt.show()


def plot_time_series(model, titulo=""):
    """Gráficas de la evolución temporal de la simulación (análisis dinámico).

    Tres series a lo largo del TIEMPO en minutos (del historial del modelo):
      #6 misiones completadas acumuladas (throughput);
      #7 misiones pendientes (vaciado de la cola);
      #9 AGVs ocupados (utilización de la flota).
    """
    h = model.history
    # Eje X en minutos (steps convertidos con seconds_per_step).
    spm = getattr(model, "seconds_per_step", 1.0)
    minutes = [s * spm / 60.0 for s in h["step"]]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    # #6 Misiones completadas acumuladas (throughput)
    ax1.plot(minutes, h["completed"], color="royalblue", linewidth=2)
    ax1.set_title("Misiones completadas acumuladas (throughput)")
    ax1.set_ylabel("Completadas")
    ax1.grid(True, alpha=0.3)

    # #7 Misiones pendientes vs tiempo (vaciado de la cola)
    ax2.plot(minutes, h["pending"], color="darkorange", linewidth=2)
    ax2.set_title("Misiones pendientes (cola de trabajo)")
    ax2.set_ylabel("Pendientes")
    ax2.grid(True, alpha=0.3)

    # #9 AGVs ocupados vs tiempo (utilización de la flota)
    ax3.plot(minutes, h["busy"], color="seagreen", linewidth=2)
    ax3.set_title("AGVs ocupados (utilización de la flota)")
    ax3.set_ylabel("AGVs busy")
    ax3.set_xlabel("Tiempo (min)")
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, len(model.agvs) + 0.5)

    if titulo:
        fig.suptitle(titulo, fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.show()
