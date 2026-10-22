package com.power.surge.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.power.surge.domain.LineType;
import com.power.surge.service.CanonicalFeatureType;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Contract C1 typed identity (WP2-3): Java and Python are held to one document.
 *
 * <p>Reads the shared fixture and schema in {@code contracts/} rather than restating them, so a CCR
 * that amends either one fails here instead of drifting silently.
 */
class TypedAvoidanceFeatureContractTest {

    private static final Path FIXTURE =
            Path.of("..", "contracts", "fixtures", "request", "typed-avoidance-feature.json");

    private static final Path SCHEMA =
            Path.of("..", "contracts", "schemas", "v1-request-typed-identity.schema.json");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    @SuppressWarnings("unchecked")
    void everyCanonicalFeatureTypeIsAcceptedByTheContractSchema() throws IOException {
        Map<String, Object> schema = MAPPER.readValue(Files.readString(SCHEMA), new TypeReference<>() {});
        Map<String, Object> definitions = (Map<String, Object>) schema.get("$defs");
        Map<String, Object> featureType = (Map<String, Object>) definitions.get("CanonicalFeatureType");
        List<String> allowed = (List<String>) featureType.get("enum");

        Set<String> sent = Stream.of(CanonicalFeatureType.values())
                .map(CanonicalFeatureType::wireValue)
                .collect(Collectors.toSet());

        // Both directions: Java can never send a value Python rejects, and the enum is not a stale
        // subset that quietly drops a type the contract defines.
        assertThat(sent).containsExactlyInAnyOrderElementsOf(allowed);
    }

    @Test
    @SuppressWarnings("unchecked")
    void theFixtureFeatureCarriesTheIdentityPropertiesJavaNowSends() throws IOException {
        Map<String, Object> fixture = MAPPER.readValue(Files.readString(FIXTURE), new TypeReference<>() {});
        Map<String, Object> properties = (Map<String, Object>) fixture.get("properties");

        assertThat(properties).containsKeys("constraint_id", "constraint_type", "routing_mode",
                "source_id", "feature_type");

        // The fixture is a hard exclusion whose identity is a forest: exactly the case the Stage 0
        // probe proved Java collapsed. Java's mapper reproduces that identity from the persisted type.
        assertThat(properties.get("constraint_type")).isEqualTo("restricted_area");
        assertThat(CanonicalFeatureType.fromRestrictionType("FOREST").wireValue())
                .isEqualTo(properties.get("feature_type"));
        assertThat(properties.get("source_id")).isInstanceOf(String.class);
    }

    @Test
    void unknownAndMissingRestrictionTypesFallBackToTheRoutingClass() {
        // Never dropped, never promoted into a specific environmental class it was not given.
        assertThat(CanonicalFeatureType.fromRestrictionType("SOMETHING_NOBODY_MAPPED"))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
        assertThat(CanonicalFeatureType.fromRestrictionType(null))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
        assertThat(CanonicalFeatureType.fromRestrictionType("   "))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
    }

    @Test
    void aliasesAreMatchedRegardlessOfSpacingCaseAndPunctuation() {
        assertThat(CanonicalFeatureType.fromRestrictionType("reserve forest"))
                .isEqualTo(CanonicalFeatureType.FOREST);
        assertThat(CanonicalFeatureType.fromRestrictionType("Reserve-Forest"))
                .isEqualTo(CanonicalFeatureType.FOREST);
        assertThat(CanonicalFeatureType.fromRestrictionType("  RESERVE_FOREST  "))
                .isEqualTo(CanonicalFeatureType.FOREST);
    }

    @Test
    void forestAndProtectedAreaStayDistinct() {
        // Finding F7 is exactly this collapse. The land and environment metrics must tell them apart.
        assertThat(CanonicalFeatureType.fromRestrictionType("FOREST"))
                .isNotEqualTo(CanonicalFeatureType.fromRestrictionType("WILDLIFE_SANCTUARY"));
    }

    @Test
    void theRestrictionTypesThisRepositoryProducesAllMap() {
        // AssetService.restrictionTypeFor and RestrictedAreaService's defaults: the values that
        // actually reach the database today.
        assertThat(CanonicalFeatureType.fromRestrictionType("WATER_BODY"))
                .isEqualTo(CanonicalFeatureType.WATER_BODY);
        assertThat(CanonicalFeatureType.fromRestrictionType("PROTECTED_AREA"))
                .isEqualTo(CanonicalFeatureType.PROTECTED_AREA);
        assertThat(CanonicalFeatureType.fromRestrictionType("SETTLEMENT"))
                .isEqualTo(CanonicalFeatureType.SETTLEMENT);
        assertThat(CanonicalFeatureType.fromRestrictionType("AVIATION"))
                .isEqualTo(CanonicalFeatureType.AVIATION);
        assertThat(CanonicalFeatureType.fromRestrictionType("RESTRICTED"))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
        assertThat(CanonicalFeatureType.fromRestrictionType("GENERAL_RESTRICTION"))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
        assertThat(CanonicalFeatureType.fromRestrictionType("GENERAL_EXCLUSION"))
                .isEqualTo(CanonicalFeatureType.RESTRICTED_AREA);
    }

    @Test
    void crossingLineTypesKeepTheirOwnIdentity() {
        assertThat(CanonicalFeatureType.fromLineType(LineType.ROAD)).isEqualTo(CanonicalFeatureType.ROAD);
        assertThat(CanonicalFeatureType.fromLineType(LineType.HT_LINE)).isEqualTo(CanonicalFeatureType.HT_LINE);
        assertThat(CanonicalFeatureType.fromLineType(LineType.WATERCOURSE))
                .isEqualTo(CanonicalFeatureType.WATERCOURSE);
    }
}
