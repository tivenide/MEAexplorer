import numpy as np
from rawsignal.filtering import FilterPipeline

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