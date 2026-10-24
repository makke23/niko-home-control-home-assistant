const DOMAIN = "niko_home_control_local";
const STRATEGY_TYPE = "niko-energy";

const suffix = (entity, value) =>
  String(entity.unique_id || "").endsWith(value);

const entityName = (entity, hass, removePattern = null) => {
  const stateName = hass.states[entity.entity_id]?.attributes?.friendly_name;
  let name =
    entity.name || entity.original_name || stateName || entity.entity_id;
  if (removePattern) {
    name = name.replace(removePattern, "");
  }
  return name.trim();
};

const namedEntities = (entities, hass, removePattern = null) =>
  entities.map((entity) => ({
    entity: entity.entity_id,
    name: entityName(entity, hass, removePattern),
  }));

const sorted = (entities) =>
  [...entities].sort((left, right) =>
    left.entity_id.localeCompare(right.entity_id),
  );

const findBySuffix = (entities, value) =>
  entities.find((entity) => suffix(entity, value));

const energySelection = (collectionKey) => ({
  type: "energy-date-selection",
  collection_key: collectionKey,
});

const changeGraph = (title, entities, collectionKey) => ({
  type: "statistics-graph",
  title,
  chart_type: "bar",
  entities,
  stat_types: ["change"],
  energy_date_selection: true,
  collection_key: collectionKey,
  min_y_axis: 0,
  fit_y_data: true,
});

const panelView = (title, path, icon, cards) => ({
  title,
  path,
  icon,
  panel: true,
  cards: [{ type: "vertical-stack", cards }],
});

const electricityView = (entities) => {
  const fromGridPower = findBySuffix(
    entities,
    "_ElectricalPowerFromGrid",
  );
  const toGridPower = findBySuffix(entities, "_ElectricalPowerToGrid");
  const monthlyPeak = findBySuffix(
    entities,
    "_ElectricalMonthlyPeakPowerFromGrid",
  );
  const importTotal = findBySuffix(
    entities,
    "_ElectricalEnergyFromGrid_total",
  );
  const exportTotal = findBySuffix(
    entities,
    "_ElectricalEnergyToGrid_total",
  );
  const cards = [];

  const liveCards = [
    fromGridPower && {
      type: "sensor",
      entity: fromGridPower.entity_id,
      name: "From grid",
      icon: "mdi:transmission-tower-import",
    },
    toGridPower && {
      type: "sensor",
      entity: toGridPower.entity_id,
      name: "To grid",
      icon: "mdi:transmission-tower-export",
    },
    monthlyPeak && {
      type: "sensor",
      entity: monthlyPeak.entity_id,
      name: "Monthly peak",
      icon: "mdi:chart-bell-curve-cumulative",
    },
  ].filter(Boolean);
  if (liveCards.length) {
    cards.push({
      type: "grid",
      columns: Math.min(3, liveCards.length),
      square: false,
      cards: liveCards,
    });
  }

  const livePower = [
    fromGridPower && {
      entity: fromGridPower.entity_id,
      name: "From grid",
    },
    toGridPower && { entity: toGridPower.entity_id, name: "To grid" },
  ].filter(Boolean);
  if (livePower.length) {
    cards.push({
      type: "history-graph",
      title: "Live grid power - last 24 hours",
      hours_to_show: 24,
      entities: livePower,
    });
  }

  if (monthlyPeak) {
    cards.push({
      type: "statistics-graph",
      title: "Monthly peak - last 30 days",
      chart_type: "line",
      days_to_show: 30,
      period: "day",
      entities: [
        { entity: monthlyPeak.entity_id, name: "Monthly peak" },
      ],
      stat_types: ["max"],
      min_y_axis: 0,
      fit_y_data: true,
    });
  }

  const totals = [
    importTotal && {
      entity: importTotal.entity_id,
      name: "Consumption",
      color: "#6b7280",
    },
    exportTotal && {
      entity: exportTotal.entity_id,
      name: "Export",
      color: "#22a06b",
    },
  ].filter(Boolean);
  if (totals.length) {
    const collectionKey = "energy_niko";
    cards.push(energySelection(collectionKey));
    const statisticCards = [
      importTotal && {
        type: "statistic",
        entity: importTotal.entity_id,
        name: "Consumption in period",
        icon: "mdi:transmission-tower-import",
        unit: "kWh",
        stat_type: "change",
        period: "energy_date_selection",
        collection_key: collectionKey,
      },
      exportTotal && {
        type: "statistic",
        entity: exportTotal.entity_id,
        name: "Export in period",
        icon: "mdi:transmission-tower-export",
        unit: "kWh",
        stat_type: "change",
        period: "energy_date_selection",
        collection_key: collectionKey,
      },
    ].filter(Boolean);
    cards.push({ type: "horizontal-stack", cards: statisticCards });
    cards.push({
      ...changeGraph("Consumption and export", totals, collectionKey),
      expand_legend: true,
    });
  }

  if (!cards.length) {
    return null;
  }
  cards.push({
    type: "markdown",
    content:
      "Niko Energy dashboard developed by Maarten Moortgat. " +
      "Only measurements exposed by this Niko installation are shown.",
  });
  return panelView("Electricity", "electricity", "mdi:lightning-bolt", cards);
};

