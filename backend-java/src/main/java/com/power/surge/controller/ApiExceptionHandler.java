package com.power.surge.controller;

import com.power.surge.dto.ApiErrorResponse;
import com.power.surge.service.ProjectNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ProjectNotFoundException.class)
    public ResponseEntity<ApiErrorResponse> handleProjectNotFound(
            ProjectNotFoundException exception
    ) {
        return errorResponse(HttpStatus.NOT_FOUND, exception.getMessage(), Map.of());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiErrorResponse> handleValidation(
            MethodArgumentNotValidException exception
    ) {
        Map<String, String> fieldErrors = new LinkedHashMap<>();
        exception.getBindingResult().getFieldErrors().forEach(error ->
                fieldErrors.putIfAbsent(error.getField(), error.getDefaultMessage())
        );

        return errorResponse(HttpStatus.BAD_REQUEST, "Request validation failed.", fieldErrors);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiErrorResponse> handleInvalidArgument(
            IllegalArgumentException exception
    ) {
        return errorResponse(HttpStatus.BAD_REQUEST, exception.getMessage(), Map.of());
    }

    @ExceptionHandler(org.springframework.dao.DataIntegrityViolationException.class)
    public ResponseEntity<ApiErrorResponse> handleDataIntegrityViolation(
            org.springframework.dao.DataIntegrityViolationException exception
    ) {
        String msg = exception.getMostSpecificCause() != null ? exception.getMostSpecificCause().getMessage() : exception.getMessage();
        return errorResponse(HttpStatus.BAD_REQUEST, "Database constraint error: " + msg, Map.of());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiErrorResponse> handleGenericException(
            Exception exception
    ) {
        return errorResponse(HttpStatus.INTERNAL_SERVER_ERROR, "An error occurred: " + exception.getMessage(), Map.of());
    }

    private ResponseEntity<ApiErrorResponse> errorResponse(
            HttpStatus status,
            String message,
            Map<String, String> fieldErrors
    ) {
        ApiErrorResponse response = new ApiErrorResponse(
                Instant.now(),
                status.value(),
                status.getReasonPhrase(),
                message,
                fieldErrors
        );
        return ResponseEntity.status(status).body(response);
    }
}
