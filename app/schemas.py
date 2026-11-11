from pydantic import BaseModel, ConfigDict, Field


class IngredientIn(BaseModel):
    """Ингредиент при создании рецепта."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название ингредиента",
        examples=["Мука"],
    )
    quantity: str = Field(
        "",
        max_length=50,
        description=(
            "Количество в свободной форме; может быть пустым («по вкусу»)"
        ),
        examples=["200 г"],
    )


class IngredientOut(IngredientIn):
    """Ингредиент в ответе сервера."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Идентификатор ингредиента", examples=[1])


class RecipeBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Название рецепта",
        examples=["Блины"],
    )
    cooking_time: int = Field(
        ...,
        gt=0,
        le=10080,
        description="Время готовки в минутах (от 1 до 10080 — неделя)",
        examples=[30],
    )


class RecipeIn(RecipeBase):
    """Тело запроса на создание рецепта."""

    description: str = Field(
        ...,
        min_length=1,
        description="Текстовое описание: шаги приготовления",
        examples=[
            "Смешать муку, яйца и молоко. Жарить на разогретой сковороде."
        ],
    )
    ingredients: list[IngredientIn] = Field(
        ...,
        min_length=1,
        description="Список ингредиентов, минимум один",
    )


class RecipeListItem(RecipeBase):
    """Строка таблицы на экране со списком рецептов."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        ...,
        description=(
            "Идентификатор рецепта — используйте его "
            "для запроса детальной информации"
        ),
        examples=[1],
    )
    views: int = Field(
        ...,
        ge=0,
        description=(
            "Количество просмотров — сколько раз открывали детальный рецепт"
        ),
        examples=[42],
    )


class RecipeDetail(RecipeBase):
    """Детальная информация о рецепте."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Идентификатор рецепта", examples=[1])
    description: str = Field(
        ..., description="Текстовое описание: шаги приготовления"
    )
    ingredients: list[IngredientOut] = Field(
        ..., description="Список ингредиентов в порядке добавления"
    )


class ErrorResponse(BaseModel):
    """Формат ошибки, когда ресурс не найден."""

    detail: str = Field(
        ..., description="Описание ошибки", examples=["Recipe not found"]
    )
