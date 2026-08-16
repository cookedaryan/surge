package com.power.surge.service;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Works out who a request came from, for rate-limiting purposes.
 *
 * <p>The backend always sits behind nginx, which means {@code getRemoteAddr()} is nginx on every
 * request. Throttling on that alone would count the whole world as one client: five wrong passwords
 * from anyone would lock out everybody, including the operator.
 *
 * <p>So the forwarded headers are used when present. They are set by our own proxy
 * ({@code proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for}), but they are still
 * ultimately client-supplied and can be spoofed — an attacker who rotates the header gets a fresh
 * budget each time. That is an accepted limit rather than an oversight: it stops the realistic
 * attack, which is someone who found the URL guessing passwords, and the tracking map is bounded so
 * rotation cannot be turned into memory exhaustion instead. Defeating a determined attacker needs
 * rate limiting at the edge, above this application.
 */
public final class ClientAddress {

    private ClientAddress() {
    }

    public static String of(HttpServletRequest request) {
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            // Leftmost entry is the original client; the rest are proxies it passed through.
            String first = forwardedFor.split(",")[0].trim();
            if (!first.isBlank()) {
                return truncate(first);
            }
        }
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return truncate(realIp.trim());
        }
        String remote = request.getRemoteAddr();
        return remote != null ? truncate(remote) : "unknown";
    }

    /** Header values are attacker-controlled, so cap what gets stored and logged. */
    private static String truncate(String value) {
        return value.length() <= 45 ? value : value.substring(0, 45);
    }
}
