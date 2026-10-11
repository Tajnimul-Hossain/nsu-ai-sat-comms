"""
generate_all_graphs.py
Generates every standard figure for the NIRO LAB CubeSat RF project
(Data / Telemetry / Telecommand links) from GNU Radio File Sink captures.

Usage:
    E:\\GNU\\python.exe generate_all_graphs.py

Each figure pops up one at a time (close the window to see the next).
Every figure is also saved as a 300 DPI PNG regardless of whether you
close the window quickly. Missing capture files are skipped with a
printed note rather than crashing the whole run.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: registers 3D projection
from scipy.ndimage import gaussian_filter
from scipy import signal

# ---------------------------------------------------------------
# CONFIG — adjust paths/sample rates to match your GNU Radio setup
# ---------------------------------------------------------------
DATA_DIR = r"E:\Communications\Satellite\STL Mode 1"
TELEMETRY_DIR = r"E:\Communications\Satellite\STL Mode 1"   # update to your actual folder
TELECOMMAND_DIR = r"E:\Communications\Satellite\STL Mode 1"  # update to your actual folder

DATA_SAMP_RATE = 2_000_000     # samp_rate_1 in the QPSK flowgraph
TM_SAMP_RATE = 48_000          # NBFM audio_rate
TC_SAMP_RATE = 48_000          # BFSK samp_rate_2
TC_SPS = 4                     # samples per symbol in the BFSK chain

TRANSIENT_SAMPLES = 8000       # discard lock-in transient on data captures


def load(path, dtype=np.complex64):
    if not os.path.exists(path):
        print(f"  [skip] not found: {path}")
        return None
    arr = np.fromfile(path, dtype=dtype)
    if arr.size == 0:
        print(f"  [skip] empty file: {path}")
        return None
    return arr


def show_and_save(fig, out_png, label):
    fig.tight_layout()
    fig.savefig(out_png, dpi=300)
    print(f"  saved: {out_png}")
    print(f"  showing '{label}' — close this window to continue...")
    plt.show()


# =================================================================
# 1. 3D Constellation Density  (Data link)
# =================================================================
def fig_constellation_density():
    print("\n[1/8] 3D Constellation Density (Data link)")
    after = load(os.path.join(DATA_DIR, "after"))
    if after is None:
        return
    after = after[TRANSIENT_SAMPLES:]

    bins = 200
    H, xedges, yedges = np.histogram2d(
        after.real, after.imag, bins=bins, range=[[-1.5, 1.5], [-1.5, 1.5]]
    )
    H_smooth = gaussian_filter(H, sigma=1.8)
    X, Y = np.meshgrid((xedges[:-1] + xedges[1:]) / 2, (yedges[:-1] + yedges[1:]) / 2)

    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(X, Y, H_smooth.T, cmap="viridis", linewidth=0, antialiased=True)
    ax.set_title("Data Link — QPSK Constellation Density (After Recovery)", fontweight="bold", pad=20)
    ax.set_xlabel("In-Phase (I)", labelpad=12)
    ax.set_ylabel("Quadrature (Q)", labelpad=12)
    ax.set_zlabel("Symbol Density", labelpad=10)
    ax.view_init(elev=35, azim=-45)
    fig.colorbar(surf, shrink=0.6, aspect=12, label="Density")
    show_and_save(fig, "1_data_constellation_3d.png", "Data — Constellation Density")


# =================================================================
# 2. PSD via Welch's method  (Data link)
# =================================================================
def fig_psd():
    print("\n[2/8] Power Spectral Density (Data link)")
    before = load(os.path.join(DATA_DIR, "before"))
    if before is None:
        return

    f, Pxx = signal.welch(before, fs=DATA_SAMP_RATE, nperseg=4096, return_onesided=False)
    f = np.fft.fftshift(f)
    Pxx = np.fft.fftshift(Pxx)

    fig = plt.figure(figsize=(9, 5.5))
    plt.plot(f / 1e3, 10 * np.log10(Pxx + 1e-15), linewidth=1.2, color="crimson")
    plt.title("Data Link — QPSK Transmit Spectrum (500 ksym/s, RRC \u03b1=0.35)", fontweight="bold")
    plt.xlabel("Frequency Offset (kHz)")
    plt.ylabel("Power Spectral Density (dB/Hz)")
    plt.grid(alpha=0.3)
    show_and_save(plt.gcf(), "2_data_psd.png", "Data — PSD")


# =================================================================
# 3. 3D Spectrogram  (Data link)
# =================================================================
def fig_spectrogram_3d():
    print("\n[3/8] 3D Spectrogram (Data link)")
    before = load(os.path.join(DATA_DIR, "before"))
    if before is None:
        return

    f, t, Sxx = signal.spectrogram(
        before, fs=DATA_SAMP_RATE, nperseg=1024, noverlap=512, return_onesided=False
    )
    f = np.fft.fftshift(f)
    Sxx = np.fft.fftshift(Sxx, axes=0)
    Sxx_db = 10 * np.log10(Sxx + 1e-12)
    T, F = np.meshgrid(t * 1e3, f / 1e3)

    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(T, F, Sxx_db, cmap="plasma", linewidth=0, antialiased=True)
    ax.set_title("Data Link — QPSK Transmit Spectrogram", fontweight="bold", pad=20)
    ax.set_xlabel("Time (ms)", labelpad=12)
    ax.set_ylabel("Frequency Offset (kHz)", labelpad=12)
    ax.set_zlabel("Power (dB)", labelpad=10)
    ax.view_init(elev=30, azim=-60)
    fig.colorbar(surf, shrink=0.6, aspect=12, label="Power (dB)")
    show_and_save(fig, "3_data_spectrogram_3d.png", "Data — 3D Spectrogram")


# =================================================================
# 4. Eye Diagram  (Data link, pre-symbol-sync tap)
# =================================================================
def fig_eye_diagram():
    print("\n[4/8] Eye Diagram (Data link)")
    tap = load(os.path.join(DATA_DIR, "eye_tap"))
    if tap is None:
        print("  Add a File Sink off the AGC output (Complex, name 'eye_tap') to enable this figure.")
        return

    sps = 4  # matches Constellation Modulator Samples/Symbol
    span = 2 * sps  # plot 2 symbol periods per trace
    trace = tap.real[TRANSIENT_SAMPLES:]
    n_traces = min(400, (len(trace) - span) // sps)

    fig = plt.figure(figsize=(9, 6))
    for i in range(n_traces):
        start = i * sps
        seg = trace[start:start + span]
        if len(seg) == span:
            plt.plot(np.arange(span), seg, color="steelblue", alpha=0.08, linewidth=1)
    plt.title("Data Link — Eye Diagram (Pre-Symbol-Sync, I channel)", fontweight="bold")
    plt.xlabel("Sample Index (within 2-symbol window)")
    plt.ylabel("Amplitude (I)")
    plt.grid(alpha=0.3)
    show_and_save(plt.gcf(), "4_data_eye_diagram.png", "Data — Eye Diagram")


# =================================================================
# 5 & 6. Telemetry TX/RX waveform + spectrum
# =================================================================
def fig_telemetry():
    print("\n[5/8] Telemetry TX/RX Waveform")
    tx = load(os.path.join(TELEMETRY_DIR, "tm_tx"), dtype=np.complex64)
    rx = load(os.path.join(TELEMETRY_DIR, "tm_rx"), dtype=np.float32)
    if tx is None or rx is None:
        print("  Add File Sinks off NBFM Transmit (Complex -> 'tm_tx') and NBFM Receive (Float -> 'tm_rx').")
        return

    n = min(2000, len(tx), len(rx))
    t_tx = np.arange(n) / TM_SAMP_RATE * 1e3
    t_rx = np.arange(n) / TM_SAMP_RATE * 1e3

    fig, axs = plt.subplots(2, 1, figsize=(9, 6), sharex=False)
    axs[0].plot(t_tx, tx.real[:n], color="darkgreen", linewidth=1)
    axs[0].set_title("Telemetry — UHF-TX Modulated Signal (I channel)", fontweight="bold")
    axs[0].set_xlabel("Time (ms)")
    axs[0].set_ylabel("Amplitude")
    axs[0].grid(alpha=0.3)

    axs[1].plot(t_rx, rx[:n], color="purple", linewidth=1)
    axs[1].set_title("Telemetry — Recovered Audio at Receiver", fontweight="bold")
    axs[1].set_xlabel("Time (ms)")
    axs[1].set_ylabel("Amplitude")
    axs[1].grid(alpha=0.3)

    show_and_save(fig, "5_telemetry_waveform.png", "Telemetry — TX/RX Waveform")

    print("\n[6/8] Telemetry Spectrum")
    f, Pxx = signal.welch(tx, fs=TM_SAMP_RATE, nperseg=1024, return_onesided=False)
    f = np.fft.fftshift(f); Pxx = np.fft.fftshift(Pxx)

    fig2 = plt.figure(figsize=(9, 5.5))
    plt.plot(f, 10 * np.log10(Pxx + 1e-15), color="darkorange", linewidth=1.2)
    plt.title("Telemetry — UHF-TX Spectrum (NBFM)", fontweight="bold")
    plt.xlabel("Frequency Offset (Hz)")
    plt.ylabel("Power Spectral Density (dB/Hz)")
    plt.grid(alpha=0.3)
    show_and_save(fig2, "6_telemetry_spectrum.png", "Telemetry — Spectrum")


# =================================================================
# 7 & 8. Telecommand symbol histogram/eye + TX/RX comparison
# =================================================================
def fig_telecommand():
    print("\n[7/8] Telecommand Symbol Distribution")
    sym = load(os.path.join(TELECOMMAND_DIR, "tc_symbols"), dtype=np.float32)
    if sym is None:
        print("  Add a File Sink off Symbol Sync 'out' (Float -> 'tc_symbols').")
        return

    fig = plt.figure(figsize=(9, 5.5))
    plt.hist(sym, bins=100, color="teal", alpha=0.8)
    plt.title("Telecommand — Recovered Symbol Value Distribution (BFSK)", fontweight="bold")
    plt.xlabel("Symbol Value")
    plt.ylabel("Count")
    plt.grid(alpha=0.3)
    show_and_save(fig, "7_telecommand_symbol_hist.png", "Telecommand — Symbol Distribution")

    print("\n[8/8] Telecommand Recovered Symbol Stream")
    n = min(400, len(sym))
    fig2 = plt.figure(figsize=(9, 5))
    plt.step(np.arange(n), sym[:n], where="mid", color="crimson", linewidth=1)
    plt.title("Telecommand — Symbol Stream (First 400 Samples)", fontweight="bold")
    plt.xlabel("Symbol Index")
    plt.ylabel("Decision Value")
    plt.grid(alpha=0.3)
    show_and_save(fig2, "8_telecommand_symbol_stream.png", "Telecommand — Symbol Stream")


# =================================================================
if __name__ == "__main__":
    fig_constellation_density()
    fig_psd()
    fig_spectrogram_3d()
    fig_eye_diagram()
    fig_telemetry()
    fig_telecommand()
    print("\nAll available graphs generated. Missing captures were skipped — see notes above.")
