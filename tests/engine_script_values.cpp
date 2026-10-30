// Opt-in native test linked against the compiled fork; see docs/AUDIO.md.
#include "WallpaperEngine/Data/Model/DynamicValue.h"
#include "WallpaperEngine/Data/JSON.h"
extern "C" {
#include "quickjs.h"
}
#include <cassert>
#include <cstring>
#include <iostream>

namespace WallpaperEngine::Scripting {
void jsToDynamicValue(JSContext*, JSValue, WallpaperEngine::Data::Model::DynamicValue&);
}

int main() {
    using WallpaperEngine::Data::Model::DynamicValue;
    using WallpaperEngine::Scripting::jsToDynamicValue;
    const auto invalid = WallpaperEngine::Data::JSON::JSON::parse("{\"padding\":\"32 16\"}");
    bool caught = false;
    try { (void)invalid.optional<int>("padding", 0); }
    catch (const std::exception&) { caught = true; }
    assert(caught); // A type mismatch must throw to the caller rather than abort via noexcept.
    JSRuntime* runtime = JS_NewRuntime();
    JSContext* context = JS_NewContext(runtime);
    DynamicValue value(99);
    auto convert = [&](const char* script) {
        JSValue result = JS_Eval(context, script, std::strlen(script), "<value-test>", JS_EVAL_TYPE_GLOBAL);
        assert(!JS_IsException(result));
        jsToDynamicValue(context, result, value);
        JS_FreeValue(context, result);
    };
    convert("'bottom'");
    assert(value.getType() == DynamicValue::String && value.getString() == "bottom");
    convert("({x: 1, y: 2})");
    assert(value.getType() == DynamicValue::Vec2 && value.getVec2() == glm::vec2(1, 2));
    convert("({x: 1, y: 2, z: 30})");
    assert(value.getType() == DynamicValue::Vec3 && value.getVec3() == glm::vec3(1, 2, 30));
    convert("({x: 1, y: 2, z: 3, w: 4})");
    assert(value.getType() == DynamicValue::Vec4 && value.getVec4() == glm::vec4(1, 2, 3, 4));
    convert("true");
    assert(value.getType() == DynamicValue::Boolean && value.getBool());
    convert("2.5");
    assert(value.getType() == DynamicValue::Float && value.getFloat() == 2.5f);
    convert("undefined");
    assert(value.getType() == DynamicValue::Float && value.getFloat() == 2.5f);
    convert("0");
    assert(value.getType() == DynamicValue::Int && value.getInt() == 0);
    JS_FreeContext(context);
    JS_FreeRuntime(runtime);
    std::cout << "String alignment, Vec2/Vec3/Vec4, booleans, scalars and undefined: OK\n";
}
