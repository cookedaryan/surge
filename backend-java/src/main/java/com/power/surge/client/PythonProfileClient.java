package com.power.surge.client;

import com.power.surge.dto.client.python.PythonDefinitionHashResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * The C7 definition-hash handshake call.
 *
 * <p>A separate client from {@link PythonOptimizationClient}, and separate for one reason: this one
 * has short timeouts. A solve takes tens of seconds and must not be cut off, while a handshake runs
 * during startup and has to fail rather than hang — an engine that accepts connections and never
 * answers would otherwise hold the service in a boot that never finishes or fails.
 */
@Component
public class PythonProfileClient {

    private final RestClient restClient;

    public PythonProfileClient(
            @Value("${surge.python-engine.url:${PYTHON_ENGINE_URL:http://localhost:8000}}") String baseUrl,
            @Value("${surge.profiles.handshake-timeout-ms:5000}") int timeoutMs
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    public PythonDefinitionHashResponse definitionHash() {
        return restClient.get()
                .uri("/api/v1/profiles/definition-hash")
                .retrieve()
                .body(PythonDefinitionHashResponse.class);
    }
}
