from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    cooking_time: Mapped[int] = mapped_column(
        Integer, comment="Время готовки, минуты"
    )
    description: Mapped[str] = mapped_column(Text)
    views: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", index=True
    )

    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Ingredient.id",
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    quantity: Mapped[str] = mapped_column(
        String(50), default="", server_default=""
    )

    recipe: Mapped[Recipe] = relationship(back_populates="ingredients")
