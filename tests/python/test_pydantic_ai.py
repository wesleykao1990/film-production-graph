from pydantic_ai.models.test import TestModel


def test_pydantic_ai_test_model_is_available_without_credentials() -> None:
    model = TestModel()
    assert model.model_name == "test"
