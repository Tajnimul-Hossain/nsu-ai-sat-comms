import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# --- Load raw IQ ---
before = np.fromfile("before", dtype=np.complex64)
after  = np.fromfile("after",  dtype=np.complex64)

# --- Constellation: density-shaded scatter (smooth, not sparse dots) ---
fig, axs = plt.subplots(1, 2, figsize=(10, 5))
axs[0].scatter(before.real, before.imag, s=2, alpha=0.15, color="steelblue")
axs[0].set_title("Before Recovery (TX, RRC-shaped)")
axs[0].set_xlabel("I"); axs[0].set_ylabel("Q"); axs[0].axis("equal")

axs[1].scatter(after.real, after.imag, s=4, alpha=0.25, color="darkorange")
axs[1].set_title("After Costas + Clock Recovery")
axs[1].set_xlabel("I"); axs[1].set_ylabel("Q"); axs[1].axis("equal")

plt.tight_layout()
plt.savefig("constellation_comparison.png", dpi=300)
plt.show()

# --- Smooth spectrum via Welch's method (much smoother than a raw FFT snapshot) ---
samp_rate = 2_000_000  # match samp_rate_1
f, Pxx = signal.welch(before, fs=samp_rate, nperseg=4096, return_onesided=False)
f = np.fft.fftshift(f); Pxx = np.fft.fftshift(Pxx)

plt.figure(figsize=(8, 5))
plt.plot(f / 1e3, 10 * np.log10(Pxx), linewidth=1.2, color="crimson")
plt.xlabel("Frequency Offset (kHz)")
plt.ylabel("Power Spectral Density (dB/Hz)")
plt.title("QPSK Transmit Spectrum — 500 ksym/s, RRC α=0.35")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("spectrum_smooth.png", dpi=300)
plt.show()