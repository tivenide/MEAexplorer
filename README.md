# MEAexplorer

## Overview
MEAexplorer is a spike detection pipeline designed for processing `.brw` files from 3Brain (Version 320). It streamlines the analysis of electrophysiological data from Multi-Electrode Arrays (MEAs) with a focus on efficiency and flexibility.

### Key Features:
- **Batch Processing**: Efficiently process multiple files in a single run.
- **Multiple Execution Modes**: Choose from various modes, including serial and windowed processing.
- **Easy Configuration**: Use a user-friendly `config.yaml` file for quick adjustments to analysis parameters.
- **Threshold-Based Detection**: Implement threshold-based spike detection for identifying spikes in data.
- **Containerization**: Leverage Docker for consistent deployment across different systems.
- **Object-Oriented Design**: Built with an object-oriented approach for future adaptability.

MEAexplorer provides researchers with a powerful tool for extracting insights from complex MEA datasets.

## Build the container
To build the Docker container for MEAexplorer, run the following command in your terminal:
```bash
docker build -t meaexplorer:latest .
```
## Run the container
To run the MEAexplorer container, use the following command:
```bash
docker run -v /path/to/data/:/app/data meaexplorer:latest
```

## Default folder structure
The following folder structure is expected for the container:
```
data/
├── input/
├── output/
└── config.yaml
```

For example `config.yaml` see in `docs`-folder within this repo.

## Configuration file
The `config.yaml` file is designed for ease of use, allowing you to easily configure the parameters for data processing. An example of the `config.yaml` file can be found in the `docs` folder within this repository. The configuration file should be structured as follows:
```yaml
InputFolder: "data/input"
OutputFolder: "data/output"
ExecutionMode: "serialWindow"
SerialWindow:
  WindowTimeInSec: 2
Filter:
  Type: "bandpass"
  LowCut: 200
  HighCut: 3000
SpikeDetection:
  Method: "threshold"
  FactorPos: 6
  FactorNeg: 6
  RefractoryPeriod: 0.001
```

## Development
### Mounting local directories and debugging
To avoid rebuilding the container every time, you can mount your local directory: add `-v .:/app` into the run command, when starting in the current working directory.

For debugging you have to set the ports according to your debugpy config: add `-p 5678:5678` into the run command.

Example:
```bash
docker run -p 5678:5678 -v .:/app -v /path/to/data/:/app/data meaexplorer:latest
```

### Running tests
To run the tests for MEAexplorer, use the following command:
```bash
docker run -v /path/to/data/:/app/data meaexplorer:latest python tests/test_spikedetection.py
```

## License
This project is licensed under the Apache License Version 2.0. See the [LICENSE](LICENSE) for details.
```
Copyright 2025 tivenide

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```