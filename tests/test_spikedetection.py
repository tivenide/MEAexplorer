import unittest
import numpy as np

# Add the src directory to the Python path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from rawsignal.spikedetection import SpikeDetection

class TestSpikeDetection(unittest.TestCase):
    """Unit tests for the SpikeDetection class."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            "SpikeDetection": {"FactorPos": 5, "FactorNeg": 5, "RefractoryPeriod": 0.001},
            "Filter": {"Type": "bandpass", "LowCut": 300, "HighCut": 3000}
        }
        self.sampling_rate = 10000  # 10 kHz
        self.spike_detector = SpikeDetection(self.config)
    
    def test_calculate_sigma(self):
        """Test sigma calculation."""
        data = np.array([1, 2, 3, 4, 5, -1, -2, -3, -4, -5])
        sigma = self.spike_detector.calculate_sigma(data)
        self.assertAlmostEqual(sigma, 4.44773906)
    
    def test_apply_threshold(self):
        """Test apply threshold function."""
        data = np.array([1, 3, 7, 10, -2, -6, -9])
        threshold = 5
        spikes = self.spike_detector.apply_threshold(data, threshold)
        self.assertTrue(np.array_equal(spikes, np.array([5, 6])))
        spikes_pos = self.spike_detector.apply_threshold(data, threshold, True)
        self.assertTrue(np.array_equal(spikes_pos, np.array([2, 3])))

    def test_thresholding(self):
        data = np.array([1, 3, 7, 10, -2, -6, -9])
        # assuming thresholdvalue of 6.67 (pos) and 4.45 (neg)
        
        # Test with both factors
        self.config = {
            "SpikeDetection": {"FactorPos": 0.75, "FactorNeg": 0.5}
        }
        self.spike_detector = SpikeDetection(self.config)
        spikes = self.spike_detector.thresholding(data)
        self.assertTrue(np.array_equal(spikes, np.array([2, 3, 5, 6])))
        
        # Test with only positive factor
        self.config = {
            "SpikeDetection": {"FactorPos": 0.75}
        }
        self.spike_detector = SpikeDetection(self.config)
        spikes = self.spike_detector.thresholding(data)
        self.assertTrue(np.array_equal(spikes, np.array([2, 3])))

        # Test with only negative factor
        self.config = {
            "SpikeDetection": {"FactorNeg": 0.5}
        }
        self.spike_detector = SpikeDetection(self.config)
        spikes = self.spike_detector.thresholding(data)
        self.assertTrue(np.array_equal(spikes, np.array([5, 6])))

        # Test with no factors
        self.config = {
            "SpikeDetection": {}
        }
        self.spike_detector = SpikeDetection(self.config)
        with self.assertRaises(ValueError):
            spikes = self.spike_detector.thresholding(data)


    def test_clean_spikes_with_refractory_period(self):
        """Test spike cleaning with refractory period."""
        spikes = np.array([15, 20, 37, 40, 56, 57, 72, 81])
        cleaned_spikes = self.spike_detector.clean_spikes_with_refractory_period(spikes, 0.2, 100)
        self.assertTrue(np.array_equal(cleaned_spikes, np.array([15, 37, 57, 81])))

    def test_pipeline(self):
        """Integration test of spike detection pipeline"""
        data = np.array(
            [-34, -66, 49, -43, -61, -23, -6, 25, -12, 51, 39, -55, -44,
            63, 29, 31, -15, 59, 82, 61, -68, -70, -41, -9, -41, 63,
            5, 58, -42, -12, 41, 75, 25, -36, 41, -68, 23, -11, 35,
            14]
            )
        sampling_rate = 100
        self.config = {
            "SpikeDetection": {"FactorPos": 0.75, "FactorNeg": 0.5, "RefractoryPeriod": 0.02},
            "Filter": {"Type": "bandpass", "LowCut": 3, "HighCut": 30}
        }
        self.spike_detector = SpikeDetection(self.config)
        spikes = self.spike_detector.pipeline(data, sampling_rate)
        self.assertTrue(np.array_equal(spikes, np.array([4, 9, 11, 13, 16, 18, 20, 22, 24, 26, 28, 30, 35])))

if __name__ == '__main__':
    unittest.main()