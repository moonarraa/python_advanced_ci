from typing import Any, cast

import pytest
from httpx import AsyncClient

Payload = dict[str, Any]

PANCAKES: Payload = {
    "title": "Блины",
    "cooking_time": 30,
    "description": "Смешать всё и жарить.",
    "ingredients": [
        {"name": "Мука", "quantity": "200 г"},
        {"name": "Молоко", "quantity": "500 мл"},
        {"name": "Соль"},
    ],
}


def make_recipe(title: str, cooking_time: int) -> Payload:
    return {
        "title": title,
        "cooking_time": cooking_time,
        "description": "Описание",
        "ingredients": [{"name": "Вода", "quantity": "1 л"}],
    }


async def create(client: AsyncClient, payload: Payload) -> Payload:
    response = await client.post("/recipes", json=payload)
    assert response.status_code == 201, response.text
    return cast(Payload, response.json())


async def test_list_empty(client: AsyncClient) -> None:
    response = await client.get("/recipes")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_recipe(client: AsyncClient) -> None:
    data = await create(client, PANCAKES)
    assert data["id"] > 0
    assert data["title"] == "Блины"
    assert data["cooking_time"] == 30
    assert data["description"] == PANCAKES["description"]
    assert [(i["name"], i["quantity"]) for i in data["ingredients"]] == [
        ("Мука", "200 г"),
        ("Молоко", "500 мл"),
        ("Соль", ""),
    ]


async def test_list_contains_table_fields(client: AsyncClient) -> None:
    created = await create(client, PANCAKES)
    response = await client.get("/recipes")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": created["id"],
            "title": "Блины",
            "cooking_time": 30,
            "views": 0,
        },
    ]


async def test_detail_returns_recipe_and_counts_views(
    client: AsyncClient,
) -> None:
    created = await create(client, PANCAKES)

    for _ in range(3):
        response = await client.get(f"/recipes/{created['id']}")
        assert response.status_code == 200
        assert response.json() == created

    recipes = (await client.get("/recipes")).json()
    assert recipes[0]["views"] == 3


async def test_list_does_not_count_views(client: AsyncClient) -> None:
    await create(client, PANCAKES)
    await client.get("/recipes")
    await client.get("/recipes")
    assert (await client.get("/recipes")).json()[0]["views"] == 0


async def test_sorting_by_views_then_cooking_time(client: AsyncClient) -> None:
    slow = await create(client, make_recipe("Медленный", 120))
    await create(client, make_recipe("Быстрый", 10))
    popular = await create(client, make_recipe("Популярный", 60))
    medium = await create(client, make_recipe("Средний", 45))

    for _ in range(2):
        await client.get(f"/recipes/{popular['id']}")
    await client.get(f"/recipes/{slow['id']}")
    await client.get(f"/recipes/{medium['id']}")

    titles = [r["title"] for r in (await client.get("/recipes")).json()]
    # popular: 2 просмотра; medium и slow: по 1 — быстрее первым; fast: 0
    assert titles == ["Популярный", "Средний", "Медленный", "Быстрый"]


async def test_detail_not_found(client: AsyncClient) -> None:
    response = await client.get("/recipes/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Recipe not found"}


@pytest.mark.parametrize("recipe_id", ["0", "-1", "abc"])
async def test_detail_invalid_id(client: AsyncClient, recipe_id: str) -> None:
    response = await client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "patch",
    [
        {"title": ""},
        {"cooking_time": 0},
        {"cooking_time": -5},
        {"ingredients": []},
        {"description": ""},
        {"ingredients": [{"quantity": "1 шт"}]},
    ],
)
async def test_create_invalid(client: AsyncClient, patch: Payload) -> None:
    response = await client.post("/recipes", json={**PANCAKES, **patch})
    assert response.status_code == 422
    assert (await client.get("/recipes")).json() == []


async def test_create_missing_field(client: AsyncClient) -> None:
    payload = dict(PANCAKES)
    del payload["cooking_time"]
    response = await client.post("/recipes", json=payload)
    assert response.status_code == 422


async def test_openapi_documents_endpoints(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert {"get", "post"} <= set(schema["paths"]["/recipes"])
    assert "get" in schema["paths"]["/recipes/{recipe_id}"]
    expected_models = {
        "RecipeIn",
        "RecipeListItem",
        "RecipeDetail",
        "IngredientIn",
        "IngredientOut",
    }
    assert expected_models <= set(schema["components"]["schemas"])
