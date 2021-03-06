"""
Functions for interacting with model classes:
"""

import numpy as np
import soundfile as sf
from .cnn_models import Conv1DModel

from features.spectral_features import stft, istft
from features.data_preprocessing import make_stft_features
from features.data_preprocessing import undo_preemphasis

def featurize_spectrogram(spectrogram):
    """
    Takes in a spectrogram and outputs a normalized version for consumption by
    the model
    """
    # Get the magnitude spectrogram and phases
    X_input = np.abs(spectrogram)
    phases = np.unwrap(np.angle(spectrogram))

    # Normalize the magnitude spectrogram
    X_input = np.sqrt(X_input)
    X_max = X_input.max()
    X_min = X_input.min()
    X_input = (X_input - X_min)/(X_max - X_min)

    return X_input, phases, X_max, X_min

def separate_sources(signal_path, model,
                     sample_rate=1e4, window_size=0.05, overlap=0.025):
    """
    Reads in the signal from signal_path and uses the model to separate it into
    component sources.
    Inputs:
        signal_path:  Path to audio file containing the signal
        model: Model object with a predict method to separate signals
        sample_rate: Sample rate expected by the model
        window_size: Size of spectrogram window in seconds
        overlap: Overlap used to compute spectrogram
    Outputs:
        sources: Numpy ndarray containing waveforms of separated sources
    """

    # Read in the audio file
    signal, rate = sf.read(signal_path)

    # Get complex spectrogram
    spectrogram = make_stft_features(signal, rate,
                                     sample_rate, window_size, overlap, fft_size=500)

    # Get model inputs
    X_input, phases, X_max, X_min = featurize_spectrogram(spectrogram)

    # Reshape the input to the form the model expects
    X_input = np.reshape(X_input, (1,X_input.shape[0],X_input.shape[1],1))

    # Get the model output for this input
    y_output = model.predict(X_input)

    # Undo the normalization
    y_output = y_output*(X_max - X_min) + X_min
    y_output = np.square(y_output)

    # Process these outputs back into waveforms
    duration = 1/2*(spectrogram.shape[0] + 1)*window_size
    source_list = []

    for i in range(y_output.shape[3]):
        complex_spectrogram = y_output[0,:,:,i]*np.exp(phases*1.0j)
        waveform = istft(complex_spectrogram,
                         sample_rate, None, overlap, two_sided=False,fft_size=500)
        waveform = undo_preemphasis(waveform)
        waveform = (waveform - waveform.mean())/waveform.std()
        source_list.append(waveform)

    sources = np.stack(source_list)

    return sources