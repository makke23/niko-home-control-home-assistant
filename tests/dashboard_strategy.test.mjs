import assert from "node:assert/strict";

globalThis.HTMLElement = class {};
globalThis.window = globalThis;
const elements = new Map();
globalThis.customElements = {
  define(name, element) {
    elements.set(name, element);
  },
  get(name) {
    return elements.get(name);
  },
};

await import(
  "../custom_components/niko_home_control_local/frontend/niko-energy-dashboard.js"
);

const Strategy = customElements.get("ll-strategy-dashboard-niko-energy");
assert.ok(Strategy, "dashboard strategy should be registered");
assert.equal(window.customStrategies[0].type, "niko-energy");

const entity = (entityId, uniqueId, deviceId = "energy") => ({
  entity_id: entityId,
  unique_id: uniqueId,
  device_id: deviceId,
  platform: "niko_home_control_local",
  disabled_by: null,
  original_name: entityId.split(".")[1].replaceAll("_", " "),
});

const entities = [
  entity("sensor.from_grid", "energy_ElectricalPowerFromGrid"),
  entity("sensor.to_grid", "energy_ElectricalPowerToGrid"),
  entity("sensor.monthly_peak", "energy_ElectricalMonthlyPeakPowerFromGrid"),
  entity("sensor.import_total", "energy_ElectricalEnergyFromGrid_total"),
  entity("sensor.export_total", "energy_ElectricalEnergyToGrid_total"),
  entity("sensor.plug_power", "plug_ElectricalPower", "plug"),
  entity("sensor.plug_energy", "plug_ElectricalEnergy_total", "plug"),
  entity("sensor.water", "water_WaterVolume_total", "water"),
  entity("sensor.gas", "gas_GasVolume_total", "gas"),
  entity("sensor.solar", "solar_ElectricalEnergyProduction_total", "solar"),
  entity("sensor.battery_power", "battery_ElectricalPower", "battery"),
  entity(
    "sensor.battery_charged",
    "battery_ElectricalEnergyCharged_total",
    "battery",
  ),
  entity(
    "sensor.battery_discharged",
    "battery_ElectricalEnergyDischarged_total",
    "battery",
  ),
  entity("select.charger_mode", "charger_charging_mode", "charger"),
  entity("sensor.charger_power", "charger_ElectricalPower", "charger"),
  entity("sensor.charger_energy", "charger_ElectricalEnergy_total", "charger"),
  entity("climate.living_room", "climate_thermostat", "climate"),
  entity(
    "sensor.living_room_temperature",
    "climate_AmbientTemperature",
    "climate",
  ),
  entity("sensor.living_room_humidity", "climate_Humidity", "climate"),
];
const devices = [
  { id: "energy", model: "energyhome" },
  { id: "plug", model: "generic" },
  { id: "water", model: "water" },
  { id: "gas", model: "gas" },
  { id: "solar", model: "solar" },
  { id: "battery", model: "battery" },
  { id: "charger", model: "charger" },
  { id: "climate", model: "thermostat" },
];
const hass = {
  states: Object.fromEntries(
    entities.map((item) => [
      item.entity_id,
      { attributes: { friendly_name: item.original_name } },
    ]),
  ),
  async callWS(message) {
    return message.type === "config/entity_registry/list" ? entities : devices;
  },
};

const dashboard = await Strategy.generate({}, hass);
assert.equal(dashboard.title, "Niko Energy");
assert.deepEqual(
  dashboard.views.map((view) => view.title),
  [
    "Electricity",
    "Smart plugs",
    "Water",
    "Gas",
    "Solar energy",
    "Battery",
    "EV charging",
    "Climate",
  ],
);

const emptyDashboard = await Strategy.generate(
  {},
  {
    states: {},
    async callWS() {
      return [];
    },
  },
);
assert.equal(emptyDashboard.views.length, 1);
assert.equal(emptyDashboard.views[0].title, "Niko Energy");

console.log("Dashboard strategy tests passed");
