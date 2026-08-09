package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.dto.auth.AuthResponse;
import com.power.surge.dto.auth.LoginRequest;
import com.power.surge.dto.auth.RegisterRequest;
import com.power.surge.repository.UserRepository;
import com.power.surge.security.JwtTokenProvider;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final AuditLogService auditLogService;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtTokenProvider tokenProvider,
            AuditLogService auditLogService
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.tokenProvider = tokenProvider;
        this.auditLogService = auditLogService;
    }

    @Transactional
    public void seedDemoUsers() {
        // Always ensure admin exists with the correct password
        upsertUser("admin", "admin@surge.energy", "admin", UserRole.ROLE_ADMIN);
        upsertUser("engineer", "engineer@surge.energy", "engineer123", UserRole.ROLE_ENGINEER);
    }

    private void upsertUser(String username, String email, String password, UserRole role) {
        String encoded = passwordEncoder.encode(password);
        userRepository.findByUsername(username).ifPresentOrElse(
            user -> {
                // Always refresh the password hash so startup credentials are guaranteed
                user.setPasswordHash(encoded);
                userRepository.save(user);
            },
            () -> {
                User user = new User(username, email, encoded, role);
                userRepository.save(user);
            }
        );
    }

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.username())) {
            throw new IllegalArgumentException("Username is already taken.");
        }
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("Email is already registered.");
        }

        String encodedPassword = passwordEncoder.encode(request.password());
        UserRole role = request.role() != null ? request.role() : UserRole.ROLE_ENGINEER;

        User user = new User(request.username(), request.email(), encodedPassword, role);
        user = userRepository.save(user);

        auditLogService.recordAudit(user.getUsername(), "USER_REGISTERED", "USER", user.getId().toString(), "New user account created");

        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }

    @Transactional
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new IllegalArgumentException("Invalid username or password."));

        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new IllegalArgumentException("Invalid username or password.");
        }

        auditLogService.recordAudit(user.getUsername(), "USER_LOGIN", "USER", user.getId().toString(), "Successful user authentication");

        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }

    public AuthResponse getCurrentUser(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + username));
        String token = tokenProvider.generateToken(user.getId(), user.getUsername(), user.getRole());
        return new AuthResponse(token, user.getUsername(), user.getEmail(), user.getRole());
    }
}
