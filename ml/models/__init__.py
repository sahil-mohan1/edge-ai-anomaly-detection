"""
1D-CNN Anomaly Detection & Correction Models
=====================================================
Uses a 1D Convolutional Neural Network with Zero-Padding Latent Interpolation 
to detect and correct anomalies in water level sensor data in real time.

Package structure:
  config.py              – constants, error codes, model hyper-parameters
  cnn_corrector.py       – CNN inference and zero-padding pipeline
  archive/               – legacy SNARIMAX and ARFR models
"""

from .cnn_corrector import CNNCorrector

__all__ = ["CNNCorrector"]
