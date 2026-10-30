// Opt-in native test; see docs/AUDIO.md for the build command.
#include "WallpaperEngine/Audio/Drivers/Recorders/Spectrum.h"
#include "kiss_fftr.h"
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <limits>

int main() {
    constexpr int size = 4096;
    constexpr float rate = 44100;
    auto cfg = kiss_fftr_alloc(size, 0, nullptr, nullptr);
    assert(cfg);
    std::array<float, size> samples{};
    std::array<kiss_fft_cpx, size / 2 + 1> fft{};
    float powers[64];
    int previous = -1;
    for (int bin : {6, 93, 929}) {
        for (int i = 0; i < size; ++i) {
            const float window = 0.5f * (1 - std::cos(2 * M_PI * i / size));
            samples[i] = std::sin(2 * M_PI * bin * i / size) * window;
        }
        kiss_fftr(cfg, samples.data(), fft.data());
        WallpaperEngine::Audio::Drivers::Recorders::spectrumPowers(fft.data(), size, rate, powers);
        int peak = std::max_element(powers, powers + 64) - powers;
        float frequency = bin * rate / size;
        int expected = static_cast<int>(64 * std::log(frequency / 20) / std::log(1000.0f));
        assert(peak == expected && peak > previous);
        assert(std::abs(powers[peak] - 1.0f) < 0.001f);
        for (int bands : {16, 32}) {
            std::array<float, 32> pooled{};
            for (int i = 0; i < 64; ++i) pooled[i * bands / 64] = std::max(pooled[i * bands / 64], powers[i]);
            assert(std::max_element(pooled.begin(), pooled.begin() + bands) - pooled.begin() == expected * bands / 64);
        }
        std::cout << frequency << " Hz -> band " << peak << "\n";
        previous = peak;
    }
    fft.fill({0, 0});
    fft[0].r = 100; // DC never becomes bass.
    fft[10].r = std::numeric_limits<float>::quiet_NaN();
    WallpaperEngine::Audio::Drivers::Recorders::spectrumPowers(fft.data(), size, rate, powers);
    for (float power : powers) assert(power == 0);
    std::free(cfg);
}
