package com.power.surge.contracts;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.power.surge.dto.client.python.PythonDesignTruth;
import com.power.surge.dto.client.python.PythonEffectiveProfile;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import com.power.surge.dto.client.python.PythonRunTermination;
import com.power.surge.dto.client.python.PythonScoringExplanation;
import com.power.surge.dto.client.python.PythonSearchEvidence;
import com.power.surge.dto.client.python.PythonSolverRun;
import com.power.surge.service.OptimisationProfile;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * WP3-9b: Java reads every response fixture and writes every request fixture it produces.
 *
 * <p>The consumer half of WP3-9a. Python proved it writes these documents; this proves Java reads
 * them back without losing anything. Fidelity is the claim, not validity: a test that only checked
 * "parses without error" would pass while Java silently dropped a field or renamed one, and the two
 * sides would then disagree about what the contract says while both looking healthy.
 *
 * <p>So each block is decoded into the type that owns it and encoded again, and the result is
 * compared as a tree against the fixture. Comparing trees rather than text is deliberate: these
 * documents carry real floats, and how a language prints {@code 0.042} is not something the
 * contract fixes.
 *
 * <p><b>Two encodings, and only one of them is canonical.</b> {@link CanonicalJson} is the
 * <em>hashing</em> encoding and rejects floats outright, because C6 needs decimals written as
 * strings for an exact hash. Only a document with no floating-point number in it can go through it
 * — which is the profile selection, and not the response blocks or the avoidance feature. That
 * split is pinned below rather than left to be rediscovered.
 */
class ConsumerConformanceContractTest {

    private static final Path CONTRACTS = Path.of("..", "contracts");
    private static final Path FIXTURES = CONTRACTS.resolve("fixtures");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static JsonNode read(String relative) throws IOException {
        return MAPPER.readTree(Files.readString(FIXTURES.resolve(relative), StandardCharsets.UTF_8));
    }

    private static JsonNode block(String name) throws IOException {
        return read("response/additive-blocks.json").get(name);
    }

    /** The document goes into the type that owns it and comes back out unchanged. */
    private static <T> void readsBackUnchanged(Class<T> type, JsonNode document) throws IOException {
        T value = MAPPER.treeToValue(document, type);
        JsonNode written = MAPPER.valueToTree(value);
        assertThat(written).as(type.getSimpleName()).isEqualTo(document);
    }

    @SuppressWarnings("unchecked")
    private static Set<String> schemaProperties(String schema, String definition) throws IOException {
        Map<String, Object> document = MAPPER.readValue(
                Files.readString(CONTRACTS.resolve("schemas").resolve(schema), StandardCharsets.UTF_8),
                new TypeReference<>() {});
        Map<String, Object> holder = definition == null
                ? document
                : (Map<String, Object>) ((Map<String, Object>) document.get("$defs")).get(definition);
        return ((Map<String, Object>) holder.get("properties")).keySet();
    }

    @SuppressWarnings("unchecked")
    private static List<String> schemaEnum(String schema, String definition) throws IOException {
        Map<String, Object> document = MAPPER.readValue(
                Files.readString(CONTRACTS.resolve("schemas").resolve(schema), StandardCharsets.UTF_8),
                new TypeReference<>() {});
        Map<String, Object> defs = (Map<String, Object>) document.get("$defs");
        return (List<String>) ((Map<String, Object>) defs.get(definition)).get("enum");
    }

    // --- Every C2 response block ----------------------------------------------------------

    @Test
    void theDesignTruthBlockReadsBackUnchanged() throws IOException {
        readsBackUnchanged(PythonDesignTruth.class, block("design_truth"));
    }

    @Test
    void theScoringExplanationBlockReadsBackUnchanged() throws IOException {
        readsBackUnchanged(PythonScoringExplanation.class, block("scoring_explanation"));
    }

    @Test
    void theSearchEvidenceBlockReadsBackUnchanged() throws IOException {
        readsBackUnchanged(PythonSearchEvidence.class, block("search_evidence"));
    }

    @Test
    void theEffectiveProfileBlockReadsBackUnchanged() throws IOException {
        readsBackUnchanged(PythonEffectiveProfile.class, block("effective_profile"));
    }

