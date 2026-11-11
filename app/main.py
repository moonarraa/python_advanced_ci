from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Annotated, Any, cast

from fastapi import Depends, FastAPI, HTTPException, Path, status
from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.database import Base, engine, get_session

# Annotated вместо `= Depends(...)` в значении по умолчанию:
# так рекомендует FastAPI, и flake8-bugbear (B008) не ругается
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RecipeId = Annotated[int, Path(gt=0, description="Идентификатор рецепта")]

RECIPE_NOT_FOUND = "Recipe not found"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Кулинарная книга",
    description=(
        "API кулинарной книги.\n\n"
        "* **Экран 1** — таблица рецептов: `GET /recipes`. Рецепты "
        "отсортированы по популярности (количеству просмотров, по убыванию), "
        "при равенстве — по времени готовки (по возрастанию).\n"
        "* **Экран 2** — детальный рецепт: `GET /recipes/{recipe_id}`. "
        "Каждый успешный запрос увеличивает счётчик просмотров на 1.\n"
        "* Добавление рецепта: `POST /recipes`."
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[{"name": "recipes", "description": "Работа с рецептами"}],
)


@app.get(
    "/recipes",
    response_model=list[schemas.RecipeListItem],
    tags=["recipes"],
    summary="Список всех рецептов",
    description=(
        "Возвращает все рецепты для таблицы на первом экране: название, "
        "количество просмотров и время готовки.\n\n"
        "Сортировка: `views` по убыванию, затем `cooking_time` "
        "по возрастанию, затем `id`. "
        "Запрос **не** увеличивает счётчик просмотров."
    ),
    response_description=(
        "Рецепты в порядке популярности; пустой список, если рецептов нет"
    ),
)
async def list_recipes(session: SessionDep) -> Sequence[models.Recipe]:
    result = await session.execute(
        select(models.Recipe).order_by(
            models.Recipe.views.desc(),
            models.Recipe.cooking_time.asc(),
            models.Recipe.id.asc(),
        )
    )
    return result.scalars().all()


@app.get(
    "/recipes/{recipe_id}",
    response_model=schemas.RecipeDetail,
    tags=["recipes"],
    summary="Детальная информация о рецепте",
    description=(
        "Возвращает название, время готовки, список ингредиентов "
        "и текстовое описание рецепта.\n\n"
        "Каждый успешный вызов увеличивает счётчик просмотров (`views`) "
        "этого рецепта на 1 — по нему сортируется список рецептов."
    ),
    response_description="Рецепт с ингредиентами",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": schemas.ErrorResponse,
            "description": "Рецепт не найден",
        }
    },
)
async def get_recipe(
    recipe_id: RecipeId, session: SessionDep
) -> models.Recipe:
    # Атомарный инкремент на стороне БД — одновременные просмотры не теряются
    # UPDATE возвращает CursorResult (у него есть rowcount),
    # но session.execute() типизирован общим Result
    result = cast(
        CursorResult[Any],
        await session.execute(
            update(models.Recipe)
            .where(models.Recipe.id == recipe_id)
            .values(views=models.Recipe.views + 1)
        ),
    )
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, RECIPE_NOT_FOUND)
    await session.commit()

    recipe = await session.get(
        models.Recipe, recipe_id, populate_existing=True
    )
    if recipe is None:  # удалён между UPDATE и SELECT
        raise HTTPException(status.HTTP_404_NOT_FOUND, RECIPE_NOT_FOUND)
    return recipe


@app.post(
    "/recipes",
    response_model=schemas.RecipeDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["recipes"],
    summary="Создать рецепт",
    description=(
        "Создаёт новый рецепт вместе с ингредиентами. "
        "Счётчик просмотров нового рецепта равен 0.\n\n"
        "При невалидных данных (пустое название, время готовки ≤ 0, "
        "пустой список ингредиентов и т.п.) возвращается `422` "
        "с описанием ошибок."
    ),
    response_description="Созданный рецепт",
)
async def create_recipe(
    recipe: schemas.RecipeIn, session: SessionDep
) -> models.Recipe:
    new_recipe = models.Recipe(
        title=recipe.title,
        cooking_time=recipe.cooking_time,
        description=recipe.description,
        views=0,
        ingredients=[
            models.Ingredient(**item.model_dump())
            for item in recipe.ingredients
        ],
    )
    session.add(new_recipe)
    await session.commit()
    return new_recipe
