
class ManageStock:
    @staticmethod
    def check_stock_availability(variant, quantity):
        return variant.quantity >= quantity
        
    @staticmethod
    def add_stock(variant, quantity):
       variant.quantity+=quantity
       variant.save(update_fields=["quantity"])
    @staticmethod
    def reduce_stock(variant, quantity):
        variant.quantity-=quantity
        variant.save(update_fields=["quantity"])