"""Regenerate the synthetic dataset containing controlled deviations."""
try:
    from .generate_synthetic_health_data import generate
except ImportError:  # Allows direct execution from this folder.
    from generate_synthetic_health_data import generate


if __name__ == "__main__":
    _, with_anomalies = generate()
    print(f"Generated {len(with_anomalies)} synthetic rows with injected deviations.")
