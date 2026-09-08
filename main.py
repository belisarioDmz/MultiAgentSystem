"""Punto de entrada del proyecto de almacén multi-agente (M4).

Ejecuta:
    python main.py

Crea el modelo (ambiente + AGVs + misiones), anima la simulación en una
ventana interactiva y al terminar muestra:
  - un panel de resultados (tabla + gráficas de barras) en una ventana,
  - el log de comunicación/negociación en la terminal.
"""

from warehouse import (
    WarehouseModel,
    animate_simulation,
    plot_results,
    plot_time_series,
)

import requests

def send_agent_data_to_unity(agents_data, url="http://localhost:5005/"):
    payload = {
        "agents": [
            {"id": agent_id, "positions": [[int(p[0]), int(p[1])] for p in positions]}
            for agent_id, positions in agents_data.items()
        ]
    }

    print(payload)

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Sent successfully: {response.json()}")
        print(f"Agents sent: {len(payload["agents"])}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send data to Unity: {e}")

# Parámetros de la simulación (configurables).
NUM_AGVS = 3
SEED = 42
TOTAL_ARRIVALS = 5   # pallets que llegan en total durante la simulación
STEPS = 155         # con más llegadas, sube esto para ver el flujo completo


def main():
    model = WarehouseModel(
        num_agvs=NUM_AGVS, seed=SEED, total_arrivals=TOTAL_ARRIVALS
    )

    # Animación en ventana interactiva. Avanza STEPS pasos.
    animate_simulation(model, steps=STEPS, interval=200)

    # Panel de resultados: tabla + gráficas de barras (en una ventana).
    plot_results(model, titulo=f"Escenario: {NUM_AGVS} AGVs")

    # Análisis dinámico: evolución temporal (throughput, cola, utilización).
    plot_time_series(model, titulo=f"Evolución temporal — {NUM_AGVS} AGVs")

    # La terminal queda solo para la evidencia de comunicación y negociación.
    print("=== LOG DE COMUNICACIÓN / NEGOCIACIÓN ===")
    for line in model.event_log:
        print(line)

    # Envio de datos a Unity
    send_agent_data_to_unity(model.agent_position_history)


if __name__ == "__main__":
    main()
