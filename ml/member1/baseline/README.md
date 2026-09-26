# Personal Baseline Engine

The Personal Baseline Engine calculates user-specific statistical baselines from historical health-event data.

## Input

Processed health-event data containing:

- user_id
- event_type
- event_time
- value

## Output

For each user and health metric:

- observation count
- mean
- median
- standard deviation
- minimum
- maximum
- 5th percentile
- 95th percentile
- lower personal boundary
- upper personal boundary
- 2-standard-deviation boundaries
- 3-standard-deviation boundaries
- baseline quality

## Baseline Quality

### Insufficient

Less than 3 observations.

### Low

3–9 observations.

### Moderate

10–29 observations.

### Strong

30 or more observations.

## Purpose

The baseline is intended to represent the user's historical pattern and will be consumed by the anomaly detection and Digital Twin layers.

The baseline is not a clinical diagnosis or medical reference range.