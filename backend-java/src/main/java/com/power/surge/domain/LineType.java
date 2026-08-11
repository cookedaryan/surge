package com.power.surge.domain;

/**
 * Classification of a linear reference feature imported from a survey KMZ.
 *
 * <p>These are existing features of the site, not SURGE output. They are stored and rendered, and
 * are intended to feed the cost surface once A* routing lands: a road or an HT line is something a
 * corridor <em>crosses at a price</em>, not a zone it must avoid, which is why they are not modelled
 * as restricted areas.</p>
 */
public enum LineType {

    /** Public road — national highway, state highway, village B.T. road. Crossing incurs a cost. */
    ROAD(true),

    /** Existing HT / EHV transmission line. Crossing requires clearance and incurs a cost. */
    HT_LINE(true),

    /** An existing or previously proposed evacuation / collector route. Reference only. */
    EVACUATION_ROUTE(false),

    /** River, canal or reservoir edge captured as a line rather than a polygon. */
    WATERCOURSE(true),

    /**
     * Google Earth "Path Measure" / "Polyline" artifacts left in the file by the surveyor's
     * measuring tool. Carried through the preview so nothing disappears silently, but not
     * imported by default.
     */
    MEASUREMENT(false),

    /** Could not be classified. Requires an explicit user decision. */
    UNKNOWN(false);

    private final boolean crossingConstraint;

    LineType(boolean crossingConstraint) {
        this.crossingConstraint = crossingConstraint;
    }

    /** Whether a routed corridor crossing this feature should incur a cost penalty. */
    public boolean isCrossingConstraint() {
        return crossingConstraint;
    }

    /** Measurement artifacts are noise; everything else is real site data worth persisting. */
    public boolean isImportable() {
        return this != MEASUREMENT && this != UNKNOWN;
    }

    public static LineType fromNullable(String value) {
        if (value == null || value.isBlank()) {
            return UNKNOWN;
        }
        String normalized = value.trim().toUpperCase().replace(' ', '_').replace('-', '_');
        for (LineType type : values()) {
            if (type.name().equals(normalized)) {
                return type;
            }
        }
        return switch (normalized) {
            case "HIGHWAY", "TRACK", "B.T.ROAD", "BT_ROAD" -> ROAD;
            case "TRANSMISSION_LINE", "EHV", "EHV_LINE", "POWER_LINE" -> HT_LINE;
            case "PCN", "COLLECTOR", "FEEDER", "ROUTE" -> EVACUATION_ROUTE;
            case "RIVER", "CANAL", "STREAM", "WATER" -> WATERCOURSE;
            default -> UNKNOWN;
        };
    }
}
