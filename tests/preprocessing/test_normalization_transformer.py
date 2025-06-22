import pandas as pd

from fin_statement_model.preprocessing.transformers.normalization import (
    NormalizationTransformer,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "revenue": [1000, 1200, 1500],
            "cogs": [600, 720, 900],
        },
        index=["2021", "2022", "2023"],
    )


def test_percent_of_normalization() -> None:
    df = _sample_df()

    transformer = NormalizationTransformer(
        normalization_type="percent_of", reference="revenue"
    )
    result = transformer.transform(df)

    # Revenue column remains unchanged for 'percent_of' implementation
    assert (result["revenue"] == df["revenue"]).all()
    # cogs as % of revenue should be 60%
    expected = pd.Series([60.0, 60.0, 60.0], index=df.index)
    assert (result["cogs"].round(1) == expected).all()


def test_scale_by_normalization() -> None:
    df = _sample_df()
    transformer = NormalizationTransformer(
        normalization_type="scale_by", scale_factor=0.001
    )
    result = transformer.transform(df)
    assert result["revenue"].iloc[0] == 1.0  # 1000 * 0.001
