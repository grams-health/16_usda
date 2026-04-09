class FdcId(int):
    def __new__(cls, value):
        if not isinstance(value, int):
            raise TypeError(f"FdcId must be int, got {type(value).__name__}")
        return super().__new__(cls, value)


class UsdaNumber(int):
    def __new__(cls, value):
        if not isinstance(value, int):
            raise TypeError(f"UsdaNumber must be int, got {type(value).__name__}")
        return super().__new__(cls, value)


class UsdaName(str):
    def __new__(cls, value):
        if not isinstance(value, str):
            raise TypeError(f"UsdaName must be str, got {type(value).__name__}")
        if not value.strip():
            raise ValueError("UsdaName cannot be empty")
        return super().__new__(cls, value)


class NutrientName(str):
    def __new__(cls, value):
        if not isinstance(value, str):
            raise TypeError(f"NutrientName must be str, got {type(value).__name__}")
        if not value.strip():
            raise ValueError("NutrientName cannot be empty")
        return super().__new__(cls, value)


class FoodId(int):
    def __new__(cls, value):
        if not isinstance(value, int):
            raise TypeError(f"FoodId must be int, got {type(value).__name__}")
        return super().__new__(cls, value)


class FoodName(str):
    def __new__(cls, value):
        if not isinstance(value, str):
            raise TypeError(f"FoodName must be str, got {type(value).__name__}")
        if not value.strip():
            raise ValueError("FoodName cannot be empty")
        return super().__new__(cls, value)


class Quantity(float):
    def __new__(cls, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"Quantity must be numeric, got {type(value).__name__}")
        return super().__new__(cls, value)
