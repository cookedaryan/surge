package com.power.surge.client;

import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.time.Duration;

@Component
public class PythonOptimizationClient {

    private final RestClient restClient;

    /**
     * Both timeouts are explicit because the default is to wait for ever: a solve that hangs would
     * hold a worker thread and the transaction around it indefinitely, and the stale-job sweeper
     * only runs at startup. The read timeout bounds a whole solve, so it is generous.
     */
    public PythonOptimizationClient(
            @Value("${surge.python-engine.url:${PYTHON_ENGINE_URL:http://localhost:8000}}") String baseUrl,
            @Value("${surge.python-engine.connect-timeout-seconds:5}") long connectTimeoutSeconds,
            @Value("${surge.python-engine.read-timeout-seconds:600}") long readTimeoutSeconds
    ) {
        HttpClient httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(connectTimeoutSeconds))
                .build();
        JdkClientHttpRequestFactory requestFactory = new JdkClientHttpRequestFactory(httpClient);
        requestFactory.setReadTimeout(Duration.ofSeconds(readTimeoutSeconds));
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    public PythonOptimisationResponse runOptimization(PythonOptimisationRequest request) {
        return restClient.post()
                .uri("/api/v1/optimise")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(PythonOptimisationResponse.class);
    }
}
