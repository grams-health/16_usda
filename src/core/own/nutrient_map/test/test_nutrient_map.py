from ..create import create_mapping
from ..list import list_nutrient_mappings, get_mapping
from ..modify import modify_mapping
from ..remove import remove_mapping


class TestNutrientMap:
    def test_create_mapping(self):
        status = create_mapping(203, "Protein", "Protein")
        assert status
        assert status.status == "success"

    def test_create_duplicate_mapping(self):
        create_mapping(203, "Protein", "Protein")
        status = create_mapping(203, "Protein", "Protein")
        assert not status
        assert status.status == "error"

    def test_list_nutrient_mappings(self):
        create_mapping(203, "Protein", "Protein")
        create_mapping(204, "Total lipid (fat)", "Fat")
        mappings = list_nutrient_mappings()
        assert len(mappings) == 2

    def test_get_mapping(self):
        create_mapping(203, "Protein", "Protein")
        mapping = get_mapping(203)
        assert mapping is not None
        assert mapping.usda_number == 203
        assert mapping.nutrient_name == "Protein"
        assert get_mapping(999) is None

    def test_modify_mapping(self):
        create_mapping(203, "Protein", "Protein")
        status = modify_mapping(203, "Total Protein")
        assert status
        mapping = get_mapping(203)
        assert mapping.nutrient_name == "Total Protein"
        # Not found
        status = modify_mapping(999, "X")
        assert not status

    def test_remove_mapping(self):
        create_mapping(203, "Protein", "Protein")
        status = remove_mapping(203)
        assert status
        assert get_mapping(203) is None
        # Not found
        status = remove_mapping(203)
        assert not status
