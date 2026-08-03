# -*- coding: utf-8 -*-
"""
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
@date: Fri Oct 17 2020
"""

import numpy as np
from scipy.linalg import solve_toeplitz
import scipy.signal as signal
import pywt
import scipy.stats as stats
import copy

from .PythonUtility import rangeSelection

def valueMapping(data, vmin=0, vmax=1, method="linear"):
    if method == "power":
        data = np.power(data,10)
    return (data - np.min(data)) / (np.max(data)-np.min(data)) * (vmax-vmin) + vmin

def stderr(data, axis=0):
    return np.std(data, axis=axis)/np.sqrt(data.shape[axis])

def rssq(array, axis=1):
    return np.sqrt(np.sum(np.square(array), axis=axis))

def rms(array, axis=1):
    return np.sqrt(np.mean(np.square(array), axis=axis))

def getIndices(length, window, overlap):
    return np.array(range(0, length+1-window, window-overlap))

def elementwise_subtract(matrix, array, axis=0):
    if axis == 0:
        return matrix - np.tile(array.reshape(1,len(array)),(matrix.shape[0],1))
    
    elif axis == 1:
        return matrix - np.tile(array.reshape(len(array),1),(1,matrix.shape[1]))
    
    else:
        raise ValueError("Only work for 2-D Matrix")

def InverseSigmoidFunc(xdata, L, k, x0, L0):
    return L / (1 + np.exp( -k * (xdata - x0) )) + L0

def PowerDecayFunc(xdata, L, k, x0, L0):
    return L * np.exp( -k * (xdata - x0) ) + L0

def getROC(y_true, y_score):
    thresholds = sorted(np.unique(y_score))
    thresholds.insert(0, min(y_score)-1)
    thresholds.append(max(y_score)+1)
    fpr = np.zeros(len(thresholds))
    tpr = np.zeros(len(thresholds))
    for i in range(len(thresholds)):
        tpr[i] = np.sum(y_true + np.array((y_score > thresholds[i]),dtype=float) == 2) / np.sum(y_true)
        fpr[i] = np.sum((y_true == 0) + np.array((y_score > thresholds[i]),dtype=float) == 2) / np.sum(y_true==False)

    return (fpr, tpr, thresholds)

def smooth(data, window):
    pre = int(window/2)
    post = window - pre
    leadingSmooth = np.array([np.mean(data[:i+post]) for i in range(pre)])
    centerSmooth = np.array([np.mean(data[i-pre:i+post]) for i in range(pre, len(data)-post+1)])
    tailingSmooth = np.array([np.mean(data[i-pre:]) for i in range(len(data)-post+1, len(data))])
    return np.concatenate((leadingSmooth, centerSmooth, tailingSmooth))

def addJitter(data, shift=0.1):
    return np.random.randn(len(data)) * np.std(data) * shift + data

def removeOutlier(data, method="zscore", zlim=3):
    if method == "zscore":
        return data[rangeSelection(data, [np.mean(data)-np.std(data)*zlim,np.mean(data)+np.std(data)*zlim])]

def linearfit(x, y, x_new):
    coefficients = np.polyfit(x, y, 1)
    return x_new * coefficients[0] + coefficients[1]

def PSDStatistic(x, y, test="parametric", window=0):
    if not x.shape[0] == y.shape[0]:
        raise Warning("X and Y do not have the same length")

    statistic = np.zeros(x.shape[0])
    pvalue = np.zeros(y.shape[0])
    if test == "parametric":
        for i in range(x.shape[0]):
            if i >= window and i+window<len(x):
                statistic[i], pvalue[i] = stats.ttest_ind(np.mean(x[i-window:i+window,:],axis=0), np.mean(y[i-window:i+window],axis=0))
            elif i < window:
                statistic[i], pvalue[i] = stats.ttest_ind(np.mean(x[:i+window],axis=0), np.mean(y[:i+window],axis=0))
            elif i+window >= len(x):
                statistic[i], pvalue[i] = stats.ttest_ind(np.mean(x[i-window:],axis=0), np.mean(y[i-window:],axis=0))

    if test == "correlation":
        label = np.concatenate([np.zeros(x.shape[1]),np.ones(y.shape[1])])
        for i in range(x.shape[0]):
            if i >= window and i+window<len(x):
                statistic[i], pvalue[i] = stats.pearsonr(np.concatenate([np.mean(x[i-window:i+window,:],axis=0), np.mean(y[i-window:i+window],axis=0)]),label)
            elif i < window:
                statistic[i], pvalue[i] = stats.pearsonr(np.concatenate([np.mean(x[:i+window],axis=0), np.mean(y[:i+window],axis=0)]),label)
            elif i+window >= len(x):
                statistic[i], pvalue[i] = stats.pearsonr(np.concatenate([np.mean(x[i-window:],axis=0), np.mean(y[i-window:],axis=0)]),label)

    return statistic, pvalue

