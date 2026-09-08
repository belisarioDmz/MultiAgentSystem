"""Modelo de dominio: Mission (misión de transporte).

Una misión sigue la fórmula del enunciado:  M = (O, D, P, S)
    O = origin       -> celda de donde se recoge el producto
    D = destination  -> celda a donde se debe llevar
    P = product       -> Product asociado a la misión
    S = status        -> estado de la misión

Se agrega:
    - id    : identificador único (necesario para los mensajes de comunicación)
    - type  : INBOUND (entrada -> rack) u OUTBOUND (rack -> truck dock).
              En M3 usamos INBOUND; OUTBOUND queda preparado para completar
              el sistema más adelante.
"""

class Mission:

    #Estados de la misión
    PENDING = "pending"          #publicada, aún sin AGV asignado
    ASSIGNED = "assigned"        #un AGV la aceptó, aún no la ejecuta
    IN_PROGRESS = "in_progress"  #el AGV la está ejecutando
    COMPLETED = "completed"      #entregada

    #Tipos de misión
    INBOUND = "inbound"    #entrada -> rack (almacenar)
    OUTBOUND = "outbound"  #rack -> truck dock (despachar)

    def __init__(self, mission_id, origin, destination, product,
                 mission_type=INBOUND):
        self.id = mission_id
        self.origin = origin            #(x, y)
        self.destination = destination  #(x, y)
        self.product = product          #Product
        self.type = mission_type
        self.status = Mission.PENDING
        #AGV que aceptó la misión (se llena durante la negociación)
        self.assigned_agv = None
        #Steps en que la misión fue aceptada y completada (para medir su
        #tiempo de ejecución). None hasta que ocurra cada evento.
        self.start_step = None
        self.complete_step = None

    def __repr__(self):
        return (
            f"Mission(id={self.id!r}, type={self.type!r}, "
            f"O={self.origin}, D={self.destination}, "
            f"P={self.product.id!r}, S={self.status!r})"
        )
