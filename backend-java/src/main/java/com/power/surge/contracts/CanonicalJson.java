package com.power.surge.contracts;

import com.fasterxml.jackson.databind.JsonNode;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * Contract C6 canonical JSON, the encoding Python and Java must agree on byte for byte.
 *
 * <p>The rules are set by {@code app/contracts/canonical_json.py}:
 *
 * <ul>
 *   <li>UTF-8, no BOM; object keys sorted by Unicode code point; no insignificant whitespace.</li>
 *   <li>Non-ASCII characters written as themselves, not as {@code \\u} escapes.</li>
 *   <li>Objects, arrays, strings, integers, {@code true}, {@code false} and {@code null} only.</li>
 *   <li><b>Floating-point numbers are rejected.</b> A decimal is written as a string such as
 *       {@code "0.25"}, because Python and Java print doubles differently and a hash cannot
 *       tolerate a difference in the last digit.</li>
 *   <li>The hash is lowercase hex SHA-256 of those bytes.</li>
 * </ul>
 *
 * <p>Written by hand rather than delegated to Jackson's pretty-printers because the requirement is
 * byte equality with another language's encoder, and "close enough" is indistinguishable from
 * correct until a hash disagrees in production. {@code contracts/profiles/hash-vector/} is the
 * oracle: it holds the exact bytes and the expected digest, and the conformance test compares
 * against both rather than against this class's own idea of them.
 */
public final class CanonicalJson {

    /** Raised when a value cannot be represented in canonical JSON. */
    public static class CanonicalJsonException extends RuntimeException {
        public CanonicalJsonException(String message) {
            super(message);
        }
    }

    /**
     * Unicode code point order, which is what Python's {@code sort_keys} uses.
     *
     * <p>Not {@link String#compareTo}: that compares UTF-16 code units, so a supplementary
     * character sorts below U+E000 rather than above it. No key in the contract reaches that range
     * today, which is exactly why the difference would go unnoticed until one did.
     */
    private static final Comparator<String> BY_CODE_POINT = (left, right) -> {
        int i = 0;
        int j = 0;
        while (i < left.length() && j < right.length()) {
            int a = left.codePointAt(i);
            int b = right.codePointAt(j);
            if (a != b) {
                return Integer.compare(a, b);
            }
            i += Character.charCount(a);
            j += Character.charCount(b);
        }
        return Integer.compare(left.length() - i, right.length() - j);
    };

    private CanonicalJson() {
    }

    /**
     * The ordering canonical JSON sorts by, exposed so anything that has to order strings the way
     * Python does — such as the definition set before it is hashed — uses one comparator rather
     * than a second, subtly different one.
     */
    public static Comparator<String> codePointOrder() {
        return BY_CODE_POINT;
    }

    /** Canonical UTF-8 bytes for {@code node}. */
    public static byte[] bytes(JsonNode node) {
        StringBuilder out = new StringBuilder();
        write(node, out, "$");
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }

    /** Lowercase hex SHA-256 of {@code node}'s canonical bytes. */
    public static String sha256(JsonNode node) {
        MessageDigest digest;
        try {
            digest = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            // Every JVM ships SHA-256; this cannot happen on a conforming runtime.
            throw new IllegalStateException("SHA-256 is unavailable", e);
        }
        byte[] hashed = digest.digest(bytes(node));
        StringBuilder hex = new StringBuilder(hashed.length * 2);
        for (byte value : hashed) {
            hex.append(Character.forDigit((value >> 4) & 0xF, 16));
            hex.append(Character.forDigit(value & 0xF, 16));
        }
        return hex.toString();
    }

    private static void write(JsonNode node, StringBuilder out, String path) {
        if (node == null || node.isNull()) {
            out.append("null");
            return;
        }
        if (node.isBoolean()) {
            out.append(node.booleanValue() ? "true" : "false");
            return;
        }
        if (node.isNumber()) {
            if (!node.isIntegralNumber()) {
                throw new CanonicalJsonException(
                        path + ": floats are not canonical; write decimals as strings");
            }
            out.append(node.bigIntegerValue().toString());
            return;
        }
        if (node.isTextual()) {
            writeString(node.textValue(), out);
            return;
        }
        if (node.isArray()) {
            out.append('[');
            for (int index = 0; index < node.size(); index++) {
                if (index > 0) {
                    out.append(',');
                }
                write(node.get(index), out, path + "[" + index + "]");
            }
            out.append(']');
            return;
        }
        if (node.isObject()) {
            List<String> keys = new ArrayList<>();
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                keys.add(fields.next().getKey());
            }
            keys.sort(BY_CODE_POINT);

            out.append('{');
            for (int index = 0; index < keys.size(); index++) {
                if (index > 0) {
                    out.append(',');
                }
                String key = keys.get(index);
                writeString(key, out);
                out.append(':');
                write(node.get(key), out, path + "." + key);
            }
            out.append('}');
            return;
        }
        throw new CanonicalJsonException(path + ": unsupported node type " + node.getNodeType());
    }

    /**
     * Escapes exactly what Python's encoder escapes with {@code ensure_ascii=False}: the quote, the
     * backslash, the five short control escapes, and any other character below U+0020 as a
     * four-digit lowercase {@code \\u}. Everything else, including every non-ASCII character, is
     * written as itself.
     */
    private static void writeString(String value, StringBuilder out) {
        out.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\b' -> out.append("\\b");
                case '\f' -> out.append("\\f");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (character < 0x20) {
                        out.append("\\u");
                        out.append(Character.forDigit((character >> 12) & 0xF, 16));
                        out.append(Character.forDigit((character >> 8) & 0xF, 16));
                        out.append(Character.forDigit((character >> 4) & 0xF, 16));
                        out.append(Character.forDigit(character & 0xF, 16));
                    } else {
                        out.append(character);
                    }
                }
            }
        }
        out.append('"');
    }
}
