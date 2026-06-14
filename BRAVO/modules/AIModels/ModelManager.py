from .MonopolarPowerEstimation.MonopolarPowerEstimation import EstimateMonopolar
from .FeatureExtraction.SurveyFeatureExtraction import FTGPeakDetector
from .BetaPeakDetection.BetaPeakDetector import BetaPeakDetector

Overview = {
    "BetaPeakDetection": {
        "Method": BetaPeakDetector,
        "DataType": "PSD",
    },
    "FTGPeakDetector": {
        "Method": FTGPeakDetector,
        "DataType": "PSD",
    },
    "MonopolarPowerEstimation": {
        "Method": EstimateMonopolar,
        "DataType": "Customized",
    }
}
