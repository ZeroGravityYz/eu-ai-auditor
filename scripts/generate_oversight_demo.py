"""Regenerate the deterministic OversightParity demonstration event log."""

from pathlib import Path

from eu_ai_auditor.oversight_demo import make_oversight_demo

OUTPUT = Path("data/oversight_demo.csv")


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = make_oversight_demo()
    data.to_csv(OUTPUT, index=False)
    print(f"Created {OUTPUT} with {len(data)} explicitly synthetic rows.")


if __name__ == "__main__":
    main()
