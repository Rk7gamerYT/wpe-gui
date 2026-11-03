#include "WallpaperEngine/Audio/Drivers/Recorders/AudioResponseControl.h"
#include "WallpaperEngine/Audio/Drivers/Recorders/AudioAnalysis.h"
#include <cassert>
#include <iostream>
using namespace WallpaperEngine::Audio::Drivers::Recorders;
int main(int argc, char** argv) {
    assert(argc == 2);
    const char* path = argv[1];
    assert(loadResponseSpeed(nullptr, 1) == 1);
    for (float value : {0.0f, 0.25f, 1.0f, 4.0f}) {
        { std::ofstream out(path); out << value << '\n'; }
        assert(loadResponseSpeed(path, 2) == value);
    }
    for (const char* text : {"", "nan", "inf", "-1", "0.1", "5", "2junk", "{}"}) {
        { std::ofstream out(path); out << text; }
        assert(loadResponseSpeed(path, 2) == 2);
    }
    assert(smoothSpectrum(0, 1, .01f, 4) > smoothSpectrum(0, 1, .01f, .25f));
    assert(smoothSpectrum(0, 1, .01f, 0) > smoothSpectrum(0, 1, .01f, 1));
    assert(smoothSpectrum(1, 0, .03f, 4) < smoothSpectrum(1, 0, .03f, .25f));
    { std::ofstream out(path); out << 0; }
    assert(loadSpectrumCurve(path, 1) == 1);
    { std::ofstream out(path); out << 2; }
    assert(loadSpectrumCurve(path, 1) == 2);
    for (float level : {0.0f, .05f, .25f, .75f, 1.0f}) {
        assert(std::abs(curveSpectrum(level, 1) - level) < 0.000001f);
        assert(curveSpectrum(level, .5f) <= level);
        assert(curveSpectrum(level, 2) >= level);
        assert(curveSpectrum(level, .25f) >= 0 && curveSpectrum(level, 4) <= 1);
    }
    assert(curveSpectrum(0, 4) == 0 && curveSpectrum(1, .25f) == 1);
    std::cout << "Live control validation, manual speed and adaptive attacks: OK\n";
}