def regressionStatistic(feature, score, window=0):
    if not feature.shape[1] == len(score):
        raise Warning("X and Y do not have the same length")
        
    statistic = np.zeros(feature.shape[0])
    pvalue = np.zeros(feature.shape[0])
    
    for i in range(len(pvalue)):
        if i >= window and i+window+1<len(feature):
            statistic[i], pvalue[i] = stats.pearsonr(np.mean(feature[i-window:i+window+1,:],axis=0),score)
        elif i < window:
            statistic[i], pvalue[i] = stats.pearsonr(np.mean(feature[:i+window+1],axis=0),score)
        elif i+window+1 >= len(feature):
            statistic[i], pvalue[i] = stats.pearsonr(np.mean(feature[i-window:],axis=0),score)

    return statistic, pvalue

# %% Sample Entropy code was obtained from Wikipedia
def sampEn(L, m, r):
    N = len(L)
    B = 0.0
    A = 0.0

    xmi = np.array([L[i : i + m] for i in range(N - m)])
    xmj = np.array([L[j : j + m] for j in range(N - m + 1)])
    B = np.sum([np.sum(np.abs(xmii - xmj).max(axis=1) <= r) - 1 for xmii in xmi])
    
    m += 1
    xm = np.array([L[i : i + m] for i in range(N - m + 1)])
    A = np.sum([np.sum(np.abs(xmi - xm).max(axis=1) <= r) - 1 for xmi in xm])
    
    return -np.log(A / B)

def computeSampleEntropy(data, window=2.0, overlap=1.0, fs=100, m=4, r=0.4):
    window = int(window * fs)
    overlap = int(overlap * fs)
    epochs = getIndices(len(data),window,overlap)
    entropy = np.array(epochs,dtype=float)
    #for index in range(len(epochs)):
        #entropy[index] = sample_entropy(data[epochs[index]:epochs[index]+window], order=m, metric="chebyshev")
    time = (epochs + window) / fs
    
    return dict({"Time": time, "Entropy": entropy})  

# %% Sharpness Meassure 
def calcSharpness(data, fs=100):
    # Step 1 - Filter to Beta
    sos = signal.butter(5, [15], 'hp', fs=fs, output='sos')
    data = signal.sosfilt(sos, data)
    
    filtCoe = signal.firwin(51, 30, pass_zero="lowpass", fs=fs)
    betaSignal = signal.filtfilt(filtCoe, 1, data)
    
    # Step 2 - Find Zero-crossing and their directionality
    RisingIndexes = np.where(np.diff(np.sign(betaSignal)) == 2)[0]
    FallingIndexes = np.where(np.diff(np.sign(betaSignal)) == -2)[0]
    
    # Step 3 - Find peak between the rising point and falling point
    SharpnessMeasure = dict()
    if RisingIndexes[0] < FallingIndexes[0]:
        peakIndexes = np.array([np.argmax(data[RisingIndexes[i]:FallingIndexes[i]]) for i in range(len(FallingIndexes))]) + RisingIndexes[0:len(FallingIndexes)]
        if len(RisingIndexes) > len(FallingIndexes):
            troughIndexes = np.array([np.argmin(data[FallingIndexes[i]:RisingIndexes[i+1]]) for i in range(len(FallingIndexes))]) + FallingIndexes[0:len(FallingIndexes)]
        else:
            troughIndexes = np.array([np.argmin(data[FallingIndexes[i]:RisingIndexes[i+1]]) for i in range(len(FallingIndexes)-1)]) + FallingIndexes[0:len(FallingIndexes)-1]
    else:
        troughIndexes = np.array([np.argmin(data[FallingIndexes[i]:RisingIndexes[i]]) for i in range(len(RisingIndexes))]) + FallingIndexes[0:len(RisingIndexes)]
        if len(FallingIndexes) > len(RisingIndexes):
            peakIndexes = np.array([np.argmax(data[RisingIndexes[i]:FallingIndexes[i+1]]) for i in range(len(RisingIndexes))]) + RisingIndexes[0:len(RisingIndexes)]
        else:
            peakIndexes = np.array([np.argmax(data[RisingIndexes[i]:FallingIndexes[i+1]]) for i in range(len(RisingIndexes)-1)]) + RisingIndexes[0:len(RisingIndexes)-1]
    
    SharpnessMeasure["trough"] = (data[troughIndexes-1] - data[troughIndexes]) + (data[troughIndexes+1] - data[troughIndexes]) / 2
    SharpnessMeasure["peak"] = (data[peakIndexes] - data[peakIndexes-1]) + (data[peakIndexes] - data[peakIndexes+1]) / 2
    SharpnessMeasure["ratio"] = np.max([np.mean(SharpnessMeasure["trough"])/np.mean(SharpnessMeasure["peak"]),
                                       np.mean(SharpnessMeasure["peak"])/np.mean(SharpnessMeasure["trough"])])
    
    return SharpnessMeasure

