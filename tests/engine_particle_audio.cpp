#include "WallpaperEngine/Render/Objects/ParticleAudio.h"
#include <cassert>
#include <cmath>
#include <limits>
using WallpaperEngine::Render::Objects::particleAudioFactor;
int main() {
    float spectrum[16] = {};
    assert(particleAudioFactor(spectrum, 0, 0, 1, 2, 0, 15) == 1);
    assert(particleAudioFactor(spectrum, 1, 0, 1, 2, 0, 15) == 0);
    spectrum[0] = 1;
    assert(particleAudioFactor(spectrum, 1, 0, 1, 1, 0, 0) == 1);
    assert(particleAudioFactor(spectrum, 1, 0, 1, 1, 10, 15) == 0);
    assert(std::abs(particleAudioFactor(spectrum, 1, 0, 1, 2, 0, 1) - .25f) < 1e-6);
    assert(std::abs(particleAudioFactor(spectrum, 1, .25, .75, 1, 0, 1) - .5f) < 1e-6);
    assert(particleAudioFactor(spectrum, 1, .8, 1, 1, 0, 1) == 0);
    spectrum[0] = std::numeric_limits<float>::quiet_NaN();
    assert(std::isfinite(particleAudioFactor(spectrum, 1, 0, 0, 0, -50, 50)));
}
