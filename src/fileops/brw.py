import warnings

import h5py
import numpy as np

from rawsignal.spikedetection import SpikeDetection

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BRWFileHandler:
    """Handles reading and processing of .brw files.

    Attributes:
        config (dict): Configuration settings for processing.
        spike_detector (SpikeDetection): An instance of SpikeDetection for detecting spikes in the data.
    """
    def __init__(self, config):
        """Initializes the BRWFileHandler with the specified configuration.

        Args:
            config (dict): Configuration settings for processing .brw files.
        """
        self.config = config
        self.spike_detector = SpikeDetection(config)

    def version_check(self, file_path):
        """Check 3Brain version compatibility.

        This method checks if the version of the .brw file and its components are compatible
        with the expected versions. It raises a warning if there is a version mismatch.

        Args:
            file_path (str): The path to the .brw file to check.
        """
        with h5py.File(file_path, 'r') as h5file:
            if h5file.attrs['Version'] != 320 or h5file['3BData'].attrs['Version'] != 102 or h5file['3BRecInfo'].attrs['Version'] != 102:
                warnings.warn("Versions mismatch!", UserWarning)
            else:
                print("Loading data...")

    def convert_digital_to_analog_in_micro_volt(self, bit_depth, max_volt, min_volt, signal_inversion, digital_value):
        """Converts digital values to analog values in microvolts.

        Args:
            bit_depth (int): The bit depth for the sampled data.
            max_volt (float): The maximum voltage of the recording amplifiers sampling range.
            min_volt (float): The minimum voltage of the of the recording amplifiers sampling range.
            signal_inversion (float): either 1.0 or -1.0 to indicate whether the signal must be inverted or not.
            digital_value (np.ndarray): The digital value(s) to convert.

        Returns:
            np.ndarray: The converted analog value(s) in microvolts.
        """
        mv_offset = signal_inversion * min_volt
        adc_counts_to_mv = signal_inversion * ((max_volt - min_volt)/2 ** bit_depth)
        analog_value = mv_offset + digital_value * adc_counts_to_mv
        return analog_value

    def load_meta_data(self, file_path):
        """Load meta data from the specified .brw file.

        Args:
            file_path (str): The path to the .brw file from which to load metadata.

        Returns:
            dict: A dictionary containing metadata such as recording information, bit depth,
                  voltage limits, number of recording frames, sampling rate, signal inversion,
                  experiment type, and channel information.
        """
        with h5py.File(file_path, 'r') as h5file:
            
            self.version_check(file_path)
            
            meta_data = {
                "rec_info": h5file['3BRecInfo'],
                "bit_depth": int(h5file['3BRecInfo']['3BRecVars']['BitDepth'][0]), # an integer value indicating the bit depth for the sampled data
                "max_volt": float(h5file['3BRecInfo']['3BRecVars']['MaxVolt'][0]), # a floating-point value for the maximum voltage of the recording amplifiers sampling range
                "min_volt": float(h5file['3BRecInfo']['3BRecVars']['MinVolt'][0]), # a floating-point value for the minimum voltage of the recording amplifiers sampling range
                "n_rec_frames": int(h5file['3BRecInfo']['3BRecVars']['NRecFrames'][0]), # an integer value defining the number of recorded frames
                "sampling_rate": float(h5file['3BRecInfo']['3BRecVars']['SamplingRate'][0]), # a floating-point value for the sampling frequency used for recording data
                "signal_inversion": float(h5file['3BRecInfo']['3BRecVars']['SignalInversion'][0]), # either 1 or -1 to indicate whether the signal must be inverted or not
                "experiment_type": int(h5file['3BRecInfo']['3BRecVars']['ExperimentType'][0]), # an integer value indicating the experiment type, according to the following enumerator:
                # enum ExperimentType
                # {
                #   Standard = 0,
                #   EFP = 1
                # }
                "n_cols": int(h5file['3BRecInfo']['3BMeaChip']['NCols'][0]), # a scalar value indicating the number of columns of the MEA chip
                "n_rows": int(h5file['3BRecInfo']['3BMeaChip']['NRows'][0]), # a scalar value indicating the number of rows of the MEA chip
                "chs": h5file['3BRecInfo']['3BMeaStreams']['Raw']['Chs'], # a one-dimensional array of Channels listing the MEA channels that have been recorded for that stream  
            }
            
            print("Meta data:")
            print(meta_data)

            return meta_data

    def process_serial(self, file_path, meta_data):
        """
        Process .brw files serially.

        This method processes the specified .brw file and extracts spike information 
        for each channel based on the provided metadata.

        Args:
            file_path (str): The path to the .brw file to be processed.
            meta_data (dict): Metadata related to the processing of the file, 
                            which may include parameters such as sampling rate, etc.

        Returns:
            tuple: A tuple containing:
                - dict: A dictionary where the keys are channel IDs (int) and the values 
                        are lists of indices (int) representing the timepoints of detected spikes.
                        
                        Example:
                        {
                            0: [0, 17, 43],  # Channel 0 detected spikes at indices 0, 17, and 43
                            1: [],          # Channel 1 detected no spikes
                            2: [38, 42]     # Channel 2 detected spikes at indices 38 and 42
                        }
                - float: The sampling rate used for processing the file.
        """
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

    def process_serial_window(self, file_path, meta_data):
        """
        Process .brw files serially with windows.

        This method processes the specified .brw file and extracts spike information 
        for each channel based on the provided metadata.

        Args:
            file_path (str): The path to the .brw file to be processed.
            meta_data (dict): Metadata related to the processing of the file, 
                            which may include parameters such as sampling rate, etc.

        Returns:
            tuple: A tuple containing:
                - dict: A dictionary where the keys are channel IDs (int) and the values 
                        are lists of indices (int) representing the timepoints of detected spikes.
                        
                        Example:
                        {
                            0: [0, 17, 43],  # Channel 0 detected spikes at indices 0, 17, and 43
                            1: [],          # Channel 1 detected no spikes
                            2: [38, 42]     # Channel 2 detected spikes at indices 38 and 42
                        }
                - float: The sampling rate used for processing the file.
        """

        sampling_rate = meta_data['sampling_rate']
        window_time_in_sec = self.config.get("SerialWindow", {}).get("WindowTimeInSec", 2)
        with h5py.File(file_path, 'r') as h5file:
            start_index = 0
            end_index = meta_data['n_rec_frames']
            step_size = int(sampling_rate * window_time_in_sec)
            n_channels = meta_data['n_cols'] * meta_data['n_rows']
            spikes_per_channel = {}
            
            # window level
            for window_start_index in range(start_index, end_index, step_size):
                
                window_end_index = min(window_start_index + step_size, end_index)
                
                data_slice = np.array(h5file['3BData/Raw'][window_start_index*n_channels:window_end_index*n_channels]).reshape(-1,n_channels)
                
                # discard windows, which are too long or too short
                if len(data_slice) == step_size:
                    logger.info(f"w: {window_start_index}")

                    # channel level within window
                    for channel_idx in range(n_channels):
                        
                        channel_data = data_slice[:, channel_idx]
                        
                        channel_data_analog = self.convert_digital_to_analog_in_micro_volt(
                            meta_data['bit_depth'],
                            meta_data['max_volt'],
                            meta_data['min_volt'],
                            meta_data['signal_inversion'],
                            digital_value=channel_data
                        )
                       
                        channel_window_spike_indices = self.spike_detector.pipeline(channel_data_analog, sampling_rate)
                        
                        if channel_idx not in spikes_per_channel:
                            spikes_per_channel[channel_idx]=[]
                        channel_spike_indices = channel_window_spike_indices + window_start_index

                        spikes_per_channel[channel_idx].extend(channel_spike_indices.tolist())
        return spikes_per_channel, sampling_rate