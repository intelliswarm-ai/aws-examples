"""Spark jobs package for EMR Fraud Detection Pipeline.

This package contains the main Spark jobs:
- feature_engineering: Transform raw transactions to ML features
- model_training: Train fraud detection models with MLlib
- batch_scoring: Score transactions in batch mode
- streaming_scoring: Real-time scoring with Structured Streaming
"""
