from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parents[1]


def test_research_workbench_runs_the_guided_demo_without_exceptions():
    page = ROOT / "pages" / "3_Research_Workbench.py"
    app = AppTest.from_file(page).run(timeout=30)

    assert not app.exception
    assert app.selectbox[1].value == "selection"
    assert app.multiselect[0].value == ["genre"]

    app.button[0].click().run(timeout=90)

    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert "CDD gap" in metrics
    assert "Eligible intersections" in metrics
    assert "Robustness score" in metrics
    assert [button.label for button in app.get("download_button")] == ["Download audit recipe"]


def test_existing_streamlit_audits_still_run_after_state_management_changes():
    classic = AppTest.from_file(ROOT / "app.py").run(timeout=30)
    classic.select_slider[0].set_value(0)
    classic.button[0].click().run(timeout=60)
    assert not classic.exception
    assert len(classic.metric) >= 10

    oversight = AppTest.from_file(ROOT / "app.py").run(timeout=30)
    oversight.switch_page("pages/2_OversightParity.py").run(timeout=30)
    oversight.select_slider[0].set_value(0)
    oversight.button[0].click().run(timeout=60)
    assert not oversight.exception
    assert len(oversight.metric) >= 8
