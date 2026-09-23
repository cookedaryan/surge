package com.power.surge.contracts;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.power.surge.dto.client.python.PythonDefinitionHashResponse;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * WP3-6b: Java reproduces the published C6 hash vector, byte for byte.
 *
 * <p>C7 requires it. The handshake it supports only ever compares two strings, so on its own it
 * could never notice that Java and Python mean different things by "the hash" — it would compare
 * two values that agree by accident, or disagree for a reason nobody could diagnose. The vector is
 * what makes the comparison mean something: {@code definitions.json} is the input,
 * {@code canonical.json} the exact bytes, {@code expected.sha256} the digest.
 *
 * <p>The vector is not a happy path. It is stored out of hash order, and it carries a non-ASCII
 * string, null-valued fields and an empty object — each of which an encoder can get wrong on its
 * own.
 */
class CanonicalJsonContractTest {

    private static final Path VECTOR = Path.of("..", "contracts", "profiles", "hash-vector");

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static JsonNode vectorDefinitions() throws IOException {
        return MAPPER.readTree(Files.readString(VECTOR.resolve("definitions.json"), StandardCharsets.UTF_8));
    }

    private static String canonical(JsonNode node) {
        return new String(CanonicalJson.bytes(node), StandardCharsets.UTF_8);
    }

    // --- The published vector -------------------------------------------------------------

    @Test
    void javaReproducesThePublishedDefinitionHash() throws IOException {
        String expected = Files.readString(VECTOR.resolve("expected.sha256"), StandardCharsets.UTF_8).strip();

        assertThat(ProfileDefinitionSetHash.of(vectorDefinitions())).isEqualTo(expected);
    }

    @Test
    void javaReproducesTheExactBytesThatWereHashed() throws IOException {
        // Trailing newline only: the file is a text file, the hash is over its content.
        String published = Files.readString(VECTOR.resolve("canonical.json"), StandardCharsets.UTF_8).strip();

        assertThat(canonical(ProfileDefinitionSetHash.hashedDocument(vectorDefinitions())))
                .isEqualTo(published);
    }

    @Test
    void theDefinitionsAreSortedBeforeHashingAndTheVectorProvesIt() throws IOException {
        JsonNode asStored = vectorDefinitions();

        // The vector is stored minimum_land_impact first, balanced second. Canonical JSON sorts
        // object keys but never array elements, so hashing it as it lies gives a different digest.
        // An implementation that forgets the sort passes every test written about key ordering.
        String storedOrder = ((ArrayNode) asStored.get("definitions")).get(0).get("profile_id").asText();
        assertThat(storedOrder).isEqualTo("minimum_land_impact");

        assertThat(canonical(ProfileDefinitionSetHash.hashedDocument(asStored)))
                .isNotEqualTo(canonical(asStored));
    }

    @Test
    void theHashIsLowercaseHexSha256() throws IOException {
        assertThat(ProfileDefinitionSetHash.of(vectorDefinitions())).matches("[0-9a-f]{64}");
    }

    @Test
    void aDefinitionSetWithoutDefinitionsIsRefused() {
        assertThatThrownBy(() -> ProfileDefinitionSetHash.of(JsonNodeFactory.instance.objectNode()))
                .isInstanceOf(CanonicalJson.CanonicalJsonException.class)
                .hasMessageContaining("definitions");
    }

    // --- The encoding rules, one at a time ------------------------------------------------

    @Test
    void objectKeysAreSortedAndNothingIsPaddedWithWhitespace() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("b", 2);
        node.put("a", 1);
        node.put("C", 3);