const smartPlugView = (entities, devices, hass, chargerKeys) => {
  const powerEntities = sorted(
    entities.filter((entity) => {
      if (!suffix(entity, "_ElectricalPower")) {
        return false;
      }
      const deviceKey = entity.unique_id.replace(/_ElectricalPower$/, "");
      if (chargerKeys.has(deviceKey)) {
        return false;
      }
      const device = devices.get(entity.device_id);
      return !device || ["generic", "naso"].includes(String(device.model));
    }),
  );
  if (!powerEntities.length) {
    return null;
  }

  const energyByDevice = new Map();
  for (const entity of entities.filter((item) =>
    suffix(item, "_ElectricalEnergy_total"),
  )) {
    energyByDevice.set(
      entity.unique_id.replace(/_ElectricalEnergy_total$/, ""),
      entity,
    );
  }

  const powerNames = namedEntities(
    powerEntities,
    hass,
    /\s+(?:Power|Vermogen)$/i,
  );
  const cards = [
    {
      type: "entities",
      title: "Live power",
      show_header_toggle: false,
      entities: powerNames,
    },
    {
      type: "history-graph",
      title: "Power - last 24 hours",
      hours_to_show: 24,
      entities: powerNames,
    },
  ];

  const collectionKey = "energy_niko_smart_plugs";
  const energyCards = [];
  for (const powerEntity of powerEntities) {
    const deviceKey = powerEntity.unique_id.replace(/_ElectricalPower$/, "");
    const energyEntity = energyByDevice.get(deviceKey);
    if (!energyEntity) {
      continue;
    }
    energyCards.push(
      changeGraph(
        entityName(powerEntity, hass, /\s+(?:Power|Vermogen)$/i),
        [{ entity: energyEntity.entity_id, name: "Consumption" }],
        collectionKey,
      ),
    );
  }
  if (energyCards.length) {
    cards.push(energySelection(collectionKey), ...energyCards);
  }
  return panelView(
    "Smart plugs",
    "smart-plugs",
    "mdi:power-socket-eu",
    cards,
  );
};

const volumeView = (entities, hass, options) => {
  if (!entities.length) {
    return null;
  }
  const collectionKey = `energy_niko_${options.path}`;
  return panelView(options.title, options.path, options.icon, [
    energySelection(collectionKey),
    {
      type: "statistic",
      entity: entities[0].entity_id,
      name: `${options.title} consumption in period`,
      icon: options.icon,
      unit: "m³",
      stat_type: "change",
      period: "energy_date_selection",
      collection_key: collectionKey,
    },
    changeGraph(
      `${options.title} consumption`,
      namedEntities(entities, hass, options.removePattern),
      collectionKey,
    ),
  ]);
};

const solarView = (entities, hass) => {
  if (!entities.length) {
    return null;
  }
  const collectionKey = "energy_niko_solar";
  return panelView("Solar energy", "solar-energy", "mdi:solar-power", [
    energySelection(collectionKey),
    {
      type: "statistic",
      entity: entities[0].entity_id,
      name: "Production in period",
      icon: "mdi:solar-power",
      unit: "kWh",
      stat_type: "change",
      period: "energy_date_selection",
      collection_key: collectionKey,
    },
    changeGraph(
      "Solar production",
      namedEntities(entities, hass, /\s+(?:Total production|Productie totaal)$/i),
      collectionKey,
    ),
  ]);
};

