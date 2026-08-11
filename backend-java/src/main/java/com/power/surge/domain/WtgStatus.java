package com.power.surge.domain;

/**
 * Lifecycle status of a turbine location, derived from the KML folder a placemark was found in.
 *
 * <p>Survey KMZ files carry the micro-siting decision in the folder structure rather than in
 * ExtendedData, e.g. {@code Approved}, {@code Cancel Location}, {@code Low AEP}. Only statuses
 * where {@link #isOptimisable()} is true are eligible to be sent to the optimisation engine.</p>
 */
public enum WtgStatus {

    /** Micro-siting approved. Feeds the optimiser. */
    APPROVED(true),

    /** Land registration complete. Feeds the optimiser. */
    REGISTRATION(true),

    /** Proposed location, not yet approved. Feeds the optimiser. */
    PROPOSED(true),

    /** Flagged for relocation. Excluded until the new coordinates are issued. */
    TO_BE_SHIFTED(false),

    /** Rejected on annual energy production grounds. Excluded. */
    LOW_AEP(false),

    /** Location cancelled. Excluded. */
    CANCELLED(false),

    /** Status could not be derived from the source. Excluded until reviewed. */
    UNKNOWN(false);

    private final boolean optimisable;

    WtgStatus(boolean optimisable) {
        this.optimisable = optimisable;
    }

    /** Whether turbines in this status should be included in grouping and routing. */
    public boolean isOptimisable() {
        return optimisable;
    }

    public static WtgStatus fromNullable(String value) {
        if (value == null || value.isBlank()) {
            return UNKNOWN;
        }
        String normalized = value.trim().toUpperCase().replace(' ', '_').replace('-', '_');
        for (WtgStatus status : values()) {
            if (status.name().equals(normalized)) {
                return status;
            }
        }
        return UNKNOWN;
    }
}
