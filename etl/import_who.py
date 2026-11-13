import logging

from etl.import_runner import (
    RAW_ROOT,
    IndicatorSpec,
    SourceSpec,
    import_for_loaded_countries,
    report_and_exit_on_failure,
)
from etl.step_result import StepResult
from etl.transform_who import transform_who_file

SOURCE = SourceSpec(
    name="WHO GHO", url="https://www.who.int/data/gho", raw_dir=RAW_ROOT / "who"
)

INDICATORS = (
    IndicatorSpec(
        code="WHOSIS_000001",
        remote_id="WHOSIS_000001",
        name="Life expectancy at birth",
        unit="years",
        raw_filename="WHOSIS_000001_from2000.json",
    ),
)


def import_all() -> list[StepResult]:
    return import_for_loaded_countries(SOURCE, INDICATORS, transform_who_file)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    report_and_exit_on_failure(import_all())
