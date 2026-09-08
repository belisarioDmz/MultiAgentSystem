"""Agente AGV (Automated Guided Vehicle).

Cada AGV es un agente autónomo que vive en el grid del almacén. Hereda de
CellAgent (mesa.discrete_space), por lo que su posición física es la celda en
la que está colocado: se accede vía `self.cell.coordinate`.

Fase 3 — movimiento y batería:
  - Movimiento 1 celda por step, en 4 direcciones ortogonales (arriba, abajo,
    izquierda, derecha). NO se permiten diagonales.
  - Ruteo con BFS respetando obstáculos; la métrica de distancia es Manhattan
    (la correcta cuando el movimiento es solo ortogonal).
  - Batería: se descarga al moverse; por debajo de un umbral el AGV va a la
    estación de carga más cercana y recarga hasta una batería objetivo.
  - Colisiones: resolución por prioridad (ver WarehouseModel / helpers).

NOTA: el grid tiene capacidad ilimitada por celda, así que la exclusión "una
celda = un AGV" la gestionamos nosotros consultando las celdas ocupadas.
"""

from collections import deque

from mesa.discrete_space import CellAgent
def chebyshev(a, b):
    #Distancia de Chebyshev entre dos celdas (permite diagonales)
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def manhattan(a, b):
    #Distancia de Manhattan (sin diagonales). manhattan==1 significa que las
    #celdas comparten un lado: el AGV está "de frente" a la celda.
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class AGVAgent(CellAgent):

    #Estados del AGV
    AVAILABLE = "available"  #libre, puede competir por misiones
    BUSY = "busy"            #ejecutando una misión
    CHARGING = "charging"    #yendo a cargar o cargando


    #Sub-fases internas del ciclo de misión (detalle de status=BUSY)
    PHASE_TO_ORIGIN = "to_origin"            #yendo a recoger el pallet
    PHASE_TO_DESTINATION = "to_destination"  #transportando el pallet al destino

    #Parámetros de batería
    BATTERY_FULL = 100          #batería inicial
    DISCHARGE_PER_MOVE = 1      # % que se descarga por cada celda movida
    RECHARGE_THRESHOLD = 30     # % por debajo del cual el AGV va a cargar
    RECHARGE_PER_STEP = 5       # % que recarga por step en la estación
    RECHARGE_TARGET = 80        # % objetivo al que carga antes de volver
    SAFETY_MARGIN = 0.20        # margen de seguridad (20%) sobre el costo estimado

    def __init__(self, model, cell, battery=None):
        super().__init__(model)

        #Posición física, colca al agente en su celda
        self.cell = cell

        #Estado interno del AGV
        self.battery = battery if battery is not None else self.BATTERY_FULL
        self.status = AGVAgent.AVAILABLE
        self.mission = None       #misión asignada actualmente
        self.task_phase = None    #sub-fase del ciclo de misión
        self.carried_product = None  #pallet que carga ahora mismo

        #Destino actual al que se dirige (celda (x, y) o None)
        self.destination = None

        #Ruta actual (lista de celdas a seguir), calculada con BFS
        self.path = []
        self._path_goal = None  # objetivo para el que se calculó self.path

        # Bandera para no moverse dos veces en el mismo step (ver colisiones)
        self._moved_this_step = False

        # étricas para los resultados finales
        self.distance_traveled = 0   #celdas recorridas
        self.completed_missions = 0  #misiones entregadas


    #Propiedades de conveniencia
    @property
    def position(self):
        #Posición actual (x, y) leída desde la celda del grid
        return self.cell.coordinate if self.cell is not None else None

    @property
    def needs_charge(self):
        #True si la batería está por debajo del umbral de recarga
        return self.battery <= self.RECHARGE_THRESHOLD

    def _has_reached(self, target):
        #True si el AGV "llegó" a `target`.
        #Si target es transitable hay que estar EN él.
        #Si NO es transitable (celda de rack), el AGV debe estar DE FRENTE:
        #ortogonalmente adyacente (Manhattan == 1), NO en diagonal. Además, si
        #es una celda de rack, solo cuenta si está sobre un LADO LARGO del rack
        #(no un lado corto): el depósito solo se hace por los lados largos.
        if self.position == target:
            return True
        env = self.model.environment
        if not env.is_walkable(target):
            return self.position in self._valid_front_cells(target)
        return False

    def _valid_front_cells(self, target):
        #Frentes VÁLIDOS (transitables y dentro del grid) de una celda de rack:
        #las celdas adyacentes por un LADO LARGO del rack que contiene `target`.
        #Es la ÚNICA fuente de verdad de "por dónde se puede depositar"; se usa
        #tanto para llegar (_has_reached), aproximarse (_approach_target) como
        #para estimar el costo de la misión (coherencia total).
        env = self.model.environment
        rack = env.rack_at(target)
        if rack is None:
            return []
        result = []
        for c in rack.front_cells(target):
            if 0 <= c[0] < env.width and 0 <= c[1] < env.height:
                if env.is_walkable(c):
                    result.append(c)
        return result


    #Negociación

    def is_available_for_bidding(self):
        #True si el AGV puede competir por una misión
        #Colaboración: un AGV solo puja si está AVAILABLE y no está por debajo
        #del umbral de batería. Un AGV busy/charging o con poca batería NO puja
        return (
            self.status == AGVAgent.AVAILABLE
            and self.mission is None
            and not self.needs_charge
        )

    def _path_length(self, start, goal):
        #Longitud (en celdas) de la ruta BFS entre `start` y `goal`,
        #respetando obstáculos. Si `goal` no es transitable (rack), se mide
        #hasta la celda adyacente transitable más cercana. Devuelve un número
        #grande si no hay ruta (inalcanzable).
        env = self.model.environment

        #Si el goal no es transitable (rack), los destinos válidos son sus
        #FRENTES por lado largo. Se mide la ruta al frente alcanzable más corto.
        if not env.is_walkable(goal):
            targets = self._valid_front_cells(goal)
            if not targets:
                return float("inf")
        else:
            targets = [goal]

        if start in targets:
            return 0

        #BFS desde start hasta el primer target alcanzado (4 dir ortogonales).
        target_set = set(targets)
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        frontier = deque([start])
        came_from = {start: None}
        reached = None
        while frontier:
            current = frontier.popleft()
            if current in target_set:
                reached = current
                break
            cx, cy = current
            for dx, dy in deltas:
                nxt = (cx + dx, cy + dy)
                if not (0 <= nxt[0] < env.width and 0 <= nxt[1] < env.height):
                    continue
                if nxt in came_from:
                    continue
                if not env.is_walkable(nxt):
                    continue
                came_from[nxt] = current
                frontier.append(nxt)
        if reached is None:
            return float("inf")

        #Reconstruir para contar pasos hasta el target alcanzado.
        length = 0
        node = reached
        while node != start:
            node = came_from[node]
            length += 1
        return length

    def _estimate_mission_cost(self, mission):
        #Estima el % de batería necesario para completar la misión Y poder
        #volver a una estación de carga después. Suma tres tramos (BFS real):
        #  1. posición actual -> origen (recoger)
        #  2. origen -> destino (transportar)
        #  3. destino -> estación de carga más cercana (reserva de retorno)
        #Se multiplica por el consumo por celda y se aplica el margen de
        #seguridad. Devuelve un % de batería.
        stations = self.model.environment.charging_stations

        leg1 = self._path_length(self.position, mission.origin)
        leg2 = self._path_length(mission.origin, mission.destination)
        #Estación más cercana al destino (para la reserva de retorno)
        return_leg = min(
            self._path_length(mission.destination, s) for s in stations
        )

        total_cells = leg1 + leg2 + return_leg
        if total_cells == float("inf"):
            return float("inf")  #algún tramo es inalcanzable

        cost = total_cells * self.DISCHARGE_PER_MOVE
        cost *= (1 + self.SAFETY_MARGIN)  #margen de seguridad
        return cost

    def can_complete(self, mission):
        #True si la batería actual alcanza para completar la misión y aún
        #poder llegar a una estación de carga (según la estimación).
        return self.battery >= self._estimate_mission_cost(mission)

    def bid_for(self, mission):
        #Calcula la puja del AGV para una misión, o None si no compite.
        #Puja = distancia de Manhattan al origen (menor = mejor). Manhattan es
        #la métrica correcta con movimiento solo ortogonal (sin diagonales).
        #Un AGV solo puja si está disponible, no bajo umbral, y además su
        #batería le alcanza para completar la misión + volver a cargar.
        if not self.is_available_for_bidding():
            return None
        if not self.can_complete(mission):
            #No puja: no le alcanza la batería para esta misión.
            self.model.log(
                f"[AGV{self.unique_id}] NO puja {mission.id}: "
                f"batería {self.battery}% insuficiente "
                f"(estima ~{self._estimate_mission_cost(mission):.0f}%)."
            )
            return None
        return manhattan(self.position, mission.origin)

    def accept_mission(self, mission):
        #El AGV acepta una misión adjudicada: pasa a BUSY y va al origen
        self.mission = mission
        self.status = AGVAgent.BUSY
        self.task_phase = AGVAgent.PHASE_TO_ORIGIN
        self.destination = mission.origin


    #Ayudas de grid / vecindario

    def _walkable_neighbor_cells(self):
        #Celdas vecinas que son transitables según el ambiente
        env = self.model.environment
        result = []
        for cell in self.cell.neighborhood:
            #Solo vecinos ORTOGONALES (arriba/abajo/izq/der), no diagonales.
            if manhattan(cell.coordinate, self.position) != 1:
                continue
            if env.is_walkable(cell.coordinate):
                result.append(cell)
        return result

    def _agv_in_cell(self, cell):
        #Devuelve otro AGVAgent que ocupe `cell`, o None si está libre
        for agent in cell.agents:
            if isinstance(agent, AGVAgent) and agent is not self:
                return agent
        return None


    #Prioridad en colisiones
    def has_priority_over(self, other):

        #Un AGV 'busy' tiene prioridad sobre uno que no lo está.
        #Si ambos están 'busy' (o ninguno), gana el de id más bajo.

        self_busy = self.status == AGVAgent.BUSY
        other_busy = other.status == AGVAgent.BUSY

        if self_busy != other_busy:
            return self_busy  #el busy tiene prioridad
        #Empate de estado: gana el id más bajo
        return self.unique_id < other.unique_id


    #Movimiento (BFS + seguimiento de ruta)
    def _compute_path(self, goal):
        #BFS: ruta más corta desde la posición actual hasta `goal`.
        #Se mueve en 4 direcciones ortogonales pisando solo celdas transitables.
        #Devuelve la lista de celdas del camino EXCLUYENDO la actual (la primera
        #entrada es el siguiente paso). Lista vacía si `goal` es la posición
        #actual o no hay ruta posible. No considera la ocupación por otros AGVs
        #(eso se resuelve al avanzar, con la lógica de colisiones)
        env = self.model.environment
        start = self.position
        if start == goal:
            return []

        #Vecinos (4 direcciones ortogonales: arriba, abajo, izq, der)
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        frontier = deque([start])
        came_from = {start: None}

        while frontier:
            current = frontier.popleft()
            if current == goal:
                break
            cx, cy = current
            for dx, dy in deltas:
                nxt = (cx + dx, cy + dy)
                if not (0 <= nxt[0] < env.width and 0 <= nxt[1] < env.height):
                    continue
                if nxt in came_from:
                    continue
                if not env.is_walkable(nxt):
                    continue
                came_from[nxt] = current
                frontier.append(nxt)

        if goal not in came_from:
            return []  #inalcanzable

        #Reconstruir camino desde goal hasta start, luego invertir
        path = []
        node = goal
        while node != start:
            path.append(node)
            node = came_from[node]
        path.reverse()
        return path

    def _ensure_path_to(self, goal):
        #Garantiza que self.path lleva a `goal`; lo recalcula si hace falta
        if goal != self._path_goal or not self.path:
            self.path = self._compute_path(goal)
            self._path_goal = goal

    def _move_to_cell(self, cell):
        #Mueve el AGV a `cell`, descuenta batería y acumula distancia.
        #Un AGV sin batería (0%) no puede moverse: se queda donde está.
        if self.battery <= 0:
            return False
        origin = self.position
        self.cell = cell
        self.battery = max(0, self.battery - self.DISCHARGE_PER_MOVE)
        self.distance_traveled += 1
        self._moved_this_step = True
        #Registrar el movimiento en el modelo (para la detección anti-swap).
        self.model.register_move(origin, cell.coordinate)
        return True

    def _try_step_toward(self, goal):
        #Avanza un paso hacia `goal` siguiendo la ruta BFS, con colisiones
        if goal is None or self.position == goal:
            return

        #Si YA se movió este step (p. ej. fue empujado por otro AGV con
        #_step_aside antes de su turno), NO se mueve otra vez: un AGV avanza a
        #lo sumo UNA celda por step. Sin esta guarda, podría moverse dos veces
        #en el mismo step y parecer un "salto" de 2 celdas o diagonal.
        if self._moved_this_step:
            return

        self._ensure_path_to(goal)
        if not self.path:
            return  #sin ruta posible

        next_pos = self.path[0]
        next_cell = self.model.environment.grid[next_pos]

        #ANTI-SWAP: dos AGVs no pueden intercambiar celdas en el mismo step
        #(atravesarse es físicamente imposible). Si otro AGV YA se movió este
        #step desde `next_pos` hacia mi celda actual, entrar sería un swap.
        if self.model.was_move_this_step(origin=next_pos, dest=self.position):
            #Es un swap: no avanzo. Recalculo ruta el próximo step para rodear.
            self._path_goal = None
            return

        occupant = self._agv_in_cell(next_cell)
        if occupant is None:
            if self._move_to_cell(next_cell):  #solo consumo el paso si me moví
                self.path.pop(0)
            return

        #La siguiente celda de la ruta está ocupada por otro AGV
        if self.has_priority_over(occupant):
            if occupant._step_aside(avoid=self.position):
                if self._move_to_cell(next_cell):
                    self.path.pop(0)
            #Si no pudo apartarse, me quedo este step (reintento luego)
        else:
            # Cedo: fuerzo recálculo de ruta el próximo step para rodear
            self._path_goal = None

    def _step_aside(self, avoid):
        #Intenta apartarse a un vecino libre para ceder el paso
        #`avoid` es la celda desde la que viene el AGV prioritario
        #si el único hueco está ocupado por otro AGV, se considera que no puede apartarse
        #Devuelve True si logró apartarse.

        if self._moved_this_step:
            #Ya se movió este step; se considera que no puede volver a moverse
            return False

        for cell in self._walkable_neighbor_cells():
            if cell.coordinate == avoid:
                continue
            if self._agv_in_cell(cell) is None:
                self._move_to_cell(cell)
                #Me aparté fuera de mi ruta: invalidarla para recalcular
                self._path_goal = None
                self.path = []
                return True
        return False


    #Batería

    def _nearest_charging_station(self):
        #Estación de carga más cercana por distancia de Manhattan
        stations = self.model.environment.charging_stations
        return min(stations, key=lambda s: manhattan(self.position, s))

    def _handle_charging(self):
        #Estado charging del AGV
        #Si aún no llegó a la estación, se acerca. Si ya está en la estación,
        #recarga hasta la batería objetivo y luego vuelve a 'available'
        station = self._nearest_charging_station()

        if self.position != station:
            self._try_step_toward(station)
            return

        #En la estación -> recarga
        self.battery = min(self.BATTERY_FULL, self.battery + self.RECHARGE_PER_STEP)
        if self.battery >= self.RECHARGE_TARGET:
            self.status = AGVAgent.AVAILABLE


    #Ciclo de misión (recoger -> transportar -> entregar)

    def _pickup_product(self):
        #Recoge el pallet en el origen (instantáneo) y pasa a transportar
        product = self.mission.product
        self.carried_product = product
        product.status = product.BEING_TRANSPORTED

        #Si es OUTBOUND, el pallet sale del rack: liberar su celda para que
        #futuros inbound puedan usarla.
        if self.mission.type == self.mission.OUTBOUND and product.rack is not None:
            product.rack.release(product)

        #Si es INBOUND desde una entrada, esa entrada queda libre: programar la
        #llegada de un nuevo pallet (llegadas continuas).
        if self.mission.type == self.mission.INBOUND:
            origin = self.mission.origin
            if origin in self.model.environment.product_entries:
                self.model.mission_manager.schedule_arrival(
                    origin, self.model.steps_taken
                )

        #A partir de ahora el AGV se dirige al destino de la misión
        self.task_phase = AGVAgent.PHASE_TO_DESTINATION
        self.destination = self.mission.destination
        self.mission.status = self.mission.IN_PROGRESS
        self.model.log(
            f"[AGV{self.unique_id}] recoge {product.id} en {self.position}; "
            f"transporta a {self.mission.destination}."
        )

    def _deliver_product(self):
        #Entrega el pallet en el destino (instantáneo) y cierra la misión.
        #El pallet se deposita en la celda de destino de la misión
        #El estado final del pallet y lo que pasa después dependen del tipo de misión:
          #Si es INBOUND, queda STORED en el rack, y el Manager programa una OUTBOUND
          #Si es OUTBOUND: queda DELIVERED en el truck dock (sale del almacén)

        product = self.carried_product
        mission = self.mission
        product.position = mission.destination

        if mission.type == mission.INBOUND:
            #La celda ya fue reservada al crear la misión; confirmar STORED.
            if product.rack is not None:
                product.rack.confirm_stored(product)
            else:
                product.status = product.STORED
            #Programar el despacho (outbound) de este pallet.
            self.model.mission_manager.schedule_outbound(
                product, self.model.steps_taken
            )
        else:  #OUTBOUND
            product.status = product.DELIVERED

        self.model.mission_manager.complete_mission(
            mission, current_step=self.model.steps_taken
        )
        self.completed_missions += 1

        #El AGV queda libre para competir de nuevo.
        self.carried_product = None
        self.mission = None
        self.task_phase = None
        self.destination = None
        self.status = AGVAgent.AVAILABLE

    def _approach_target(self, target):
        #Punto transitable al que dirigirse para "llegar" a `target`.
        #Si `target` es transitable, es él mismo. Si no lo es (celda de rack),
        #se devuelve un FRENTE válido (celda adyacente por un LADO LARGO del
        #rack, transitable). Se elige el frente con la RUTA BFS más corta desde
        #la posición actual (no solo Manhattan), para no apuntar a un frente
        #geométricamente cercano pero inalcanzable (p. ej. detrás del rack).
        env = self.model.environment
        if env.is_walkable(target):
            return target

        fronts = self._valid_front_cells(target)
        if not fronts:
            return target  #sin frente accesible (no debería pasar en el layout)

        #Elegir el frente con menor longitud de ruta real; descartar los
        #inalcanzables (ruta infinita). Desempate estable por coordenada.
        def route_len(c):
            return self._path_length(self.position, c)
        best = min(fronts, key=lambda c: (route_len(c), c))
        if route_len(best) == float("inf"):
            return target  #ninguno alcanzable ahora (se reintenta luego)
        return best

    def _handle_mission(self):
        #Avanza la máquina de estados de la misión en curso

        #Moverse hacia un punto alcanzable que satisfaga la fase
        approach = self._approach_target(self.destination)
        self._try_step_toward(approach)

        #El pallet cargado sigue al AGV
        if self.carried_product is not None:
            self.carried_product.position = self.position

        #¿Llegó al punto de la fase actual? (adyacente si es no transitable)
        if not self._has_reached(self.destination):
            return

        if self.task_phase == AGVAgent.PHASE_TO_ORIGIN:
            self._pickup_product()
        elif self.task_phase == AGVAgent.PHASE_TO_DESTINATION:
            self._deliver_product()

    def _should_recharge_proactively(self):
        #Auto-carga proactiva: un AGV libre que NO puede completar ninguna
        #misión pendiente por falta de batería debería ir a cargar, aunque esté
        #por encima del umbral (RECHARGE_THRESHOLD). Esto evita el bloqueo en el
        #que hay trabajo pendiente pero nadie lo toma y nadie se descarga.
        #Devuelve True si conviene cargar proactivamente.
        pending = self.model.mission_manager.pending_missions()
        if not pending:
            return False  #no hay trabajo: no tiene sentido ir a cargar
        #Si ya está lleno (al máximo), no ganaría nada cargando.
        if self.battery >= self.BATTERY_FULL:
            return False
        #Si no puede completar NINGUNA misión pendiente -> conviene cargar.
        return not any(self.can_complete(m) for m in pending)

    #Step
    def step(self):
        #Comportamiento por paso de simulación:
        #NOTA: la bandera _moved_this_step la reinicia el modelo para TODOS los
        #AGVs antes de activarlos (no aquí), para evitar movimientos dobles
        #cuando un AGV empuja a otro con _step_aside antes de su turno.

        #Si ya está cargando: seguir cargando
        if self.status == AGVAgent.CHARGING:
            self._handle_charging()
            return

        #Si hay misión en curso: avanzarla (no se interrumpe por batería)
        if self.mission is not None:
            self._handle_mission()
            return

        #Si está bajo el umbral, ir a cargar (comportamiento reactivo).
        if self.needs_charge:
            self.status = AGVAgent.CHARGING
            self._handle_charging()
            return

        #Auto-carga PROACTIVA: aunque esté sobre el umbral, si hay misiones
        #pendientes y no puede con ninguna por batería, se va a cargar.
        if self._should_recharge_proactively():
            self.model.log(
                f"[AGV{self.unique_id}] va a cargar proactivamente "
                f"(batería {self.battery}%: insuficiente para el trabajo pendiente)."
            )
            self.status = AGVAgent.CHARGING
            self._handle_charging()

    def __repr__(self):
        carried = self.carried_product.id if self.carried_product else None
        return (
            f"AGV(id={self.unique_id}, pos={self.position}, "
            f"battery={self.battery}, status={self.status!r}, "
            f"carried={carried}, done={self.completed_missions})"
        )
