# app.py

import os
import h5py
import numpy as np
import time
import yaml
import warnings
from scipy.signal import butter, filtfilt
import debugpy

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


## Start the debug server on port 5678
# debugpy.listen(("0.0.0.0", 5678))
# print("Waiting for debugger to attach...")
# debugpy.wait_for_client()  # Optional: wait for the debugger to attach

class ConfigLoader:
    """Loads configuration from a YAML file."""
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)


class FilterPipeline:
    """Applies filtering methods to the signal."""
    def apply_bandpass_filter(self, data, lowcut, highcut, sampling_rate, order=5):
        nyquist = 0.5 * sampling_rate
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)

class SpikeDetection:
    """Handles spike detection logic."""
    def __init__(self, config):
        self.config = config
        self.filter_pipeline = FilterPipeline()    

    def calculate_sigma(self, data):
        """Calulate sigma according to 
        R. Quian Quiroga, Z. Nadasdy, Y. Ben-Shaul
        Unsupervised spike detection and sorting with wavelets and superparamagnetic clustering
        Neural Comput., 16 (2004), pp. 1661-1687
        https://doi.org/10.1162/089976604774201631
        """
        return np.median(np.abs(data) / 0.6745)

    def apply_threshold(self, data, threshold, positive=False):
        """Apply single threshold to data"""
        return np.where(data > threshold)[0] if positive else np.where(data < -threshold)[0]
    
    def thresholding(self, data):
        """Handle positive and negative threshold application to data"""
        sigma = self.calculate_sigma(data)
        factor_pos = self.config.get("SpikeDetection", {}).get("FactorPos")
        factor_neg = self.config.get("SpikeDetection", {}).get("FactorNeg")
        if factor_pos and factor_neg:
            pos_threshold = factor_pos * sigma
            neg_threshold = factor_neg * sigma
            spikes_pos = self.apply_threshold(data, pos_threshold, True)
            spikes_neg = self.apply_threshold(data, neg_threshold)
            spikes_merged = np.concatenate((spikes_pos, spikes_neg))
            spikes = np.unique(spikes_merged)
        elif factor_pos:
            pos_threshold = factor_pos * sigma
            spikes = self.apply_threshold(data, pos_threshold, True)
        elif factor_neg:
            neg_threshold = factor_neg * sigma
            spikes = self.apply_threshold(data, neg_threshold)
        else:
            raise ValueError("Either FactorPos or FactorNeg must be specified")
        return spikes

    def clean_spikes_with_refractory_period(self, spikes, refractory_period_in_sec, sampling_rate):
        """Clean detected spikes by removing those within the refractory period."""
        refractory_samples = int(refractory_period_in_sec * sampling_rate)
        cleaned_spikes = []
        last_spike = -refractory_samples  # Initialize to allow the first spike

        for spike in spikes:
            if spike >= last_spike + refractory_samples:
                cleaned_spikes.append(spike)
                last_spike = spike

        return np.array(cleaned_spikes)

    def pipeline(self, data, sampling_rate):
        """Spike detection pipeline according to
        H. Gonzalo Rey, C. Pedreira, R. Quian Quiroga
        Past, present and future of spike sorting techniques
        Brain Research Bulletin, Volume 119, Part B, October 2015, pp. 106-117
        https://doi.org/10.1016/j.brainresbull.2015.04.007
        """
        filter_type = self.config.get("Filter", {}).get("Type", "bandpass")
        if filter_type == "bandpass":
            lowcut = self.config.get("Filter", {}).get("LowCut", 200)
            highcut = self.config.get("Filter", {}).get("HighCut", 3000)
            data_filtered = self.filter_pipeline.apply_bandpass_filter(data, lowcut, highcut, sampling_rate)
        else:
            data_filtered = data
        
        method = self.config.get("SpikeDetection", {}).get("Method", "threshold")
        if method == "threshold":
            spikes_unique = self.thresholding(data_filtered)
            refractory_period = self.config.get("SpikeDetection", {}).get("RefractoryPeriod", 0.001)
            spikes_cleaned = self.clean_spikes_with_refractory_period(spikes_unique, refractory_period, sampling_rate)
            spikes = spikes_cleaned
            return spikes
        else:
            raise NotImplementedError("Other detection method not yet implemented")