    @Test
    void theTerminationBlockReadsBackUnchanged() throws IOException {
        readsBackUnchanged(PythonRunTermination.class, block("termination"));
    }

    @Test
    void everySolverRunReadsBackUnchanged() throws IOException {
        JsonNode runs = block("solver_runs");

        assertThat(runs.isArray()).isTrue();
        assertThat(runs).as("the fixture must carry at least one solver run").isNotEmpty();
        for (JsonNode run : runs) {
            readsBackUnchanged(PythonSolverRun.class, run);
        }
    }

    @Test
    void everyBlockInTheFixtureIsCoveredHere() throws IOException {
        // A block added to C2 must not slip past this file unnoticed, which is exactly how a
        // consumer ends up silently dropping one.
        Set<String> covered = Set.of("design_truth", "scoring_explanation", "search_evidence",
                "effective_profile", "termination", "solver_runs");

        JsonNode blocks = read("response/additive-blocks.json");
        List<String> present = new ArrayList<>();
        blocks.fieldNames().forEachRemaining(present::add);

        assertThat(present).containsExactlyInAnyOrderElementsOf(covered);
    }

    @Test
    void aWholeResponseCarriesEveryBlockThroughToJava() throws IOException {
        // The blocks reaching their own types is not enough: they have to survive on the response
        // that actually arrives, which is where they were being dropped before this task.
        ObjectNode blocks = (ObjectNode) read("response/additive-blocks.json");
        ObjectNode response = MAPPER.createObjectNode();
        response.put("request_id", "job-1");
        response.put("status", "success");
        response.setAll(blocks);

        PythonOptimisationResponse read =
                MAPPER.treeToValue(response, PythonOptimisationResponse.class);

        assertThat(read.designTruth()).isNotNull();
        assertThat(read.scoringExplanation()).isNotNull();
        assertThat(read.searchEvidence()).isNotNull();
        assertThat(read.effectiveProfile()).isNotNull();
        assertThat(read.termination()).isNotNull();
        assertThat(read.solverRuns()).hasSize(1);
    }

    @Test
    void aV0ResponseLeavesEveryBlockNull() throws IOException {
        // C2 blocks are absent when not produced, which is every response the product makes today.
        PythonOptimisationResponse read = MAPPER.readValue(
                "{\"request_id\":\"job-1\",\"status\":\"success\"}",
                PythonOptimisationResponse.class);

        assertThat(read.designTruth()).isNull();
        assertThat(read.scoringExplanation()).isNull();
        assertThat(read.searchEvidence()).isNull();
        assertThat(read.effectiveProfile()).isNull();
        assertThat(read.termination()).isNull();
        assertThat(read.solverRuns()).isNull();
    }

    // --- The vocabularies Java must not choke on -------------------------------------------

    @Test
    void everySolverStatusTheSchemaAllowsIsAccepted() throws IOException {
        for (String status : schemaEnum("v1-response-solver-run.schema.json", "SolverStatus")) {
            PythonSolverRun run = MAPPER.readValue(
                    "{\"status\":\"" + status + "\"}", PythonSolverRun.class);
            assertThat(run.status()).isEqualTo(status);
        }
    }

    @Test
    void everyTerminationReasonTheSchemaAllowsIsAccepted() throws IOException {
        List<String> reasons =
                schemaEnum("v1-response-termination.schema.json", "RunTerminationReason");

        assertThat(reasons).isNotEmpty();
        for (String reason : reasons) {
            PythonRunTermination termination = MAPPER.readValue(
                    "{\"reason\":\"" + reason + "\"}", PythonRunTermination.class);
            assertThat(termination.reason()).isEqualTo(reason);
        }
    }

    @Test
    void aReasonNobodyHasDefinedYetIsStillRead() throws IOException {
        // Why these are Strings and not Java enums. C2 is additive; a reason added on the Python
        // side must not become a parse failure here that reads like a broken engine.
        PythonRunTermination termination = MAPPER.readValue(
                "{\"reason\":\"SOME_FUTURE_REASON\"}", PythonRunTermination.class);

        assertThat(termination.reason()).isEqualTo("SOME_FUTURE_REASON");
    }

