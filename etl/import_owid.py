import logging

from etl.import_runner import (
    RAW_ROOT,
    IndicatorSpec,
    SourceSpec,
    import_for_loaded_countries,
    report_and_exit_on_failure,
)
from etl.step_result import StepResult
from etl.transform_owid import transform_owid_chart_file

SOURCE = SourceSpec(
    name="Our World in Data",
    url="https://ourworldindata.org",
    raw_dir=RAW_ROOT / "owid",
)

INDICATORS = (
    IndicatorSpec(
        code="OWID_LIFE_EXPECTANCY",
        remote_id="life-expectancy",
        name="Life expectancy (OWID)",
        unit="years",
        raw_filename="life-expectancy_full.csv",
    ),
)


def import_all() -> list[StepResult]:
    return import_for_loaded_countries(SOURCE, INDICATORS, transform_owid_chart_file)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    report_and_exit_on_failure(import_all())
