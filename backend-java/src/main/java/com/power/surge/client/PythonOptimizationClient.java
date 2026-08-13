package com.power.surge.client;

import com.power.surge.dto.client.python.PythonOptimisationRequest;
import com.power.surge.dto.client.python.PythonOptimisationResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class PythonOptimizationClient {

    private final RestClient restClient;

    public PythonOptimizationClient(@Value("${surge.python-engine.url:${PYTHON_ENGINE_URL:http://localhost:8000}}") String baseUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(baseUrl)
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
