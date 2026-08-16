package com.power.surge.service;

import com.power.surge.domain.User;
import com.power.surge.domain.UserRole;
import com.power.surge.dto.auth.AuthResponse;
import com.power.surge.dto.auth.LoginRequest;
import com.power.surge.dto.auth.RegisterRequest;
import com.power.surge.repository.UserRepository;
import com.power.surge.security.JwtTokenProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    /**
     * The password this project used to seed the first administrator with. No longer a default —
     * it is published in this repository's history, so it is now explicitly refused.
     */
    public static final String DEFAULT_BOOTSTRAP_PASSWORD = "admin";

    /** Matches the minimum enforced on every account created through the admin panel. */
    static final int MIN_BOOTSTRAP_PASSWORD_LENGTH = 8;

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

    /**
     * Creates the bootstrap administrator when it does not already exist.
     *
     * <p>This deliberately never touches an existing account. The previous implementation
     * re-encoded the password on every startup, which meant any credential change — including one
     * made through the admin flow — was silently reverted the next time the backend restarted.
     *
     * <p>Credentials come from configuration so they are not baked into the source tree. The
     * defaults exist only to keep a fresh local checkout usable, and are logged as a warning so an
     * unchanged default cannot go unnoticed in a deployed environment.
     */
    @Transactional
    public void seedBootstrapAdmin(String username, String email, String password) {
        if (userRepository.findByUsername(username).isPresent()) {
            log.info("Bootstrap administrator '{}' already exists; leaving its credentials untouched.", username);
            return;
        }
        requireUsableBootstrapPassword(password);
        userRepository.save(new User(username, email, passwordEncoder.encode(password), UserRole.ROLE_ADMIN));
        log.info("Created bootstrap administrator '{}'.", username);
    }

    /**
     * Refuses to create the first administrator without a real password.
     *
     * <p>This used to default to {@value #DEFAULT_BOOTSTRAP_PASSWORD} and merely log a warning. It
     * did not work: an instance seeded that way was briefly reachable from the internet with
     * administrator access, and the warning sat unread in container logs the whole time. A log line
     * cannot compete with a service that starts successfully.
     *
     * <p>The check runs only when an account is actually about to be created, so an existing
     * deployment keeps starting without configuration — the requirement lands on fresh databases,
     * which are the only ones at risk.
     */
    private void requireUsableBootstrapPassword(String password) {
        if (password == null || password.isBlank()) {
            throw new IllegalStateException(
                    "Refusing to create the bootstrap administrator without a password. Set "
                            + "SURGE_BOOTSTRAP_ADMIN_PASSWORD to a value of at least "
                            + MIN_BOOTSTRAP_PASSWORD_LENGTH + " characters. There is deliberately no default.");
        }
        if (DEFAULT_BOOTSTRAP_PASSWORD.equalsIgnoreCase(password)) {
            throw new IllegalStateException(
                    "SURGE_BOOTSTRAP_ADMIN_PASSWORD is set to the password this project used to default to. "
                            + "It is published in this repository's history — choose another.");
        }
        if (password.length() < MIN_BOOTSTRAP_PASSWORD_LENGTH) {
            throw new IllegalStateException(
                    "SURGE_BOOTSTRAP_ADMIN_PASSWORD must be at least " + MIN_BOOTSTRAP_PASSWORD_LENGTH
                            + " characters, matching the minimum enforced on every other account.");
        }
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

        // Checked after the password so a suspended account is not distinguishable from a wrong
        // password by response timing or message alone, and recorded so a locked-out colleague's
        // attempts are visible rather than mysterious.
        if (!user.isEnabled()) {
            auditLogService.recordAudit(user.getUsername(), "USER_LOGIN_DENIED", "USER",
                    user.getId().toString(), "Sign-in refused: account is suspended");
            throw new IllegalArgumentException("This account has been suspended. Contact an administrator.");
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