const batteryView = (entities, hass) => {
  const energyEntities = sorted(
    entities.filter((entity) =>
      /_ElectricalEnergy(?:Charged|Discharged)_total$/.test(
        entity.unique_id,
      ),
    ),
  );
  if (!energyEntities.length) {
    return null;
  }
  const batteryKeys = new Set(
    energyEntities.map((entity) =>
      entity.unique_id.replace(
        /_ElectricalEnergy(?:Charged|Discharged)_total$/,
        "",
      ),
    ),
  );
  const powerEntities = sorted(
    entities.filter(
      (entity) =>
        suffix(entity, "_ElectricalPower") &&
        batteryKeys.has(entity.unique_id.replace(/_ElectricalPower$/, "")),
    ),
  );
  const cards = [];
  if (powerEntities.length) {
    cards.push({
      type: "entities",
      title: "Live battery power",
      show_header_toggle: false,
      entities: namedEntities(
        powerEntities,
        hass,
        /\s+(?:Power|Vermogen)$/i,
      ),
    });
  }
  const collectionKey = "energy_niko_battery";
  cards.push(energySelection(collectionKey));
  cards.push(
    changeGraph(
      "Charging and discharging",
      energyEntities.map((entity) => {
        const name = entityName(
          entity,
          hass,
          /\s+(?:Total battery (?:charge|discharge)|Batterij (?:geladen|ontladen) totaal)$/i,
        );
        const direction = suffix(entity, "_ElectricalEnergyCharged_total")
          ? "Charging"
          : "Discharging";
        return { entity: entity.entity_id, name: `${name} - ${direction}` };
      }),
      collectionKey,
    ),
  );
  return panelView("Battery", "battery", "mdi:home-battery", cards);
};

const chargerView = (entities, hass, chargerKeys) => {
  if (!chargerKeys.size) {
    return null;
  }
  const chargerEntities = sorted(
    entities.filter((entity) =>
      [...chargerKeys].some(
        (key) =>
          entity.unique_id === key || entity.unique_id.startsWith(`${key}_`),
      ),
    ),
  );
  const powerEntities = chargerEntities.filter((entity) =>
    suffix(entity, "_ElectricalPower"),
  );
  const energyEntities = chargerEntities.filter((entity) =>
    suffix(entity, "_ElectricalEnergy_total"),
  );
  const statusEntities = chargerEntities.filter(
    (entity) =>
      !suffix(entity, "_ElectricalPower") &&
      !String(entity.unique_id).includes("_ElectricalEnergy"),
  );
  const cards = [];
  if (statusEntities.length) {
    cards.push({
      type: "entities",
      title: "Charger status and controls",
      show_header_toggle: false,
      entities: namedEntities(statusEntities, hass),
    });
  }
  if (powerEntities.length) {
    cards.push({
      type: "history-graph",
      title: "Charging power - last 24 hours",
      hours_to_show: 24,
      entities: namedEntities(
        powerEntities,
        hass,
        /\s+(?:Power|Vermogen)$/i,
      ),
    });
  }
  if (energyEntities.length) {
    const collectionKey = "energy_niko_chargers";
    cards.push(
      energySelection(collectionKey),
      changeGraph(
        "Charged energy",
        namedEntities(
          energyEntities,
          hass,
          /\s+(?:Total energy|Energie totaal)$/i,
        ),
        collectionKey,
      ),
    );
  }
  return cards.length
    ? panelView("EV charging", "ev-charging", "mdi:ev-station", cards)
    : null;
};

const climateView = (entities, hass) => {
  const climateEntities = sorted(
    entities.filter((entity) => entity.entity_id.startsWith("climate.")),
  );
  if (!climateEntities.length) {
    return null;
  }
  const cards = [
    {
      type: "grid",
      columns: 2,
      square: false,
      cards: climateEntities.map((entity) => ({
        type: "thermostat",
        entity: entity.entity_id,
        name: entityName(entity, hass),
      })),
    },
  ];
  for (const climateEntity of climateEntities) {
    const deviceEntities = sorted(
      entities.filter((entity) => entity.device_id === climateEntity.device_id),
    );
    const temperatures = deviceEntities.filter((entity) =>
      /_(?:AmbientTemperature|SetpointTemperature|OverruleSetpoint|OutdoorTemperature)$/.test(
        entity.unique_id,
      ),
    );
    if (temperatures.length) {
      cards.push({
        type: "history-graph",
        title: `${entityName(climateEntity, hass)} - temperature`,
        hours_to_show: 24,
        entities: namedEntities(temperatures, hass),
      });
    }
    const humidity = deviceEntities.filter((entity) =>
      suffix(entity, "_Humidity"),
    );
    if (humidity.length) {
      cards.push({
        type: "history-graph",
        title: `${entityName(climateEntity, hass)} - humidity`,
        hours_to_show: 24,
        entities: namedEntities(humidity, hass),
      });
    }
  }
  return panelView("Climate", "climate", "mdi:home-thermometer", cards);
};

