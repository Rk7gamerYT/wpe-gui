#include "WallpaperEngine/Audio/Drivers/Recorders/AudioAnalysis.h"
#include "WallpaperEngine/Audio/Drivers/Recorders/Spectrum.h"
#include "kiss_fftr.h"
#include <array>
#include <cassert>
#include <iostream>
using namespace WallpaperEngine::Audio::Drivers::Recorders;
template<size_t Size> float onset (float frequency) {
    AudioSampleWindow<Size> window;
    std::array<float, Size> samples;
    std::array<kiss_fft_cpx, Size/2+1> fft;
    auto cfg = kiss_fftr_alloc(Size, 0, nullptr, nullptr);
    assert(cfg);
    float elapsed = -1;
    for (int i = 0; i < 8820; ++i) {
        window.push(std::sin(2 * M_PI * frequency * i / 44100.0f));
        if ((i+1) % 220) continue;
        window.windowed(samples.data());
        kiss_fftr(cfg, samples.data(), fft.data());
        float powers[64]; spectrumPowers(fft.data(), Size, 44100, powers);
        if (*std::max_element(powers, powers+64) >= 0.25f) {
            elapsed = (i+1) / 44.1f;
            break;
        }
    }
    std::free(cfg);
    assert(elapsed > 0);
    return elapsed;
}
int main () {
    const float oldBass = onset<4096>(86.1328125f);
    const float bass = onset<2048>(86.1328125f);
    const float oldGuitar = onset<4096>(1378.125f);
    const float guitar = onset<1024>(1378.125f);
    assert(bass < oldBass && guitar < oldGuitar);
    assert(guitar <= 15 && bass <= 30);
    std::cout << "Synthetic FFT onset (25% power): bass " << oldBass << " -> " << bass
              << " ms; midrange " << oldGuitar << " -> " << guitar << " ms\n";
    float slow[64], fast[64];
    std::fill(slow, slow+64, 1); std::fill(fast, fast+64, 0);
    mergeSpectrumWindows(slow, fast);
    assert(slow[0] == 1 && slow[63] == 0);
    for (int i = 1; i < 64; ++i) assert(slow[i] <= slow[i-1]);
    assert(smoothSpectrum(0, 1, 0.015f) > 0.9f);
}
