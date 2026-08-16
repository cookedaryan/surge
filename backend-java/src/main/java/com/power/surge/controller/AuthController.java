package com.power.surge.controller;

import com.power.surge.dto.auth.AuthResponse;
import com.power.surge.dto.auth.LoginRequest;
import com.power.surge.dto.auth.RegisterRequest;
import com.power.surge.service.AuthService;
import com.power.surge.service.ClientAddress;
import com.power.surge.service.LoginThrottleService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final LoginThrottleService loginThrottleService;

    public AuthController(AuthService authService, LoginThrottleService loginThrottleService) {
        this.authService = authService;
        this.loginThrottleService = loginThrottleService;
    }

    /**
     * Provisions a new account. Administrators only — accounts are never self-served, because a
     * world-open registration endpoint would hand any caller a valid token for the whole API.
     * Enforced here as well as in {@code SecurityConfig} so neither alone is load-bearing.
     */
    @PreAuthorize("hasRole('ADMIN')")
    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        AuthResponse response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * The throttle is checked before the credentials are, so a locked-out caller never reaches
     * BCrypt. Hashing is intentionally slow; letting unauthenticated traffic drive it would be a
     * second denial of service sitting underneath the guessing.
     */
    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest httpRequest
    ) {
        String client = ClientAddress.of(httpRequest);
        loginThrottleService.checkNotLockedOut(client);
        try {
            AuthResponse response = authService.login(request);
            loginThrottleService.recordSuccess(client);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            loginThrottleService.recordFailure(client, request.username());
            throw e;
        }
    }

    @GetMapping("/me")
    public ResponseEntity<AuthResponse> getCurrentUser(Authentication authentication) {
        if (authentication == null || authentication.getName() == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        AuthResponse response = authService.getCurrentUser(authentication.getName());
        return ResponseEntity.ok(response);
    }
}
