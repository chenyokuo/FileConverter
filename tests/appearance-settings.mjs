import assert from "node:assert/strict";
import {
  backgroundPreset,
  defaultAppearance,
  defaults,
  mergeSettings,
} from "../src/defaults.ts";

const fresh = mergeSettings({});
assert.deepEqual(fresh.appearance, defaultAppearance);
assert.equal(fresh.appearanceVersion, 2);
const legacy = mergeSettings({
  appearance: {
    ...structuredClone(defaultAppearance),
    image: "data:image/png;base64,test",
    imageOpacity: 75,
    brightness: 85,
    overlay: 25,
    materials: {
      ...structuredClone(defaultAppearance.materials),
      main: { ...defaultAppearance.materials.main, opacity: 38, blur: 20 },
    },
  },
});
assert.equal(legacy.appearance.imageOpacity, 100);
assert.equal(legacy.appearance.brightness, 100);
assert.equal(legacy.appearance.overlay, 10);
assert.equal(legacy.appearance.materials.main.opacity, 8);
assert.equal(legacy.appearance.materials.main.blur, 0);
assert.equal(legacy.appearance.image, "data:image/png;base64,test");
const custom = structuredClone(defaults);
custom.appearance.image = "custom-image";
custom.appearance.imageOpacity = 43;
custom.appearance.brightness = 122;
custom.appearance.backgroundBlur = 7;
custom.appearance.materials.card.blur = 31;
custom.appearance.materials.main.blur = 31;
custom.appearance.materials.main.opacity = 27;
const before = structuredClone(custom);
const merged = mergeSettings(custom);
assert.equal(merged.appearance.materials.main.blur, 0);
assert.equal(merged.appearance.materials.main.opacity, 27);
assert.equal(merged.appearance.materials.card.blur, 31);
assert.equal(merged.appearance.imageOpacity, 43);
assert.equal(merged.appearance.backgroundBlur, 7);
assert.deepEqual(custom, before);
for (const kind of ["clear", "frosted"]) {
  const preset = backgroundPreset(merged.appearance, kind);
  assert.equal(preset.image, "custom-image");
  assert.equal(preset.materials.main.blur, 0);
  assert.equal(preset.backgroundBlur, kind === "clear" ? 0 : 12);
}
console.log(
  "PASS appearance defaults, legacy migration, preference preservation, and clear/frosted presets",
);