class BRWFileProcessor:
    def __init__(self, config):
        self.config = config
        self.spike_detector = SpikeDetection(config)

    def version_check(self, file_path):
        """Check 3Brain version compatibility."""
        with h5py.File(file_path, 'r') as h5file:
            if h5file.attrs['Version'] != 320 or h5file['3BData'].attrs['Version'] != 102 or h5file['3BRecInfo'].attrs['Version'] != 102:
                warnings.warn("Versions mismatch!", UserWarning)
            else:
                print("Loading data...")

    def convert_digital_to_analog_in_micro_volt(self, bit_depth, max_volt, min_volt, signal_inversion, digital_value):
        mv_offset = signal_inversion * min_volt
        adc_counts_to_mv = signal_inversion * ((max_volt - min_volt)/2 ** bit_depth)
        analog_value = mv_offset + digital_value * adc_counts_to_mv
        return analog_value

    def load_meta_data(self, file_path):
        """Load meta data from file."""
        with h5py.File(file_path, 'r') as h5file:
            
            self.version_check(file_path)
            
            meta_data = {
                "rec_info": h5file['3BRecInfo'],
                "bit_depth": int(h5file['3BRecInfo']['3BRecVars']['BitDepth'][0]),
                "max_volt": float(h5file['3BRecInfo']['3BRecVars']['MaxVolt'][0]),
                "min_volt": float(h5file['3BRecInfo']['3BRecVars']['MinVolt'][0]),
                "n_rec_frames": int(h5file['3BRecInfo']['3BRecVars']['NRecFrames'][0]),
                "sampling_rate": float(h5file['3BRecInfo']['3BRecVars']['SamplingRate'][0]),
                "signal_inversion": float(h5file['3BRecInfo']['3BRecVars']['SignalInversion'][0]),
                "experiment_type": int(h5file['3BRecInfo']['3BRecVars']['ExperimentType'][0]),
                "n_cols": int(h5file['3BRecInfo']['3BMeaChip']['NCols'][0]),
                "n_rows": int(h5file['3BRecInfo']['3BMeaChip']['NRows'][0]),
                "chs": h5file['3BRecInfo']['3BMeaStreams']['Raw']['Chs'],    
            }
            
            print("Meta data:")
            print(meta_data)

            return meta_data

    def process_serial(self, file_path, meta_data):
        """Process .brw files serial."""
        sampling_rate = meta_data['sampling_rate']
        spikes_per_channel = {}  # Dictionary for spike times per channel

        with h5py.File(file_path, 'r') as h5file:
            
            self.version_check(file_path)

            dataset = h5file['3BData/Raw']
            data_array = dataset[:]
            n_channels = meta_data['n_cols'] * meta_data['n_rows']
            print(f"Process 1D-dataset with {dataset.shape[0]} samples and {n_channels} channels...")

            # Reshape in 2D-array (Samples x channels)     
            data_reshaped = data_array.reshape(-1, n_channels)
            print(data_reshaped.shape)

            # Process of each channel
            for channel_idx in range(n_channels):
                channel_data = data_reshaped[:, channel_idx]
                channel_data_analog = self.convert_digital_to_analog_in_micro_volt(
                    meta_data['bit_depth'],
                    meta_data['max_volt'],
                    meta_data['min_volt'],
                    meta_data['signal_inversion'],
                    digital_value=channel_data
                )
                
                channel_spike_indices = self.spike_detector.pipeline(channel_data_analog, sampling_rate)
                # channel_spike_indices = detect_spikes_wavelet(channel_data)

                if channel_idx not in spikes_per_channel:
                    spikes_per_channel[channel_idx] = []
                spikes_per_channel[channel_idx].extend(channel_spike_indices.tolist())

                # Debugging print
                # print(f"Channel\t{channel_idx}\tSpikes\t{len(channel_spike_indices)}")

        return spikes_per_channel, sampling_rate


