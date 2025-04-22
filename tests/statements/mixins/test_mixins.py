from fin_statement_model.statements.mixins.analysis_mixin import AnalysisOperationsMixin
from fin_statement_model.statements.mixins.merge_mixin import MergeOperationsMixin
from fin_statement_model.statements.mixins.metrics_mixin import MetricsOperationsMixin
from fin_statement_model.statements.mixins.forecast_mixin import ForecastOperationsMixin


def test_mixins_importable():
    assert AnalysisOperationsMixin
    assert MergeOperationsMixin
    assert MetricsOperationsMixin
    assert ForecastOperationsMixin
