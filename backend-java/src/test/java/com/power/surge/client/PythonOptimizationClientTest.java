package com.power.surge.client;

import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.ResourceAccessException;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;

/**
 * A solve that never answers must end the job, not hold it open.
 *
 * <p>The client used to be built with no timeouts at all. One hung request then pinned a worker
 * thread and the database transaction around it for ever, and with a small worker pool a handful
 * of those stops every later run from starting.
 */
class PythonOptimizationClientTest {

    private HttpServer engine;

    @BeforeEach
    void startAnEngineThatNeverReplies() throws IOException {
        engine = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        engine.createContext("/api/v1/optimise", exchange -> {
            try {
                Thread.sleep(5_000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            exchange.close();
        });
        engine.start();
    }

    @AfterEach
    void stopTheEngine() {
        engine.stop(0);
    }

    @Test
    void giveUpWhenTheEngineDoesNotAnswerInTime() {
        String url = "http://127.0.0.1:" + engine.getAddress().getPort();
        PythonOptimizationClient client = new PythonOptimizationClient(url, 1, 1);
        PythonOptimisationRequest request = new PythonOptimisationRequest(
                "job-1", "project-1", "Balanced", null, null, null, null, null, null, null, null);

        assertTimeoutPreemptively(Duration.ofSeconds(4), () ->
                assertThatThrownBy(() -> client.runOptimization(request))
                        .isInstanceOf(ResourceAccessException.class));
    }
}
