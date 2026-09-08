"""Modelo de dominio: Producto."""


class Product:
    #Estados del producto
    WAITING_FOR_PICKUP = "waiting_for_pickup"
    STORED = "stored"
    BEING_TRANSPORTED = "being_transported"
    DELIVERED = "delivered"

    def __init__(self, product_id, position=None):
        self.id = product_id
        self.status = Product.WAITING_FOR_PICKUP
        self.rack = None
        #Celda (x, y) donde se encuentra físicamente el pallet
        self.position = position

    def __repr__(self):
        return f"Product(id={self.id!r}, status={self.status!r}, pos={self.position})"
