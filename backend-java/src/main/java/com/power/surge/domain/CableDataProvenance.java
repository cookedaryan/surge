package com.power.surge.domain;

/**
 * How much trust the electrical parameters of a conductor have earned.
 *
 * <p>Mirrors the land engine's treatment of prices, for the same reason: a figure nobody has
 * checked produces results indistinguishable from a checked one, so provenance has to be carried
 * with the number rather than remembered.
 */
public enum CableDataProvenance {

    /** Checked against a supplier datasheet or utility standard for this project. */
    VERIFIED,

    /** A published typical value. Good enough to plan with, not to build from. */
    INDICATIVE,

    /** Present for identification only. */
    UNKNOWN
}
