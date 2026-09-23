package com.power.surge.service;

import com.power.surge.dto.client.python.PythonProfileSelection;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Contract C6: the profile IDs and versions Java is allowed to send (WP3-5).
 *
 * <p>Python owns profile <em>definitions</em> — the metrics, weights and reference ranges. Java
 * holds only this allow-list and, from WP3-6b, the expected definition hash. That split is the
 * point of the contract: a policy change is a Python change plus a hash bump, never a Java release.
 *
 * <p><b>This class never falls back.</b> An unknown ID, an unknown version, a blank or a null is an
 * error. {@link ScenarioProfile#forScenario(String)} next door does the opposite and defaults to
 * Balanced, which is correct there — a scenario is a display label, and no run should fail over
 * one. A profile is not a label. It decides which design is recommended, so answering an
 * unrecognised profile with Balanced's winner would present a result as though it came from the
 * policy the client asked for. Python refuses the same case with a stable code rather than
 * defaulting (WP3-1); this is the same rule on the near side of the wire, so a bad value is
 * rejected before a job is created rather than after a solve.
 *
 * <p>The scenario label is carried here, not restated by callers, because C1 pairs the two: Python
 * rejects a request whose {@code scenario} does not match the profile's own label
 * ({@code PROFILE_SCENARIO_MISMATCH}). Reading both from one place is what keeps them agreeing.
 */
public enum OptimisationProfile {

    MINIMUM_COST("minimum_cost", ScenarioProfile.MINIMUM_COST),
    MINIMUM_LAND_IMPACT("minimum_land_impact", ScenarioProfile.MINIMUM_LAND_IMPACT),
    MINIMUM_ENVIRONMENTAL_IMPACT("minimum_environmental_impact", ScenarioProfile.MINIMUM_ENVIRONMENTAL_IMPACT),
    BALANCED("balanced", ScenarioProfile.BALANCED);

    /**
     * The versions a client may be served, newest last. A version joins or leaves this list only
     * through a contract change request; an explicit unknown version is rejected, never rounded to
     * the nearest known one.
     */
    private static final List<String> ALLOWED_VERSIONS = List.of("1");

    private static final Map<String, OptimisationProfile> BY_WIRE_ID;

    static {
        Map<String, OptimisationProfile> byWireId = new LinkedHashMap<>();
        for (OptimisationProfile profile : values()) {
            byWireId.put(profile.wireId, profile);
        }
        BY_WIRE_ID = Collections.unmodifiableMap(byWireId);
    }

    private final String wireId;
    private final String scenarioLabel;

    OptimisationProfile(String wireId, String scenarioLabel) {
        this.wireId = wireId;
        this.scenarioLabel = scenarioLabel;
    }

    /** The C6 ID as it appears on the wire and in {@code contracts/profiles/allow-list.json}. */
    public String wireId() {
        return wireId;
    }

    /** The V1 {@code scenario} label this profile must be sent with. */
    public String scenarioLabel() {
        return scenarioLabel;
    }

    /** Every version a client may request. */
    public List<String> allowedVersions() {
        return ALLOWED_VERSIONS;
    }

    /** The version Java pins when a client names a profile without one. */
    public String currentVersion() {
        return ALLOWED_VERSIONS.get(ALLOWED_VERSIONS.size() - 1);
    }

    public boolean allowsVersion(String version) {
        return ALLOWED_VERSIONS.contains(version);
    }

    /**
     * Resolves a client-supplied ID, or throws.
     *
     * <p>Matching is exact. The C6 IDs are contract tokens rather than anything a person types, so
     * accepting {@code "Balanced"} or {@code " balanced "} would only widen what Java promises to
     * keep working.
     */
    public static OptimisationProfile fromClientId(String id) {
        OptimisationProfile profile = id == null ? null : BY_WIRE_ID.get(id);
        if (profile == null) {
            throw new IllegalArgumentException(
                    "Unknown optimisation profile '" + id + "'. Allowed: " + BY_WIRE_ID.keySet());
        }
        return profile;
    }

    /**
     * Resolves an explicit ID and version, or throws.
     *
     * <p>Used where a client names both. A known ID at an unknown version is still a refusal: it is
     * a request for a policy this deployment does not have.
     */
    public static OptimisationProfile fromClientId(String id, String version) {
        OptimisationProfile profile = fromClientId(id);
        if (!profile.allowsVersion(version)) {
            throw new IllegalArgumentException(
                    "Unknown version '" + version + "' for optimisation profile '" + id
                            + "'. Allowed: " + ALLOWED_VERSIONS);
        }
        return profile;
    }

    /** This profile as the C1 request block, at the version Java pins. */
    public PythonProfileSelection selection() {
        return new PythonProfileSelection(wireId, currentVersion());
    }
}
