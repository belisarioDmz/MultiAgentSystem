"""Ambiente del almacén: grid espacial, capa de transitabilidad y puntos clave."""

from mesa.discrete_space import OrthogonalMooreGrid, PropertyLayer

from warehouse.rack import Rack
from warehouse.product import Product

class WarehouseEnvironment:
    def __init__(self, random=None, seed=None):
        # Generador aleatorio (reproducibilidad)
        if random is None:
            import random as random_module
            random = random_module.Random(seed)
        self.random = random

        # Dimensiones del almacén
        self.width = 20
        self.height = 20

        # Grid de Mesa
        self.grid = OrthogonalMooreGrid(
            (self.width, self.height), torus=False, random=random
        )

        # Capa para transitabilidad
        self.walkable_layer = PropertyLayer(
            "walkable", (self.width, self.height), default_value=True, dtype=bool
        )

        # Puntos clave del almacén
        self.product_entries = [(0, 3), (0, 8), (0, 11), (0, 16)]
        self.product_exits = [(19, 3), (19, 8), (19, 11), (19, 16)]
        self.charging_stations = [(2, 0), (6, 0), (14, 19), (18, 19)]

        # Definición de Racks (la capacidad es automática = número de celdas)
        self.racks = [
            Rack(1, [(4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5),
                     (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4), (10, 4)]),
            Rack(2, [(4, 13), (5, 13), (6, 13), (7, 13), (8, 13), (9, 13), (10, 13),
                     (4, 14), (5, 14), (6, 14), (7, 14), (8, 14), (9, 14), (10, 14)]),
            Rack(3, [(15, 12), (15, 11), (15, 10), (15, 9), (15, 8), (15, 7), (15, 6),
                     (14, 12), (14, 11), (14, 10), (14, 9), (14, 8), (14, 7), (14, 6)]),
            Rack(4, [(12, 0), (13, 0), (14, 0)]),
            Rack(5, [(5, 19), (6, 19), (7, 19)]),
        ]

        # Construir capa transitabilidad
        self.build_walkable_layer()

        # Poblar el ambiente con pallets (un pallet por entrada, sin apilar).
        self.num_products = 4
        self.products = []
        self.populate_products()

    def populate_products(self):
        #Crea los pallets en las entradas (una entrada = máx. un pallet).
        n = min(self.num_products, len(self.product_entries))
        self.num_products = n
        for i in range(self.num_products):
            entry = self.product_entries[i]
            product = Product(product_id=f"P{i + 1:03d}", position=entry)
            self.products.append(product)

    def create_product(self, product_id, position):
        #Crea un producto nuevo en `position` y lo agrega al ambiente.
        #Usado por las llegadas continuas (inbound dinámico).
        product = Product(product_id=product_id, position=position)
        self.products.append(product)
        return product

    def remove_product(self, product):
        #Quita un producto del ambiente (para deshacer una creación fallida).
        if product in self.products:
            self.products.remove(product)

    def build_walkable_layer(self):
        #Bloquea las celdas ocupadas por los racks.
        for rack in self.racks:
            for (x, y) in rack.cells:
                self.walkable_layer.data[x, y] = False

    def is_walkable(self, pos):
        #Consulta si una posición es transitable.
        x, y = pos
        return bool(self.walkable_layer.data[x, y])

    def rack_at(self, cell):
        #Devuelve el Rack que contiene `cell`, o None si ninguna la contiene.
        for rack in self.racks:
            if cell in rack.cell_occupant:
                return rack
        return None

    def get_spawn_cells(self):
        #Celdas para spawn de AGVs.
        reserved = set(self.product_entries + self.product_exits + self.charging_stations)
        spawn_cells = []
        for x in range(self.width):
            for y in range(self.height):
                pos = (x, y)
                if self.is_walkable(pos) and pos not in reserved:
                    spawn_cells.append(pos)
        return spawn_cells
