"""Modelo de dominio: Rack (estantería de almacenamiento).

Regla de capacidad: UNA celda = UN producto. Por eso la capacidad del rack es
dinámicamente el número de celdas (len(cells)); si el rack crece o decrece, la
capacidad se ajusta sola.

El rack lleva el control de qué celda ocupa cada producto mediante un mapa
`cell_occupant` (celda -> producto o None). Una celda reservada/ocupada no puede
recibir otro producto.
"""

from warehouse.product import Product


class Rack:
    def __init__(self, rack_id, cells):
        self.id = rack_id
        self.cells = cells
        # Mapa de ocupación: celda -> producto (o None si está libre).
        self.cell_occupant = {cell: None for cell in cells}

        # Orientación del rack según su bounding box (ancho vs alto). Determina
        # los "lados largos", únicos por donde se puede depositar un producto:
        #   - horizontal (más ancho que alto): lados largos arriba/abajo.
        #   - vertical   (más alto que ancho): lados largos izquierda/derecha.
        #   - cuadrado   (ancho == alto): sin restricción (los 4 lados). No se
        #     usa en este proyecto, pero se maneja por robustez.
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        if width > height:
            self.orientation = "horizontal"
            # Direcciones (dx, dy) de los lados largos: arriba y abajo.
            self._long_side_dirs = [(0, -1), (0, 1)]
        elif height > width:
            self.orientation = "vertical"
            # Lados largos: izquierda y derecha.
            self._long_side_dirs = [(-1, 0), (1, 0)]
        else:
            self.orientation = "square"
            # Sin restricción: los 4 lados.
            self._long_side_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def front_cells(self, cell):
        """Celdas-frente candidatas para depositar en `cell` (una celda del rack).

        Son las celdas adyacentes por un LADO LARGO del rack (según su
        orientación). Devuelve coordenadas geométricas (sin filtrar por límites
        del grid ni transitabilidad; eso lo hace quien las consume). Un pallet
        solo puede depositarse/recogerse estando en una de estas celdas.
        """
        cx, cy = cell
        return [(cx + dx, cy + dy) for dx, dy in self._long_side_dirs]

    @property
    def capacity(self):
        """Capacidad = número de celdas (una celda = un producto)."""
        return len(self.cells)

    @property
    def products(self):
        """Productos actualmente en el rack (celdas ocupadas)."""
        return [p for p in self.cell_occupant.values() if p is not None]

    def is_full(self):
        return all(o is not None for o in self.cell_occupant.values())

    def free_cells(self):
        """Celdas del rack que están libres."""
        return [c for c, o in self.cell_occupant.items() if o is None]

    def reserve_cell(self, product):
        """Reserva una celda libre para un producto y devuelve esa celda.

        Se usa al crear una misión inbound: la celda queda ocupada por el
        producto desde ya, para que ninguna otra misión la use. Devuelve None
        si el rack está lleno.
        """
        free = self.free_cells()
        if not free:
            return None
        cell = free[0]
        self.cell_occupant[cell] = product
        product.rack = self
        return cell

    def confirm_stored(self, product):
        """Confirma que el producto ya fue depositado físicamente (STORED)."""
        product.status = Product.STORED

    def release(self, product):
        """Libera la celda que ocupaba el producto (p. ej. al hacer outbound)."""
        for cell, occ in self.cell_occupant.items():
            if occ is product:
                self.cell_occupant[cell] = None
                break
        product.rack = None
