package com.power.surge.service;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The sign-in throttle is only as good as the key it counts against.
 *
 * <p>nginx sets {@code X-Real-IP} to the address it actually saw and <em>overwrites</em> anything the
 * caller sent, but {@code X-Forwarded-For} is {@code $proxy_add_x_forwarded_for}: it appends to
 * whatever the caller supplied. The leftmost entry is therefore the one an attacker controls — and
 * was the one used, so rotating a header gave a fresh guessing budget on every request.
 */
class ClientAddressTest {

    private static MockHttpServletRequest request() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr("172.18.0.5");
        return request;
    }

    @Test
    void usesTheAddressTheProxyObservedNotOneTheCallerSupplied() {
        MockHttpServletRequest request = request();
        request.addHeader("X-Forwarded-For", "6.6.6.6, 203.0.113.7");
        request.addHeader("X-Real-IP", "203.0.113.7");

        assertThat(ClientAddress.of(request)).isEqualTo("203.0.113.7");
    }

    @Test
    void rotatingTheClientSuppliedForwardedForDoesNotChangeTheKey() {
        MockHttpServletRequest first = request();
        first.addHeader("X-Forwarded-For", "1.1.1.1, 203.0.113.7");
        MockHttpServletRequest second = request();
        second.addHeader("X-Forwarded-For", "2.2.2.2, 203.0.113.7");

        assertThat(ClientAddress.of(first)).isEqualTo(ClientAddress.of(second));
    }

    @Test
    void withoutARealIpHeaderTheLastForwardedEntryIsTheOneTheProxyAppended() {
        MockHttpServletRequest request = request();
        request.addHeader("X-Forwarded-For", "6.6.6.6, 203.0.113.7");

        assertThat(ClientAddress.of(request)).isEqualTo("203.0.113.7");
    }

    @Test
    void fallsBackToTheConnectionAddress() {
        assertThat(ClientAddress.of(request())).isEqualTo("172.18.0.5");
    }

    @Test
    void capsWhatIsStoredBecauseHeaderValuesAreAttackerControlled() {
        MockHttpServletRequest request = request();
        request.addHeader("X-Real-IP", "9".repeat(200));

        assertThat(ClientAddress.of(request)).hasSize(45);
    }
}
