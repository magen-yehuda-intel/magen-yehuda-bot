// V2 Dashboard — Static data: US bases, Iran military, SAM, waterways, patrol routes
// This file is loaded inline in the dashboard HTML

var V2_DATA = {

// ═══════════════════════════════════════════════════════════
// US & ALLIED MILITARY BASES
// ═══════════════════════════════════════════════════════════
US_BASES: [
  // Gulf / CENTCOM
  { name: "Al Udeid Air Base", lat: 25.117, lon: 51.315, type: "airbase", country: "Qatar", forces: "CENTCOM HQ, 379th AEW", emoji: "✈" },
  { name: "Al Dhafra Air Base", lat: 24.248, lon: 54.547, type: "airbase", country: "UAE", forces: "380th AEW, F-22/F-35", emoji: "✈" },
  { name: "Camp Arifjan", lat: 28.956, lon: 48.086, type: "base", country: "Kuwait", forces: "Third Army/ARCENT", emoji: "🎖" },
  { name: "Ali Al Salem Air Base", lat: 29.346, lon: 47.521, type: "airbase", country: "Kuwait", forces: "386th AEW, KC-135", emoji: "✈" },
  { name: "Ahmed Al Jaber Air Base", lat: 28.934, lon: 47.792, type: "airbase", country: "Kuwait", forces: "US Army Aviation", emoji: "✈" },
  { name: "NSA Bahrain / NAVCENT", lat: 26.228, lon: 50.598, type: "naval", country: "Bahrain", forces: "US Fifth Fleet HQ", emoji: "⚓" },
  { name: "Isa Air Base", lat: 25.918, lon: 50.591, type: "airbase", country: "Bahrain", forces: "USAF units", emoji: "✈" },
  { name: "Prince Sultan Air Base", lat: 24.062, lon: 47.580, type: "airbase", country: "Saudi Arabia", forces: "378th AEW, Patriot", emoji: "✈" },
  { name: "Eskan Village", lat: 24.619, lon: 46.755, type: "base", country: "Saudi Arabia", forces: "USMTM", emoji: "🎖" },
  { name: "Al Minhad Air Base", lat: 25.028, lon: 55.366, type: "airbase", country: "UAE", forces: "Australian/Coalition", emoji: "✈" },
  { name: "Fujairah Naval Facility", lat: 25.131, lon: 56.338, type: "naval", country: "UAE", forces: "Naval logistics", emoji: "⚓" },
  { name: "Camp Lemonnier", lat: 11.547, lon: 43.153, type: "base", country: "Djibouti", forces: "CJTF-HOA, MQ-9", emoji: "🎖" },
  // Iraq
  { name: "Al Asad Air Base", lat: 33.786, lon: 42.441, type: "airbase", country: "Iraq", forces: "USMC/USAF rotational", emoji: "✈" },
  { name: "Erbil Air Base", lat: 36.237, lon: 43.963, type: "airbase", country: "Iraq", forces: "Special Ops", emoji: "✈" },
  { name: "Victory Base Complex", lat: 33.291, lon: 44.231, type: "base", country: "Iraq", forces: "Embassy support", emoji: "🎖" },
  // Jordan / Eastern Med
  { name: "Muwaffaq Salti Air Base", lat: 31.826, lon: 36.782, type: "airbase", country: "Jordan", forces: "F-16CJ, Patriot, THAAD", emoji: "✈" },
  { name: "Tanf Garrison", lat: 33.468, lon: 38.662, type: "base", country: "Syria", forces: "SOF, deconfliction zone", emoji: "🎖" },
  { name: "NSA Souda Bay", lat: 35.487, lon: 24.118, type: "naval", country: "Greece/Crete", forces: "6th Fleet logistics", emoji: "⚓" },
  { name: "NAS Sigonella", lat: 37.402, lon: 14.922, type: "airbase", country: "Italy/Sicily", forces: "P-8A, MQ-4C, ISR hub", emoji: "✈" },
  { name: "Incirlik Air Base", lat: 36.990, lon: 35.426, type: "airbase", country: "Turkey", forces: "39th ABW, B-61 storage", emoji: "✈" },
  // Israel
  { name: "Nevatim Air Base", lat: 31.208, lon: 34.937, type: "airbase", country: "Israel", forces: "F-35I Adir, THAAD", emoji: "✈" },
  { name: "Ramon Air Base", lat: 30.776, lon: 34.667, type: "airbase", country: "Israel", forces: "F-35I, USAF rotational", emoji: "✈" },
  { name: "Dimona Radar Facility", lat: 31.022, lon: 35.098, type: "radar", country: "Israel", forces: "AN/TPY-2 X-band radar", emoji: "📡" },
  // Red Sea / Indian Ocean
  { name: "Diego Garcia", lat: -7.316, lon: 72.411, type: "airbase", country: "BIOT", forces: "B-2/B-52 staging", emoji: "✈" },
  { name: "Camp Justice (Al Masirah)", lat: 20.677, lon: 58.886, type: "airbase", country: "Oman", forces: "P-8A ISR staging", emoji: "✈" },
],

// ═══════════════════════════════════════════════════════════
// IRAN NUCLEAR SITES
// ═══════════════════════════════════════════════════════════
IRAN_NUCLEAR: [
  { name: "Natanz (FEP)", lat: 33.725, lon: 51.727, desc: "Primary enrichment facility, underground centrifuge halls", threat: "critical" },
  { name: "Natanz Pilot Plant", lat: 33.720, lon: 51.718, desc: "Above-ground pilot enrichment facility", threat: "high" },
  { name: "Fordow (FFEP)", lat: 34.880, lon: 51.584, desc: "Underground enrichment, built inside mountain", threat: "critical" },
  { name: "Isfahan UCF", lat: 32.678, lon: 51.681, desc: "Uranium Conversion Facility, UF6 production", threat: "high" },
  { name: "Isfahan Nuclear Research Center", lat: 32.678, lon: 51.700, desc: "Research reactors, fuel fabrication", threat: "high" },
  { name: "Arak IR-40 Reactor", lat: 34.380, lon: 49.243, desc: "Heavy water reactor (modified), plutonium path", threat: "high" },
  { name: "Arak Heavy Water Plant", lat: 34.367, lon: 49.271, desc: "Heavy water production", threat: "medium" },
  { name: "Bushehr Nuclear Power Plant", lat: 28.831, lon: 50.888, desc: "1000MW light water reactor, Russian-built", threat: "medium" },
  { name: "Tehran Research Reactor", lat: 35.738, lon: 51.390, desc: "5MW TRR, medical isotope production", threat: "medium" },
  { name: "Parchin Military Complex", lat: 35.515, lon: 51.770, desc: "Suspected weapons-related testing, explosive chambers", threat: "critical" },
  { name: "Lavizan-Shian", lat: 35.772, lon: 51.496, desc: "Former Physics Research Center (PHRC), demolished 2004", threat: "low" },
  { name: "Saghand Uranium Mine", lat: 32.585, lon: 55.170, desc: "Underground uranium mine", threat: "medium" },
  { name: "Gchine Uranium Mine", lat: 27.248, lon: 56.228, desc: "Open-pit uranium mine & yellowcake mill", threat: "medium" },
  { name: "Bonab Atomic Energy Research Center", lat: 37.340, lon: 46.050, desc: "Agricultural/industrial isotope research", threat: "low" },
  { name: "Karaj Nuclear Research Complex", lat: 35.755, lon: 50.860, desc: "Centrifuge component manufacturing, sabotaged 2021", threat: "high" },
  { name: "Darkhovin", lat: 31.391, lon: 48.491, desc: "360MW power reactor (planned, incomplete)", threat: "low" },
  { name: "Khondab (Arak area)", lat: 34.404, lon: 49.090, desc: "Heavy water production storage", threat: "medium" },
  { name: "Anarak Waste Storage", lat: 33.317, lon: 53.700, desc: "Nuclear waste storage facility", threat: "low" },
],

// ═══════════════════════════════════════════════════════════
// IRAN MISSILE SITES (52 entries — major known/suspected)
// ═══════════════════════════════════════════════════════════
IRAN_MISSILES: [
  // IRGC Aerospace Force — Major bases
  { name: "Imam Ali Missile Base", lat: 33.552, lon: 48.794, system: "Shahab-3, Emad, Khorramshahr", range: 2000, desc: "Primary MRBM base" },
  { name: "Tabriz Missile Base", lat: 38.070, lon: 46.400, system: "Fateh-110, Shahab-2", range: 300, desc: "NW Iran, covers Turkey/Caucasus" },
  { name: "Khorramabad Missile Base", lat: 33.450, lon: 48.380, system: "Shahab-3, Ghadr", range: 1950, desc: "Lorestan, deep underground" },
  { name: "Shahrud Missile Base", lat: 36.420, lon: 54.950, system: "Sejjil, Khorramshahr-4", range: 2500, desc: "Solid-fuel MRBM complex" },
  { name: "Semnan Space/Missile Center", lat: 35.234, lon: 53.921, system: "Simorgh SLV, Qased", range: 0, desc: "Rocket/missile test site" },
  { name: "Bid Kaneh Missile Complex", lat: 35.058, lon: 52.400, system: "Shahab-3 assembly", range: 1300, desc: "Near Parchin, assembly/storage" },
  { name: "Ahvaz Missile Base", lat: 31.320, lon: 48.690, system: "SRBM, cruise missiles", range: 700, desc: "Southwest, covers Gulf" },
  { name: "Bandar Abbas Missile Storage", lat: 27.190, lon: 56.270, system: "Anti-ship, coastal defense", range: 300, desc: "Strait of Hormuz defense" },
  { name: "Chabahar Missile Site", lat: 25.290, lon: 60.620, system: "Coastal defense missiles", range: 200, desc: "Gulf of Oman" },
  { name: "Kerman Missile Base", lat: 30.280, lon: 56.980, system: "Shahab-3 variants", range: 1300, desc: "Central Iran" },
  { name: "Isfahan Missile Research Center", lat: 32.590, lon: 51.750, system: "R&D, guidance systems", range: 0, desc: "Defense Industries Organization" },
  { name: "Shiraz Missile Base", lat: 29.540, lon: 52.540, system: "Zolfaghar, Dezful", range: 1000, desc: "Fars Province" },
  { name: "Haj Ahmad Motevasselian Base", lat: 34.100, lon: 50.250, system: "Emad, Ghadr-1", range: 1950, desc: "Central mountains" },
  { name: "Hormozgan Cruise Missile Base", lat: 27.080, lon: 55.150, system: "Soumar, Hoveyzeh GLCM", range: 1650, desc: "Ground-launched cruise" },
  { name: "Dezful Underground Base", lat: 32.380, lon: 48.400, system: "Emad, Khorramshahr", range: 2000, desc: "Hardened underground, Khuzestan" },
  { name: "IRGC Aerospace HQ Tehran", lat: 35.700, lon: 51.400, system: "Command & control", range: 0, desc: "Hassan Tehrani Moghaddam complex" },
  { name: "Birjand Missile Site", lat: 32.860, lon: 59.210, system: "Shahab-1/2", range: 500, desc: "Eastern Iran" },
  { name: "Zahedan Missile Storage", lat: 29.490, lon: 60.880, system: "Fateh-110, Zolfaghar", range: 700, desc: "SE Iran, Baluchistan" },
  { name: "Mashad Underground Storage", lat: 36.290, lon: 59.600, system: "IRGC reserve missiles", range: 0, desc: "NE Iran, deep storage" },
  { name: "Khojir Complex", lat: 35.580, lon: 51.650, system: "Solid fuel R&D, warheads", range: 0, desc: "Tehran suburbs, SPND suspected" },
  { name: "Esfandiar Tunnel Complex", lat: 34.200, lon: 51.500, system: "Underground launch ready", range: 2000, desc: "Mountain tunnel base" },
  // IRGC Navy — Anti-ship missiles
  { name: "Abu Musa Island", lat: 25.876, lon: 55.033, system: "C-802, Noor anti-ship", range: 200, desc: "Forward naval/missile base" },
  { name: "Greater Tunb Island", lat: 26.267, lon: 55.317, system: "HY-2 Silkworm", range: 120, desc: "Strategic island, Hormuz" },
  { name: "Lesser Tunb Island", lat: 26.233, lon: 55.133, system: "Radar/observation", range: 0, desc: "Small garrison" },
  { name: "Qeshm Island Base", lat: 26.800, lon: 55.980, system: "ASCM, fast attack boats", range: 200, desc: "IRGCN forward base" },
  { name: "Larak Island", lat: 26.860, lon: 56.350, system: "Anti-ship missiles", range: 200, desc: "Strait of Hormuz chokepoint" },
  // Additional suspected/confirmed from OSINT
  { name: "Doroud Missile Storage", lat: 33.490, lon: 49.060, system: "Fateh-313", range: 500, desc: "Lorestan Province" },
  { name: "Sanandaj Area", lat: 35.310, lon: 47.000, system: "SRBM mobile launchers", range: 300, desc: "Kurdistan Province" },
  { name: "Hamadan Air/Missile Base", lat: 34.870, lon: 48.550, system: "Drone + missile", range: 1000, desc: "Tu-22M staging (2016)" },
  { name: "Yasuj Military Area", lat: 30.670, lon: 51.580, system: "Mobile MRBM", range: 1300, desc: "Kohgiluyeh Province" },
  { name: "Abadeh Missile Site", lat: 31.161, lon: 52.650, system: "Suspected solid fuel", range: 0, desc: "Identified by IAEA/NCRI" },
  { name: "Shahroud Solid Fuel Plant", lat: 36.400, lon: 55.000, system: "Solid propellant production", range: 0, desc: "Manufacturing" },
  // Drone/UAV bases (dual-use)
  { name: "Kashan Drone Base", lat: 33.900, lon: 51.450, system: "Shahed-136, Mohajer-6", range: 2500, desc: "Primary attack drone base" },
  { name: "Chabahar Drone Base", lat: 25.440, lon: 60.350, system: "Ababil, Mohajer", range: 1000, desc: "Maritime surveillance drones" },
  { name: "Konarak UAV Site", lat: 25.350, lon: 60.450, system: "Maritime drones", range: 500, desc: "Coastal drone ops" },
  { name: "Gorgan Drone Facility", lat: 36.840, lon: 54.500, system: "Shahed production", range: 0, desc: "Manufacturing" },
  // Additional from satellite imagery analysis
  { name: "Bid Kaneh Storage 2", lat: 35.080, lon: 52.380, system: "Underground storage", range: 0, desc: "Expansion of Bid Kaneh" },
  { name: "Imam Hossein University Complex", lat: 35.730, lon: 51.550, system: "R&D, propulsion", range: 0, desc: "IRGC academic/military R&D" },
  { name: "Bakhtaran (Kermanshah) Base", lat: 34.350, lon: 47.110, system: "Fateh-110, SRBM", range: 300, desc: "Western Iran, covers Iraq" },
  { name: "Rasht Area", lat: 37.280, lon: 49.580, system: "Air defense missiles", range: 200, desc: "Caspian coast defense" },
  { name: "Orumiyeh Missile Depot", lat: 37.550, lon: 45.060, system: "SRBM reserve", range: 300, desc: "NW Iran near Turkey border" },
  { name: "Mashhad Area Storage", lat: 36.300, lon: 59.550, system: "Strategic reserve", range: 0, desc: "Eastern Iran" },
  { name: "Natanz Area Military", lat: 33.750, lon: 51.680, system: "AD/missile defense of nuclear site", range: 200, desc: "Nuclear site defense" },
  { name: "Fordow Area Military", lat: 34.900, lon: 51.600, system: "AD/missile defense of nuclear site", range: 200, desc: "Nuclear site defense" },
  { name: "Qom Missile Storage", lat: 34.640, lon: 50.900, system: "IRGC storage", range: 0, desc: "Underground storage tunnels" },
  { name: "Arak Military Complex", lat: 34.100, lon: 49.700, system: "Missile assembly", range: 0, desc: "Co-located with nuclear" },
  { name: "Jask Forward Base", lat: 25.650, lon: 57.770, system: "Anti-ship, coastal", range: 300, desc: "Indian Ocean access" },
  { name: "Parsian Coastal", lat: 27.200, lon: 54.400, system: "Shore-based ASCM", range: 200, desc: "Persian Gulf coast" },
  { name: "Bushehr AD/Missile", lat: 28.900, lon: 50.830, system: "Nuclear site defense", range: 200, desc: "Protecting power plant" },
  { name: "Sirjan Storage", lat: 29.450, lon: 55.680, system: "Reserve missiles", range: 0, desc: "Central plateau storage" },
  { name: "Jiroft Area", lat: 28.670, lon: 57.740, system: "Mobile launchers", range: 500, desc: "Kerman Province" },
  { name: "Iranshahr Military", lat: 27.200, lon: 60.680, system: "Baluchistan garrison", range: 200, desc: "SE Iran" },
],

// ═══════════════════════════════════════════════════════════
// IRAN NAVAL BASES
// ═══════════════════════════════════════════════════════════
IRAN_NAVAL: [
  { name: "Bandar Abbas Naval Base", lat: 27.177, lon: 56.253, type: "major", forces: "IRIN HQ, Kilo-class subs", emoji: "⚓" },
  { name: "Bushehr Naval Base", lat: 28.905, lon: 50.830, type: "major", forces: "IRIN surface fleet", emoji: "⚓" },
  { name: "Jask Naval Base", lat: 25.635, lon: 57.774, type: "forward", forces: "New forward base, Indian Ocean", emoji: "⚓" },
  { name: "Chabahar Naval Base", lat: 25.292, lon: 60.619, type: "major", forces: "IRIN East Fleet", emoji: "⚓" },
  { name: "Bandar-e Anzali", lat: 37.472, lon: 49.463, type: "caspian", forces: "Caspian flotilla", emoji: "⚓" },
  { name: "Khorramshahr Naval", lat: 30.441, lon: 48.152, type: "riverine", forces: "Shatt al-Arab patrol", emoji: "⚓" },
  { name: "IRGCN Bandar Abbas", lat: 27.150, lon: 56.210, type: "irgcn", forces: "Fast attack boats, mines", emoji: "🚤" },
  { name: "IRGCN Asaluyeh", lat: 27.469, lon: 52.599, type: "irgcn", forces: "Fast boats, South Pars gas", emoji: "🚤" },
  { name: "Larak Island Naval", lat: 26.860, lon: 56.350, type: "forward", forces: "IRGCN fast boats", emoji: "🚤" },
],

// ═══════════════════════════════════════════════════════════
// IRAN AIR DEFENSE (26 entries + SAM system info)
// ═══════════════════════════════════════════════════════════
IRAN_AIRDEFENSE: [
  { name: "Tehran S-300 Battery", lat: 35.700, lon: 51.420, system: "S-300PMU-2", range_km: 200, emoji: "🛡️" },
  { name: "Isfahan S-300 Battery", lat: 32.700, lon: 51.700, system: "S-300PMU-2", range_km: 200, emoji: "🛡️" },
  { name: "Natanz S-300/Bavar", lat: 33.730, lon: 51.730, system: "S-300PMU-2 + Bavar-373", range_km: 300, emoji: "🛡️" },
  { name: "Fordow AD Complex", lat: 34.885, lon: 51.590, system: "Bavar-373", range_km: 300, emoji: "🛡️" },
  { name: "Bushehr AD", lat: 28.840, lon: 50.890, system: "S-300PMU-2", range_km: 200, emoji: "🛡️" },
  { name: "Arak AD", lat: 34.385, lon: 49.250, system: "Bavar-373", range_km: 300, emoji: "🛡️" },
  { name: "Kharg Island AD", lat: 29.235, lon: 50.325, system: "Mersad, Hawk", range_km: 50, emoji: "🛡️" },
  { name: "Tabriz AD", lat: 38.080, lon: 46.240, system: "S-200, Sayyad-2", range_km: 150, emoji: "🛡️" },
  { name: "Bandar Abbas AD", lat: 27.190, lon: 56.260, system: "Tor-M1, S-300", range_km: 200, emoji: "🛡️" },
  { name: "Shiraz AD", lat: 29.550, lon: 52.540, system: "S-200, Raad", range_km: 150, emoji: "🛡️" },
  { name: "Mashad AD", lat: 36.240, lon: 59.640, system: "S-200, Sayyad-3", range_km: 150, emoji: "🛡️" },
  { name: "Ahvaz AD", lat: 31.330, lon: 48.700, system: "Mersad, Hawk upgrade", range_km: 50, emoji: "🛡️" },
  { name: "Kermanshah AD", lat: 34.320, lon: 47.120, system: "S-200, Bavar-373", range_km: 300, emoji: "🛡️" },
  { name: "Dezful AD", lat: 32.390, lon: 48.400, system: "Tor-M1, Pantsir copy", range_km: 12, emoji: "🛡️" },
  { name: "Parchin AD", lat: 35.520, lon: 51.780, system: "Bavar-373, Khordad-15", range_km: 300, emoji: "🛡️" },
  { name: "Semnan AD", lat: 35.550, lon: 53.400, system: "S-300, mobile", range_km: 200, emoji: "🛡️" },
  { name: "Qom AD", lat: 34.640, lon: 50.880, system: "Sayyad-2, Raad", range_km: 100, emoji: "🛡️" },
  { name: "Esfahan South AD", lat: 32.600, lon: 51.650, system: "Khordad-3", range_km: 75, emoji: "🛡️" },
  { name: "Birjand AD", lat: 32.870, lon: 59.220, system: "S-200", range_km: 150, emoji: "🛡️" },
  { name: "Zahedan AD", lat: 29.500, lon: 60.890, system: "Mersad", range_km: 50, emoji: "🛡️" },
  { name: "Kerman AD", lat: 30.290, lon: 56.990, system: "S-200, Sayyad-2", range_km: 150, emoji: "🛡️" },
  { name: "Hamadan AD", lat: 34.880, lon: 48.560, system: "Bavar-373", range_km: 300, emoji: "🛡️" },
  { name: "Chabahar AD", lat: 25.300, lon: 60.630, system: "Tor-M1", range_km: 12, emoji: "🛡️" },
  { name: "Rasht AD", lat: 37.290, lon: 49.590, system: "S-200", range_km: 150, emoji: "🛡️" },
  { name: "Orumiyeh AD", lat: 37.560, lon: 45.070, system: "Mersad", range_km: 50, emoji: "🛡️" },
  { name: "Kish Island AD", lat: 26.540, lon: 53.980, system: "Hawk, SHORAD", range_km: 30, emoji: "🛡️" },
],

// ═══════════════════════════════════════════════════════════
// IRAN AIR BASES (29)
// ═══════════════════════════════════════════════════════════
IRAN_AIRBASES: [
  { name: "Mehrabad (TFB.1)", lat: 35.690, lon: 51.315, aircraft: "F-4, F-5, C-130", emoji: "✈" },
  { name: "Tabriz (TFB.2)", lat: 38.134, lon: 46.235, aircraft: "F-5E/F, MiG-29", emoji: "✈" },
  { name: "Nojeh/Hamadan (TFB.3)", lat: 34.876, lon: 48.546, aircraft: "F-4D/E, Su-24", emoji: "✈" },
  { name: "Vahdati/Dezful (TFB.4)", lat: 32.434, lon: 48.392, aircraft: "F-5E, Saeqeh", emoji: "✈" },
  { name: "Omidiyeh (TFB.5)", lat: 30.835, lon: 49.535, aircraft: "F-4D/E", emoji: "✈" },
  { name: "Bushehr (TFB.6)", lat: 28.946, lon: 50.835, aircraft: "F-4E, MiG-29", emoji: "✈" },
  { name: "Shiraz (TFB.7)", lat: 29.539, lon: 52.591, aircraft: "F-14A, F-4E", emoji: "✈" },
  { name: "Isfahan/Khatami (TFB.8)", lat: 32.751, lon: 51.863, aircraft: "F-14A Tomcat", emoji: "✈" },
  { name: "Bandar Abbas (TFB.9)", lat: 27.218, lon: 56.378, aircraft: "F-4E, Su-24MK", emoji: "✈" },
  { name: "Chabahar (TFB.10)", lat: 25.443, lon: 60.383, aircraft: "F-7, transport", emoji: "✈" },
  { name: "Tehran/Doshan Tappeh", lat: 35.702, lon: 51.478, aircraft: "Helicopter, VIP", emoji: "🚁" },
  { name: "Birjand Air Base", lat: 32.898, lon: 59.265, aircraft: "F-5E, training", emoji: "✈" },
  { name: "Mashad Air Base", lat: 36.236, lon: 59.640, aircraft: "F-5E, MiG-29", emoji: "✈" },
  { name: "Isfahan/Badr", lat: 32.616, lon: 51.697, aircraft: "IRIAF training", emoji: "✈" },
  { name: "Shahid Doran (Kerman)", lat: 30.274, lon: 56.951, aircraft: "Transport", emoji: "✈" },
  { name: "Shiraz/Shahid Dastghaib", lat: 29.540, lon: 52.589, aircraft: "Civilian/military dual", emoji: "✈" },
  { name: "Ahvaz Air Base", lat: 31.337, lon: 48.761, aircraft: "AH-1J, helicopter", emoji: "🚁" },
  { name: "Sanandaj Air Base", lat: 35.246, lon: 47.009, aircraft: "F-7, F-5", emoji: "✈" },
  { name: "Yasuj Air Base", lat: 30.700, lon: 51.545, aircraft: "Training", emoji: "✈" },
  { name: "Zahedan Air Base", lat: 29.475, lon: 60.906, aircraft: "F-7, transport", emoji: "✈" },
  // IRGC Aerospace bases
  { name: "IRGC Kashan UAV Base", lat: 33.895, lon: 51.445, aircraft: "Shahed-136/129, Mohajer-6", emoji: "🛩" },
  { name: "IRGC Gorgan UAV", lat: 36.909, lon: 54.401, aircraft: "Shahed production/ops", emoji: "🛩" },
  { name: "IRGC Chabahar UAV", lat: 25.440, lon: 60.350, aircraft: "Maritime drones", emoji: "🛩" },
  { name: "IRGC Konarak UAV", lat: 25.350, lon: 60.450, aircraft: "Maritime surveillance", emoji: "🛩" },
  { name: "Semnan Space Center", lat: 35.234, lon: 53.921, aircraft: "SLV launches", emoji: "🚀" },
  { name: "Shahroud Space/Missile", lat: 36.420, lon: 54.950, aircraft: "Solid fuel rockets", emoji: "🚀" },
  { name: "Imam Khomeini Space Center", lat: 35.260, lon: 52.050, aircraft: "SLV launch", emoji: "🚀" },
  { name: "Khamenei Air Base / Hamadan", lat: 34.860, lon: 48.530, aircraft: "Su-35 (ordered)", emoji: "✈" },
  { name: "Tehran/Ghale Morghi", lat: 35.648, lon: 51.384, aircraft: "IRIAF HQ, helicopters", emoji: "🚁" },
],

// ═══════════════════════════════════════════════════════════
// IRAN IRGC FACILITIES
// ═══════════════════════════════════════════════════════════
IRAN_IRGC: [
  { name: "IRGC HQ (Sa'adabad)", lat: 35.810, lon: 51.420, desc: "IRGC Headquarters, northern Tehran", emoji: "⚔" },
  { name: "IRGC Ground Forces HQ", lat: 35.700, lon: 51.400, desc: "Sarallah Base", emoji: "⚔" },
  { name: "IRGC Navy HQ", lat: 27.190, lon: 56.240, desc: "Bandar Abbas, fast boat fleet", emoji: "⚔" },
  { name: "IRGC Aerospace HQ", lat: 35.710, lon: 51.410, desc: "Missile & drone command", emoji: "⚔" },
  { name: "Quds Force HQ", lat: 35.750, lon: 51.440, desc: "External operations, ex-Soleimani", emoji: "⚔" },
  { name: "IRGC Intelligence (Ramazan)", lat: 35.730, lon: 51.380, desc: "Intelligence Organization", emoji: "⚔" },
  { name: "Baqiatallah Hospital/Base", lat: 35.740, lon: 51.370, desc: "IRGC military hospital + garrison", emoji: "⚔" },
  { name: "Imam Hossein University", lat: 35.730, lon: 51.550, desc: "IRGC officer training", emoji: "⚔" },
],

// ═══════════════════════════════════════════════════════════
// IRAN OIL & GAS (38 major facilities)
// ═══════════════════════════════════════════════════════════
IRAN_ENERGY: [
  { name: "Kharg Island Terminal", lat: 29.240, lon: 50.330, type: "oil_terminal", desc: "90% of oil exports" },
  { name: "Abadan Refinery", lat: 30.339, lon: 48.283, type: "refinery", desc: "Oldest, 400k bpd capacity" },
  { name: "Isfahan Refinery", lat: 32.590, lon: 51.630, type: "refinery", desc: "375k bpd" },
  { name: "Bandar Abbas Refinery", lat: 27.149, lon: 56.267, type: "refinery", desc: "320k bpd" },
  { name: "Tehran Refinery", lat: 35.590, lon: 51.410, type: "refinery", desc: "250k bpd, Rey" },
  { name: "Arak Refinery (Shazand)", lat: 33.980, lon: 49.440, type: "refinery", desc: "250k bpd" },
  { name: "Tabriz Refinery", lat: 37.800, lon: 46.310, type: "refinery", desc: "110k bpd" },
  { name: "Lavan Refinery", lat: 26.810, lon: 53.356, type: "refinery", desc: "60k bpd, island" },
  { name: "Shiraz Refinery", lat: 29.530, lon: 52.480, type: "refinery", desc: "60k bpd" },
  { name: "Persian Star Refinery (Siraf)", lat: 27.620, lon: 52.340, type: "refinery", desc: "480k bpd mega-project" },
  { name: "South Pars Gas Field", lat: 26.620, lon: 52.200, type: "gasfield", desc: "World's largest gas field (shared w/ Qatar)" },
  { name: "South Pars Phases 1-5 (Asaluyeh)", lat: 27.469, lon: 52.599, type: "gas_processing", desc: "Major LNG processing" },
  { name: "Asaluyeh Petrochemical Zone", lat: 27.480, lon: 52.610, type: "petrochemical", desc: "Massive petrochemical complex" },
  { name: "Mahshahr Petrochemical Zone", lat: 30.500, lon: 49.160, type: "petrochemical", desc: "Major petrochemical hub" },
  { name: "Gachsaran Oil Field", lat: 30.340, lon: 50.800, type: "oilfield", desc: "Major onshore field" },
  { name: "Marun Oil Field", lat: 31.200, lon: 49.300, type: "oilfield", desc: "Second largest field" },
  { name: "Aghajari Oil Field", lat: 30.700, lon: 49.800, type: "oilfield", desc: "Major Khuzestan field" },
  { name: "Ahvaz Oil Field", lat: 31.300, lon: 48.700, type: "oilfield", desc: "Major Khuzestan field" },
  { name: "Karoun Oil Field", lat: 31.400, lon: 48.900, type: "oilfield", desc: "Supergiant" },
  { name: "Yadavaran Oil Field", lat: 31.600, lon: 47.800, type: "oilfield", desc: "Shared w/ Iraq" },
  { name: "South Azadegan", lat: 31.250, lon: 47.750, type: "oilfield", desc: "Recently developed" },
  { name: "West Karoun Fields", lat: 31.500, lon: 48.000, type: "oilfield", desc: "Major development zone" },
  { name: "Doroud Oil Field (Offshore)", lat: 29.370, lon: 50.400, type: "offshore", desc: "Persian Gulf platform" },
  { name: "Salman Oil Field (Offshore)", lat: 26.500, lon: 53.500, type: "offshore", desc: "Gulf offshore" },
  { name: "Forouzan Oil Field (Offshore)", lat: 28.200, lon: 50.100, type: "offshore", desc: "Gulf offshore" },
  { name: "Reshadat Oil Field (Offshore)", lat: 27.800, lon: 51.800, type: "offshore", desc: "Gulf offshore" },
  { name: "Nowruz Oil Field (Offshore)", lat: 29.800, lon: 49.700, type: "offshore", desc: "Gulf offshore" },
  { name: "Bahrgansar Oil Platform", lat: 29.600, lon: 49.800, type: "offshore", desc: "Gulf platform" },
  { name: "IGAT-6 Pipeline Hub", lat: 32.000, lon: 51.000, type: "pipeline", desc: "Major gas trunkline" },
  { name: "IGAT-9 Pipeline Hub", lat: 33.000, lon: 50.000, type: "pipeline", desc: "Gas to Turkey" },
  { name: "Neka Oil Terminal (Caspian)", lat: 36.650, lon: 53.300, type: "oil_terminal", desc: "Caspian oil import" },
  { name: "Jask Oil Terminal", lat: 25.650, lon: 57.770, type: "oil_terminal", desc: "New export terminal, bypasses Hormuz" },
  { name: "Imam Khomeini Port (Petrochemical)", lat: 30.410, lon: 49.080, type: "petrochemical", desc: "Major port + petrochemical" },
  { name: "Kangan Gas Refinery", lat: 27.850, lon: 52.070, type: "gas_processing", desc: "Gas processing" },
  { name: "Bid Boland Gas Refinery", lat: 30.850, lon: 50.350, type: "gas_processing", desc: "NGL processing" },
  { name: "Fajr Jam Gas Refinery", lat: 27.700, lon: 52.400, type: "gas_processing", desc: "South Pars gas" },
  { name: "Hasheminejad Gas Refinery", lat: 36.100, lon: 58.800, type: "gas_processing", desc: "NE Iran gas" },
  { name: "Ilam Gas Refinery", lat: 33.600, lon: 46.400, type: "gas_processing", desc: "Western Iran" },
],

// ═══════════════════════════════════════════════════════════
// REGIONAL ENERGY INFRASTRUCTURE (non-Iran)
// ═══════════════════════════════════════════════════════════
REGIONAL_ENERGY: [
  // QATAR
  { name: "North Field (North Dome)", lat: 26.000, lon: 52.000, type: "gasfield", country: "QA", desc: "World's largest gas field (shared w/ Iran South Pars)" },
  { name: "Ras Laffan LNG Complex", lat: 25.920, lon: 51.540, type: "lng", country: "QA", desc: "World's largest LNG export facility" },
  { name: "Dukhan Oil Field", lat: 25.420, lon: 50.780, type: "oilfield", country: "QA", desc: "Qatar's oldest onshore field" },
  { name: "Pearl GTL Plant", lat: 25.930, lon: 51.550, type: "gas_processing", country: "QA", desc: "World's largest GTL plant (Shell)" },
  // UAE
  { name: "ADNOC Ruwais Refinery", lat: 24.100, lon: 52.730, type: "refinery", country: "AE", desc: "922k bpd, world's 4th largest" },
  { name: "Upper Zakum Field", lat: 24.850, lon: 53.700, type: "offshore", country: "AE", desc: "4th largest oil field globally" },
  { name: "Das Island LNG", lat: 25.152, lon: 52.872, type: "lng", country: "AE", desc: "ADNOC LNG export terminal" },
  { name: "Jebel Ali Free Zone", lat: 25.000, lon: 55.080, type: "petrochemical", country: "AE", desc: "Major industrial/petrochemical hub" },
  { name: "Habshan Gas Plant", lat: 23.850, lon: 53.300, type: "gas_processing", country: "AE", desc: "ADNOC sour gas processing" },
  // SAUDI ARABIA
  { name: "Ghawar Oil Field", lat: 25.400, lon: 49.600, type: "oilfield", country: "SA", desc: "World's largest oil field" },
  { name: "Ras Tanura Terminal", lat: 26.640, lon: 50.160, type: "oil_terminal", country: "SA", desc: "World's largest offshore oil loading" },
  { name: "Abqaiq Processing", lat: 25.940, lon: 49.680, type: "gas_processing", country: "SA", desc: "World's largest oil processing, Houthi drone target 2019" },
  { name: "Yanbu Refinery", lat: 24.100, lon: 38.050, type: "refinery", country: "SA", desc: "400k bpd, Red Sea coast" },
  { name: "Shaybah Oil Field", lat: 22.500, lon: 54.000, type: "oilfield", country: "SA", desc: "Remote Rub' al Khali field" },
  { name: "Safaniya Field (Offshore)", lat: 28.200, lon: 49.200, type: "offshore", country: "SA", desc: "World's largest offshore oil field" },
  { name: "Ras al-Khair Desalination + Gas", lat: 27.130, lon: 49.250, type: "gas_processing", country: "SA", desc: "Massive desal + power + gas" },
  { name: "Jazan Refinery", lat: 16.900, lon: 42.560, type: "refinery", country: "SA", desc: "400k bpd, near Yemen border" },
  // IRAQ
  { name: "Basra Oil Terminal", lat: 29.700, lon: 48.850, type: "oil_terminal", country: "IQ", desc: "Iraq's main export terminal" },
  { name: "Rumaila Oil Field", lat: 30.600, lon: 47.350, type: "oilfield", country: "IQ", desc: "Iraq's largest field, BP operated" },
  { name: "West Qurna Field", lat: 31.000, lon: 47.200, type: "oilfield", country: "IQ", desc: "Supergiant, ExxonMobil/Lukoil" },
  { name: "Baiji Refinery", lat: 34.930, lon: 43.480, type: "refinery", country: "IQ", desc: "Iraq's largest refinery (war-damaged)" },
  { name: "Kirkuk Oil Field", lat: 35.450, lon: 44.400, type: "oilfield", country: "IQ", desc: "Supergiant, disputed territory" },
  // KUWAIT
  { name: "Burgan Oil Field", lat: 28.950, lon: 47.920, type: "oilfield", country: "KW", desc: "World's 2nd largest field" },
  { name: "Mina Al-Ahmadi Refinery", lat: 29.080, lon: 48.150, type: "refinery", country: "KW", desc: "466k bpd" },
  { name: "Al-Zour LNG Terminal", lat: 28.730, lon: 48.400, type: "lng", country: "KW", desc: "Kuwait's LNG import facility" },
  // BAHRAIN
  { name: "Bahrain Petroleum (BAPCO) Refinery", lat: 26.020, lon: 50.560, type: "refinery", country: "BH", desc: "267k bpd, Sitra" },
  { name: "Bahrain LNG Import Terminal", lat: 26.000, lon: 50.600, type: "lng", country: "BH", desc: "Offshore import facility" },
  // OMAN
  { name: "Oman LNG (Qalhat)", lat: 22.950, lon: 59.370, type: "lng", country: "OM", desc: "10.4 MTPA LNG export" },
  { name: "Sohar Refinery", lat: 24.350, lon: 56.700, type: "refinery", country: "OM", desc: "198k bpd" },
  // ISRAEL
  { name: "Leviathan Gas Platform", lat: 32.950, lon: 34.100, type: "offshore", country: "IL", desc: "Israel's largest gas field, 22 TCF" },
  { name: "Tamar Gas Platform", lat: 32.600, lon: 34.000, type: "offshore", country: "IL", desc: "Major gas field, 10 TCF" },
  { name: "Karish Gas Platform", lat: 33.100, lon: 33.800, type: "offshore", country: "IL", desc: "Energean, Hezbollah target threats" },
  { name: "Haifa Oil Refinery", lat: 32.820, lon: 35.060, type: "refinery", country: "IL", desc: "Israel's main refinery (closing)" },
  { name: "Ashdod Oil Terminal", lat: 31.830, lon: 34.630, type: "oil_terminal", country: "IL", desc: "Israel's main oil import terminal" },
  // EGYPT
  { name: "Zohr Gas Field", lat: 31.900, lon: 32.500, type: "offshore", country: "EG", desc: "Eastern Mediterranean supergiant" },
  { name: "Idku LNG Plant", lat: 31.350, lon: 30.250, type: "lng", country: "EG", desc: "Egypt's LNG export" },
  { name: "Suez Oil Refinery", lat: 29.960, lon: 32.550, type: "refinery", country: "EG", desc: "Near Suez Canal" },
],

// ═══════════════════════════════════════════════════════════
// DAMAGED / ATTACKED FACILITIES (explosion overlay markers)
// ═══════════════════════════════════════════════════════════
DAMAGED_FACILITIES: [
  // NATURAL GAS — ATTACKED / HIT
  { name: "South Pars Gas Field (Phase 14)", lat: 26.620, lon: 52.200, status: "hit", date: "2025-06-15", by: "IDF", type: "gas", desc: "Struck by Israeli forces Jun 2025, fire at Phase 14. Resumed ops after repairs." },
  { name: "South Pars Processing (Asaluyeh)", lat: 27.469, lon: 52.599, status: "hit", date: "2025-06-15", by: "IDF", type: "gas", desc: "Processing units damaged in Jun 2025 strikes, partial production suspension." },

  // NATURAL GAS — PRECAUTIONARY SHUTDOWN
  { name: "Leviathan Gas Field", lat: 32.950, lon: 34.100, status: "shutdown", date: "2026-02-28", by: "precautionary", type: "gas", desc: "Shut down by Israel Energy Ministry Feb 28, Chevron operated. Gas exports to Egypt halted." },
  { name: "Karish Gas Platform", lat: 33.100, lon: 33.800, status: "shutdown", date: "2026-02-28", by: "precautionary", type: "gas", desc: "Shut down by Israel Energy Ministry Feb 28, Energean operated. Hezbollah threat target." },
  { name: "Tamar Gas Platform", lat: 32.600, lon: 34.000, status: "shutdown", date: "2026-02-28", by: "precautionary", type: "gas", desc: "Likely shut down alongside Leviathan/Karish per security assessment." },

  // OIL — ATTACKED / HIT
  { name: "Kharg Island Terminal", lat: 29.240, lon: 50.330, status: "hit", date: "2026-02-28", by: "US/IDF", type: "oil", desc: "Struck in Operation Roaring Lion / Epic Fury. 90% of Iran oil exports. 7M bpd capacity." },
  { name: "Haifa Oil Refinery", lat: 32.820, lon: 35.060, status: "hit", date: "2026-02-28", by: "Iran/IRGC", type: "oil", desc: "Hit by Iranian missile strikes. Some units shut down." },
  { name: "Isfahan Oil & Gas Refinery", lat: 32.590, lon: 51.630, status: "hit", date: "2026-02-28", by: "US/IDF", type: "oil", desc: "Confirmed damage from Operation Roaring Lion strikes. 375k bpd." },

  // SHIPPING — DISRUPTED
  { name: "Strait of Hormuz (LNG Halt)", lat: 26.570, lon: 56.250, status: "blocked", date: "2026-02-28", by: "IRGC", type: "shipping", desc: "LNG tanker crossings halted Feb 28. IRGC warned all tankers. 150+ anchored in open Gulf." },
],

// ═══════════════════════════════════════════════════════════
// STRATEGIC WATERWAYS (GeoJSON-style line coordinates)
// ═══════════════════════════════════════════════════════════
WATERWAYS: [
  {
    name: "Strait of Hormuz",
    emoji: "⚓",
    color: "#22d3ee",
    coords: [[26.56,56.25],[26.50,56.30],[26.44,56.40],[26.37,56.48],[26.30,56.52],[26.20,56.58],[26.10,56.60],[26.00,56.55],[25.90,56.45]],
    desc: "21km wide, ~21M bpd oil (~30% global), most critical chokepoint"
  },
  {
    name: "Bab el-Mandeb",
    emoji: "⚓",
    color: "#22d3ee",
    coords: [[12.60,43.30],[12.55,43.35],[12.50,43.40],[12.45,43.45],[12.40,43.50],[12.35,43.55]],
    desc: "26km wide, Red Sea → Gulf of Aden, Houthi threat zone"
  },
  {
    name: "Suez Canal",
    emoji: "⚓",
    color: "#22d3ee",
    coords: [[31.26,32.34],[31.10,32.37],[30.95,32.38],[30.80,32.40],[30.60,32.40],[30.45,32.38],[30.30,32.35],[30.00,32.32],[29.95,32.55]],
    desc: "193km long, ~12% global trade, ~1M bpd oil"
  },
  {
    name: "Persian Gulf Sea Lane (Westbound)",
    emoji: "🚢",
    color: "#0ea5e9",
    coords: [[26.00,56.50],[26.20,55.50],[26.30,54.50],[26.40,53.50],[26.50,52.50],[26.80,51.50],[27.20,50.50],[28.50,49.50],[29.50,48.80]],
    desc: "Main shipping channel through Persian Gulf"
  },
],

// ═══════════════════════════════════════════════════════════
// AIR PATROL ROUTES (approximate known CAP patterns)
// ═══════════════════════════════════════════════════════════
PATROL_ROUTES: [
  {
    name: "Southern Gulf CAP",
    color: "#22c55e",
    coords: [[25.50,54.00],[25.50,56.00],[26.50,56.00],[26.50,54.00],[25.50,54.00]],
    desc: "Standard UAE/Qatar patrol box"
  },
  {
    name: "Strait of Hormuz CAP",
    color: "#22c55e",
    coords: [[26.00,56.50],[26.50,57.50],[27.00,57.50],[27.00,56.50],[26.00,56.50]],
    desc: "Hormuz approach monitoring"
  },
  {
    name: "Northern Gulf CAP",
    color: "#22c55e",
    coords: [[28.50,49.00],[28.50,50.50],[29.50,50.50],[29.50,49.00],[28.50,49.00]],
    desc: "Kuwait/Iraq southern no-fly zone legacy"
  },
  {
    name: "Red Sea CAP (Anti-Houthi)",
    color: "#f59e0b",
    coords: [[15.00,42.00],[15.00,43.00],[17.00,43.00],[17.00,42.00],[15.00,42.00]],
    desc: "Bab el-Mandeb approach monitoring"
  },
],

// ═══════════════════════════════════════════════════════════
// RECONNAISSANCE SATELLITES (CelesTrak catalog numbers)
// ═══════════════════════════════════════════════════════════
RECON_SATS: [
  { name: "USA-224 (KH-11)", norad: 37348, country: "us", type: "Electro-optical", desc: "Advanced imaging satellite" },
  { name: "USA-245 (KH-11)", norad: 39232, country: "us", type: "Electro-optical", desc: "Advanced imaging satellite" },
  { name: "USA-290 (KH-11)", norad: 44826, country: "us", type: "Electro-optical", desc: "Latest KH-11 Block V" },
  { name: "USA-314 (KH-11)", norad: 51442, country: "us", type: "Electro-optical", desc: "Newest KH-11" },
  { name: "Lacrosse/Onyx-5", norad: 28646, country: "us", type: "SAR Radar", desc: "Radar imaging" },
  { name: "USA-215 (SAR)", norad: 36119, country: "us", type: "SAR Radar", desc: "Radar imaging" },
  { name: "Ofek 16", norad: 45918, country: "il", type: "Electro-optical", desc: "Israeli spy satellite" },
  { name: "Ofek 13", norad: 46099, country: "il", type: "SAR Radar", desc: "Israeli radar imaging" },
  { name: "EROS-C2", norad: 52831, country: "il", type: "Electro-optical", desc: "Israeli commercial imaging" },
  { name: "TecSAR-2", norad: 51081, country: "il", type: "SAR Radar", desc: "Israeli radar" },
  { name: "Noor-1", norad: 45529, country: "ir", type: "Unknown", desc: "IRGC first satellite (mostly dead)" },
  { name: "Khayyam", norad: 53315, country: "ir", type: "Electro-optical", desc: "Russia-launched for Iran" },
],

};

if (typeof module !== 'undefined') module.exports = V2_DATA;