def computeSharpnessFunction(data, window=2.0, overlap=1.0, fs=100):
    window = int(window * fs)
    overlap = int(overlap * fs)
    epochs = getIndices(len(data),window,overlap)
    
    SharpnessRatio = np.array(range(len(epochs)),dtype=float)
    for index in range(len(epochs)):
        SharpnessMeasure = calcSharpness(data[epochs[index]:epochs[index]+window], fs=fs)
        SharpnessRatio[index] = SharpnessMeasure["ratio"]
        
    time = (epochs + window) / fs
    return dict({"Time": time, "SharpnessRatio": SharpnessRatio})

# %% Beta Bursts
def computeBetaBurstMetrics(data, frequency_band=[20,30], threshold=75, fs=100):
    sos = signal.butter(5, frequency_band, 'bp', fs=fs, output='sos')
    filtered = signal.sosfiltfilt(sos, data)
    envelope = np.abs(signal.hilbert(filtered))
    medianSignal = np.percentile(envelope, 50)
    thresholdSignal = np.percentile(envelope, threshold)
    betaBurstIdentification = np.where(envelope > thresholdSignal, 1, 0)
    referencePower = np.mean(envelope[np.bitwise_and(envelope > medianSignal, envelope < thresholdSignal)])
    
    metric = dict()
    
    # Metrics 1 - Burst Count
    betaBurstOnset = np.add(np.where(np.diff(betaBurstIdentification)==1), 1).flatten()
    if betaBurstIdentification[0] == 1:
        betaBurstOnset = np.append(0, betaBurstOnset)
    metric["index"] = betaBurstOnset
    metric["count"] = betaBurstOnset.size
    
    # Metrics 2 - Burst Duration
    metric["duration"] = np.zeros(metric["index"].shape)
    for i in range(metric["count"]):
        endPoint = np.where(betaBurstIdentification[metric["index"][i]:]==0)[0]
        if len(endPoint) == 0:
            endPoint = len(betaBurstIdentification) - metric["index"][i] - 1
        else:
            endPoint = endPoint[0]
        metric["duration"][i] = endPoint / fs
    
    # Metrics 2 - Burst Strength
    metric["strength"] = np.zeros(metric["index"].shape)
    for i in range(metric["count"]):
        if metric["duration"][i] > 0.1:
            endPoint = np.where(betaBurstIdentification[metric["index"][i]:]==0)[0]
            if len(endPoint) == 0:
                endPoint = len(betaBurstIdentification) - metric["index"][i] - 1
            else:
                endPoint = endPoint[0]
            metric["strength"][i] = np.max(envelope[metric["index"][i] : metric["index"][i] + endPoint]) - referencePower
    
    return metric

# %% Adaptive Signal Processing
def filtLMS(data, expected, order=10, step_size=0.001, regularizer=0.01, label=None):
    
    # Using Least-Mean-Square Adaptive Filter to Predict missing data
    Predicted = np.zeros(data.shape)
    Error = np.zeros(data.shape)
    Weights = np.zeros((order,len(data)))
    Predicted[:order] = data[:order]
    if label is  None:
        label = np.zeros(data.shape)
        
    for n in range(order, len(data)):
        variance = np.sum(data[n-order:n] * data[n-order:n])
        Predicted[n] = np.sum(Weights[:,n-1] * data[n-order:n])
        if label[n] > 0:
            Error[n] = 0
        else:
            Error[n] = expected[n] - Predicted[n]
        Weights[:,n] = Weights[:,n-1] + step_size / (regularizer + variance) * data[n-order:n] * Error[n]
    
    return (Predicted, Error, Weights)

