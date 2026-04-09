import json


class TestNutrientMapRest:
    def test_create_mapping(self, client):
        resp = client.post("/usda/nutrient-map", json={
            "usda_number": 203,
            "usda_name": "Protein",
            "nutrient_name": "Protein",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"

    def test_create_mapping_missing_field(self, client):
        resp = client.post("/usda/nutrient-map", json={
            "usda_number": 203,
        })
        assert resp.status_code == 400

    def test_list_mappings(self, client):
        client.post("/usda/nutrient-map", json={
            "usda_number": 203, "usda_name": "Protein", "nutrient_name": "Protein",
        })
        resp = client.get("/usda/nutrient-map")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["usda_number"] == 203

    def test_get_modify_mapping(self, client):
        client.post("/usda/nutrient-map", json={
            "usda_number": 203, "usda_name": "Protein", "nutrient_name": "Protein",
        })
        # Get single
        resp = client.get("/usda/nutrient-map/203")
        assert resp.status_code == 200
        assert resp.get_json()["nutrient_name"] == "Protein"
        # Modify
        resp = client.put("/usda/nutrient-map/203", json={"nutrient_name": "Total Protein"})
        assert resp.status_code == 200
        # Verify
        resp = client.get("/usda/nutrient-map/203")
        assert resp.get_json()["nutrient_name"] == "Total Protein"
        # Not found
        resp = client.get("/usda/nutrient-map/999")
        assert resp.status_code == 404

    def test_delete_mapping(self, client):
        client.post("/usda/nutrient-map", json={
            "usda_number": 203, "usda_name": "Protein", "nutrient_name": "Protein",
        })
        resp = client.delete("/usda/nutrient-map/203")
        assert resp.status_code == 200
        resp = client.delete("/usda/nutrient-map/203")
        assert resp.status_code == 404
