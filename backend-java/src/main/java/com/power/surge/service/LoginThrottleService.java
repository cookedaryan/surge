package com.power.surge.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Slows down password guessing against the sign-in endpoint.
 *
 * <p>Before this, sign-in had no rate limit, lockout or delay of any kind: eight wrong passwords in
 * a row all returned 400 as fast as the server could hash them. With an eight-character minimum and
 * unlimited attempts, an exposed login page is guessable at leisure — the {@code tester} account on
 * this very instance was guessed by hand on the second try.
 *
 * <p>Deliberately in memory. The application already assumes a single replica (SSE emitters and the
 * optimisation executor are both in-process), so a shared store would add a dependency without
 * buying correctness. If this is ever scaled out, this is one of the things that has to move.
 */
@Service
public class LoginThrottleService {

    private static final Logger log = LoggerFactory.getLogger(LoginThrottleService.class);

    /** Attempts allowed inside {@link #WINDOW} before a client is locked out. */
    static final int MAX_FAILURES = 5;

    /** Failures older than this no longer count, so an honest typo does not accumulate for ever. */
    static final Duration WINDOW = Duration.ofMinutes(15);

    /** How long a client stays locked out once it trips the limit. */
    static final Duration LOCKOUT = Duration.ofMinutes(15);

    /**
     * Upper bound on tracked clients.
     *
     * <p>The client key comes partly from a request header, which the caller controls. Without a
     * bound, an attacker rotating that header would grow this map without limit — turning a
     * brute-force defence into a memory-exhaustion hole. Least-recently-seen entries are evicted,
     * which at worst forgets an attacker's counter; it never locks out someone innocent.
     */
    static final int MAX_TRACKED_CLIENTS = 10_000;

    private final Clock clock;
    private final AuditLogService auditLogService;
    private final Map<String, Deque<Instant>> failuresByClient;
    private final Map<String, Instant> lockedUntilByClient;

    @org.springframework.beans.factory.annotation.Autowired
    public LoginThrottleService(AuditLogService auditLogService) {
        this(auditLogService, Clock.systemUTC());
    }

    /** Package-private for tests, which drive time rather than sleeping through the lockout. */
    LoginThrottleService(AuditLogService auditLogService, Clock clock) {
        this.auditLogService = auditLogService;
        this.clock = clock;
        this.failuresByClient = boundedMap();
        this.lockedUntilByClient = boundedMap();
    }

    private static <V> Map<String, V> boundedMap() {
        return new LinkedHashMap<>(64, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, V> eldest) {
                return size() > MAX_TRACKED_CLIENTS;
            }
        };
    }

    /**
     * Rejects the attempt if this client is locked out.
     *
     * <p>Called before the password is checked, so a locked-out caller never reaches BCrypt.
     * Hashing is intentionally slow, and letting unauthenticated traffic drive it is a second,
     * quieter denial of service on top of the guessing itself.
     */
    public synchronized void checkNotLockedOut(String clientKey) {
        Instant lockedUntil = lockedUntilByClient.get(clientKey);
        if (lockedUntil == null) {
            return;
        }
        Instant now = clock.instant();
        if (now.isBefore(lockedUntil)) {
            throw new TooManyLoginAttemptsException(Duration.between(now, lockedUntil));
        }
        lockedUntilByClient.remove(clientKey);
        failuresByClient.remove(clientKey);
    }

    /** Records a rejected sign-in, locking the client out once it has had too many. */
    public synchronized void recordFailure(String clientKey, String attemptedUsername) {
        Instant now = clock.instant();
        Deque<Instant> failures = failuresByClient.computeIfAbsent(clientKey, k -> new ArrayDeque<>());
        failures.addLast(now);
        while (!failures.isEmpty() && failures.peekFirst().isBefore(now.minus(WINDOW))) {
            failures.removeFirst();
        }

        if (failures.size() >= MAX_FAILURES) {
            lockedUntilByClient.put(clientKey, now.plus(LOCKOUT));
            failures.clear();
            log.warn("Locked out sign-in attempts from {} for {} minutes after {} failures.",
                    clientKey, LOCKOUT.toMinutes(), MAX_FAILURES);
            // Written once per lockout rather than per blocked request. The audit log is
            // unpaginated, so a row per attempt would bury every real action under an attack.
            auditLogService.recordAudit(attemptedUsername, "USER_LOGIN_LOCKED_OUT", "AUTH", clientKey,
                    MAX_FAILURES + " failed sign-in attempts; further attempts refused for "
                            + LOCKOUT.toMinutes() + " minutes");
        }
    }

    /** Clears the record for a client that has just signed in successfully. */
    public synchronized void recordSuccess(String clientKey) {
        failuresByClient.remove(clientKey);
        lockedUntilByClient.remove(clientKey);
    }
}