# %% Phase Amplitude Coupling Filters
def UpperbandFilter(data, cutoff, fs=100):
    filtCoe = signal.firwin(51, cutoff, pass_zero="bandpass", fs=fs)
    filtSignal = signal.filtfilt(filtCoe, 1, data)
    return np.abs(signal.hilbert(filtSignal))

def PhaseBandFilter(data, cutoff, fs=100):
    sos = signal.butter(3, cutoff, 'bp', fs=fs, output='sos')
    filtSignal = signal.sosfiltfilt(sos, data)
    return np.angle(signal.hilbert(filtSignal)) * 180 / np.pi + 180

# %% Fitted Normalization
# Reference: Wang et. al., 2017. doi: 10.1016/j.nbd.2016.02.015
def fittedNormalization(psd, frequency, fitted_label, order=5):
    coefficients = np.polynomial.polynomial.polyfit(frequency[fitted_label], psd[fitted_label], order)
    fittedLine = np.ones(frequency.shape) * coefficients[0]
    for n in range(1, len(coefficients)):
        fittedLine += np.power(frequency,n) * coefficients[n]
    return fittedLine

# %% Spectrogram Methods
def normalizeSpectrogram(data, label, axis=0, log=False):
    normData = copy.deepcopy(data)
    
    if axis == 0:
        average = np.mean(data[label,:],axis=0)
        for i in range(data.shape[0]):
            if log:
                normData[i,:] = data[i,:] - average
            else:
                normData[i,:] = data[i,:] / average
                
    if axis == 1:
        average = np.mean(data[:,label],axis=1)
        for i in range(data.shape[1]):
            if log:
                normData[:,i] = data[:,i] - average
            else:
                normData[:,i] = data[:,i] / average
                
    return normData

def estimateARCoefficients(x, p):
    x = np.asarray(x, dtype=float) - np.mean(x)
    n = len(x)
    acov = np.correlate(x, x, mode='full')[n-1:] / n
    r_col = acov[:p]
    rhs = acov[1:p+1]
    phi = solve_toeplitz((r_col, r_col), rhs)
    sigma2 = acov[0] - np.dot(phi, rhs)
    return phi, sigma2

def autoregressivePSD(phi, sigma2, fs=250, nfft=256):
    a = np.concatenate([[1.0], -np.asarray(phi, dtype=float)])
    freq, h = signal.freqz([1.0], a, worN=nfft, fs=fs)
    psd = sigma2 * (np.abs(h) ** 2) / float(fs)
    psd *= 2
    return freq, psd

def estimateOrderByBIC(x, max_order):
    bic = np.zeros(max_order)
    for p in range(1, max_order+1):
        phi, sigma2 = estimateARCoefficients(x, p)
        bic[p-1] = np.log(len(x))*p + len(x) * np.log(sigma2)
        if p > 1 and bic[p-1] > bic[p-2]:
            return p-1
        
    return np.argmin(bic) + 1

def MedtronicPSD(data, packets=[24,38,25,38], fs=250):
    window = 256

    maxIndex = 250
    count = 8
    nfft = 0
    while maxIndex < len(data):
        if maxIndex >= 250:
            nfft += 1
        maxIndex += packets[count % len(packets)]
        count += 1

    freq = np.arange(window)/window*fs
    power = np.zeros((len(freq), nfft))
    time = np.zeros((nfft))

    maxIndex = 250
    for i in range(nfft):
        time[i] = maxIndex / fs
        windowed_data = np.zeros(window)
        windowed_data[:250] = data[maxIndex-250:maxIndex] * (np.hanning(250)/54)
        power[:,i] = np.abs(np.fft.fft(windowed_data))
        maxIndex += packets[i % len(packets)]

    return {"Time": time, "Frequency": freq[:100], "Power": power[:100,:], "logPower": 10*np.log10(power[:100,:]), "Config": {"Window": 256, "Overlap": 0}}

def defaultSpectrogram(data, window=2.0, overlap=1.0, frequency_resolution=0.5, fs=100):
    configuration = {"Window": window, "Overlap": overlap}
    window = int(window * fs)
    overlap = int(overlap * fs)
    NFFT = int(fs / frequency_resolution)
    frequency, time, spectrum = signal.spectrogram(data, window="hamming", nperseg=window, noverlap=overlap, nfft=NFFT, fs=fs)
    return dict({"Time": time, "Frequency": frequency, "Power": np.abs(spectrum), "logPower": 10*np.log10(np.abs(spectrum)), "Config": configuration})

