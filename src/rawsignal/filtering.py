from scipy.signal import butter, filtfilt

class FilterPipeline:
    """Applies filtering methods to the signal."""
    def apply_bandpass_filter(self, data, lowcut, highcut, sampling_rate, order=5):
        nyquist = 0.5 * sampling_rate
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)