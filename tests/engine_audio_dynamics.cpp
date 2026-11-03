// Native regressions for rolling float capture, spectral motion and FPS independence.
#include "WallpaperEngine/Audio/Drivers/Recorders/AudioAnalysis.h"
#include <cassert>
#include <iostream>
#include <limits>
using namespace WallpaperEngine::Audio::Drivers::Recorders;
int main () {
    AudioSampleWindow<16> window;
    float output[16];
    for (int i = 0; i < 16; ++i) window.push (i % 2 ? 0.0005f : -0.0005f);
    window.windowed (output);
    assert(window.dirty && output[8] < -0.0004f); // well below an 8-bit step
    window.dirty = false;
    window.push (0.001f);
    window.windowed (output);
    assert(window.dirty && output[8] > 0.0f); // update after one sample, no block wait
    window.push (std::numeric_limits<float>::quiet_NaN());
    window.windowed (output);
    for (float value : output) assert(std::isfinite(value));
    window.clear(); window.windowed(output);
    for (float value : output) assert(value == 0.0f);

    float powers[64] {}, levels[64];
    SpectrumDynamics dynamics;
    powers[10] = 0.01f;
    dynamics.levels(powers, 1, 1, levels);
    assert(levels[10] > 0.7f && levels[40] == 0.0f);
    // Same energy and overall volume, different note: response follows the new band.
    powers[10] = 0; powers[40] = 0.01f;
    dynamics.levels(powers, 1, 0.03f, levels);
    assert(levels[40] > 0.9f && levels[10] == 0.0f);
    float onset = levels[40];
    dynamics.levels(powers, 1, 0.03f, levels);
    assert(onset > levels[40] + 0.2f); // positive spectral flux accents the attack
    dynamics.levels(powers, 3, 0.03f, levels);
    assert(levels[40] < 1.0f && levels[40] > 0.75f); // high gain preserves headroom
    dynamics.levels(powers, 0, 0.03f, levels);
    for (float level : levels) assert(level == 0.0f);
    for (float& power : powers) power = 1e-9f;
    dynamics.levels(powers, 4, 3, levels);
    for (float level : levels) assert(level == 0.0f); // silence/noise is not amplified
    powers[0] = std::numeric_limits<float>::quiet_NaN();
    dynamics.levels(powers, 1, 0.03f, levels);
    for (float level : levels) assert(std::isfinite(level) && level >= 0 && level <= 1);

    float reference = 0;
    for (int fps : {15, 30, 60, 144}) {
        float level = 0;
        for (int frame = 0; frame < fps; ++frame) level = smoothSpectrum(level, 1, 1.0f/fps);
        for (int frame = 0; frame < fps/5; ++frame) level = smoothSpectrum(level, 0, 1.0f/fps);
        // Exact elapsed time for each frame rate, including fractional final frame.
        level = smoothSpectrum(level, 0, 0.2f - static_cast<float>(fps/5)/fps);
        if (fps == 15) reference = level;
        assert(std::abs(level - reference) < 0.00001f);
    }
    std::cout << "Float capture, rolling updates, equal-volume spectral changes, onsets, silence and FPS: OK\n";
}
