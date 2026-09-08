"""WarehouseModel: el mesa.Model que orquesta la simulación.

Responsabilidades:
  - Contener el ambiente físico (WarehouseEnvironment).
  - Crear y contener los agentes AGV.
  - Contener el MissionManager (coordinación de misiones).
  - Llevar el log de eventos (evidencia de comunicación/negociación).
  - Avanzar la simulación paso a paso (step()), disparando la subasta.

Relación con el ambiente: COMPOSICIÓN. El modelo "tiene un" ambiente. El
ambiente describe el mundo físico (grid, racks, docks, pallets); el modelo le
suma los agentes, el manager y la dinámica temporal.
"""

from mesa import Model

from warehouse.environment import WarehouseEnvironment
from warehouse.agv import AGVAgent
from warehouse.mission_manager import MissionManager

class WarehouseModel(Model):

    #Cada cuántos steps se abre una ronda de subasta
    AUCTION_INTERVAL = 3

    #Duración física de un step de simulación, en segundos. Convierte el tiempo
    #discreto (steps) a tiempo físico para los KPIs y el análisis. Configurable.
    SECONDS_PER_STEP = 1.0

    def __init__(self, num_agvs=4, seed=None, total_arrivals=12,
                 seconds_per_step=None):

        super().__init__(rng=seed)

        #Permite sobreescribir la duración del step al crear el modelo.
        if seconds_per_step is not None:
            self.seconds_per_step = seconds_per_step
        else:
            self.seconds_per_step = self.SECONDS_PER_STEP

        #Salvaguarda: si Mesa no dejó un generador utilizable (p. ej. con
        #seed=None en algunas versiones), creamos uno propio.
        import random as _random
        if not hasattr(self, "random") or self.random is None \
                or not hasattr(self.random, "sample"):
            self.random = _random.Random(seed)

        self.num_agvs = num_agvs

        #Mundo físico
        self.environment = WarehouseEnvironment(random=self.random)

        #Log de eventos para evidencia de comunicación y negociación
        self.event_log = []

        #Manager de misiones (NO decide quién ejecuta cada misión).
        #total_arrivals = tope de pallets que llegan en toda la simulación.
        self.mission_manager = MissionManager(
            self.environment, log=self.log, random=self.random,
            total_arrivals=total_arrivals,
        )

        #Contador de pasos de la simulación
        self.steps_taken = 0

        #Registro de movimientos por step (para detección anti-swap)
        self._moves_this_step = {}

        #Historial de métricas por step (para las gráficas de análisis):
        #  step, misiones completadas acumuladas, misiones pendientes,
        #  AGVs ocupados (busy). Se llena al final de cada step.
        self.history = {
            "step": [],
            "completed": [],
            "pending": [],
            "busy": [],
        }

        #Crear los AGVs en celdas de spawn válidas
        self.create_agvs()

        #Diccionario de historial de agentes
        self.agent_position_history = {}

        #Creacion de agentes en historia
        for agent in self.agents:
            self.agent_position_history[f"Agent_{agent.unique_id}"] = []
            self.agent_position_history[f"Agent_{agent.unique_id}"].append(agent.position)


    #Log
    def log(self, message):
        #Registra un evento en el log, prefijado con el step actual
        self.event_log.append(f"step {self.steps_taken:>3} | {message}")


    #Creación de agentes
    def create_agvs(self):
        #Crea n AGVs en celdas aleatorias válidas, sin repetir celda

        #Las celdas válidas las provee el ambiente con get_spawn_cells()
        spawn_cells = self.environment.get_spawn_cells()

        if self.num_agvs > len(spawn_cells):
            raise ValueError(
                f"Se pidieron {self.num_agvs} AGVs pero solo hay "
                f"{len(spawn_cells)} celdas disponibles para spawn."
            )

        #Elegir celdas distintas al azar
        chosen = self.random.sample(spawn_cells, self.num_agvs)

        for pos in chosen:
            cell = self.environment.grid[pos]
            AGVAgent(self, cell)  #se registra solo en self.agents

    @property
    def agvs(self):
        #Todos los agentes AGV del modelo
        return self.agents_by_type[AGVAgent]


    # Negociación por medio de subasta
    def run_auction(self):

          #1. El Manager anuncia una misión pendiente
          #2. Cada AGV disponible calcula su puja (distancia al origen)
          #3. El Manager registra al ganador (menor puja; si hay empate elije id menor)
          #4. El AGV ganador acepta la misión (pasa a BUSY, fija destino)

        #Recorrer las misiones pendientes hasta adjudicar UNA. Así una misión
        #que temporalmente nadie puede tomar (p. ej. por batería) NO bloquea a
        #las viables que están detrás en la cola.
        for mission in self.mission_manager.pending_missions():
            self.mission_manager.announce(mission)

            #Recolectar pujas. Cada AGV decide si compite y con cuánto.
            bids = []
            for agv in self.agvs:
                bid = agv.bid_for(mission)
                if bid is not None:
                    bids.append((agv, bid))
                    self.log(
                        f"[AGV{agv.unique_id} -> MANAGER] puja {mission.id}: "
                        f"dist={bid}"
                    )

            winner = self.mission_manager.award_mission(
                mission, bids, current_step=self.steps_taken
            )
            if winner is not None:
                winner.accept_mission(mission)
                self.log(
                    f"[AGV{winner.unique_id}] acepta {mission.id} y se dirige a "
                    f"O={mission.origin}."
                )
                return  #adjudicada una: fin de la ronda


    # Step
    #Registro de movimientos del step actual (para detección anti-swap).
    #Mapea origen -> destino de cada AGV que se movió en este step.
    def register_move(self, origin, dest):
        self._moves_this_step[origin] = dest

    def was_move_this_step(self, origin, dest):
        #True si algún AGV ya se movió este step desde `origin` hacia `dest`.
        #Se usa para impedir que dos AGVs intercambien celdas (swap).
        return self._moves_this_step.get(origin) == dest

    def step(self):
        #Avanza un paso de simulación

        #Reiniciar el registro de movimientos del step (anti-swap)
        self._moves_this_step = {}

        # Materializar llegadas de pallets (inbound) y outbounds cuyo retraso venció
        self.mission_manager.process_scheduled_arrivals(self.steps_taken)
        self.mission_manager.process_scheduled(self.steps_taken)

        #Ronda de subasta (al inicio del step correspondiente)
        if self.steps_taken % self.AUCTION_INTERVAL == 0:
            self.run_auction()

        #Reiniciar la bandera de movimiento de TODOS los AGVs antes de
        #activarlos. Debe hacerse aquí (no en el step individual del agente)
        #porque un AGV puede ser empujado por otro (_step_aside) ANTES de su
        #propio turno; si el reset fuera individual, su bandera reflejaría el
        #step anterior y podría moverse dos veces en un mismo step.
        for agv in self.agvs:
            agv._moved_this_step = False

        self.agents.shuffle_do("step")
        self.steps_taken += 1

        #Registrar métricas de este step para las gráficas de análisis.
        self._record_history()

        #Registramos posiciones de agentes
        for agent in self.agents:
            self.agent_position_history[f"Agent_{agent.unique_id}"].append(agent.position)

    def _record_history(self):
        #Guarda las métricas del step actual en el historial.
        missions = self.mission_manager.missions
        completed = sum(1 for m in missions if m.status == "completed")
        pending = sum(1 for m in missions if m.status == "pending")
        busy = sum(1 for a in self.agvs if a.status == AGVAgent.BUSY)

        self.history["step"].append(self.steps_taken)
        self.history["completed"].append(completed)
        self.history["pending"].append(pending)
        self.history["busy"].append(busy)

    def run(self, max_steps):
        #Corre la simulación un número fijo de pasos
        for _ in range(max_steps):
            self.step()


    # Resultados
    def results_table(self):
        #Devuelve la tabla de resultados básicos como texto
        #Incluye por AGV: misiones completadas, distancia recorrida, batería
        #final y estado final; más los totales de misiones

        lines = []
        lines.append("=" * 60)
        lines.append(f"RESULTADOS — {self.steps_taken} steps simulados")
        lines.append("=" * 60)
        header = f"{'AGV':>4} | {'misiones':>8} | {'distancia':>9} | {'batería':>7} | estado"
        lines.append(header)
        lines.append("-" * 60)

        total_missions = 0
        for agv in sorted(self.agvs, key=lambda a: a.unique_id):
            total_missions += agv.completed_missions
            lines.append(
                f"{agv.unique_id:>4} | {agv.completed_missions:>8} | "
                f"{agv.distance_traveled:>9} | {agv.battery:>6}% | {agv.status}"
            )

        lines.append("-" * 60)
        completed = sum(
            1 for m in self.mission_manager.missions if m.status == "completed"
        )
        lines.append(
            f"Misiones completadas (total): {completed}/"
            f"{len(self.mission_manager.missions)}"
        )
        lines.append(f"Suma de misiones por AGV: {total_missions}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def steps_to_minutes(self, steps):
        """Convierte una cantidad de steps a minutos usando seconds_per_step."""
        if steps is None:
            return None
        return steps * self.seconds_per_step / 60.0

    def kpis(self):
        """Calcula KPIs resumidos para el análisis, expresados en TIEMPO (min).

        El tiempo físico se obtiene de los steps vía seconds_per_step. Devuelve
        un dict:
          - completion_time_min: minutos hasta completar TODAS las misiones
            (None si no se completaron todas dentro de la simulación).
          - throughput_per_min: misiones completadas por minuto.
          - avg_mission_time_min: tiempo promedio de ejecución de una misión
            (desde que se asigna hasta que se completa), en minutos.
          - dist_per_mission: distancia total de la flota / misiones completadas
            (en celdas; métrica de eficiencia de recorrido).
          - load_imbalance: desviación estándar de misiones por AGV (0 = reparto
            perfectamente parejo; mayor = más desbalance).
          - utilization: fracción media de AGVs ocupados (0..1) en el tiempo.
        """
        import statistics

        missions = self.mission_manager.missions
        total_missions = len(missions)
        completed = sum(1 for m in missions if m.status == "completed")

        agvs = list(self.agvs)
        misiones_por_agv = [a.completed_missions for a in agvs]
        distancia_total = sum(a.distance_traveled for a in agvs)

        # Tiempo de completado (en steps): primer step en que se completó TODO.
        completion_step = None
        if total_missions > 0 and completed == total_missions:
            h = self.history
            for i, pend in enumerate(h["pending"]):
                if pend == 0 and h["completed"][i] == total_missions:
                    completion_step = h["step"][i]
                    break

        # Throughput: misiones por minuto. Si se completó TODO, se mide sobre el
        # tiempo de completado (no penaliza correr de más); si no, sobre el
        # tiempo total simulado.
        if completion_step is not None and completion_step > 0:
            span_steps = completion_step
        else:
            span_steps = self.steps_taken if self.steps_taken > 0 else 1
        span_min = span_steps * self.seconds_per_step / 60.0
        throughput_per_min = (completed / span_min) if span_min > 0 else 0.0

        # Tiempo promedio de ejecución de misión (asignación -> completado).
        durations_steps = [
            m.complete_step - m.start_step
            for m in missions
            if m.status == "completed"
            and m.start_step is not None and m.complete_step is not None
        ]
        if durations_steps:
            avg_mission_time_min = (
                statistics.mean(durations_steps) * self.seconds_per_step / 60.0
            )
        else:
            avg_mission_time_min = 0.0

        dist_per_mission = (distancia_total / completed) if completed > 0 else 0.0

        load_imbalance = (
            statistics.pstdev(misiones_por_agv) if len(misiones_por_agv) > 1 else 0.0
        )

        # Utilización media: promedio de (AGVs busy / total AGVs) por step.
        n_agvs = len(agvs) if agvs else 1
        busy_series = self.history["busy"]
        if busy_series:
            utilization = sum(busy_series) / (len(busy_series) * n_agvs)
        else:
            utilization = 0.0

        return {
            "completion_time_min": self.steps_to_minutes(completion_step),
            "throughput_per_min": throughput_per_min,
            "avg_mission_time_min": avg_mission_time_min,
            "dist_per_mission": dist_per_mission,
            "load_imbalance": load_imbalance,
            "utilization": utilization,
        }
