from datetime import datetime


class ImportLog:
    def __init__(self, fdc_id: int, food_id: int, food_name: str, imported_at: datetime = None):
        self.fdc_id = fdc_id
        self.food_id = food_id
        self.food_name = food_name
        self.imported_at = imported_at or datetime.utcnow()