def autoRegressiveSpectrogram(data, window=2.0, overlap=1.0, frequency_resolution=0.5, max_frequency=100, fs=100, order=0):
    configuration = {"Window": window, "Overlap": overlap}
    window = int(window * fs)
    overlap = int(overlap * fs)
    NFFT = int(fs / frequency_resolution)
    epochs = getIndices(len(data),window,overlap)
    
    if order == 0:
        order = estimateOrderByBIC(data, int(fs / 5))
    
    for index in range(len(epochs)):
        phi, sigma2 = estimateARCoefficients(data[epochs[index]:epochs[index]+window], order)
        frequency, p = autoregressivePSD(phi, sigma2, fs=fs, nfft=NFFT)
        if index == 0:
            spectrum = np.ndarray((len(frequency), len(epochs)))
        spectrum[:,index] = p
    time = (epochs + window) / fs
    
    return dict({"Time": time, "Frequency": frequency, "Power": spectrum, "logPower": 10*np.log10(spectrum), "Config": configuration})

def welchSpectrogram(data, window=2.0, overlap=1.0, frequency_resolution=0.5, max_frequency=100, fs=100):
    configuration = {"Window": window, "Overlap": overlap}

    target_fs = max_frequency * 4
    decimation_factor = int(fs // target_fs)
    while decimation_factor > 1:
        step = min(decimation_factor, 10)
        data = signal.decimate(data, step, zero_phase=True)
        fs = fs / step
        decimation_factor = int(fs // target_fs)

    window = int(window * fs)
    overlap = int(overlap * fs)
    NFFT = int(fs / frequency_resolution)
    epochs = getIndices(len(data),window,overlap)

    frequency = np.fft.rfftfreq(NFFT, d=1/fs)
    frequency_mask = frequency <= max_frequency
    frequency = frequency[frequency_mask]

    spectrum = np.ndarray((len(frequency), len(epochs)))
    for index in range(len(epochs)):
        _, p = signal.welch(data[epochs[index]:epochs[index]+window], fs=fs, nfft=NFFT)
        spectrum[:,index] = p[frequency_mask]
    time = (epochs + window) / fs
    
    return dict({"Time": time, "Frequency": frequency, "Power": spectrum, "logPower": 10*np.log10(spectrum), "Config": configuration})

def inertiaHilbertSpectrogram(data, frequency, freq_bandwidth=2, fs=100):
    spectrum = np.ndarray((len(frequency), len(data)))
    for index in range(len(frequency)):
        filterBand = [frequency[index] - freq_bandwidth / 2, frequency[index] + freq_bandwidth / 2]
        sos = signal.butter(5, filterBand, 'bp', fs=fs, output='sos')
        filteredData = signal.sosfiltfilt(sos, data, axis=0)
        filteredDataMagnitude = rssq(filteredData, axis=1)
        spectrum[index,:] = np.abs(signal.hilbert(filteredDataMagnitude))
    return spectrum

def waveletTimeFrequency(data, freq, ma=1, w=6, fs=100):
    widths = w * fs / (2 * freq * np.pi)
    cwtm = signal.cwt(data, signal.morlet2, widths, w=w)
    configuration = {"Window": widths, "Type": "morlet2", "MovingAverage": ma}
    power = np.abs(cwtm)
    if ma > 1:
        for i in range(len(data)):
            if i < ma:
                power[:,i] = np.mean(power[:,:i+ma],axis=1)
            elif i+ma >= len(data):
                power[:,i] = np.mean(power[:,i-ma:],axis=1)
            else:
                power[:,i] = np.mean(power[:,i-ma:i+ma],axis=1)
    return dict({"Time": np.array(range(len(data)))/fs,"Frequency": freq, "Power": power, "logPower": 10*np.log10(power), "Config": configuration})

def calculateMissingLabel(missing, threshold=0, window=2.0, overlap=1.0, fs=100):
    window = int(window * fs)
    overlap = int(overlap * fs)
    epochs = getIndices(len(missing),window,overlap)
    missing_label = np.ndarray((len(epochs)), dtype=bool)
    for index in range(len(epochs)):
        missing_label[index] = np.mean(missing[epochs[index]:epochs[index]+window]) > threshold
    return missing_label