class SpikeDataSaver:

    def preparation_of_spike_data_for_saving(self, spikes_per_channel):
        """Preprocessing."""
        spike_times, spike_channels = [], []

        for channel_idx, Times in spikes_per_channel.items():
            spike_times.extend(Times)
            spike_channels.extend([channel_idx] * len(Times))

        # Sorting the spikes by time
        indices_sorted = np.argsort(spike_times)
        spike_times = np.array(spike_times)[indices_sorted]
        spike_channels = np.array(spike_channels)[indices_sorted]

        print(f"Total detected {len(spike_times)} spikes across all channels.")
        return spike_times, spike_channels

    def save_spike_data_to_bxr(self, spike_times, spike_channels, min_analog_value, max_analog_value, sampling_rate, output_dir, output_filename='SpikeDetectionResults.bxr'):
        """Saves the results in .bxr format."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_file = os.path.join(output_dir, output_filename)

        with h5py.File(output_file, 'w') as h5file:
            h5file.attrs['Version'] = 301
            h5file.attrs['SamplingRate'] = sampling_rate
            h5file.attrs['MinAnalogValue'] = min_analog_value
            h5file.attrs['MaxAnalogValue'] = max_analog_value

            group = h5file.create_group('Well_A1')
            group.create_dataset('SpikeTimes', data=np.array(spike_times, dtype=np.int64))
            group.create_dataset('SpikeChIdxs', data=np.array(spike_channels, dtype=np.int32))
        
            print(f"BXR file '{output_file}' successfully saved.")

class FileProcessor:
    """Handles processing of files."""
    def __init__(self, config_path):
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config
        self.brw_processor = BRWFileProcessor(self.config)
        self.data_saver = SpikeDataSaver()


    def process_one_file(self, file_path):
        output_dir = self.config.get("OutputFolder", 'data/output')

        meta_data = self.brw_processor.load_meta_data(file_path)
        min_analog_value = meta_data['min_volt']
        max_analog_value = meta_data['max_volt']

        time_start = time.time()
        if self.config.get("ExecutionMode", "serial") == "serial":
            spikes_per_channel, sampling_rate = self.brw_processor.process_serial(file_path, meta_data)
        # elif self.config.get("ExecutionMode") == "parallel":
        #     spikes_per_channel, sampling_rate = self.brw_processor.process_parallel(file_path, meta_data)
        else:
            raise NotImplementedError("Other execution mode not yet implemented")

        spike_times, spike_channels = self.data_saver.preparation_of_spike_data_for_saving(spikes_per_channel)
        output_filename=f'{os.path.basename(file_path)}.bxr' 

        # Saving the data in a .bxr file
        self.data_saver.save_spike_data_to_bxr(
            spike_times,
            spike_channels,
            min_analog_value,
            max_analog_value,
            sampling_rate,
            output_dir,
            output_filename
        )

        print("Processing completed. Results were saved.")
        time_end = time.time()
        print(f"Total execution time: {time_end - time_start:.2f} Seconds")


    def load_and_process_files(self):
        folder_path = self.config.get("InputFolder", 'data/input')
        # Create input path
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        print(f"Files found: {len(os.listdir(folder_path))}")
        # Iterate over each file in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            print("Current:", file_path)
            # Check if it's a file (not a directory)
            if os.path.isfile(file_path):
                try:
                    # Load the file
                    self.process_one_file(file_path)

                except Exception as e:
                    logger.error(f"Error processing file {filename}: {e}", exc_info=True)



if __name__ == "__main__":
    print('startup...')
    CONFIG_PATH = "data/config.yaml"
    processor = FileProcessor(CONFIG_PATH)
    processor.load_and_process_files()
    print('All operations finished.')