    @Test
    void theSearchCountersJavaCarriesAreTheOnesTheContractDefines() throws IOException {
        PythonSearchEvidence evidence =
                MAPPER.treeToValue(block("search_evidence"), PythonSearchEvidence.class);

        // Read as maps, so this checks Java against the schema rather than against a Java copy of
        // the names - and a CCR adding a counter arrives as data instead of being dropped.
        assertThat(evidence.caps().keySet()).containsExactlyInAnyOrderElementsOf(
                schemaProperties("v1-response-search-evidence.schema.json", "SearchCaps"));
        assertThat(evidence.counts().keySet()).containsExactlyInAnyOrderElementsOf(
                schemaProperties("v1-response-search-evidence.schema.json", "SearchCounts"));
    }

    // --- The request fixtures Java writes ---------------------------------------------------

    @Test
    void theProfileSelectionIsWrittenInCanonicalJson() throws IOException {
        // The one request document with no floating-point number anywhere in it, so the hashing
        // encoding applies and byte equality is a fair thing to ask for.
        JsonNode fixture = read("request/profile-selection.json");
        JsonNode written = MAPPER.valueToTree(OptimisationProfile.BALANCED.selection());
        // Bound above so the generic return type is fixed before AssertJ sees it.

        assertThat(written).isEqualTo(fixture);
        assertThat(CanonicalJson.bytes(written)).isEqualTo(CanonicalJson.bytes(fixture));
        assertThat(new String(CanonicalJson.bytes(written), StandardCharsets.UTF_8))
                .isEqualTo("{\"id\":\"balanced\",\"version\":\"1\"}");
    }

    @Test
    void theAvoidanceFeatureSurvivesADecodeAndReEncode() throws IOException {
        // Java sends this document, so a decode and re-encode must reproduce it.
        JsonNode fixture = read("request/typed-avoidance-feature.json");

        assertThat(MAPPER.readTree(MAPPER.writeValueAsString(fixture))).isEqualTo(fixture);
    }

    @Test
    void theAvoidanceFeatureCannotGoThroughTheHashingEncoding() throws IOException {
        // Why the request fixtures are not all compared as canonical bytes: this one carries
        // coordinates. A float has no exact decimal form, so C6 forbids one rather than hashing an
        // approximation, and the two languages would not print it identically anyway.
        JsonNode fixture = read("request/typed-avoidance-feature.json");

        assertThatThrownBy(() -> CanonicalJson.bytes(fixture))
                .isInstanceOf(CanonicalJson.CanonicalJsonException.class)
                .hasMessageContaining("floats are not canonical");
    }

    // --- C11, the feeder/segment document ----------------------------------------------------

    @Test
    void theFeederSegmentFixtureSurvivesADecodeAndReEncode() throws IOException {
        // What the rule means for persistence is proven end to end in
        // FeederSegmentIdentityContractTest, which runs RouteService over this same document. What
        // is left for conformance is that Java reproduces the document itself.
        JsonNode fixture = read("feeder-segment-identity.json");

        assertThat(MAPPER.readTree(MAPPER.writeValueAsString(fixture))).isEqualTo(fixture);
    }

    @Test
    void oneRouteRowPerSegmentFeatureUnderItsOwnFeeder() throws IOException {
        // C11 itself, asserted against the shared document rather than restated, so a CCR amending
        // the fixture reaches Java too.
        JsonNode fixture = read("feeder-segment-identity.json");
        JsonNode features = fixture.get("feeder_routes_geojson").get("features");
        JsonNode rows = fixture.get("expected_route_rows");

        assertThat(features).isNotEmpty();
        assertThat(rows.size()).isEqualTo(features.size());
        for (int index = 0; index < features.size(); index++) {
            JsonNode properties = features.get(index).get("properties");
            JsonNode row = rows.get(index);
            assertThat(properties.get("segment_id").asText()).isEqualTo(row.get("segmentId").asText());
            assertThat(properties.get("feeder_id").asText()).isEqualTo(row.get("feederName").asText());
            // feederName is the engine's feeder id, which is what BOM aggregates on.
            assertThat(properties.get("feederName").asText()).isEqualTo(row.get("feederName").asText());
        }
    }
}
