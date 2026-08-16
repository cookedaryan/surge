package com.power.surge.service;

import java.time.Duration;

/** Raised when a client has failed sign-in too often and is temporarily refused. */
public class TooManyLoginAttemptsException extends RuntimeException {

    private final Duration retryAfter;

    public TooManyLoginAttemptsException(Duration retryAfter) {
        super("Too many failed sign-in attempts. Try again in "
                + Math.max(1, retryAfter.toMinutes() + (retryAfter.toSecondsPart() > 0 ? 1 : 0)) + " minute(s).");
        this.retryAfter = retryAfter;
    }

    public Duration getRetryAfter() {
        return retryAfter;
    }
}
