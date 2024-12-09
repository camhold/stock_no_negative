from odoo import _, models
from odoo.exceptions import UserError

class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _get_available_quantity(
        self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False
    ):
        res = super()._get_available_quantity(
            product_id=product_id,
            location_id=location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
            allow_negative=allow_negative,
        )

        if location_id and not location_id.allow_negative_stock and res < 0.0:
            error_params = self._prepare_error_params(product_id, location_id, res)
            
            if location_id.usage == "production":
                self._validate_production_stock(error_params)
            elif location_id.usage == "internal":
                self._validate_internal_stock(error_params)
            elif location_id.usage == "transit":
                self._validate_transit_stock(error_params)

        return res

    def _prepare_error_params(self, product_id, location_id, quantity):
        return {
            "lot_qty": quantity,
            "product_name": product_id.name,
            "location_name": location_id.complete_name,
        }

    def _validate_production_stock(self, error_params):
        message = _(
            "Stock negativo detectado en ubicación de producción.\n"
            "• Producto: %(product_name)s\n"
            "• Ubicación: %(location_name)s\n"
            "• Stock resultante: %(lot_qty)s unidades\n\n"
            "Por favor, ajuste las cantidades o realice un ajuste de inventario."
        )
        raise UserError(message % error_params)

    def _validate_internal_stock(self, error_params):
        message = _(
            "Stock negativo detectado en almacén interno.\n"
            "• Producto: %(product_name)s\n"
            "• Ubicación: %(location_name)s\n"
            "• Stock resultante: %(lot_qty)s unidades\n\n"
            "Por favor, ajuste las cantidades o realice un ajuste de inventario."
        )
        raise UserError(message % error_params)

    def _validate_transit_stock(self, error_params):
        message = _(
            "Stock negativo detectado en ubicación de tránsito.\n"
            "• Producto: %(product_name)s\n"
            "• Ubicación: %(location_name)s\n"
            "• Stock resultante: %(lot_qty)s unidades\n\n"
            "Por favor, ajuste las cantidades o realice un ajuste de inventario."
        )
        raise UserError(message % error_params)


class StockMove(models.Model):
    _inherit = "stock.move"

    def action_assign(self):
        for move in self:
            quant = self.env['stock.quant']
            
            # Verificamos el stock disponible en la ubicación de origen
            available = quant._get_available_quantity(
                move.product_id,
                move.location_id,  # Ubicación de origen
                lot_id=move.lot_id,
                package_id=move.package_id,
                owner_id=move.owner_id,
            )

            # Validar el stock disponible en la ubicación de origen
            if not move.location_id.allow_negative_stock and available < move.product_uom_qty:
                error_params = quant._prepare_error_params(
                    move.product_id, 
                    move.location_id, 
                    available - move.product_uom_qty
                )
                quant._validate_internal_stock(error_params)

            # Verificamos el stock disponible en la ubicación de destino
            if move.location_dest_id and not move.location_dest_id.allow_negative_stock:
                available_dest = quant._get_available_quantity(
                    move.product_id,
                    move.location_dest_id,  # Ubicación de destino
                    lot_id=move.lot_id,
                    package_id=move.package_id,
                    owner_id=move.owner_id,
                )

                # Validar el stock disponible en la ubicación de destino
                if available_dest < move.product_uom_qty:
                    error_params = quant._prepare_error_params(
                        move.product_id, 
                        move.location_dest_id, 
                        available_dest - move.product_uom_qty
                    )
                    quant._validate_internal_stock(error_params)

        # Continuar con la acción original de asignación de stock
        return super().action_assign()
