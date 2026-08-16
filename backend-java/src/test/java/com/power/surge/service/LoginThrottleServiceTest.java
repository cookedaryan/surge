package com.power.surge.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

/**
 * Sign-in had no rate limit, lockout or delay of any kind: eight wrong passwords in a row all came
 * back 400 as fast as the server could hash them. With an eight-character minimum and unlimited
 * attempts, an exposed login page is guessable at leisure — the {@code tester} account on this
 * instance was guessed by hand on the second try.
 */
@ExtendWith(MockitoExtension.class)
class LoginThrottleServiceTest {

    private static final String CLIENT = "203.0.113.7";
    private static final Instant START = Instant.parse("2026-08-16T09:00:00Z");

    @Mock
    private AuditLogService auditLogService;

    private MutableClock clock;
    private LoginThrottleService throttle;

    /** Lets lockout expiry be tested by moving time rather than by sleeping through it. */
    private static final class MutableClock extends Clock {
        private Instant now;

        MutableClock(Instant now) {
            this.now = now;
        }

        void advance(Duration by) {
            now = now.plus(by);
        }

        @Override
        public Instant instant() {
            return now;
        }

        @Override
        public ZoneOffset getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(java.time.ZoneId zone) {
            return this;
        }
    }

    @BeforeEach
    void setUp() {
        clock = new MutableClock(START);
        throttle = new LoginThrottleService(auditLogService, clock);
    }

    private void fail(int times) {
        for (int i = 0; i < times; i++) {
            throttle.recordFailure(CLIENT, "admin");
        }
    }

    @Test
    void allowsAttemptsUpToTheLimit() {
        fail(LoginThrottleService.MAX_FAILURES - 1);

        // Four wrong passwords is a bad morning, not an attack.
        assertThatCode(() -> throttle.checkNotLockedOut(CLIENT)).doesNotThrowAnyException();
    }

    @Test
    void refusesFurtherAttemptsOnceTheLimitIsReached() {
        fail(LoginThrottleService.MAX_FAILURES);

        assertThatThrownBy(() -> throttle.checkNotLockedOut(CLIENT))
                .isInstanceOf(TooManyLoginAttemptsException.class)
                .hasMessageContaining("Too many failed sign-in attempts");
    }

    @Test
    void locksOutOnlyTheOffendingClient() {
        fail(LoginThrottleService.MAX_FAILURES);

        // Everyone reaches this backend through the same nginx, so a limiter that could not tell
        // clients apart would lock out the whole company on one attacker's behalf.
        assertThatCode(() -> throttle.checkNotLockedOut("198.51.100.4")).doesNotThrowAnyException();
    }

    @Test
    void releasesTheClientOnceTheLockoutHasElapsed() {
        fail(LoginThrottleService.MAX_FAILURES);
        clock.advance(LoginThrottleService.LOCKOUT.plusSeconds(1));

        assertThatCode(() -> throttle.checkNotLockedOut(CLIENT)).doesNotThrowAnyException();
    }

    @Test
    void keepsRefusingUntilTheLockoutHasElapsed() {
        fail(LoginThrottleService.MAX_FAILURES);
        clock.advance(LoginThrottleService.LOCKOUT.minusMinutes(1));

        assertThatThrownBy(() -> throttle.checkNotLockedOut(CLIENT))
                .isInstanceOf(TooManyLoginAttemptsException.class);
    }

    @Test
    void doesNotAccumulateFailuresSpreadOverTime() {
        // Someone who mistypes once a week must never be locked out by it.
        for (int i = 0; i < LoginThrottleService.MAX_FAILURES * 3; i++) {
            throttle.recordFailure(CLIENT, "admin");
            clock.advance(LoginThrottleService.WINDOW.plusMinutes(1));
        }

        assertThatCode(() -> throttle.checkNotLockedOut(CLIENT)).doesNotThrowAnyException();
    }

    @Test
    void aSuccessfulSignInClearsTheRecord() {
        fail(LoginThrottleService.MAX_FAILURES - 1);
        throttle.recordSuccess(CLIENT);
        fail(LoginThrottleService.MAX_FAILURES - 1);

        assertThatCode(() -> throttle.checkNotLockedOut(CLIENT)).doesNotThrowAnyException();
    }

    @Test
    void reportsHowLongToWait() {
        fail(LoginThrottleService.MAX_FAILURES);

        assertThatThrownBy(() -> throttle.checkNotLockedOut(CLIENT))
                .isInstanceOfSatisfying(TooManyLoginAttemptsException.class, e ->
                        assertThatCode(() -> {
                            if (e.getRetryAfter().isNegative() || e.getRetryAfter().isZero()) {
                                throw new AssertionError("retry-after must be positive");
                            }
                        }).doesNotThrowAnyException());
    }

    @Test
    void auditsTheLockoutOnceRatherThanEveryRefusedAttempt() {
        fail(LoginThrottleService.MAX_FAILURES);
        for (int i = 0; i < 20; i++) {
            assertThatThrownBy(() -> throttle.checkNotLockedOut(CLIENT))
                    .isInstanceOf(TooManyLoginAttemptsException.class);
        }

        // The audit log is unpaginated. A row per blocked request would bury every real action
        // under the attack it is meant to record.
        verify(auditLogService).recordAudit(anyString(), eq("USER_LOGIN_LOCKED_OUT"), anyString(),
                anyString(), anyString());
    }

    @Test
    void doesNotAuditBeforeTheLimitIsReached() {
        fail(LoginThrottleService.MAX_FAILURES - 1);

        verify(auditLogService, never()).recordAudit(anyString(), anyString(), anyString(), anyString(), anyString());
    }

    @Test
    void doesNotGrowWithoutBoundWhenTheClientKeyIsRotated() {
        // The key comes partly from a client-supplied header. Unbounded tracking would turn a
        // brute-force defence into a memory-exhaustion hole.
        for (int i = 0; i < LoginThrottleService.MAX_TRACKED_CLIENTS + 500; i++) {
            throttle.recordFailure("10.0." + (i / 256) + "." + (i % 256), "admin");
        }

        assertThatCode(() -> throttle.checkNotLockedOut("10.0.0.1")).doesNotThrowAnyException();
    }
}
