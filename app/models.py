from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Sex(StrEnum):
    """Sex dimension of an observation (WHO GHO codes)."""

    BOTH = "BTSX"
    MALE = "MLE"
    FEMALE = "FMLE"


class Source(Base):
    __tablename__ = "source"

    source_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    url: Mapped[str | None] = mapped_column(Text)


class Country(Base):
    __tablename__ = "country"

    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    iso2: Mapped[str | None] = mapped_column(String(2))
    name: Mapped[str] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    income_group: Mapped[str | None] = mapped_column(String(50))


class Indicator(Base):
    __tablename__ = "indicator"

    indicator_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    source_id: Mapped[int] = mapped_column(ForeignKey("source.source_id"))

    source: Mapped[Source] = relationship()


class Observation(Base):
    __tablename__ = "observation"
    __table_args__ = (
        UniqueConstraint(
            "country_iso3", "indicator_id", "year", "sex", name="uq_observation"
        ),
        Index("ix_observation_indicator_year", "indicator_id", "year"),
    )

    observation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    country_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    indicator_id: Mapped[int] = mapped_column(ForeignKey("indicator.indicator_id"))
    year: Mapped[int] = mapped_column(SmallInteger)
    # Non-native enum: stored as VARCHAR(10) holding the code (e.g. "BTSX").
    sex: Mapped[Sex] = mapped_column(
        Enum(
            Sex,
            native_enum=False,
            length=10,
            values_callable=lambda members: [m.value for m in members],
        ),
        server_default=Sex.BOTH.value,
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    country: Mapped[Country] = relationship()
    indicator: Mapped[Indicator] = relationship()


class ImportLog(Base):
    __tablename__ = "import_log"

    import_id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100))
    indicator_code: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(Text)
    rows_loaded: Mapped[int]
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