class NikoEnergyDashboardStrategy extends HTMLElement {
  static getCreateSuggestions() {
    return {
      title: "Niko Energy",
      icon: "mdi:lightning-bolt",
    };
  }

  static async generate(config, hass) {
    const [entityRegistry, deviceRegistry] = await Promise.all([
      hass.callWS({ type: "config/entity_registry/list" }),
      hass.callWS({ type: "config/device_registry/list" }),
    ]);
    const entities = sorted(
      entityRegistry.filter(
        (entity) =>
          entity.platform === DOMAIN &&
          !entity.disabled_by &&
          hass.states[entity.entity_id],
      ),
    );
    const devices = new Map(
      deviceRegistry.map((device) => [device.id, device]),
    );
    const chargerKeys = new Set(
      entities
        .filter(
          (entity) =>
            suffix(entity, "_charging_mode") ||
            suffix(entity, "_Chargingstatus") ||
            suffix(entity, "_EVStatus"),
        )
        .map((entity) =>
          entity.unique_id.replace(
            /_(?:charging_mode|Chargingstatus|EVStatus)$/,
            "",
          ),
        ),
    );

    const views = [
      electricityView(entities),
      smartPlugView(entities, devices, hass, chargerKeys),
      volumeView(
        entities.filter((entity) => suffix(entity, "_WaterVolume_total")),
        hass,
        {
          title: "Water",
          path: "water",
          icon: "mdi:water",
          removePattern: /\s+(?:Total water consumption|Waterverbruik totaal)$/i,
        },
      ),
      volumeView(
        entities.filter((entity) =>
          /_(?:GasVolume|Gasvolume)_total$/.test(entity.unique_id),
        ),
        hass,
        {
          title: "Gas",
          path: "gas",
          icon: "mdi:meter-gas",
          removePattern: /\s+(?:Total gas consumption|Gasverbruik totaal)$/i,
        },
      ),
      solarView(
        entities.filter((entity) =>
          suffix(entity, "_ElectricalEnergyProduction_total"),
        ),
        hass,
      ),
      batteryView(entities, hass),
      chargerView(entities, hass, chargerKeys),
      climateView(entities, hass),
    ].filter(Boolean);

    if (!views.length) {
      views.push(
        panelView("Niko Energy", "niko-energy", "mdi:lightning-bolt", [
          {
            type: "markdown",
            title: "No Niko measurements found",
            content:
              "Set up **Niko Home Control II** first. This dashboard will " +
              "populate automatically when measurement entities become available.",
          },
        ]),
      );
    }
    return { title: config.title || "Niko Energy", views };
  }
}

const registerStrategy = () => {
  const elementName = `ll-strategy-dashboard-${STRATEGY_TYPE}`;
  if (!customElements.get(elementName)) {
    customElements.define(elementName, NikoEnergyDashboardStrategy);
  }

  window.customStrategies = window.customStrategies || [];
  if (!window.customStrategies.some((item) => item.type === STRATEGY_TYPE)) {
    window.customStrategies.push({
      type: STRATEGY_TYPE,
      strategyType: "dashboard",
      name: "Niko Energy",
      description:
        "Dynamic energy, water, smart-plug, battery, solar, EV and climate views for Niko Home Control II.",
      documentationURL:
        "https://github.com/makke23/niko-home-control-home-assistant#niko-energy-dashboard",
    });
  }
};

// Extra frontend modules can arrive before Home Assistant installs its scoped
// custom-element registry. Registering after page load avoids losing the
// strategy when that registry is initialized.
if (
  typeof window.addEventListener === "function" &&
  typeof document !== "undefined" &&
  document.readyState === "loading"
) {
  window.addEventListener("load", registerStrategy, { once: true });
} else {
  registerStrategy();
}
