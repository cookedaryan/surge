package com.power.surge.controller;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;

import java.sql.SQLException;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Error bodies go to whoever called the API, so they must not carry what the server knows.
 *
 * <p>The catch-all used to return {@code "An error occurred: " + exception.getMessage()}, and the
 * constraint handler returned the database's own text — table, constraint and column names, and the
 * offending value ("Key (name)=(…) already exists"). Both are reconnaissance for anyone probing the
 * API, and neither helps a legitimate caller more than a fixed sentence would.
 */
class ApiExceptionHandlerTest {

    private final ApiExceptionHandler handler = new ApiExceptionHandler();

    @Test
    void anUnexpectedFailureDoesNotEchoItsMessage() {
        var response = handler.handleGenericException(new RuntimeException(
                "jdbc:postgresql://db:5432/surgedb: password authentication failed for user \"postgres\""));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(response.getBody().message())
                .doesNotContain("jdbc")
                .doesNotContain("postgres")
                .doesNotContain("password");
    }

    @Test
    void aConstraintViolationDoesNotEchoTheDatabaseText() {
        var cause = new SQLException(
                "duplicate key value violates unique constraint \"uk_projects_name\" "
                        + "Detail: Key (name)=(Confidential Site) already exists.");

        var response = handler.handleDataIntegrityViolation(
                new DataIntegrityViolationException("could not execute statement", cause));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody().message())
                .doesNotContain("uk_projects_name")
                .doesNotContain("Confidential Site")
                .doesNotContain("Key (");
    }
}
