import os

import h5py
import numpy as np

class SpikeDataSaver:
    """Handles saving spike data in .bxr format.

    This class provides methods to prepare spike data for saving and to save the data 
    in a specified format.

    Methods:
        preparation_of_spike_data_for_saving(spikes_per_channel):
            Prepares spike data for saving by organizing and sorting it.
        
        save_spike_data_to_bxr(spike_times, spike_channels, min_analog_value, max_analog_value, sampling_rate, output_dir, output_filename):
            Saves the spike data to a .bxr file.
    """

    def preparation_of_spike_data_for_saving(self, spikes_per_channel):
        """Preprocesses spike data for saving.

        This method organizes the spike times and their corresponding channel indices 
        into sorted arrays.

        Args:
            spikes_per_channel (dict): A dictionary where the keys are channel IDs (int) 
                                        and the values are lists of spike times (int).

        Returns:
            tuple: A tuple containing:
                - np.ndarray: An 1D array of sorted spike times.
                - np.ndarray: An 1D array of channel indices corresponding to the sorted spike times.
        """
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
        """Saves the results in .bxr format.

        This method creates a .bxr file and saves the spike times and channel indices 
        along with metadata such as sampling rate and analog value limits.

        Args:
            spike_times (np.ndarray): An 1D array of spike times to be saved.
            spike_channels (np.ndarray): An 1D array of channel indices corresponding to the spike times.
            min_analog_value (float): The minimum voltage of the of the recording amplifiers sampling range.
            max_analog_value (float): The maximum voltage of the recording amplifiers sampling range.
            sampling_rate (float): Value for the sampling frequency used for recording data.
            output_dir (str): The directory where the .bxr file will be saved.
            output_filename (str, optional): The name of the output .bxr file. Defaults to 'SpikeDetectionResults.bxr'.

        Raises:
            OSError: If the output directory cannot be created or accessed.
        """
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