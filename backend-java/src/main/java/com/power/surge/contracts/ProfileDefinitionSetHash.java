package com.power.surge.contracts;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Contract C6: the definition hash, Java's side of the C7 handshake value.
 *
 * <p>Mirrors {@code app/contracts/profiles.py::definition_set_hash}. The one thing that is easy to
 * miss, and the reason this is a class rather than a line at a call site: <b>the definitions are
 * sorted by {@code (profile_id, version)} before they are hashed.</b> Canonical JSON sorts object
 * keys but never array elements, so a set that arrives in a different order hashes differently
 * unless it is ordered first. The published vector is deliberately stored out of order to catch
 * exactly that, and an implementation that skips the sort reproduces neither the vector's bytes nor
 * its digest.
 *
 * <p>Java has no definitions of its own — Python owns those, and Java holds only the expected hash
 * as configuration (C7 step 3, set at FRZ-1). This exists because C7 requires Java to be able to
 * reproduce the published vector, which is what shows both sides mean the same thing by "the hash"
 * before anyone relies on comparing two of them. WP3-9b is the next caller.
 */
public final class ProfileDefinitionSetHash {

    private ProfileDefinitionSetHash() {
    }

    /** The C6 hash of a {@code {"definitions": [...]}} document. */
    public static String of(JsonNode definitionSet) {
        return CanonicalJson.sha256(hashedDocument(definitionSet));
    }

    /**
     * The document {@link #of} hashes: the same definitions, ordered.
     *
     * <p>Separate from the digest so a test can compare the bytes themselves against the published
     * {@code canonical.json} rather than only the digest. A hash that matches tells you the bytes
     * matched; a hash that does not tells you nothing about where they diverged.
     */
    public static ObjectNode hashedDocument(JsonNode definitionSet) {
        JsonNode definitions = definitionSet == null ? null : definitionSet.get("definitions");
        if (definitions == null || !definitions.isArray()) {
            throw new CanonicalJson.CanonicalJsonException(
                    "$.definitions: a definition set must carry an array of definitions");
        }

        List<JsonNode> ordered = new ArrayList<>();
        definitions.forEach(ordered::add);
        ordered.sort(Comparator
                .comparing((JsonNode definition) -> definition.path("profile_id").asText(),
                        CanonicalJson.codePointOrder())
                .thenComparing(definition -> definition.path("version").asText(),
                        CanonicalJson.codePointOrder()));

        ObjectNode root = JsonNodeFactory.instance.objectNode();
        ArrayNode array = root.putArray("definitions");
        ordered.forEach(array::add);

        return root;
    }
}
