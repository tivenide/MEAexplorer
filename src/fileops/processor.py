import os
import yaml
import time

from fileops.brw import BRWFileHandler
from fileops.saver import SpikeDataSaver

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads configuration from a YAML file.
    
    Attributes:
        config_path (str): The path to the YAML configuration file.
        config (dict): The loaded configuration data.   
    """

    def __init__(self, config_path):
        """Initializes the ConfigLoader with the specified configuration path.

        Args:
            config_path (str): The path to the YAML configuration file.
        """
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self):
        """Loads the configuration from the YAML file.

        Returns:
            dict: The configuration data loaded from the file.
        """
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)

class FileProcessor:
    """Handles processing of files based on the loaded configuration.

    Attributes:
        config_loader (ConfigLoader): An instance of ConfigLoader to load configurations.
        config (dict): The loaded configuration data.
        brw_handler (BRWFileHandler): An instance of BRWFileHandler for file operations.
        data_saver (SpikeDataSaver): An instance of SpikeDataSaver for saving processed data.
    """

    def __init__(self, config_path):
        """Initializes the FileProcessor with the specified configuration path.

        Args:
            config_path (str): The path to the YAML configuration file.
        """
        self.config_loader = ConfigLoader(config_path)
        self.config = self.config_loader.config
        self.brw_handler = BRWFileHandler(self.config)
        self.data_saver = SpikeDataSaver()


    def process_one_file(self, file_path):
        """Processes a single file and saves the results.

        Args:
            file_path (str): The path to the file to be processed.

        Raises:
            NotImplementedError: If the execution mode is not implemented.
        """
        output_dir = self.config.get("OutputFolder", 'data/output')

        meta_data = self.brw_handler.load_meta_data(file_path)
        min_analog_value = meta_data['min_volt']
        max_analog_value = meta_data['max_volt']

        time_start = time.time()
        if self.config.get("ExecutionMode", "serial") == "serial":
            spikes_per_channel, sampling_rate = self.brw_handler.process_serial(file_path, meta_data)
        # elif self.config.get("ExecutionMode") == "parallel":
        #     spikes_per_channel, sampling_rate = self.brw_handler.process_parallel(file_path, meta_data)
        elif self.config.get("ExecutionMode") == "serialWindow":
            spikes_per_channel, sampling_rate = self.brw_handler.process_serial_window(file_path, meta_data)
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
        """Loads and processes all files in the input folder specified in the configuration.

        Creates the input folder if it does not exist and processes each file found.

        Raises:
            Exception: If an error occurs during file processing.
        """
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
