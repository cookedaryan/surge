package com.power.surge.service;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Works out who a request came from, for rate-limiting purposes.
 *
 * <p>The backend always sits behind nginx, which means {@code getRemoteAddr()} is nginx on every
 * request. Throttling on that alone would count the whole world as one client: five wrong passwords
 * from anyone would lock out everybody, including the operator.
 *
 * <p>So the proxy's headers are used, but only the parts the proxy itself wrote. nginx sets
 * {@code X-Real-IP} to the address it saw and overwrites any value the caller sent. It also
 * <em>appends</em> that address to {@code X-Forwarded-For} (so the <em>last</em> entry is the proxy's,
 * while everything to its left is whatever the caller chose to send). Reading the leftmost entry, as
 * this class used to, let a caller get a fresh guessing budget on every request by changing one
 * header.
 *
 * <p>This is only sound for traffic that really came through our nginx. A caller that reaches the
 * backend port directly can set these headers freely, which is why docker-compose publishes that
 * port on the loopback interface only. Behind a further proxy or tunnel, nginx needs
 * {@code set_real_ip_from}/{@code real_ip_header}, or every user shares the tunnel's address. Even
 * done right this is a speed bump rather than a wall: the tracking map is in memory and bounded, and
 * a determined attacker needs rate limiting at the edge, above this application.
 */
public final class ClientAddress {

    private ClientAddress() {
    }

    public static String of(HttpServletRequest request) {
        String realIp = request.getHeader("X-Real-IP");
        if (realIp != null && !realIp.isBlank()) {
            return truncate(realIp.trim());
        }
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (forwardedFor != null && !forwardedFor.isBlank()) {
            // Rightmost entry is the one our proxy appended; the rest came from the caller.
            String[] hops = forwardedFor.split(",");
            String last = hops[hops.length - 1].trim();
            if (!last.isBlank()) {
                return truncate(last);
            }
        }
        String remote = request.getRemoteAddr();
        return remote != null ? truncate(remote) : "unknown";
    }

    /** Header values are attacker-controlled, so cap what gets stored and logged. */
    private static String truncate(String value) {
        return value.length() <= 45 ? value : value.substring(0, 45);
    }
}
