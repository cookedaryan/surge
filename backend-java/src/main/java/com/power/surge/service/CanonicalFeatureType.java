package com.power.surge.service;

import com.power.surge.domain.LineType;

import java.util.Locale;
import java.util.Map;

/**
 * Contract C1 typed identity of an avoidance feature, independent of its routing class (WP2-3).
 *
 * <p>{@code constraint_type} keeps selecting routing treatment exactly as before. This type is the
 * separate identity that land and environment metrics read, which the Stage 0 WP2-1 probe proved was
 * never leaving Java: every restricted area arrived at Python as the generic {@code restricted_area},
 * so a reserve forest and a radar zone were indistinguishable (finding F7).
 *
 * <p>{@code restriction_type} is free text on {@link com.power.surge.domain.RestrictedArea} — fifty
 * characters, written by three different paths, including operator-supplied GeoJSON properties. The
 * alias table below maps what this repository actually produces plus the common spellings around
 * them. Anything unrecognised becomes {@link #RESTRICTED_AREA}: a feature is never dropped and never
 * silently promoted into a specific environmental class it was not given.
 */
public enum CanonicalFeatureType {

    ROAD("road"),
    HT_LINE("ht_line"),
    WATERCOURSE("watercourse"),
    PARCEL("parcel"),
    FOREST("forest"),
    PROTECTED_AREA("protected_area"),
    ENVIRONMENTAL("environmental"),
    WATER_BODY("water_body"),
    SETTLEMENT("settlement"),
    AVIATION("aviation"),
    RESTRICTED_AREA("restricted_area");

    /**
     * Aliases are matched after normalisation: trimmed, upper-cased, and every run of non-alphanumeric
     * characters folded to one underscore, so {@code "reserve forest"}, {@code "Reserve-Forest"} and
     * {@code "RESERVE_FOREST"} are one key.
     *
     * <p>Forest stays distinct from protected area deliberately. Collapsing the two is finding F7, and
     * the land and environment metrics are required to tell them apart.
     */
    private static final Map<String, CanonicalFeatureType> ALIASES = Map.ofEntries(
            Map.entry("ROAD", ROAD),
            Map.entry("HIGHWAY", ROAD),
            Map.entry("HT_LINE", HT_LINE),
            Map.entry("TRANSMISSION_LINE", HT_LINE),
            Map.entry("POWER_LINE", HT_LINE),
            Map.entry("WATERCOURSE", WATERCOURSE),
            Map.entry("STREAM", WATERCOURSE),
            Map.entry("NALA", WATERCOURSE),
            Map.entry("PARCEL", PARCEL),
            Map.entry("LAND_PARCEL", PARCEL),
            Map.entry("FOREST", FOREST),
            Map.entry("RESERVE_FOREST", FOREST),
            Map.entry("FOREST_LAND", FOREST),
            Map.entry("PROTECTED_AREA", PROTECTED_AREA),
            Map.entry("PROTECTED", PROTECTED_AREA),
            Map.entry("SANCTUARY", PROTECTED_AREA),
            Map.entry("WILDLIFE", PROTECTED_AREA),
            Map.entry("WILDLIFE_SANCTUARY", PROTECTED_AREA),
            Map.entry("NATIONAL_PARK", PROTECTED_AREA),
            Map.entry("ENVIRONMENTAL", ENVIRONMENTAL),
            Map.entry("ENVIRONMENT", ENVIRONMENTAL),
            Map.entry("ECO_SENSITIVE", ENVIRONMENTAL),
            Map.entry("ECO_SENSITIVE_ZONE", ENVIRONMENTAL),
            Map.entry("WETLAND", ENVIRONMENTAL),
            Map.entry("WATER_BODY", WATER_BODY),
            Map.entry("WATER", WATER_BODY),
            Map.entry("RIVER", WATER_BODY),
            Map.entry("RESERVOIR", WATER_BODY),
            Map.entry("CANAL", WATER_BODY),
            Map.entry("TANK", WATER_BODY),
            Map.entry("LAKE", WATER_BODY),
            Map.entry("POND", WATER_BODY),
            Map.entry("SETTLEMENT", SETTLEMENT),
            Map.entry("VILLAGE", SETTLEMENT),
            Map.entry("HABITATION", SETTLEMENT),
            Map.entry("RESIDENTIAL", SETTLEMENT),
            Map.entry("AVIATION", AVIATION),
            Map.entry("AIRPORT", AVIATION),
            Map.entry("AIRSTRIP", AVIATION),
            Map.entry("HELIPAD", AVIATION),
            Map.entry("RADAR", AVIATION),
            Map.entry("RESTRICTED", RESTRICTED_AREA),
            Map.entry("RESTRICTED_AREA", RESTRICTED_AREA),
            Map.entry("GENERAL_RESTRICTION", RESTRICTED_AREA),
            Map.entry("GENERAL_EXCLUSION", RESTRICTED_AREA),
            Map.entry("NO_GO", RESTRICTED_AREA),
            Map.entry("NO_GO_ZONE", RESTRICTED_AREA));

    private final String wireValue;

    CanonicalFeatureType(String wireValue) {
        this.wireValue = wireValue;
    }

    /** The value sent as {@code feature_type}; matches the C1 schema enum exactly. */
    public String wireValue() {
        return wireValue;
    }

    /**
     * Maps a persisted {@code restriction_type} onto its canonical identity. Null, blank and
     * unrecognised values map to {@link #RESTRICTED_AREA}, which is what the feature already routes as.
     */
    public static CanonicalFeatureType fromRestrictionType(String restrictionType) {
        if (restrictionType == null) {
            return RESTRICTED_AREA;
        }
        String normalised = normalise(restrictionType);
        if (normalised.isEmpty()) {
            return RESTRICTED_AREA;
        }
        return ALIASES.getOrDefault(normalised, RESTRICTED_AREA);
    }

    /**
     * Maps a reference line's type onto its canonical identity. The three classes that are not
     * crossing constraints never reach an avoidance feature, and route as roads if they ever do.
     */
    public static CanonicalFeatureType fromLineType(LineType lineType) {
        return switch (lineType) {
            case ROAD -> ROAD;
            case HT_LINE -> HT_LINE;
            case WATERCOURSE -> WATERCOURSE;
            case EVACUATION_ROUTE, MEASUREMENT, UNKNOWN -> ROAD;
        };
    }

    private static String normalise(String value) {
        return value.trim()
                .toUpperCase(Locale.ROOT)
                .replaceAll("[^A-Z0-9]+", "_")
                .replaceAll("^_+|_+$", "");
    }
}
