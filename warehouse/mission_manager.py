"""MissionManager: coordina las misiones, pero NO decide quién las ejecuta.

Rol (según el enunciado):
  - Mantiene la lista de misiones.
  - Publica misiones pendientes (las anuncia a los AGVs).
  - Registra qué AGV aceptó una misión (el ganador de la subasta).
  - Registra la finalización de misiones.

Restricción central del enunciado:
  El Manager NO selecciona centralmente qué AGV ejecuta cada misión. La
  selección EMERGE de la negociación: los AGVs calculan su puja y el Manager
  solo compara las pujas recibidas y registra al ganador. La "inteligencia" de
  la decisión vive en los agentes, no en el Manager.

Protocolo de negociación (Contract Net simplificado), por ronda de subasta:
  1. announce_mission()  -> el Manager anuncia una misión pendiente.
  2. cada AGV disponible calcula su puja (bid) para esa misión.
  3. award_mission()     -> el Manager compara pujas y registra al ganador.
"""

from warehouse.mission import Mission

class MissionManager:

    #Rango del retraso aleatorio (en steps) para generar una outbound tras
    #almacenarse un pallet.
    OUTBOUND_DELAY_MIN = 3
    OUTBOUND_DELAY_MAX = 10

    #Rango del retraso aleatorio (en steps) para que llegue un nuevo pallet a
    #una entrada liberada (llegadas continuas / inbound dinámico).
    ARRIVAL_DELAY_MIN = 3
    ARRIVAL_DELAY_MAX = 10

    def __init__(self, environment, log=None, random=None, total_arrivals=12):

        self.environment = environment

        #Función de logging inyectada por el modelo (para la evidencia visible
        #de comunicación/negociación). Si no se pasa, no registra nada
        self._log = log if log is not None else (lambda msg: None)

        #Generador aleatorio compartido con el modelo (reproducibilidad)
        self._random = random if random is not None else environment.random

        #Lista completa de misiones (en todos los estados)
        self.missions = []

        #Contadores para ids únicos y para rotar la salida de las outbound
        self._mission_counter = 0
        self._exit_rotation = 0
        self._rack_rotation = 0  #para repartir inbound entre racks distintos

        #Outbounds programadas pero aún no publicadas
        #Se materializan cuando la simulación alcanza due_step (ver process_scheduled).
        self._scheduled_outbound = []

        #Llegadas continuas de pallets (inbound dinámico):
        # - total_arrivals: tope de pallets a generar en TODA la simulación.
        # - _arrivals_generated: cuántos se han generado ya (incluye iniciales).
        # - _product_counter: para ids únicos de producto (P001, P002, ...).
        # - _scheduled_arrivals: llegadas programadas pendientes de materializar.
        self.total_arrivals = total_arrivals
        self._arrivals_generated = 0
        self._product_counter = 0
        self._scheduled_arrivals = []

        self.create_missions()

    def _next_mission_id(self):
        self._mission_counter += 1
        return f"M{self._mission_counter:03d}"

    def _next_product_id(self):
        self._product_counter += 1
        return f"P{self._product_counter:03d}"


    #Creación misiones INBOUND iniciales
    def create_missions(self):
        #Toma los pallets iniciales que ya creó el ambiente (uno por entrada) y
        #les crea su misión INBOUND. Estos cuentan dentro de total_arrivals.
        env = self.environment
        for product in env.products:
            product.id = self._next_product_id()  #id consistente con el contador
            self._create_inbound_for(product)
            self._arrivals_generated += 1

    def _create_inbound_for(self, product):
        #Crea una misión INBOUND para `product`, reservando una celda libre de
        #rack. Devuelve la misión, o None si NO hay celda libre en ningún rack
        #(en ese caso el llamador decide posponer).
        destination = self._reserve_in_any_rack(product)
        if destination is None:
            return None
        mission = Mission(
            mission_id=self._next_mission_id(),
            origin=product.position,
            destination=destination,
            product=product,
            mission_type=Mission.INBOUND,
        )
        self.missions.append(mission)
        return mission

    def _reserve_in_any_rack(self, product):
        #Reserva una celda libre repartiendo entre racks DISTINTOS de forma
        #rotatoria (para que el movimiento se distribuya por todo el almacén).
        #Empieza por el rack rotatorio; si está lleno, prueba los siguientes.
        #Devuelve la celda o None si todos los racks están llenos.
        racks = self.environment.racks
        n = len(racks)
        for offset in range(n):
            rack = racks[(self._rack_rotation + offset) % n]
            cell = rack.reserve_cell(product)
            if cell is not None:
                #Avanzar la rotación para que la próxima misión empiece en otro rack.
                self._rack_rotation = (self._rack_rotation + offset + 1) % n
                return cell
        return None

    #Llegadas continuas de pallets (inbound dinámico)
    def schedule_arrival(self, entry, current_step):
        #Programa la llegada de un NUEVO pallet a una entrada liberada, con un
        #retraso aleatorio. No hace nada si ya se alcanzó el tope total_arrivals
        #(contando las ya generadas + las ya programadas).
        pending_scheduled = len(self._scheduled_arrivals)
        if self._arrivals_generated + pending_scheduled >= self.total_arrivals:
            return  #ya no llegan más pallets

        delay = self._random.randint(
            self.ARRIVAL_DELAY_MIN, self.ARRIVAL_DELAY_MAX
        )
        due = current_step + delay
        self._scheduled_arrivals.append({"entry": entry, "due_step": due})
        self._log(
            f"[MANAGER] Programa LLEGADA de pallet a entrada {entry} "
            f"en step {due} (retraso {delay})."
        )

    def process_scheduled_arrivals(self, current_step):
        #Materializa las llegadas cuyo retraso venció (llamar cada step).
        #Para cada llegada vencida:
        #  - si la entrada está libre Y hay celda de rack disponible -> crea el
        #    pallet en la entrada + su misión inbound.
        #  - si la entrada está ocupada o NO hay celda libre en ningún rack ->
        #    POSPONE (se reintenta en el siguiente step).
        still_waiting = []
        for item in self._scheduled_arrivals:
            if item["due_step"] > current_step:
                still_waiting.append(item)
                continue

            entry = item["entry"]

            #¿La entrada está libre? (que no haya ya un pallet esperando ahí)
            entry_occupied = any(
                p.position == entry and p.status == p.WAITING_FOR_PICKUP
                for p in self.environment.products
            )
            #¿Hay celda de rack libre en algún rack?
            has_free_rack = any(not r.is_full() for r in self.environment.racks)

            if entry_occupied or not has_free_rack:
                #Posponer: reintentar el próximo step.
                item["due_step"] = current_step + 1
                still_waiting.append(item)
                continue

            #Crear el pallet nuevo en la entrada y su misión inbound.
            product = self.environment.create_product(
                self._next_product_id(), entry
            )
            mission = self._create_inbound_for(product)
            if mission is None:
                #Carrera rara: se llenó justo ahora. Deshacer y posponer.
                self.environment.remove_product(product)
                self._product_counter -= 1
                item["due_step"] = current_step + 1
                still_waiting.append(item)
                continue

            self._arrivals_generated += 1
            self._log(
                f"[MANAGER] LLEGA pallet {product.id} a entrada {entry} "
                f"({self._arrivals_generated}/{self.total_arrivals}); "
                f"crea inbound {mission.id}."
            )
        self._scheduled_arrivals = still_waiting


    #Creación Misiones OUTBOUND (dinámicas)
    def schedule_outbound(self, product, current_step):
        #Programa una misión OUTBOUND para un pallet recién almacenado
        #Se agenda con un retraso aleatorio
        delay = self._random.randint(
            self.OUTBOUND_DELAY_MIN, self.OUTBOUND_DELAY_MAX
        )
        due = current_step + delay
        self._scheduled_outbound.append({"product": product, "due_step": due})
        self._log(
            f"[MANAGER] Programa OUTBOUND para {product.id} "
            f"en step {due} (retraso {delay})."
        )

    def process_scheduled(self, current_step):
        #Materializa las outbounds cuyo retraso ya venció
        #Convierte cada outbound programada vencida en una misión PENDING
        exits = self.environment.product_exits
        still_waiting = []
        for item in self._scheduled_outbound:
            if item["due_step"] > current_step:
                still_waiting.append(item)
                continue

            product = item["product"]
            #Rotar la salida de despacho
            destination = exits[self._exit_rotation % len(exits)]
            self._exit_rotation += 1

            mission = Mission(
                mission_id=self._next_mission_id(),
                origin=product.position,   #donde está almacenado el pallet
                destination=destination,
                product=product,
                mission_type=Mission.OUTBOUND,
            )
            self.missions.append(mission)
            self._log(
                f"[MANAGER] Crea OUTBOUND {mission.id}: {product.id} "
                f"O={mission.origin} -> D={destination} (truck dock)."
            )
        self._scheduled_outbound = still_waiting

    #Consultas

    def pending_missions(self):
        return [m for m in self.missions if m.status == Mission.PENDING]

    def has_pending(self):
        return len(self.pending_missions()) > 0

    def all_completed(self):
        return all(m.status == Mission.COMPLETED for m in self.missions)


    # Protocolo de negociación

    def announce(self, mission):
        #Publica una misión concreta a los AGVs (registra el mensaje en el log).
        self._log(
            f"[MANAGER -> AGVs] Publica {mission.id}: "
            f"O={mission.origin} D={mission.destination} "
            f"P={mission.product.id}"
        )

    def award_mission(self, mission, bids, current_step=None):
        #Registra al ganador de la subasta a partir de las pujas recibidas
        #`bids` es una lista de tuplas (agv, bid_value)
        #El Manager NO decide
        if not bids:
            self._log(f"[MANAGER] {mission.id} sin pujas: nadie disponible.")
            return None

        #Menor puja gana; empate -> id más bajo
        winner, best_bid = min(bids, key=lambda b: (b[1], b[0].unique_id))

        mission.status = Mission.ASSIGNED
        mission.assigned_agv = winner
        #Registrar el step de inicio (para medir el tiempo de ejecución).
        mission.start_step = current_step

        self._log(
            f"[MANAGER] {mission.id} adjudicada a AGV{winner.unique_id} "
            f"(puja={best_bid}). Deja de estar disponible."
        )
        return winner

    def complete_mission(self, mission, current_step=None):
        #Registra que una misión fue completada
        mission.status = Mission.COMPLETED
        #Registrar el step de finalización (para medir el tiempo de ejecución).
        mission.complete_step = current_step
        self._log(
            f"[MANAGER] {mission.id} completada por "
            f"AGV{mission.assigned_agv.unique_id if mission.assigned_agv else '?'}."
        )
