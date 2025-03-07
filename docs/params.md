# Parameters Configuration

## Input and Output
- **InputFolder**: Directory where input data files are located.
- **OutputFolder**: Directory where processed output files will be saved.

## Execution Settings
- **ExecutionMode**: Mode of execution for processing data (e.g., "serial", "serialWindow").
    Options:
        **serial**: Loads the complete data stream into RAM and processes individual channels serially. This mode can be memory-intensive.
        **serialWindow**: Loads only the specified time window into RAM and processes these windows one after the other (serially). This approach is more memory-efficient.
- **SerialWindow**: Configuration for windowed processing.
  - **WindowTimeInSec**: Duration of each processing window in seconds.
> **Note**: SerialWindow is dependent on the ExecutionMode.

## Signal Filtering
- **Filter**: Configuration for signal filtering.
  - **Type**: Type of filter to apply (e.g., "bandpass").
  - **LowCut**: Lower cutoff frequency for the filter.
  - **HighCut**: Upper cutoff frequency for the filter.

## Spike Detection
- **SpikeDetection**: Configuration for spike detection parameters.
  - **Method**: Method used for spike detection (e.g., "threshold").
  - **FactorPos**: Positive threshold factor for spike detection.
  - **FactorNeg**: Negative threshold factor for spike detection.
  - **RefractoryPeriod**: Minimum time between detected spikes in seconds.

> **Note**: If one threshold factor (FactorPos or FactorNeg) is commented out or absent, only the present factor will be applied.