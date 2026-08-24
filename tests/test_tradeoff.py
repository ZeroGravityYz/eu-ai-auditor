import numpy as np

from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.tradeoff import compare_models


def test_tradeoff_returns_lr_cart_and_pareto_points():
    data = make_demo_dataset(rows=260)
    result = compare_models(
        data,
        target_attribute="selection",
        favourable_value="Retenu",
        protected_attribute="genre",
        protected_value="Femme",
        conditioning_attributes=["diplome"],
        thresholds=(0.4, 0.5, 0.6),
        logistic_c_values=(1.0,),
        tree_depths=(3,),
    )

    assert set(result.points["model"]) == {"Régression logistique", "CART"}
    assert result.points["pareto_efficient"].any()
    assert np.isfinite(result.points["balanced_accuracy"]).all()
    assert result.test_rows + result.train_rows == 260