        // Uppercase sorts before lowercase: this is code point order, not alphabetical order.
        assertThat(canonical(node)).isEqualTo("{\"C\":3,\"a\":1,\"b\":2}");
    }

    @Test
    void arrayOrderIsLeftAlone() {
        ArrayNode node = JsonNodeFactory.instance.arrayNode();
        node.add("b");
        node.add("a");

        assertThat(canonical(node)).isEqualTo("[\"b\",\"a\"]");
    }

    @Test
    void floatsAreRefusedRatherThanRounded() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("weight", 0.1);

        // The reason decimals travel as strings: 0.1 has no exact binary form, and Python and Java
        // do not print the inexact one identically. A hash cannot survive that.
        assertThatThrownBy(() -> CanonicalJson.bytes(node))
                .isInstanceOf(CanonicalJson.CanonicalJsonException.class)
                .hasMessageContaining("floats are not canonical");
    }

    @Test
    void aWholeNumberWrittenAsADoubleIsStillRefused() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("weight", 1.0);

        // 1.0 looks safe and is not: Python rejects it too, so accepting it here would be the one
        // value on which the two encoders disagree about what is even legal.
        assertThatThrownBy(() -> CanonicalJson.bytes(node))
                .isInstanceOf(CanonicalJson.CanonicalJsonException.class);
    }

    @Test
    void integersAreWrittenPlainlyAtAnySize() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("small", 0);
        node.put("negative", -7);
        node.put("big", new BigInteger("123456789012345678901234567890"));

        assertThat(canonical(node)).isEqualTo(
                "{\"big\":123456789012345678901234567890,\"negative\":-7,\"small\":0}");
    }

    @Test
    void nonAsciiIsWrittenAsItselfInUtf8() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("note", "café");

        // ensure_ascii=False on the Python side. Escaping it would still be valid JSON and would
        // still parse - and would hash differently, which is the whole problem.
        assertThat(canonical(node)).isEqualTo("{\"note\":\"café\"}");
        assertThat(CanonicalJson.bytes(node)).isEqualTo(
                "{\"note\":\"café\"}".getBytes(StandardCharsets.UTF_8));
    }

    @Test
    void theShortEscapesMatchPythons() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("v", "a\"b\\c\nd\te\rf\bg\fh");

        assertThat(canonical(node))
                .isEqualTo("{\"v\":\"a\\\"b\\\\c\\nd\\te\\rf\\bg\\fh\"}");
    }

    @Test
    void otherControlCharactersBecomeLowercaseFourDigitEscapes() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("v", "a\u0001b\u001fc");

        assertThat(canonical(node)).isEqualTo("{\"v\":\"a\\u0001b\\u001fc\"}");
    }

    @Test
    void nullsAndEmptyContainersSurvive() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.putNull("tolerance");
        node.putObject("generation_settings");
        node.putArray("tie_breaks");

        // All three appear in the vector. A dropped null is the easiest way to hash differently
        // while producing JSON that looks equivalent to a reader.
        assertThat(canonical(node)).isEqualTo(
                "{\"generation_settings\":{},\"tie_breaks\":[],\"tolerance\":null}");
    }

    @Test
    void booleansAreWrittenAsLiterals() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("placeholder", true);
        node.put("frozen", false);

        assertThat(canonical(node)).isEqualTo("{\"frozen\":false,\"placeholder\":true}");
    }

    // --- The C7 response body -------------------------------------------------------------

    @Test
    void theHandshakeResponseReadsTheThreeC7Fields() throws IOException {
        PythonDefinitionHashResponse body = MAPPER.readValue("""
                {
                  "definition_hash": "0872b2c8d53c03b6bae5708b2adadbb7503b9de0a23cf3a3603c1aa975f0f99f",
                  "metric_registry_version": "2",
                  "contract_pack_version": "1.0.0"
                }
                """, PythonDefinitionHashResponse.class);

        assertThat(body.definitionHash())
                .isEqualTo("0872b2c8d53c03b6bae5708b2adadbb7503b9de0a23cf3a3603c1aa975f0f99f");
        assertThat(body.metricRegistryVersion()).isEqualTo("2");
        assertThat(body.contractPackVersion()).isEqualTo("1.0.0");
    }

    @Test
    void aFieldPythonAddsLaterDoesNotBreakTheHandshake() throws IOException {
        // C2 and C7 are additive contracts. A new field must not turn a healthy startup into a
        // parse failure that reads like a policy mismatch.
        PythonDefinitionHashResponse body = MAPPER.readValue("""
                {"definition_hash": "abc", "metric_registry_version": "2",
                 "contract_pack_version": "1.0.0", "something_new": true}
                """, PythonDefinitionHashResponse.class);

        assertThat(body.definitionHash()).isEqualTo("abc");
    }
}
